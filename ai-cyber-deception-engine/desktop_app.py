#!/usr/bin/env python3
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
