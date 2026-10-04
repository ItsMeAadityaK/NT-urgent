"""
generator.py

Builds a fresh, random-but-replayable "shift" of correspondence for the demo.

Why this exists: the original 152 hand-written messages are the same every run,
so any model evaluated on them has effectively seen the answers. A shift is
generated from a seed instead — same seed, identical shift; new seed, new
messages — and its true urgency is a HIDDEN answer key. The queue never shows
it and no classifier sees it; it is only used afterwards to score them.

Each message is assembled from independent random pieces, so combinations
almost never repeat:
    situation (hidden urgency)  x  who/how long/where  x  writing style
    x  noise (typos, SMS shorthand, caps, voice-to-text mistakes)  x  access.

The mix is deliberately skewed toward routine mail (the "haystack"), but the
randomness is constrained so every shift still contains the cases worth
demonstrating: a flooded, cut-off critical message, a child alone, a
medication risk, senders who go silent, a sender who follows up (so the
dropout detector is shown NOT flagging), a routine message from a cut-off
sender (access weighting), and three formal/informal fairness pairs.

Honest limitation: these messages are written by us, so scores on them are
optimistic compared with real correspondence. The hand-written 152 stay in the
project as an independent benchmark for exactly that reason.

Community phrases: this file never invents Kriol or Aboriginal-language text.
If data/community_phrases.json exists it is mixed in. Format — a JSON list of
entries written or reviewed by a speaker or interpreter:
    [{"text": "...", "true_urgency": "critical", "language": "Kriol",
      "source": "reviewed by <name/organisation>"}]
"""

import json
import os
import random
from datetime import timedelta

from messages import SIMULATION_START

DEFAULT_SIZE = 55
SHIFT_MINUTES = 450
MIX = (("critical", 0.13), ("high", 0.18), ("medium", 0.25), ("low", 0.44))

REMOTE = ["Daly River area", "Peppimenarti", "Wadeye", "Maningrida", "Ngukurr", "Borroloola", "Nhulunbuy", "Jabiru"]
URBAN = ["Darwin", "Palmerston", "Humpty Doo", "Batchelor", "Katherine"]
CENTRAL = ["Alice Springs", "Tennant Creek", "Yuendumu", "Elliott"]

COMMUNITY_PHRASES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                      "data", "community_phrases.json")


def S(key, urgency, informal, formal, weather=False):
    return {"key": key, "urgency": urgency, "weather": weather, "informal": informal, "formal": formal}


