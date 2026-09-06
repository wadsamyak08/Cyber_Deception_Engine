"""Telnet/IoT decoy: classic login prompt capturing credential stuffing."""

import socket

from decoys.base_decoy import BaseDecoy


class TelnetDecoy(BaseDecoy):
    DECOY_NAME = "telnet"

    def _handle(self, conn, addr):
        conn.sendall(b"Welcome to CorpRouter v2.4 (build 118)\r\n"
                     b"Unauthorized access is prohibited.\r\n\r\nlogin: ")
        user = self._read_line(conn) or ""
        conn.sendall(b"Password: ")
        pwd = self._read_line(conn) or ""
        canary = bool(self.canaries and self.canaries.is_canary_credential(user, pwd))
        self.emit(addr, "auth_attempt",
                  {"username": user, "password": pwd, "canary": canary},
                  raw=f"telnet login {user}:{pwd}")
        conn.sendall(b"\r\nLogin incorrect\r\n\r\n")

    def _read_line(self, conn, limit=128):
        conn.settimeout(30)
        buf = b""
        try:
            while len(buf) < limit:
                byte = conn.recv(1)
                if not byte or byte in (b"\r", b"\n"):
                    break
                if byte[0] < 32 or byte[0] > 126:
                    continue
                buf += byte
        except (socket.timeout, OSError):
            pass
        return buf.decode("ascii", errors="ignore")
