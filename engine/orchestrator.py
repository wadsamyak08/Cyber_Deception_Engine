"""Orchestrator: decoys -> event bus -> rules + ML + brute-force -> alerts."""

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