# Slots available in templates: {days} {hours} {kin} {kids} {kids_f} {n}
SCENARIOS = [
    # ------------------------------ CRITICAL ------------------------------
    S("flood_no_water_old", "critical", weather=True,
      informal=["{days} days with no water here, the flood has us cut off, the elders are struggling pls send help",
                "{days} days no drinking water, road is under, we got elders and a baby here please",
                "flood cut us off and theres no water for {days} days, my {kin} is old and getting weak"],
      formal=["Our community has been without drinking water for {days} days because of flooding. Elderly residents here urgently need assistance.",
              "Floodwater has isolated our community and there has been no safe water for {days} days. Several elderly residents are unwell."]),
    S("water_in_house", "critical", weather=True,
      informal=["water is coming in the house fast got {kids} and cant get out",
                "flood water in the house up to my knees, {kids} with me, road is gone",
                "water rising inside the house dont know how to get {kids} out"],
      formal=["Floodwater is entering our home and I have {kids_f} with me. We cannot leave because the road is cut.",
              "Caller reports water rising inside the house with young children present and no way out."]),
    S("unsafe_home", "critical",
      informal=["hes been threatening to hurt me and i cant stay here tonight, need a safe place for me and the kids",
                "not safe here tonight he is drunk and angry need to get out with my kids",
                "he keeps threatening me and i dont feel safe at home tonight please help"],
      formal=["I am afraid to remain in my home this evening. I am seeking emergency help to find a safe place for my family.",
              "My partner has threatened to harm me. I need urgent help to leave with my children."]),
    S("child_alone", "critical",
      informal=["theres a little kid at the house on their own since early this morning and the mum wont pick up",
                "my {n} yo is home alone since last night and mum isnt answering her phone",
                "little kid by themselves at the house all day, no adult around"],
      formal=["I am concerned for a young child who has been alone at a residence since this morning. The parent cannot be contacted.",
              "A child of about {n} years has been left unsupervised overnight and the carer is not answering."]),
    S("medical_collapse", "critical",
      informal=["my {kin} collapsed and wont wake up, cant get an ambulance the road is flooded",
                "{kin} fell down and isnt breathing right, no ambulance can get here",
                "my {kin} collapsed and is not responding, need help now"],
      formal=["An elderly relative has collapsed and is unresponsive. Floodwater is preventing ambulance access.",
              "Caller reports a person collapsed and not breathing normally, requesting urgent medical assistance."]),
    S("labour_cutoff", "critical", weather=True,
      informal=["my wife is in labour and the causeway is under water cant get to the clinic",
                "baby is coming now and the road is cut off no way to the hospital"],
      formal=["My wife has gone into labour and the flooded causeway means we cannot get to the health centre."]),
    S("croc_school", "critical", weather=True,
      informal=["saw a massive croc in the flood water just near the school entrance, the kids are about to finish",
                "croc spotted in the flood water right where the kids play"],
      formal=["A crocodile has been sighted in floodwater beside the school gate and children are about to be dismissed."]),
    S("powerline_down", "critical", weather=True,
      informal=["a power cable has come down in the flood water on our street and its sparking, kids walk here all the time",
                "live wire down in the water outside our house and the kids play there"],
      formal=["A power line is down and sparking in floodwater on a street used daily by children."]),
    S("missing_person_flood", "critical", weather=True,
      informal=["husband went to check the pump this morning and hasnt come back, roads are underwater now",
                "my {kin} went down to the creek at first light and no sign of him, water is rising"],
      formal=["My husband left this morning to check the pump and has not returned. The roads are underwater and I cannot search for him."]),
    S("cyclone_no_exit", "critical", weather=True,
      informal=["heard on the radio a cyclone is coming and the water has cut every road out, we have no safe place to go",
                "they said cyclone tonight and our road out is under water, dont know where to take the kids"],
      formal=["We have been told a cyclone is approaching. Floodwater has closed our only route out and there is no high ground we can reach."]),

    # -------------------------------- HIGH --------------------------------
    S("roof_off_shelter", "high",
      informal=["the wind ripped our roof off last night, nothing dry left in the house and we have {kids}",
                "storm took half our roof, {kids} and nowhere to stay tonight"],
      formal=["Storm damage has removed part of our roof. With {kids_f} in the household we need urgent shelter for tonight."]),
    S("insulin_fridge", "high",
      informal=["power out since yesterday and my dads insulin is in the fridge, getting warm now",
                "no power {hours} hours and mums insulin needs to stay cold, not sure how long its ok"],
      formal=["We have had no power for {hours} hours and a family member's insulin is stored in the refrigerator. Please advise urgently."]),
    S("oxygen_power", "high",
      informal=["dad relies on his oxygen concentrator, power has been down for {hours} hrs and the backup is nearly flat",
                "no power and dad needs his oxygen, backup is running low"],
      formal=["The power has been out for {hours} hours and a resident depends on an oxygen concentrator. The backup battery is running low."]),
    S("elderly_uncontactable", "high",
      informal=["cant get hold of my nan since yesterday arvo shes 84 and lives alone, phone just rings",
                "havent heard from my old man out bush since the rain started, could someone check on him"],
      formal=["I have been unable to reach my elderly father, who lives alone, since yesterday evening. Could someone check on his welfare?"]),
    S("water_rising_not_in", "high", weather=True,
      informal=["the flood is nearly at our door, not inside yet, should we be getting out now",
                "creek is coming up fast near the house, not in yet but close, what do we do"],
      formal=["Floodwater is approaching our home. It has not entered yet but we need guidance on whether to evacuate."]),
    S("unsafe_structure", "high",
      informal=["the veranda post snapped in the wind and the roof is sagging over the front steps, the kids use those steps daily",
                "big branch broke the carport roof and its looking like it will fall more"],
      formal=["A section of our verandah has partially collapsed and is leaning over a walkway used by children every day."]),
    S("tablets_clinic_cut", "high", weather=True,
      informal=["road to the clinic is under water and mum is nearly out of her heart tablets",
                "cant get to the clinic, road is cut, and my bub has a fever"],
      formal=["The road to the health clinic is flooded. A family member is almost out of essential heart medication and we have no other route."]),
    S("flood_hardship", "high", weather=True,
      informal=["no job and now the flood has ruined our things, honestly dont know how to feed the family this week",
                "flood took everything we have no money for food this week"],
      formal=["Following flood damage to our home we have lost most of our belongings and have no savings. We urgently need help with basic needs this week."]),
    S("water_nearly_gone", "high", weather=True,
      informal=["roads are still closed and our drinking water is almost used up",
                "no word on when the road opens and the food is nearly gone"],
      formal=["Our community remains isolated by floodwater and our drinking water supply is nearly exhausted."]),
    S("wheelchair_stuck", "high", weather=True,
      informal=["flood broke the ramp and my husband in a wheelchair cant leave the house",
                "my {kin} uses a wheelchair and the path outside is washed out, hes stuck inside"],
      formal=["The flood has destroyed our ramp. My husband uses a wheelchair and cannot get out of the house at all."]),

    # ------------------------------- MEDIUM -------------------------------
    S("power_out_hours", "medium",
      informal=["still no electricity after about {hours} hours, anyone know when its coming back",
                "no power since the storm, {hours} hours, generator is going ok"],
      formal=["We have been without electricity for roughly {hours} hours and have not been told when it will return."]),
    S("water_pressure", "medium",
      informal=["water pressure has been terrible two days, barely a trickle at night",
                "tap water coming out really slow again, cant even shower properly"],
      formal=["For two days now the water pressure at our house has been very poor, mostly in the evening."]),
    S("unanswered_complaint", "medium",
      informal=["rang 3 times this week about my pension being short and still nothing, getting frustrated",
                "no one has called me back about my payment, third time ive asked"],
      formal=["I have contacted your office three times this week about an incorrect payment and have not received a reply."]),
    S("minor_storm_damage", "medium",
      informal=["wind knocked our fence over overnight, the dogs wandered off but came back ok",
                "small amount of rain got under the back door and wet the mat, no real damage"],
      formal=["Storm winds damaged our fence overnight. There was no injury but we would like it recorded and repaired."]),
    S("pothole_hazard", "medium",
      informal=["huge water-filled pothole at the end of our street, a car swerved badly there this morning",
                "road edge is crumbling near the bus stop after the rain, someone is going to get a flat"],
      formal=["A large water-filled pothole on our street caused a near-miss this morning. Please arrange repair."]),
    S("pest_issue", "medium",
      informal=["rats in the kitchen for about a week now, its gross but nothing urgent",
                "ants everywhere in the pantry since the rain"],
      formal=["Rats have been getting into our kitchen for about a week. It worries us but it is not an emergency."]),
    S("internet_outage", "medium",
      informal=["no internet for 2 days so i cant lodge my income report online",
                "phone and internet both out, worried about missing my appointment"],
      formal=["Our internet has been unavailable for two days and I cannot complete my online income reporting."]),
    S("billing_dispute", "medium",
      informal=["keep getting overdue notices for something ive already paid, can you look into it",
                "late fee on my account but the power was out and i couldnt pay online"],
      formal=["I have received a third overdue notice for an account I have already paid. Please review your records."]),
    S("appointment_unconfirmed", "medium",
      informal=["still havent got confirmation for my specialist appointment next tuesday, worried its cancelled",
                "no letter about my scan next week yet"],
      formal=["I have not received confirmation of my specialist appointment next week and am worried it may have been cancelled."]),
    S("streetlight_out", "medium",
      informal=["the light on our street has been dead for 2 weeks and its really dark when i walk back from the bus",
                "no light at the bus stop and its pitch black at night now"],
      formal=["For a fortnight the street light near our property has been out, and walking from the bus stop after dark feels unsafe."]),

    # --------------------------------- LOW --------------------------------
    S("permit_renew", "low",
      informal=["hi when does my permit renew, no rush", "when is my community grant due to be renewed?"],
      formal=["Could you please advise when my permit is due for renewal?"]),
    S("change_address", "low",
      informal=["what forms do i need for a change of address", "moved house, how do i update my address with you"],
      formal=["Which forms are required to update my residential address?"]),
    S("opening_hours", "low",
      informal=["what time is the office open over the long weekend", "are you open saturday morning?"],
      formal=["Will your office be open on the public holiday, and if so until what time?"]),
    S("rego_renewal", "low",
      informal=["when's my car rego due again?", "when is my rego due"],
      formal=["I would like to know when my vehicle registration is next due."]),
    S("thanks_feedback", "low",
      informal=["big thanks to the woman who helped me out last week, she was so patient", "cheers for sorting my form so quick"],
      formal=["I would like to thank the staff member who assisted me last week. She was very patient and helpful."]),
    S("status_check", "low",
      informal=["just checking on my application no rush", "any update on my form from a few weeks ago"],
      formal=["I am following up on my application submitted three weeks ago. There is no urgency."]),
    S("minor_maintenance", "low",
      informal=["gutter on the side of the house has a small leak, not urgent whenever you can",
                "paint peeling on the community sign, just cosmetic"],
      formal=["There is a minor leak in the guttering. It is not urgent and can be attended to when convenient."]),
    S("unsubscribe", "low",
      informal=["pls take me off the newsletter list", "stop sending me the emails thanks"],
      formal=["Please remove this email address from your mailing list."]),
    S("receipt_request", "low",
      informal=["could i get a receipt for what i paid last week", "need a copy of my receipt for my records"],
      formal=["I need a copy of the receipt for my recent payment; please email it to me."]),
    S("resolved_complaint", "low",
      informal=["the noise issue i complained about is sorted now thanks, nothing more needed",
                "all fixed now cheers no need to do anything"],
      formal=["The matter I raised last month has been resolved. No further action is required."]),
    S("grant_info", "low",
      informal=["whats the deal with the small business grant, how do i apply", "where can i find the youth sports grant info"],
      formal=["Where can I find the application guidelines for the small business grant?"]),
    S("hall_booking", "low",
      informal=["keen to book the hall for my daughters 10th, what dates are open", "is the hall free sat 14th for a party"],
      formal=["I would like to hire the community hall for a private event next month. Is it available?"]),
    S("library_reopen", "low",
      informal=["hi just wondering when the library reopens after the storm, no rush", "is the library open again yet"],
      formal=["Could you let me know when the library will reopen following the storm? There is no urgency."]),
    S("payment_plan", "low",
      informal=["is it ok to pay what i owe a bit at a time", "is there a payment plan option for my rates"],
      formal=["Can I arrange to pay my account in instalments?"]),
    S("id_appointment", "low",
      informal=["what paperwork do i take to my id renewal appointment", "do i need to book for the id thing or just walk in"],
      formal=["Which documents should I bring to my identification renewal appointment?"]),
    S("contact_update", "low",
      informal=["can u add my other phone number to my file when u get a chance", "want to switch to email instead of post"],
      formal=["Please add a second contact number to my file and update my preferred contact method to email."]),
    S("concession_status", "low",
      informal=["did my concession card renewal go thru yet, no rush", "checking if you got my concession form from last month"],
      formal=["I would like to confirm that my concession card renewal has been processed. There is no urgency."]),
    S("bin_day", "low",
      informal=["which day is bin day this week with the public holiday", "does recycling still get picked up after the storm"],
      formal=["Could you confirm the bin collection day for this week given the public holiday?"]),
    S("lost_card", "low",
      informal=["lost my health card, how do i get a new one", "cant find my medicare card anywhere, need a replacement"],
      formal=["I have misplaced my health card. How do I apply for a replacement?"]),
    S("tip_hours", "low",
      informal=["what are the hours at the tip this weekend", "is the rubbish tip open on sunday"],
      formal=["What are the opening hours of the waste facility this weekend?"]),
    S("dog_registration", "low",
      informal=["need to register my dog, where do i do that", "how much is it to register a new puppy"],
      formal=["How can I register my dog with the council?"]),
    S("program_info", "low",
      informal=["do you have any info on the community ranger program", "how do i sign up for the training course you run"],
      formal=["Could you provide details about the community ranger program?"]),
    S("name_misspelt", "low",
      informal=["my name is spelt wrong on the letter you sent, can u fix it", "got a letter with my surname wrong, pls update"],
      formal=["My surname is misspelt on your recent letter. Could you correct your records?"]),
    S("interpreter_info", "low",
      informal=["do you have an interpreter for appointments", "can someone help translate when i come in to the office"],
      formal=["Is an interpreter service available for appointments at your office?"]),
]

