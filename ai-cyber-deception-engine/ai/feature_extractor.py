"""Converts raw decoy events into fixed-length numeric feature vectors.
The same code path is used at training and at inference time (no skew)."""

import math
from collections import Counter
from datetime import datetime
from urllib.parse import unquote_plus

DECOY_VOCAB = ["ssh", "http", "ftp", "telnet", "mysql"]
EVENT_TYPE_VOCAB = ["connection", "auth_attempt", "command",
                    "http_request", "http_login", "file_access"]

COMMON_USERNAMES = {"root", "admin", "administrator", "user", "test", "guest",
                    "ubuntu", "pi", "oracle", "postgres", "anonymous", "ftp"}

SQLI_PATTERNS = ["'", "%27", "--", " or ", "union select", "1=1",
                 "drop table", "insert into", "sleep(", "benchmark("]
TRAVERSAL_PATTERNS = ["../", "..\\", "/etc/passwd", "/etc/shadow",
                      "win.ini", "boot.ini", "%2e%2e"]
INTERESTING_CMDS = ["wget", "curl ", "chmod", "chown", "/etc/shadow",
                    "ifconfig", "crontab", "history", "nc -", "bash -i",
                    "python -c", "id_rsa", ".ssh"]

NUMERIC_FEATURES = ["payload_len", "payload_entropy", "has_sqli",
                    "has_traversal", "has_suspect_command",
                    "common_username", "hour_frac"]


def shannon_entropy(s):
    if not s:
        return 0.0
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in Counter(s).values())


def payload_text(event):
    """Flatten an event into one lowercase string (URL-decoded twice)."""
    parts = [str(event.get("raw", "") or "")]
    for k, v in (event.get("data") or {}).items():
        parts.append(f"{k}={v}")
    text = " ".join(parts).lower()
    text = unquote_plus(unquote_plus(text))
    return text


def extract_features(event):
    data = event.get("data") or {}
    text = payload_text(event)
    ts = event.get("timestamp", "") or ""
    try:
        hour = datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
    except ValueError:
        hour = datetime.utcnow().hour
    return {
        "decoy": event.get("decoy", ""),
        "event_type": event.get("event_type", ""),
        "payload_len": min(len(text), 2000),
        "payload_entropy": round(shannon_entropy(text), 4),
        "has_sqli": int(any(p in text for p in SQLI_PATTERNS)),
        "has_traversal": int(any(p in text for p in TRAVERSAL_PATTERNS)),
        "has_suspect_command": int(any(c in text for c in INTERESTING_CMDS)),
        "common_username": int(str(data.get("username", "")).lower()
                               in COMMON_USERNAMES),
        "hour_frac": hour / 24.0,
    }


def feature_names():
    names = [f"decoy={d}" for d in DECOY_VOCAB]
    names += [f"event_type={e}" for e in EVENT_TYPE_VOCAB]
    names += NUMERIC_FEATURES
    return names


def vectorize(feat):
    vec = [1 if feat["decoy"] == d else 0 for d in DECOY_VOCAB]
    vec += [1 if feat["event_type"] == e else 0 for e in EVENT_TYPE_VOCAB]
    vec += [feat["payload_len"], feat["payload_entropy"], feat["has_sqli"],
            feat["has_traversal"], feat["has_suspect_command"],
            feat["common_username"], feat["hour_frac"]]
    return vec
