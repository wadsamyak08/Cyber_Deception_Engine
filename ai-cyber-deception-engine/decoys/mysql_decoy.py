"""MySQL decoy: realistic handshake banner; logs every connection."""

import socket

from decoys.base_decoy import BaseDecoy


class MySQLDecoy(BaseDecoy):
    DECOY_NAME = "mysql"
    VERSION = b"8.0.32"

    def _handle(self, conn, addr):
        self.emit(addr, "connection",
                  {"note": "TCP connection to decoy MySQL service"})
        try:
            conn.sendall(self._greeting())
            conn.settimeout(5)
            data = conn.recv(512)
            if data:
                self.emit(addr, "connection",
                          {"note": "client handshake data",
                           "hex": data[:64].hex()},
                          raw=data[:64].hex())
        except (socket.timeout, OSError):
            pass

    def _greeting(self):
        salt = b"abcdef123456"
        payload = (b"\x0a" + self.VERSION + b"\x00"
                   + b"\x2a\x00\x00\x00"
                   + salt + b"\x00"
                   + b"\xff\xf7\x08\x02\x00"
                   + b"\x0f\x80\x15\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                   + b"mysql_native_password\x00")
        return len(payload).to_bytes(3, "little") + b"\x01" + payload
