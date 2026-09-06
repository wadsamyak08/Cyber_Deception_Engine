# Demo Script (5 minutes)

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
