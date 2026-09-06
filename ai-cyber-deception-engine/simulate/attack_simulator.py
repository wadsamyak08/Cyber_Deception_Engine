"""SAFE, fully local simulated attack campaign used to demo the engine.
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
