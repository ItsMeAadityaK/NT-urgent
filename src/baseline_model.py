"""
baseline_model.py

Traditional ML baseline — TF-IDF + Logistic Regression.

This exists to compare against the LLM classifier (classifier.py) for
your report's "technical sophistication" section: does a lightweight,
locally-trained model perform differently to an LLM, especially on
dialect-varied or informal phrasing?

Unlike the LLM classifier, this one needs to be TRAINED on labelled
examples before it can predict anything. Right now it trains on a tiny
hardcoded set just to prove the pipeline works — you'll retrain it on
your real synthetic dataset once that exists.

Schema this function produces (matches data/messages.csv columns):
    urgency_score : one of "low", "medium", "high", "critical"
    model_source  : "baseline"
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

URGENCY_LEVELS = ["low", "medium", "high", "critical"]

# Tiny hardcoded fallback set — only used if this module is imported
# without ever calling train_baseline_from_dataset() (e.g. running this
# file directly, or an early test). The real app trains on the full
# 152-message synthetic dataset via train_baseline_from_dataset(), called
# from server.py at startup.
_TRAINING_MESSAGES = [
    "when does my permit renew",
    "just checking my application status",
    "what are your opening hours",
    "please update my mailing address",
    "leak in the bathroom, not urgent, whenever convenient",
    "power has been out for a few hours, generator on standby",
    "no water for 3 days, community cut off by flooding, elderly residents",
    "roof gone in the storm, no where to stay tonight",
    "child alone at home, no contact from parent since yesterday, worried",
    "fire near the community, evacuation may be needed",
]
_TRAINING_LABELS = [
    "low", "low", "low", "low",
    "medium", "medium",
    "critical", "high",
    "critical", "critical",
]


class BaselineUrgencyModel:
    """Wraps the TF-IDF vectorizer + classifier as one trainable unit."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.model = LogisticRegression(max_iter=1000)
        self._is_trained = False

    def train(self, messages: list[str], labels: list[str]):
        X = self.vectorizer.fit_transform(messages)
        self.model.fit(X, labels)
        self._is_trained = True

    def predict(self, message_text: str) -> dict:
        if not self._is_trained:
            raise RuntimeError("Model not trained yet — call .train() first.")

        X = self.vectorizer.transform([message_text])
        prediction = self.model.predict(X)[0]

        return {
            "urgency_score": prediction,
            "model_source": "baseline",
        }


# Module-level singleton so other files can just import and use it
# without worrying about training it themselves.
_baseline = BaselineUrgencyModel()
_baseline.train(_TRAINING_MESSAGES, _TRAINING_LABELS)


def classify_urgency_baseline(message_text: str) -> dict:
    """Same call shape as classifier.classify_urgency(), for easy comparison."""
    return _baseline.predict(message_text)


def train_baseline_from_dataset(messages: list[str], true_labels: list[str],
                                 test_size: float = 0.2, random_state: int = 42) -> dict:
    """
    Proper train/test evaluation, then a final production fit.

    Step 1: split the real dataset, train ONLY on the train split, and
    measure accuracy against true_labels on the held-out test split —
    this is what "the baseline is X% accurate" should actually mean,
    rather than just eyeballing agreement with the LLM.

    Step 2: once that honest number is captured, refit the module-level
    singleton (used by classify_urgency_baseline everywhere else in the
    app) on the FULL dataset, so the live predictions shown in the
    dashboard benefit from every labelled example, not just 80% of them.

    Returns:
        dict: {"accuracy": float, "n_train": int, "n_test": int,
               "n_total": int, "misclassified": list of
               {"text", "true_label", "predicted"} for the test-split
               errors — useful for the report's error-analysis section}
    """
    X_train, X_test, y_train, y_test = train_test_split(
        messages, true_labels, test_size=test_size, random_state=random_state,
        stratify=true_labels,
    )

    eval_model = BaselineUrgencyModel()
    eval_model.train(X_train, y_train)

    predictions = [eval_model.predict(text)["urgency_score"] for text in X_test]
    accuracy = accuracy_score(y_test, predictions)

    misclassified = [
        {"text": text, "true_label": true, "predicted": pred}
        for text, true, pred in zip(X_test, y_test, predictions)
        if true != pred
    ]

    # Final production fit on everything, for live use in the app.
    _baseline.train(messages, true_labels)

    return {
        "accuracy": accuracy,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "n_total": len(messages),
        "misclassified": misclassified,
    }


if __name__ == "__main__":
    # Same test messages as classifier.py, so you can directly compare output.
    test_messages = [
        "when does my permit renew? just checking the date",
        "no water for 3 days, community cut off by flooding, elderly residents affected",
        "can u help my roof gone in the storm last nite got no where to stay",
    ]

    for msg in test_messages:
        result = classify_urgency_baseline(msg)
        print(f"\nMessage: {msg}")
        print(f"  -> {result}")