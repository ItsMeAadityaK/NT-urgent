"""
acknowledgement.py

Drafts an acknowledgement for each item — for a HUMAN to approve.

Trust twist from the brief: the system escalates, it never responds by
itself. So every draft comes back with requires_approval=True and there
is no code path anywhere in this project that sends one automatically.
The officer reads it, edits it if needed, and approves it.

Drafts are deliberately template-based, not LLM-written:
  - wording to the public is predictable and pre-approved (no
    hallucinated promises like "help is on the way");
  - it works offline;
  - safety-sensitive cases get safety-aware wording (below).

Safety-aware wording: for personal-safety items the draft never repeats
what the person reported. In a family-violence situation the person
causing harm may read the reply on a shared phone. The draft is neutral
and the officer is prompted to phone first rather than text.
"""

RESPONSE_TIMES = {
    "critical": "now",
    "high": "today",
    "medium": "within 2 business days",
    "low": "within 5 business days",
}


def _ref(message_id: str) -> str:
    return f"NT-{message_id}"


def draft_acknowledgement(message_id: str, priority: str, category: str, team: str, channel: str) -> dict:
    """
    Returns:
        dict: {
            "draft": str,                # text for the officer to review
            "requires_approval": True,   # always — never auto-sent
            "officer_note": str,         # guidance shown to the officer, not the sender
        }
    """
    ref = _ref(message_id)
    short = channel == "sms"

    if category == "Personal safety":
        draft = (f"Hi, this is the NT Government contact centre returning your enquiry (ref {ref}). "
                 f"An officer will call you shortly. If you are in danger right now, call 000.")
        note = ("SAFETY-AWARE WORDING: the draft deliberately does not repeat what was reported, in case "
                "someone else reads this device. Phone the sender first; only send a written reply if a call "
                "is not possible or safe.")
    elif priority == "critical":
        draft = (f"We have your message (ref {ref}) and a duty officer has it now. "
                 f"If anyone is in immediate danger, call 000."
                 if short else
                 f"Thank you for contacting us. We have received your message (ref {ref}) and it has been "
                 f"passed to a duty officer, who is dealing with it now. If anyone is in immediate danger, "
                 f"please call 000.")
        note = "Critical: make direct contact (phone) first. Send this only as a confirmation after or alongside the call."
    elif priority == "high":
        draft = (f"We have your message (ref {ref}). It is marked urgent and our {team} team will contact you today. "
                 f"In an emergency call 000."
                 if short else
                 f"Thank you for contacting us. Your message (ref {ref}) has been marked urgent and passed to our "
                 f"{team} team, who will contact you today. If the situation becomes an emergency, please call 000.")
        note = "Check the draft matches what the team can actually deliver today before approving."
    else:
        when = RESPONSE_TIMES.get(priority, "soon")
        draft = (f"Thanks, we have your message (ref {ref}). Our {team} team will reply {when}."
                 if short else
                 f"Thank you for contacting us. We have received your message (ref {ref}) and our {team} team "
                 f"will respond {when}.")
        note = "Routine acknowledgement."

    return {"draft": draft, "requires_approval": True, "officer_note": note}
