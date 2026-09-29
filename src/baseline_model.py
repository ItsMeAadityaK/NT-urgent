"""
baseline_model.py

Traditional ML baseline — TF-IDF (unigrams + bigrams) + Logistic Regression.

Two jobs:
  1. A comparison point for the LLM classifier (classifier.py): does a
     lightweight, locally-trained model behave differently, especially on
     informal phrasing?
  2. A fallback that runs with no network. If the LLM is unavailable, the
     triage pipeline degrades to baseline + safety net instead of stopping.

Evaluation is done honestly with 5-fold stratified cross-validation: every
message gets a prediction from a model that never saw it during training
("out-of-fold" predictions). Those are the predictions the dashboard shows
for the dataset, so the LLM-vs-baseline comparison isn't flattered by the
baseline having memorised the very messages it's being judged on. A final
model fitted on everything is used only for brand-new text (the "Try a
message" tab).

class_weight="balanced" because the dataset is skewed toward low/medium
(deliberately — that's the haystack), and without it the model under-
predicts the rare critical class, which is the one that matters most.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

URGENCY_LEVELS = ["low", "medium", "high", "critical"]

# Tiny hardcoded fallback set — only used if this module is imported
# without ever calling train_baseline_from_dataset() (e.g. running this
# file directly). The app trains on the full dataset at startup.
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
    "floodwater entering the house, cant get out",
]
_TRAINING_LABELS = [
    "low", "low", "low", "low",
    "medium", "medium",
    "critical", "high",
    "critical", "critical",
]


def _new_pipeline():
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
        LogisticRegression(max_iter=2000, class_weight="balanced"),
    )


class BaselineUrgencyModel:
    """Wraps the TF-IDF vectorizer + classifier as one trainable unit."""

    def __init__(self):
        self.pipeline = _new_pipeline()
        self._is_trained = False

    def train(self, messages: list[str], labels: list[str]):
        self.pipeline.fit(messages, labels)
        self._is_trained = True

    def predict(self, message_text: str) -> dict:
        if not self._is_trained:
            raise RuntimeError("Model not trained yet — call .train() first.")
        probs = self.pipeline.predict_proba([message_text])[0]
        classes = list(self.pipeline.classes_)
        best = max(range(len(classes)), key=lambda i: probs[i])
        return {
            "urgency_score": classes[best],
            "confidence": float(probs[best]),
            "model_source": "baseline",
        }


# Module-level singleton so other files can just import and use it.
_baseline = BaselineUrgencyModel()
_baseline.train(_TRAINING_MESSAGES, _TRAINING_LABELS)


def classify_urgency_baseline(message_text: str) -> dict:
    """Same call shape as classifier.classify_urgency(), for easy comparison."""
    return _baseline.predict(message_text)


def train_baseline_from_dataset(messages: list[str], true_labels: list[str],
                                n_folds: int = 5, random_state: int = 42) -> dict:
    """
    Cross-validated evaluation, then a final fit for new text.

    Returns:
        dict: {"accuracy", "n_total", "n_folds",
               "oof_predictions": list[str] aligned with `messages`,
               "per_class_recall": {level: float},
               "misclassified": [{"text", "true_label", "predicted"}]}
    """
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    oof = list(cross_val_predict(_new_pipeline(), messages, true_labels, cv=cv))

    per_class_recall = {}
    for level in URGENCY_LEVELS:
        idx = [i for i, t in enumerate(true_labels) if t == level]
        if idx:
            per_class_recall[level] = sum(oof[i] == level for i in idx) / len(idx)

    misclassified = [
        {"text": t, "true_label": y, "predicted": p}
        for t, y, p in zip(messages, true_labels, oof) if y != p
    ]

    # Final fit on everything — used only for text the model has never seen.
    _baseline.train(messages, true_labels)

    return {
        "accuracy": accuracy_score(true_labels, oof),
        "n_total": len(messages),
        "n_folds": n_folds,
        "oof_predictions": oof,
        "per_class_recall": per_class_recall,
        "misclassified": misclassified,
    }


if __name__ == "__main__":
    for msg in [
        "when does my permit renew? just checking the date",
        "no water for 3 days, community cut off by flooding, elderly residents affected",
        "can u help my roof gone in the storm last nite got no where to stay",
    ]:
        print(f"\nMessage: {msg}\n  -> {classify_urgency_baseline(msg)}")
