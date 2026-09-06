from ai.feature_extractor import (extract_features, feature_names,
                                  shannon_entropy, vectorize)


def test_entropy_zero_for_uniform_string():
    assert shannon_entropy("aaaa") == 0.0


def test_sqli_pattern_detected():
    event = {"timestamp": "2024-01-01T10:00:00Z", "source_ip": "1.2.3.4",
             "source_port": 5, "decoy": "http", "event_type": "http_request",
             "data": {"path": "/admin?id=1' OR '1'='1"},
             "raw": "GET /admin?id=1' OR '1'='1"}
    assert extract_features(event)["has_sqli"] == 1


def test_vector_length_matches_feature_names():
    event = {"timestamp": "2024-01-01T10:00:00Z", "source_ip": "1.2.3.4",
             "source_port": 5, "decoy": "ssh", "event_type": "auth_attempt",
             "data": {"username": "root"}, "raw": ""}
    assert len(vectorize(extract_features(event))) == len(feature_names())
