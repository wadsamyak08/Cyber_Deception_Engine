# Architecture

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