_MORE_MEDIUM = [
    S("noise_complaint", "medium",
      informal=["neighbours playing loud music till 3am again, third time this week",
                "still no reply about the noise next door, its been a fortnight"],
      formal=["I have reported noise from a neighbouring property three times this week and have had no response."]),
    S("bins_missed", "medium",
      informal=["bins missed twice in a row and the rubbish is piling up", "rubbish hasnt been collected for 2 weeks, starting to smell"],
      formal=["Our rubbish has not been collected on two consecutive weeks and it is starting to pile up."]),
    S("mozzies_dengue", "medium", weather=True,
      informal=["the mozzies are terrible since the floods and im worried about dengue for the kids",
                "so many mosquitoes since the flood, kids keep getting bitten"],
      formal=["There has been a marked increase in mosquitoes around our community since the flooding, and we are concerned about dengue."]),
    S("road_info_outdated", "medium", weather=True,
      informal=["the road closure info on the noticeboard is out of date, people keep driving out and turning back",
                "nobody knows which roads are open, the info online is old"],
      formal=["The road closure information available to our community appears to be out of date. Could it be refreshed?"]),
]
SCENARIOS += _MORE_MEDIUM

# Generic "we're OK now" follow-ups, sent by someone who earlier reported something serious.
ALL_CLEAR = [
    "update: someone got to us, were ok now thanks for checking in",
    "all sorted now sorry for the trouble, thanks",
    "everything is ok now thank you",
]
ALL_CLEAR_FORMAL = ["Update: assistance has arrived and we are now safe. Thank you for your help."]

