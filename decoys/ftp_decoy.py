"""Minimal FTP decoy: logs USER/PASS attempts, always replies 530."""

from decoys.base_decoy import BaseDecoy


class FTPDecoy(BaseDecoy):
    DECOY_NAME = "ftp"

    def _handle(self, conn, addr):
        conn.sendall(b"220 corp-files FTP service ready\r\n")
        conn.settimeout(60)
        fobj = conn.makefile("rb")
        last_user = ""
        while True:
            line = fobj.readline()
            if not line:
                break
            cmd = line.decode("utf-8", errors="ignore").strip()
            if not cmd:
                continue
            parts = cmd.split(" ", 1)
            verb = parts[0].upper()
            arg = parts[1] if len(parts) > 1 else ""

            if verb == "USER":
                last_user = arg
                self.emit(addr, "auth_attempt", {"username": arg, "password": ""},
                          raw=cmd)
                conn.sendall(b"331 User name okay, need password\r\n")
            elif verb == "PASS":
                canary = bool(self.canaries and
                              self.canaries.is_canary_credential(last_user, arg))
                self.emit(addr, "auth_attempt",
                          {"username": last_user, "password": arg, "canary": canary},
                          raw=f"USER {last_user} / PASS {arg}")
                conn.sendall(b"530 Login incorrect.\r\n")
            elif verb == "SYST":
                conn.sendall(b"215 UNIX Type: L8\r\n")
            elif verb == "QUIT":
                conn.sendall(b"221 Goodbye.\r\n")
                break
            else:
                conn.sendall(b"502 Command not implemented.\r\n")
