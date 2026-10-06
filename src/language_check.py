"""
language_check.py

Can this system actually READ the message?

Why this exists: every layer of the triage (the AI, the trained model, the danger-phrase
rules) works on English. A message written in Kriol or a traditional Aboriginal language
looks like noise to all three, and "noise" would normally come out as LOW priority:
the exact way a vulnerable person's message gets buried. So when the text is mostly
words the system doesn't know, it is never allowed to rank low. It is raised to HIGH with
the flag "language not recognised", routed to an interpreter/community-liaison desk, and
a person reads it in full.

How it decides, in plain terms (no AI, fully explainable):
  - Real English, even badly spelt, is full of known words and the little connecting words
    (the, is, and, my). Typos still count as known because they are close to a known word.
  - Text in another language has almost none of either.
Both signals must be low before anything is flagged, so a typo-ridden English message is not.

It only ever RAISES a priority, never lowers one, and it cannot tell WHICH language it is
looking at. It is a safety net for text the system can't read, not a translator.
Known limits: very short messages (under 2 words) are not judged, and a creole that uses
many English-looking words (Kriol) may partly read as English. Those need real speakers
to test, which is what data/community_phrases.json and scripts/language_parity.py are for.
"""

import difflib
import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

_WORD = re.compile(r"[a-z]+")
# SMS shorthand and contractions-without-apostrophes that are English, not "another language".
_SMS = {"u", "ur", "r", "pls", "plz", "thx", "msg", "ppl", "abt", "bcz", "b4", "yo", "hrs", "hr", "arvo",
        "cant", "dont", "wont", "didnt", "isnt", "im", "ive", "hes", "shes", "thats", "whats", "wasnt",
        "couldnt", "wouldnt", "havent", "hasnt", "weve", "theyre", "youre", "ok", "nite", "tmrw"}

MIN_KNOWN_RATIO = 0.35   # below this share of recognised words...
MAX_STOP_RATIO = 0.15    # ...and below this share of little English words, the text is unreadable.

_checker = None


class _Checker:
    def __init__(self, texts):
        self.vocab = set()
        for text in texts:
            self.vocab.update(w for w in _WORD.findall(text.lower()) if len(w) >= 2)
        self.by_first = {}
        for w in self.vocab:
            if len(w) >= 4:
                self.by_first.setdefault(w[0], []).append(w)

    def known(self, word: str) -> bool:
        if word in self.vocab or word in ENGLISH_STOP_WORDS or word in _SMS:
            return True
        if len(word) >= 4:  # a typo of a known word still counts as known
            for cand in self.by_first.get(word[0], []):
                if abs(len(cand) - len(word)) <= 2 and difflib.SequenceMatcher(None, word, cand).ratio() >= 0.8:
                    return True
        return False

    def check(self, text: str) -> dict:
        tokens = [w for w in _WORD.findall((text or "").lower()) if len(w) >= 2]
        if len(tokens) < 2:
            return {"readable": True, "reason": "", "known_ratio": 1.0, "stop_ratio": 1.0, "words": len(tokens)}
        known = sum(self.known(w) for w in tokens) / len(tokens)
        stop = sum(w in ENGLISH_STOP_WORDS or w in _SMS for w in tokens) / len(tokens)
        unreadable = known < MIN_KNOWN_RATIO and stop < MAX_STOP_RATIO
        reason = ""
        if unreadable:
            reason = (f"Language not recognised: only {known:.0%} of the words match anything this system knows and "
                      f"the common little words of English (the, is, and, my) are almost absent. It may be written in "
                      f"another language, or be too garbled to read.")
        return {"readable": not unreadable, "reason": reason, "known_ratio": known, "stop_ratio": stop,
                "words": len(tokens)}


def configure(texts):
    """Teach the checker what ordinary messages look like. Called once at startup."""
    global _checker
    _checker = _Checker(texts)


def disable():
    global _checker
    _checker = None


def check_readable(text: str) -> dict:
    """Disabled (always readable) until configure() has been called."""
    if _checker is None:
        return {"readable": True, "reason": "", "known_ratio": 1.0, "stop_ratio": 1.0, "words": 0}
    return _checker.check(text)