BY_KEY = {s["key"]: s for s in SCENARIOS}
MUST_HAVE = {
    "critical": ["flood_no_water_old", "child_alone", "medical_collapse"],
    "high": ["insulin_fridge"],
    "medium": [],
    "low": ["thanks_feedback"],
}

SMS = {"you": "u", "your": "ur", "are": "r", "to": "2", "for": "4", "please": "pls", "because": "bcz", "with": "w",
       "before": "b4", "tonight": "2nite", "tomorrow": "tmrw", "people": "ppl", "thanks": "thx", "about": "abt",
       "message": "msg"}
VOICE_TO_TEXT = {"road": "rode", "father": "farther", "wait": "weight", "their": "there", "write": "right"}


# ------------------------------------------------------------------ noise
def _typo(word, rng):
    if len(word) < 4:
        return word
    i = rng.randrange(1, len(word) - 1)
    op = rng.choice(("drop", "swap", "double"))
    if op == "drop":
        return word[:i] + word[i + 1:]
    if op == "swap":
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    return word[:i] + word[i] + word[i:]


def _split_punct(token):
    core = token.rstrip(".,!?;:")
    return core, token[len(core):]


def _add_noise(text, rng, style):
    if style == "informal":
        text = text.lower().rstrip(".")
        rate = rng.choices([0.0, 0.06, 0.12, 0.2], weights=[3, 3, 2, 1])[0]
        sms = rng.random() < 0.3
        voice = rng.random() < 0.08
    else:
        rate = rng.choices([0.0, 0.03], weights=[3, 1])[0]
        sms, voice = False, rng.random() < 0.05

    out = []
    for token in text.split():
        core, tail = _split_punct(token)
        low = core.lower()
        if sms and low in SMS and rng.random() < 0.7:
            core = SMS[low]
        elif voice and low in VOICE_TO_TEXT:
            core = VOICE_TO_TEXT[low]
        elif core.isalpha() and rng.random() < rate:
            core = _typo(core, rng)
        out.append(core + tail)
    text = " ".join(out)

    if style == "informal" and rng.random() < 0.06:
        text = text.upper()
    elif style == "formal" and text:
        text = text[0].upper() + text[1:]
    return text


