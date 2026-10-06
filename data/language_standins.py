"""
language_standins.py

STAND-INS, NOT A REAL LANGUAGE.

We do not write Kriol or any Aboriginal language: it can't be done accurately by us, and
inventing it would be disrespectful. What we CAN test honestly is the property that matters:
what does this system do with text it cannot read?

standin() scrambles English with a fixed letter-swap so the result looks like some other
language to the system but is obviously invented. Each English original has a known true
urgency, so we can check that the unreadable version is never ranked below it by accident.

When real phrases arrive (see data/community_phrases.json, written or reviewed by a speaker
or interpreter, each with its English meaning), they go through exactly the same test:
scripts/language_parity.py.
"""

_VOWELS_IN, _VOWELS_OUT = "aeiou", "oueai"
_CONS = "bcdfghjklmnpqrstvwxyz"
_CONS_OUT = _CONS[7:] + _CONS[:7]
_TABLE = str.maketrans(_VOWELS_IN + _CONS, _VOWELS_OUT + _CONS_OUT)


def standin(english: str) -> str:
    """Invented letter-swap. Digits, spaces and punctuation are kept."""
    return english.lower().translate(_TABLE)


# (English original, true urgency). Four of each level, written fresh (not from the training data).
PAIRS = [
    ("my aunty collapsed and wont wake up, we cant get an ambulance, the road is flooded", "critical"),
    ("water is coming into the house fast and i have the kids, we cant get out", "critical"),
    ("he said he will hurt me tonight, i need somewhere safe for me and the kids", "critical"),
    ("a little kid has been home alone since this morning and the mum wont answer her phone", "critical"),
    ("the wind took our roof off last night and we have nowhere dry to sleep with two kids", "high"),
    ("power has been out since yesterday and my dads insulin is in the fridge getting warm", "high"),
    ("i cant get hold of my nan since yesterday, she is 84 and lives alone", "high"),
    ("the road to the clinic is under water and mum is nearly out of her heart tablets", "high"),
    ("i rang three times this week about my pension being short and nobody has called back", "medium"),
    ("our rubbish has not been collected for two weeks and it is starting to pile up", "medium"),
    ("the internet has been down for two days and i cant do my income report online", "medium"),
    ("there is a big pothole on our street and a car nearly lost control this morning", "medium"),
    ("hi, when does my permit need to be renewed, no rush at all", "low"),
    ("i just wanted to say thanks to the lady who helped me last week, she was very patient", "low"),
    ("could i please get a receipt for the payment i made last week", "low"),
    ("what time is the office open on saturday morning", "low"),
]
