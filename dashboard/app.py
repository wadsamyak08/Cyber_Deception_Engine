"""Flask dashboard: live events, alerts, stats, blocklist + an endpoint that
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