# ----------------------------------------------------------------- pieces
def _slots(rng):
    return {
        "days": rng.choice(["2", "3", "4"]),
        "hours": rng.choice(["5", "8", "14", "18"]),
        "kin": rng.choice(["mum", "dad", "nan", "pop", "aunty", "uncle", "brother"]),
        "kids": rng.choice(["2 kids", "the kids", "3 little ones", "a baby", "my 2 young ones"]),
        "kids_f": rng.choice(["two young children", "a small baby", "three young children"]),
        "n": str(rng.randint(4, 9)),
    }


def _pick_location(rng, weather):
    if weather:
        return rng.choices(REMOTE + URBAN, weights=[5] * len(REMOTE) + [2] * len(URBAN))[0]
    return rng.choices(URBAN + REMOTE + CENTRAL, weights=[4] * len(URBAN) + [2] * len(REMOTE) + [2] * len(CENTRAL))[0]


def _pick_access(rng, location, weather, urgency="low"):
    # "cut-off" only happens in serious weather scenarios: it means isolated by
    # floodwater, so routine mail never arrives as cut-off (it can still be "limited").
    if urgency in ("low", "medium") and weather and location in REMOTE:
        return rng.choices(["normal", "limited"], weights=[0.45, 0.55])[0]
    if urgency in ("low", "medium") and weather:
        return rng.choices(["normal", "limited"], weights=[0.7, 0.3])[0]
    if location in CENTRAL:
        w = (0.85, 0.15, 0.0)
    elif weather and location in REMOTE:
        w = (0.1, 0.4, 0.5)
    elif weather:
        w = (0.45, 0.45, 0.1)
    elif location in REMOTE:
        w = (0.65, 0.35, 0.0)
    else:
        w = (0.9, 0.1, 0.0)
    return rng.choices(["normal", "limited", "cut-off"], weights=w)[0]


