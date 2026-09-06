"""Low-interaction SSH decoy.

With paramiko: password logins all fail EXCEPT canary credentials, which
'succeed' and drop the attacker into a fake shell that logs every command.
Without paramiko: banner-grab honeypot only.
"""

import time

try:
    import paramiko
    HAVE_PARAMIKO = True
except ImportError:
    HAVE_PARAMIKO = False

from decoys.base_decoy import BaseDecoy


class SSHDecoy(BaseDecoy):
    DECOY_NAME = "ssh"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hostname = self.config.get("hostname", "prod-web-01")
        if HAVE_PARAMIKO:
            self.host_key = paramiko.RSAKey.generate(2048)
        else:
            self.host_key = None
            self.logger.warning("paramiko missing - SSH decoy in banner-only mode")

    def run(self):
        self._serve_tcp(self._handle_ssh if HAVE_PARAMIKO else self._handle_banner_only)

    def _handle_banner_only(self, conn, addr):
        try:
            conn.sendall((self.config.get("banner", "SSH-2.0-OpenSSH_8.2p1")
                          + "\r\n").encode())
            conn.settimeout(15)
            data = conn.recv(512)
            if data:
                snippet = data[:120].decode("utf-8", errors="ignore")
                self.emit(addr, "banner_grab", {"client_banner": snippet}, raw=snippet)
        except OSError:
            pass

    def _handle_ssh(self, sock, addr):
        try:
            transport = paramiko.Transport(sock)
            transport.local_version = self.config.get("banner", "SSH-2.0-OpenSSH_8.2p1")
            transport.add_server_key(self.host_key)
            server = self._HoneyServer(self, addr)
            transport.start_server(server=server)
            chan = transport.accept(timeout=60)
            if chan is None:
                transport.close()
                return
            time.sleep(0.7)
            if server.exec_command:
                chan.send(self._canned_response(server.exec_command) + "\r\n")
            elif server.authenticated:
                self._fake_shell(chan, addr)
            transport.close()
        except Exception as exc:
            self.logger.debug("ssh session error: %s", exc)

    class _HoneyServer(paramiko.ServerInterface):
        def __init__(self, decoy, addr):
            self.decoy, self.addr = decoy, addr
            self.authenticated = False
            self.exec_command = None

        def get_allowed_auths(self, username):
            return "password"

        def check_auth_password(self, username, password):
            canary = bool(self.decoy.canaries and
                          self.decoy.canaries.is_canary_credential(username, password))
            self.decoy.emit(self.addr, "auth_attempt",
                            {"username": username, "password": password,
                             "canary": canary},
                            raw=f"ssh auth {username}:{password}")
            if canary:
                self.authenticated = True
                return paramiko.AUTH_SUCCESSFUL
            return paramiko.AUTH_FAILED

        def check_channel_request(self, kind, chanid):
            return paramiko.OPEN_SUCCEEDED

        def check_channel_pty_request(self, channel, term, width, height,
                                      pixelwidth, pixelheight, modes):
            return True

        def check_channel_shell_request(self, channel):
            return True

        def check_channel_exec_request(self, channel, command):
            self.exec_command = command.decode("utf-8", errors="ignore")
            self.decoy.emit(self.addr, "command", {"command": self.exec_command},
                            raw=self.exec_command)
            return True

    def _fake_shell(self, chan, addr):
        prompt = f"svc_backup@{self.hostname}:~$ "
        try:
            chan.send("Welcome to Ubuntu 20.04.5 LTS (GNU/Linux 5.4.0-169-generic x86_64)"
                      "\r\n\r\nLast login: Mon Jun  3 09:14:22 2024 from 10.20.30.2\r\n")
            chan.send(prompt)
            buf, commands = "", 0
            while commands < 8 and not self._stop_event.is_set():
                data = chan.recv(1024)
                if not data:
                    break
                for ch in data.decode("utf-8", errors="ignore"):
                    if ch in ("\r", "\n"):
                        cmd, buf = buf.strip(), ""
                        chan.send("\r\n")
                        if cmd:
                            commands += 1
                            self.emit(addr, "command", {"command": cmd}, raw=cmd)
                            chan.send(self._canned_response(cmd) + "\r\n")
                        chan.send(prompt)
                        if cmd in ("exit", "logout"):
                            return
                    elif ch == "\x7f":
                        if buf:
                            buf = buf[:-1]
                            chan.send("\b \b")
                    elif ch >= " ":
                        buf += ch
                        chan.send(ch)
        except Exception as exc:
            self.logger.debug("shell error: %s", exc)

    def _canned_response(self, cmd):
        c = cmd.strip().lower()
        if c == "whoami":
            return "svc_backup"
        if c.startswith("uname"):
            return "Linux prod-web-01 5.4.0-169-generic #187-Ubuntu SMP x86_64 GNU/Linux"
        if c == "ls":
            return "app  backup  deploy  logs  notes.txt"
        if c.startswith("cat /etc/passwd"):
            return ("root:x:0:0:root:/root:/bin/bash\n"
                    "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
                    "svc_backup:x:1002:1002::/home/svc_backup:/bin/bash")
        if c.startswith("cat /etc/shadow"):
            return "cat: /etc/shadow: Permission denied"
        if c.startswith("cat "):
            return f"cat: {cmd[4:].strip()}: No such file or directory"
        if c.startswith("ifconfig") or c.startswith("ip a"):
            return "eth0: inet 10.20.30.15  netmask 255.255.255.0"
        if c in ("exit", "logout"):
            return "logout"
        return f"bash: {cmd}: command not found"
