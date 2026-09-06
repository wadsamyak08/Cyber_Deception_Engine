"""Thread-safe SQLite storage for events, alerts and the blocklist."""

import json
import os
import sqlite3
import threading

EVENT_COLS = ["id", "timestamp", "source_ip", "source_port",
              "decoy", "event_type", "data", "raw"]
ALERT_COLS = ["id", "timestamp", "event_id", "source_ip", "decoy",
              "severity", "label", "reason", "score", "blocked"]


class Database:
    def __init__(self, path="data/deception.db"):
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def _init_schema(self):
        with self._lock:
            conn = self._connect()
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source_ip TEXT,
                    source_port INTEGER,
                    decoy TEXT,
                    event_type TEXT,
                    data TEXT,
                    raw TEXT
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_id INTEGER,
                    source_ip TEXT,
                    decoy TEXT,
                    severity INTEGER,
                    label TEXT,
                    reason TEXT,
                    score REAL,
                    blocked INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS blocklist (
                    ip TEXT PRIMARY KEY,
                    reason TEXT,
                    timestamp TEXT
                );
                """
            )
            conn.commit()
            conn.close()

    def insert_event(self, event):
        with self._lock:
            conn = self._connect()
            cur = conn.execute(
                "INSERT INTO events (timestamp, source_ip, source_port, decoy, "
                "event_type, data, raw) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event.get("timestamp"), event.get("source_ip"),
                 int(event.get("source_port") or 0), event.get("decoy"),
                 event.get("event_type"),
                 json.dumps(event.get("data") or {}), event.get("raw", "")),
            )
            conn.commit()
            row_id = cur.lastrowid
            conn.close()
            return row_id

    def insert_alert(self, alert):
        with self._lock:
            conn = self._connect()
            cur = conn.execute(
                "INSERT INTO alerts (timestamp, event_id, source_ip, decoy, "
                "severity, label, reason, score, blocked) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (alert.get("timestamp"), alert.get("event_id"),
                 alert.get("source_ip"), alert.get("decoy"),
                 alert.get("severity"), alert.get("label"),
                 alert.get("reason"), alert.get("score", 0.0),
                 int(alert.get("blocked", 0))),
            )
            conn.commit()
            row_id = cur.lastrowid
            conn.close()
            return row_id

    def add_block(self, ip, reason):
        with self._lock:
            conn = self._connect()
            conn.execute(
                "INSERT OR REPLACE INTO blocklist (ip, reason, timestamp) "
                "VALUES (?, ?, datetime('now'))",
                (ip, reason),
            )
            conn.commit()
            conn.close()

    def get_events(self, limit=100):
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            conn.close()
        out = []
        for r in rows:
            d = dict(zip(EVENT_COLS, r))
            d["data"] = json.loads(d["data"] or "{}")
            out.append(d)
        return out

    def get_alerts(self, limit=100):
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            conn.close()
        return [dict(zip(ALERT_COLS, r)) for r in rows]

    def get_blocklist(self):
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT ip, reason, timestamp FROM blocklist ORDER BY timestamp DESC"
            ).fetchall()
            conn.close()
        return [{"ip": r[0], "reason": r[1], "timestamp": r[2]} for r in rows]

    def get_stats(self):
        with self._lock:
            conn = self._connect()
            stats = {
                "total_events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
                "total_alerts": conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0],
                "critical_alerts": conn.execute(
                    "SELECT COUNT(*) FROM alerts WHERE severity >= 4").fetchone()[0],
                "blocked_ips": conn.execute("SELECT COUNT(*) FROM blocklist").fetchone()[0],
                "alerts_by_severity": dict(conn.execute(
                    "SELECT severity, COUNT(*) FROM alerts GROUP BY severity").fetchall()),
                "events_by_decoy": dict(conn.execute(
                    "SELECT decoy, COUNT(*) FROM events GROUP BY decoy").fetchall()),
                "top_sources": [
                    {"ip": r[0], "count": r[1]} for r in conn.execute(
                        "SELECT source_ip, COUNT(*) FROM events "
                        "GROUP BY source_ip ORDER BY COUNT(*) DESC LIMIT 5")],
            }
            conn.close()
            return stats
