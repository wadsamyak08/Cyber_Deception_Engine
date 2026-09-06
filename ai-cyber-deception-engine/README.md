# AI Cyber Deception Engine (Desktop App)

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