def _template(rng, scenario, style, used_templates):
    """Pick a template, preferring one not already used in this shift."""
    pool = scenario[style]
    fresh = [t for t in pool if (scenario["key"], t) not in used_templates]
    choice = rng.choice(fresh or pool)
    used_templates.add((scenario["key"], choice))
    return choice


def _channel(rng, style):
    if style == "informal":
        return rng.choices(["sms", "webform", "phone"], weights=[75, 15, 10])[0]
    return rng.choices(["email", "webform", "phone"], weights=[50, 40, 10])[0]


def _arrival(rng, urgency):
    """Storm shifts are front-loaded: plenty arrives in the first hour or two, then it
    tapers. Critical messages stay early enough (<= 5h20m) for the 2h dropout check to
    be able to fire before the shift ends."""
    if urgency == "critical":
        return rng.randint(5, 90) if rng.random() < 0.45 else rng.randint(90, 320)
    if urgency == "high":
        return rng.randint(5, 120) if rng.random() < 0.35 else rng.randint(120, 400)
    return int(SHIFT_MINUTES * rng.random() ** 1.4)


def _quotas(n):
    counts = {k: max(2 if k in ("critical", "high") else 1, round(n * f)) for k, f in MIX}
    counts["low"] += n - sum(counts.values())
    return counts


def load_community_phrases(path=COMMUNITY_PHRASES_PATH):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [e for e in json.load(f) if e.get("text") and e.get("true_urgency") in dict(MIX)]


