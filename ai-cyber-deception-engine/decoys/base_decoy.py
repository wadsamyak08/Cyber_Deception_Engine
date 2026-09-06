"""Base class for all decoy services: TCP server + event emission."""

import logging
import socket
import threading
from datetime import datetime, timezone


class BaseDecoy(threading.Thread):
    DECOY_NAME = "base"

    def __init__(self, host, port, event_bus, config=None, canaries=None):
        super().__init__(daemon=True, name=f"decoy-{self.DECOY_NAME}")
        self.host = host
        self.port = int(port)
        self.event_bus = event_bus
        self.config = config or {}
        self.canaries = canaries
        self.logger = logging.getLogger(f"decoy.{self.DECOY_NAME}")
        self._stop_event = threading.Event()

    def emit(self, addr, event_type, data=None, raw=""):
        try:
            self.event_bus.publish({
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_ip": addr[0] if addr else "unknown",
                "source_port": int(addr[1]) if addr and len(addr) > 1 else 0,
                "decoy": self.DECOY_NAME,
                "event_type": event_type,
                "data": data or {},
                "raw": str(raw)[:2000],
            })
        except Exception:
            self.logger.exception("failed to publish event")

    def run(self):
        self._serve_tcp(self._handle)

    def _handle(self, conn, addr):
        raise NotImplementedError

    def stop(self):
        self._stop_event.set()

    def _serve_tcp(self, handler):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.host, self.port))
            sock.listen(16)
            self.logger.info("%s decoy listening on %s:%d",
                             self.DECOY_NAME, self.host, self.port)
            sock.settimeout(1.0)
            while not self._stop_event.is_set():
                try:
                    conn, addr = sock.accept()
                except socket.timeout:
                    continue
                threading.Thread(target=self._safe, args=(handler, conn, addr),
                                 daemon=True).start()
        except OSError as exc:
            self.logger.error("could not bind %s:%d (%s)", self.host, self.port, exc)
        finally:
            sock.close()

    def _safe(self, handler, conn, addr):
        try:
            handler(conn, addr)
        except Exception as exc:
            self.logger.debug("handler error: %s", exc)
        finally:
            try:
                conn.close()
            except OSError:
                pass
