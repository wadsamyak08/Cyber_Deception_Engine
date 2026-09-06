"""Deterministic rules engine: canary use, SQLi, traversal, brute signals."""

from ai.feature_extractor import (SQLI_PATTERNS, TRAVERSAL_PATTERNS,
                                  INTERESTING_CMDS, COMMON_USERNAMES,
                                  payload_text)

AUTH_EVENTS = ("http_request", "http_login", "auth_attempt")


def evaluate_rules(event, canaries=None):
    """Return a verdict dict, or None when no rule fires."""
    data = event.get("data") or {}
    text = payload_text(event)

    if data.get("canary") or (
        canaries and data.get("username") and
        canaries.is_canary_credential(data.get("username", ""),
                                      data.get("password", ""))
    ):
        return {"label": "malicious", "severity": 5, "score": 1.0,
                "reason": "Canary credential used - confirmed unauthorized activity"}

    if data.get("username") and canaries and canaries.is_canary_username(data["username"]):
        return {"label": "malicious", "severity": 5, "score": 1.0,
                "reason": "Canary username attempted on decoy"}

    if data.get("canary_file"):
        return {"label": "malicious", "severity": 4, "score": 1.0,
                "reason": "Canary decoy file accessed - attacker looting fake secrets"}

    if any(p in text for p in SQLI_PATTERNS) and event.get("event_type") in AUTH_EVENTS:
        return {"label": "malicious", "severity": 4, "score": 1.0,
                "reason": "SQL injection pattern detected in request"}

    if any(p in text for p in TRAVERSAL_PATTERNS):
        return {"label": "malicious", "severity": 4, "score": 1.0,
                "reason": "Path traversal / sensitive file access attempt"}

    if event.get("event_type") == "command" and any(c in text for c in INTERESTING_CMDS):
        return {"label": "malicious", "severity": 4, "score": 1.0,
                "reason": "Suspicious command executed on decoy host"}

    if event.get("event_type") == "auth_attempt" and \
            str(data.get("username", "")).lower() in COMMON_USERNAMES:
        return {"label": "suspicious", "severity": 2, "score": 1.0,
                "reason": "Authentication attempt with default/common username"}

    return None