# ------------------------------------------------------------------ shift
def generate_shift(seed, n=DEFAULT_SIZE, community=None):
    """Return a list of message dicts (same shape as data/messages.py entries,
    minus the hand-written LLM stand-ins). `true_urgency` is the hidden key."""
    rng = random.Random(seed)
    if community is None:
        community = load_community_phrases()
    quota = _quotas(n)
    used = set()

    def take(urgency):
        pool = [s for s in SCENARIOS if s["urgency"] == urgency]
        fresh = [s for s in pool if s["key"] not in used]
        pick = rng.choice(fresh or pool)
        used.add(pick["key"])
        return pick

    items = []  # {"scenario", "urgency", "pair", "followup_of", "force_access", "text"}

    # Matched formal/informal pairs: one low, one high, one critical.
    for pair_no, urgency in enumerate(("low", "high", "critical"), start=1):
        if quota[urgency] >= 2:
            items.append({"scenario": take(urgency), "urgency": urgency, "pair": f"FP{pair_no}"})
            quota[urgency] -= 2

    # Guaranteed highlights.
    for urgency, keys in MUST_HAVE.items():
        for key in keys:
            if quota[urgency] > 0 and key not in used:
                used.add(key)
                items.append({"scenario": BY_KEY[key], "urgency": urgency,
                              "force_access": "cut-off" if key == "flood_no_water_old" else None})
                quota[urgency] -= 1

    # A routine/medium message from a remote, access-limited sender (access weighting demo).
    if quota["medium"] > 0:
        items.append({"scenario": take("medium"), "urgency": "medium", "force_access": "limited",
                      "force_location": rng.choice(REMOTE)})
        quota["medium"] -= 1

    # Two "we're ok now" follow-ups from earlier serious senders (dropout NOT flagged for them).
    followups = min(2, quota["low"])
    quota["low"] -= followups

    # Fill the rest at random.
    for urgency, count in quota.items():
        for _ in range(count):
            items.append({"scenario": take(urgency), "urgency": urgency})

    messages = []
    used_templates = set()
    for item in items:
        sc, urgency = item["scenario"], item["urgency"]
        location = item.get("force_location") or _pick_location(rng, sc["weather"])
        access = item.get("force_access") or _pick_access(rng, location, sc["weather"], urgency)
        vals = _slots(rng)
        base = _arrival(rng, urgency)

        if item.get("pair"):
            inf = _add_noise(_template(rng, sc, "informal", used_templates).format(**vals), rng, "informal")
            frm = _add_noise(_template(rng, sc, "formal", used_templates).format(**vals), rng, "formal")
            for style, text, offset in (("informal", inf, 0), ("formal", frm, rng.randint(2, 12))):
                messages.append({"text": text, "urgency": urgency, "location": location, "access": access,
                                 "minute": min(base + offset, SHIFT_MINUTES), "style": style,
                                 "pair": item["pair"], "scenario": sc["key"], "channel": _channel(rng, style)})
            continue

        style = "informal" if rng.random() < 0.65 else "formal"
        text = _add_noise(_template(rng, sc, style, used_templates).format(**vals), rng, style)
        messages.append({"text": text, "urgency": urgency, "location": location, "access": access,
                         "minute": base, "style": style, "pair": None, "scenario": sc["key"],
                         "channel": _channel(rng, style)})

    # Follow-ups reuse the sender of an earlier critical/high message that arrived with room to spare.
    candidates = [m for m in messages if m["urgency"] in ("critical", "high") and not m["pair"] and m["minute"] <= 330]
    rng.shuffle(candidates)
    for parent in candidates[:followups]:
        parent["followed_up"] = True
        style = "informal" if rng.random() < 0.7 else "formal"
        text = rng.choice(ALL_CLEAR if style == "informal" else ALL_CLEAR_FORMAL)
        # Once they say they're OK, their situation has resolved — access is normal again.
        messages.append({"text": _add_noise(text, rng, style), "urgency": "low", "location": parent["location"],
                         "access": "normal", "minute": min(parent["minute"] + rng.randint(40, 100), SHIFT_MINUTES),
                         "style": style, "pair": None, "scenario": "all_clear", "channel": _channel(rng, style),
                         "sender_of": id(parent)})
    # If there weren't enough eligible parents, fill the missing slots with ordinary low messages.
    for _ in range(followups - min(followups, len(candidates))):
        sc = take("low")
        style = "informal"
        messages.append({"text": _add_noise(_template(rng, sc, style, used_templates).format(**_slots(rng)), rng, style),
                         "urgency": "low", "location": _pick_location(rng, False), "access": "normal",
                         "minute": _arrival(rng, "low"), "style": style, "pair": None, "scenario": sc["key"],
                         "channel": _channel(rng, style)})

    # Optionally mix in real community-supplied phrases, replacing random non-structural messages.
    swappable = [m for m in messages if not m["pair"] and not m.get("followed_up") and m["scenario"] != "all_clear"]
    rng.shuffle(swappable)
    for entry in community[:2]:
        for m in swappable:
            if m["urgency"] == entry["true_urgency"] and "language" not in m:
                m["text"], m["language"] = entry["text"], entry.get("language", "community-supplied")
                break

    # Order by arrival, then assign ids and senders.
    messages.sort(key=lambda m: m["minute"])
    sender_for = {}
    out = []
    for i, m in enumerate(messages, start=1):
        sender = f"U{i:03d}"
        if "sender_of" in m:
            parent_sender = sender_for.get(m["sender_of"])
            sender = parent_sender or sender
        sender_for[id(m)] = sender
        out.append({
            "message_id": f"L{i:03d}",
            "timestamp": SIMULATION_START + timedelta(minutes=m["minute"]),
            "channel": m["channel"],
            "sender_id": sender,
            "raw_text": m["text"],
            "location": m["location"],
            "access_status": m["access"],
            "true_urgency": m["urgency"],
            "fairness_pair": m["pair"],
            "fairness_style": m["style"] if m["pair"] else None,
            "scenario": m["scenario"],
            "language": m.get("language"),
        })
    return out


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    for m in generate_shift(seed):
        print(f"{m['message_id']} {m['timestamp']:%H:%M} {m['true_urgency']:8} {m['access_status']:8} "
              f"{m['location']:16} {m['raw_text']}")
