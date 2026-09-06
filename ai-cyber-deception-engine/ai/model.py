"""Random-Forest threat classifier wrapper (train/save/load/predict)."""

import os

import joblib


class ThreatClassifier:
    def __init__(self, model=None, classes=None, feature_names=None):
        self.model = model
        self.classes = classes or []
        self.feature_names = feature_names or []

    def train(self, X, y, n_estimators=200, seed=42):
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=seed, stratify=y)
        clf = RandomForestClassifier(n_estimators=n_estimators,
                                     random_state=seed, n_jobs=-1)
        clf.fit(X_train, y_train)
        report = classification_report(y_test, clf.predict(X_test), digits=3)
        self.model = clf
        self.classes = [str(c) for c in clf.classes_]
        return report

    def predict(self, X):
        """Returns a list of (label, confidence) tuples."""
        results = []
        for row in self.model.predict_proba(X):
            idx = int(row.argmax())
            results.append((self.classes[idx], float(row[idx])))
        return results

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump({"model": self.model, "classes": self.classes,
                     "feature_names": self.feature_names}, path)

    @classmethod
    def load(cls, path):
        if not os.path.exists(path):
            return None
        blob = joblib.load(path)
        return cls(blob["model"], blob["classes"], blob["feature_names"])
