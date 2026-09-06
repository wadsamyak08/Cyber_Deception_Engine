"""Train the AI threat classification model."""

import os

from ai.data_generator import generate_dataset
from ai.feature_extractor import extract_features, feature_names, vectorize
from ai.model import ThreatClassifier


def train_model(config, n_samples=6000):
    model_path = config.get("model", {}).get("path", "models/threat_model.joblib")
    report_path = config.get("model", {}).get("report_path",
                                              "models/training_report.txt")

    print(f"[*] Generating {n_samples} synthetic labelled events ...")
    events, labels = generate_dataset(n_samples)

    print("[*] Extracting features ...")
    X = [vectorize(extract_features(e)) for e in events]

    clf = ThreatClassifier(feature_names=feature_names())
    print("[*] Training Random Forest classifier ...")
    report = clf.train(X, labels)
    print(report)

    clf.save(model_path)
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("AI Cyber Deception Engine - Model Training Report\n")
        fh.write("=" * 60 + "\n")
        fh.write(f"samples: {n_samples}\n")
        fh.write(f"features: {len(feature_names())}\n")
        fh.write("algorithm: sklearn RandomForestClassifier (200 trees)\n\n")
        fh.write(report)

    print(f"[+] Model saved to   {model_path}")
    print(f"[+] Report saved to  {report_path}")
    return clf


if __name__ == "__main__":
    import yaml
    with open("config/config.yaml", encoding="utf-8") as fh:
        train_model(yaml.safe_load(fh))
