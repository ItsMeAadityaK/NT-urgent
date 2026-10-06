"""
routing.py

Routes each item to the team that should own it.

Rules are ordered most-serious first and the first match wins, so a
message mentioning both a threat of harm and a power outage goes to the
duty officer, not the utilities desk. Routing is keyword-based on
purpose: it's instant, runs offline, and every decision can be explained
as "matched the word X" — an officer can see exactly why an item landed
in their queue and re-route it if the rule was wrong.

Regardless of team, anything that ends up CRITICAL is also copied to the
Duty Officer (see route_message) — the team owns the follow-up, but a
named human owns the first response.
"""

import re

ROUTES = [
    ("Personal safety", "Duty Officer \u2014 safety response", [
        r"hurt me", r"hit me", r"(don'?t|do not|does not|doesn'?t|not) feel safe", r"somewhere safe for",
        r"need somewhere safe", r"threat", r"violen", r"suicid", r"kill (me|myself|us)",
    ]),
    ("Medical / health", "Health liaison", [
        r"clinic", r"ambulance", r"dialysis", r"insulin", r"medication", r"oxygen", r"\blabou?r\b",
        r"\bsick\b", r"(aunty|auntie|he|she|mum|dad|father|mother|someone|nan|pop)\b[^.]{0,20}collapsed",
        r"pharmacy", r"medical", r"diabetic", r"hospital",
    ]),
    ("Welfare check", "Community welfare", [
        r"heard from", r"reach (him|her|them|my)", r"no contact", r"not answering", r"no answer",
        r"come home", r"living alone|lives alone", r"on (their|his|her) own", r"wheelchair",
    ]),
    ("Acute hazard", "Infrastructure & hazards", [
        r"\bgas\b", r"sparking", r"power ?line", r"live wiring", r"electrics",
    ]),
    ("Housing / shelter", "Housing", [
        r"nowhere (dry )?to (stay|sleep)", r"no ?where to stay", r"(alternative|emergency) shelter",
        r"nowhere else to go",
    ]),
    ("Financial hardship", "Hardship & payments", [
        r"lost my job", r"no savings|savings left", r"cover basics", r"how (we'?re|were|we are) eating",
    ]),
    ("Flood & evacuation", "Emergency operations", [
        r"flood", r"causeway", r"cyclone", r"evacuat", r"\bcroc", r"crocodile", r"creek", r"bridge",
        r"water'?s? (coming|rising|pouring|in the house|up|at the)", r"road.{0,20}(cut|underwater|under water|out)",
        r"cut off", r"higher ground", r"drinking water", r"should be leaving",
    ]),
    ("Hazard / infrastructure", "Infrastructure & hazards", [
        r"retaining wall", r"\btree\b", r"branch", r"verandah", r"carport", r"pothole", r"footpath",
        r"streetlight", r"\bdrain", r"gutter", r"\broof\b", r"fence", r"bus shelter", r"leak",
    ]),
    ("Utilities & comms", "Utilities", [
        r"\bpower\b", r"electricity", r"generator", r"internet", r"phone line|landline|mobile",
        r"reception", r"water pressure", r"freezer|fridge",
    ]),
    ("Environmental health", "Environmental health", [
        r"rodent", r"\bpest", r"\bants\b", r"mozzie", r"mosquito", r"dengue",
    ]),
    ("Payments & billing", "Hardship & payments", [
        r"payment", r"pension", r"\bbill\b", r"\bfee\b", r"centrelink", r"concession", r"overdue",
    ]),
    ("Feedback", "Customer experience", [
        r"thank", r"compliment", r"fantastic", r"feedback", r"cheers", r"great", r"appreciation",
    ]),
    ("Admin & records", "Customer service", [
        r"form", r"address", r"renew", r"record", r"receipt", r"application", r"unsubscribe",
        r"mailing list", r"opening hours|office open|open this", r"appointment", r"grant", r"booking|hire",
        r"contact (method|number|details)", r"surname|name on", r"rego|registration", r"complaint",
        r"\bbin\b|bin collection", r"maintenance request",
    ]),
]

_COMPILED = [(cat, team, [re.compile(p) for p in pats]) for cat, team, pats in ROUTES]
DEFAULT_ROUTE = ("General enquiries", "Customer service")


def route_message(text: str, priority: str = None, unreadable: bool = False) -> dict:
    """
    Returns:
        dict: {"category", "team", "cc_duty_officer": bool, "matched", "reason"}
    """
    if unreadable:
        # Keyword rules can't read it, so don't pretend to route by keyword.
        team = "Interpreter & community liaison"
        cc = priority == "critical"
        reason = (f"Routed to {team}: the language was not recognised, so a person reads it in full and arranges "
                  f"an interpreter if needed.")
        if cc:
            reason += " Critical priority, so the Duty Officer is copied in as first responder."
        return {"category": "Language not recognised", "team": team, "cc_duty_officer": cc, "matched": None,
                "reason": reason}

    t = (text or "").lower().replace("’", "'")
    category, team, matched = DEFAULT_ROUTE[0], DEFAULT_ROUTE[1], None
    for cat, tm, patterns in _COMPILED:
        for p in patterns:
            m = p.search(t)
            if m:
                category, team, matched = cat, tm, m.group(0)
                break
        if matched:
            break

    cc = priority == "critical" and not team.startswith("Duty Officer")
    if matched:
        reason = f"Routed to {team} ({category}) — matched “{matched}”."
    else:
        reason = f"No routing rule matched — sent to {team} for manual sorting."
    if cc:
        reason += " Critical priority, so the Duty Officer is copied in as first responder."

    return {"category": category, "team": team, "cc_duty_officer": cc, "matched": matched, "reason": reason}
