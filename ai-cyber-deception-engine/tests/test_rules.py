from engine.rules import evaluate_rules
from tokens.canary_manager import CanaryManager


def _event(**data):
    return {"timestamp": "2024-01-01T10:00:00Z", "source_ip": "9.9.9.9",
            "source_port": 4, "decoy": "ssh",
            "event_type": "auth_attempt", "data": data, "raw": ""}


def test_canary_credentials_are_critical():
    canaries = CanaryManager({})
    u, p = canaries.pairs[0]
    verdict = evaluate_rules(_event(username=u, password=p), canaries)
    assert verdict["label"] == "malicious"
    assert verdict["severity"] == 5


def test_common_username_is_suspicious():
    verdict = evaluate_rules(_event(username="root", password="toor"),
                             CanaryManager({}))
    assert verdict["label"] == "suspicious"


def test_benign_health_check_raises_nothing():
    ev = {"timestamp": "2024-01-01T10:00:00Z", "source_ip": "127.0.0.1",
          "source_port": 1, "decoy": "mysql", "event_type": "connection",
          "data": {"note": "internal health check"}, "raw": ""}
    assert evaluate_rules(ev, CanaryManager({})) is None
