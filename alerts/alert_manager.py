"""AlertManager: console / log file / webhook alerts + SIMULATED blocking."""

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
