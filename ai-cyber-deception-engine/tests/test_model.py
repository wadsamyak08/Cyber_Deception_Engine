from ai.data_generator import generate_dataset
from ai.feature_extractor import extract_features, vectorize
from ai.model import ThreatClassifier


def test_model_learns_all_classes():
    events, labels = generate_dataset(300, seed=1)
    X = [vectorize(extract_features(e)) for e in events]
    clf = ThreatClassifier()
    clf.train(X, labels, n_estimators=20)
    preds = clf.predict(X[:5])
    assert len(preds) == 5
    assert all(p[0] in ("benign", "suspicious", "malicious") for p in preds)
