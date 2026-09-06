#!/usr/bin/env python3
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
