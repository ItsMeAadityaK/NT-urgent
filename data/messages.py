"""
messages.py

Synthetic demo dataset for the correspondence triage dashboard: 152
messages simulating one high-volume wet-season shift for a generic NT
government correspondence/complaints unit.

Design choices, deliberately:
- One evolving weather event (a monsoon trough bringing flooding and
  damaging winds across the Top End) rather than mixing in unrelated
  disaster types — e.g. no bushfire scenarios, since bushfire risk in the
  NT is a dry-season (May-Oct) phenomenon and this dataset is explicitly
  framed as wet season (Nov-Apr). Getting this wrong would be an easy
  authenticity slip for anyone who knows the region.
- Two geographic clusters: Top End / monsoon-affected communities (Darwin,
  Palmerston, Katherine, Batchelor, Humpty Doo, Jabiru, Daly River area,
  Peppimenarti, Wadeye, Maningrida, Ngukurr, Borroloola, Nhulunbuy) where
  flood/storm messages concentrate, and Central Australia / Barkly towns
  (Alice Springs, Tennant Creek, Yuendumu, Ali Curung, Elliott) which are
  NOT affected by this particular weather system and mostly generate
  routine correspondence plus occasional UNRELATED urgent cases (medical,
  welfare). This stops the dataset being monotonously "everything is a
  flood emergency" and is geographically honest — the NT is not one
  uniform climate zone.
- true_urgency: a ground-truth label, separate from llm_urgency (the
  pre-authored LLM stand-in) and from the baseline model's own live
  prediction. Needed to actually measure accuracy for both classifiers
  against a real answer key, not just compare them to each other.
- fairness_pair / fairness_style: five formal/informal phrasing pairs
  (10 messages), one from each urgency band, describing the SAME
  underlying situation two different ways. More rigorous than a single
  pair — checks whether writing-style bias shows up consistently or only
  at certain severity levels.
- Deliberate repeat senders with realistic gaps (some who go silent after
  an urgent message, some who follow up promptly) — needed to exercise
  the dropout detector against both a positive and a negative case.

Urgency distribution is deliberately skewed toward low/medium (most real
correspondence is mundane) with a meaningful but minority share of
high/critical — that skew IS the "needle in a haystack" problem the
brief is about, so it's part of the point, not an oversight.

    low: 56   medium: 41   high: 32   critical: 23   (total 152)

(152, not the round 150, because two of the "does the dropout detector
correctly NOT flag a sender who follows up?" control messages were added
after the main 150 — see the comment above M151/M152.)
"""

from datetime import datetime, timedelta

# Fixed anchor time so the demo is reproducible: 06:00, start of a wet
# season dispatch shift. The dashboard's time slider moves forward FROM
# this point (up to +480 minutes / 8 hours) to simulate the shift.
SIMULATION_START = datetime(2026, 2, 10, 6, 0, 0)


def _t(minutes_after_start: int) -> datetime:
    return SIMULATION_START + timedelta(minutes=minutes_after_start)


def _m(mid, minutes, channel, sender, text, location, access, urgency, reason,
       true_urgency=None, pair=None, style=None):
    return {
        "message_id": mid,
        "timestamp": _t(minutes),
        "channel": channel,
        "sender_id": sender,
        "raw_text": text,
        "location": location,
        "access_status": access,
        "llm_urgency": urgency,
        "llm_reason": reason,
        "true_urgency": true_urgency or urgency,
        "fairness_pair": pair,
        "fairness_style": style,
    }


SAMPLE_MESSAGES = [

    # ---------------------------------------------------------------
    # CRITICAL (23) — immediate safety risk, time-critical, vulnerable
    # ---------------------------------------------------------------
    _m("M001", 4, "sms", "S001",
       "no water 3 days now, community cut off by the flood, got old people here need help",
       "Daly River area", "cut-off", "critical",
       "Immediate health/safety risk (prolonged lack of water) compounded by physical isolation and a vulnerable group (elderly residents).",
       pair="FP1", style="informal"),

    _m("M002", 9, "webform", "S002",
       "Our household has been without a reliable water supply for three consecutive days due to flooding that has isolated our community. We have elderly residents present who require assistance.",
       "Daly River area", "cut-off", "critical",
       "Identical situation to M001, phrased formally: prolonged lack of water, physical isolation, vulnerable residents present.",
       pair="FP1", style="formal"),

    _m("M003", 11, "sms", "S003",
       "no power no water baby is sick cant get to clinic road all flooded",
       "Peppimenarti", "cut-off", "critical",
       "Sick infant combined with no access to medical care due to road flooding — direct, time-critical safety risk to a vulnerable dependent."),

    _m("M004", 15, "sms", "S004",
       "kid on their own since this morning no answer from mum worried something wrong",
       "Wadeye", "limited", "critical",
       "Unsupervised child with no contact from responsible adult for an extended period — direct child-safety risk."),

    _m("M005", 41, "email", "S005",
       "havent heard from my mum since this morning shes not answering and i cant get there roads are cut",
       "Daly River area", "cut-off", "critical",
       "No contact with an elderly/vulnerable relative for an extended period, compounded by the reporter being physically unable to check on her — possible welfare emergency.",
       pair="FP5", style="informal"),

    _m("M006", 44, "webform", "S006",
       "I have had no contact with my mother since this morning despite repeated attempts, and I am unable to travel to check on her welfare due to road closures.",
       "Daly River area", "cut-off", "critical",
       "Same underlying welfare-check emergency as M005, formally phrased: prolonged loss of contact with a vulnerable relative, reporter unable to attend in person.",
       pair="FP5", style="formal"),

    _m("M007", 48, "sms", "S007",
       "water coming up fast at the community, kids and old people here, dont know if we can get out",
       "Peppimenarti", "cut-off", "critical",
       "Rapidly rising floodwater with an explicit statement that evacuation may not be possible, and vulnerable groups present — immediate risk to life."),

    _m("M008", 63, "phone", "S008",
       "Caller reports floodwater now entering the house, elderly father present, no vehicle access, requesting urgent help.",
       "Daly River area", "cut-off", "critical",
       "Active, escalating physical danger (water entering the dwelling) with a vulnerable resident and no means of self-evacuation."),

    _m("M009", 77, "sms", "S009",
       "big croc in the floodwater right by the school gate kids about to come out for pickup",
       "Wadeye", "limited", "critical",
       "Dangerous wildlife (displaced by floodwater, a known NT wet-season hazard) in immediate proximity to children about to be released from school — acute, time-critical safety risk."),

    _m("M010", 92, "webform", "S010",
       "My partner is in labour and we cannot reach the clinic, the causeway is underwater and there is no other road out.",
       "Peppimenarti", "cut-off", "critical",
       "Active medical emergency with no possible access to care due to flooding — maximum time-criticality and safety risk."),

    _m("M011", 105, "sms", "S011",
       "roof half gone now water pouring straight in electrics sparking dont know if its safe to stay",
       "Katherine", "limited", "critical",
       "Storm damage has created an active electrical hazard inside an occupied dwelling — immediate physical danger."),

    _m("M012", 118, "phone", "S012",
       "Caller states gas smell in the house after storm damage to the external line, unsure whether to evacuate, young children present.",
       "Palmerston", "normal", "critical",
       "Suspected gas leak is an acute, potentially life-threatening hazard regardless of access status — vulnerable occupants (children) present."),

    _m("M013", 134, "sms", "S013",
       "cyclone warning just came thru on radio we got nowhere safe to go here everything already flooded round us",
       "Wadeye", "cut-off", "critical",
       "Active severe weather warning combined with the community already being isolated by floodwater — no safe evacuation option identified."),

    _m("M014", 149, "webform", "S014",
       "The Bureau has issued a cyclone warning for our area. Our usual evacuation route is already flooded and we have no alternative route to higher ground.",
       "Daly River area", "cut-off", "critical",
       "Formal echo of the same evacuation-route failure under an active cyclone warning — life-safety risk with no viable escape path."),

    _m("M015", 156, "sms", "S015",
       "husband hasnt come home since he went to check the pump at first light nothing since roads are underwater now",
       "Daly River area", "cut-off", "critical",
       "Missing person in a flood-affected area with no contact for an extended period and worsening access conditions — high risk of harm."),

    _m("M016", 171, "phone", "S016",
       "Caller reports next-door neighbour, an elderly man living alone, has not answered his door or phone since yesterday and floodwater is now at his fence line.",
       "Katherine", "limited", "critical",
       "Elderly person living alone, uncontactable, with rising floodwater nearby — high risk welfare check needed immediately."),

    _m("M017", 188, "sms", "S017",
       "water in the house now up to my knees got 2 little ones cant carry both and our stuff same time",
       "Peppimenarti", "cut-off", "critical",
       "Floodwater has entered the home with two young children present and the reporter states they cannot safely manage evacuation alone — immediate risk to life."),

    _m("M018", 203, "webform", "S018",
       "There is a crocodile in the floodwater at the edge of our yard and my children usually play in that area after school.",
       "Daly River area", "cut-off", "critical",
       "Dangerous wildlife directly adjacent to a residence with children who routinely use that space — acute safety risk."),

    _m("M019", 219, "sms", "S019",
       "he said he was going to hurt me if i dont get out tonight i need somewhere safe with the kids",
       "Katherine", "limited", "critical",
       "Explicit statement of an imminent threat of harm with children involved — immediate safety risk requiring urgent human response, not an automated reply."),

    _m("M020", 226, "phone", "S020",
       "Caller, distressed, states she does not feel safe at her current address tonight and needs somewhere safe for herself and her children as soon as possible.",
       "Palmerston", "normal", "critical",
       "Same category of imminent personal-safety risk as M019 via a different channel — requires immediate human escalation, never an automated response."),

    _m("M021", 241, "sms", "S021",
       "power line down sparking in the flooded street right where kids walk to the bus stop",
       "Humpty Doo", "limited", "critical",
       "Live downed powerline in floodwater on a route used by children — acute electrocution risk."),

    _m("M022", 258, "webform", "S022",
       "The access road to the health centre is now completely underwater and a resident here urgently needs dialysis today.",
       "Ngukurr", "cut-off", "critical",
       "Time-critical medical treatment (dialysis) is unreachable due to flooding — direct risk to life if not resolved same-day."),

    _m("M023", 274, "sms", "S023",
       "elderly aunty collapsed we cant get an ambulance in the water is too high on the only road",
       "Borroloola", "cut-off", "critical",
       "Reported medical collapse with no ambulance access due to flooding — maximum urgency, immediate risk to life."),

    # ---------------------------------------------------------------
    # HIGH (32) — urgent, time-critical, but not immediate danger to life
    # ---------------------------------------------------------------
    _m("M024", 19, "email", "S024",
       "Roof came off in last night's storm, nowhere to stay tonight, got two kids with me.",
       "Katherine", "limited", "high",
       "Loss of shelter following a storm event, dependents present — urgent housing need, though sender has some local services access."),

    _m("M025", 24, "sms", "S025",
       "roof half off from the storm, kids and me got nowhere dry to sleep tonight",
       "Batchelor", "normal", "high",
       "Loss of safe, dry shelter with children present after storm damage — urgent but sender has normal access to alternative help.",
       pair="FP2", style="informal"),

    _m("M026", 27, "webform", "S026",
       "Following storm damage, a significant portion of our roof has been lost. With two children in the household, we require urgent alternative shelter for tonight.",
       "Batchelor", "normal", "high",
       "Same underlying shelter emergency as M025, phrased formally — urgent housing need for a household with children.",
       pair="FP2", style="formal"),

    _m("M027", 35, "sms", "S027",
       "fence and half the carport gone in the wind last night, water starting to pool near the house",
       "Jabiru", "normal", "high",
       "Structural storm damage plus rising local water — urgent attention needed before the situation worsens, though not yet an immediate danger."),

    _m("M028", 52, "phone", "S028",
       "Caller reports floodwater is rising steadily near their property and they are concerned about access being cut within hours.",
       "Daly River area", "limited", "high",
       "Anticipatory flood risk — not yet cut off, but access is expected to fail imminently, warranting urgent (not routine) handling."),

    _m("M029", 58, "email", "S029",
       "My elderly father lives alone out here and I haven't been able to reach him since the rain started, could someone check on him please.",
       "Nhulunbuy", "normal", "high",
       "Welfare-check request for an elderly person living alone during severe weather — urgent given vulnerability, though not yet an active emergency."),

    _m("M030", 66, "sms", "S030",
       "mums on oxygen machine and the powers been out 14 hours now backup battery wont last much longer",
       "Palmerston", "normal", "high",
       "Extended power outage threatens a household with a medical-equipment dependency — urgent, time-limited window before it becomes critical."),

    _m("M031", 71, "webform", "S031",
       "The retaining wall next to our carport has partially collapsed after the rain and is now leaning further each hour.",
       "Katherine", "normal", "high",
       "Deteriorating structural hazard that is worsening over time — needs prompt inspection before it fails completely."),

    _m("M032", 84, "sms", "S032",
       "only road into town is under water now, cant get mums medication from the pharmacy",
       "Peppimenarti", "cut-off", "high",
       "Isolation has cut off access to ongoing essential medication — urgent, though not an acute medical emergency yet."),

    _m("M033", 97, "email", "S033",
       "We've had no power since 4am and the fridge full of insulin needs to stay cold, not sure how much longer it's safe.",
       "Darwin", "normal", "high",
       "Power outage threatens cold-chain storage of essential medication — urgent, time-sensitive, though sender currently has normal access to alternatives."),

    _m("M034", 109, "phone", "S034",
       "Caller states the causeway near their community is expected to go under within the hour and they still need to collect an elderly relative from the other side.",
       "Daly River area", "limited", "high",
       "Narrow, closing window to complete a necessary trip before isolation — urgent and time-boxed."),

    _m("M035", 121, "sms", "S035",
       "big branch came down on the carport roof last night, structurally dodgy now, not sure if safe to park under",
       "Humpty Doo", "normal", "high",
       "Storm-damaged structure poses an ongoing hazard requiring prompt assessment, though not an immediate danger to occupants."),

    _m("M036", 129, "webform", "S036",
       "Our internet and phone lines have been down since the storm and we rely on a medical alert pendant service that needs connectivity to work.",
       "Katherine", "limited", "high",
       "Loss of connectivity has disabled a safety-critical medical alert system for a vulnerable resident — urgent to restore or provide an interim solution."),

    _m("M037", 141, "sms", "S037",
       "water's at the bottom step now, still got a bit of time but need to know if we should be leaving",
       "Peppimenarti", "limited", "high",
       "Floodwater approaching the dwelling with a still-open (but narrowing) window to act — urgent guidance needed."),

    _m("M038", 152, "email", "S038",
       "Our house flooded through the bottom floor last night, we've lost most of our food and can't get to the shops with the road out.",
       "Daly River area", "cut-off", "high",
       "Loss of food supply combined with isolation — urgent material hardship, not an immediate danger but needs prompt support."),

    _m("M039", 163, "sms", "S039",
       "generator packed it in, been running the freezer with mums medication in it since yesterday",
       "Wadeye", "limited", "high",
       "Backup power failure threatens medication storage — urgent, time-sensitive, though not yet an acute emergency."),

    _m("M040", 178, "phone", "S040",
       "Caller reports a large tree has fallen across their driveway blocking the only vehicle access, and a household member has a medical appointment this afternoon they cannot miss.",
       "Batchelor", "normal", "high",
       "Access blockage threatens a time-specific medical need — urgent but resolvable within the day if actioned promptly."),

    _m("M041", 194, "webform", "S041",
       "The clinic access road has been damaged by the flooding and ambulances can no longer reach our end of the community safely.",
       "Ngukurr", "cut-off", "high",
       "Infrastructure damage has compromised emergency-service access for an entire community — urgent systemic risk requiring prompt attention."),

    _m("M042", 209, "sms", "S042",
       "lost my job last week and now the flood's wrecked what was left in the house, dont know how were eating this week",
       "Katherine", "normal", "high",
       "Acute financial hardship compounding flood damage — urgent need for material support, though not a physical safety emergency."),

    _m("M043", 224, "email", "S043",
       "With the flood damage to our home we've lost nearly everything and have no savings left, we need help urgently to cover basics this week.",
       "Daly River area", "limited", "high",
       "Severe financial hardship following flood damage — urgent, time-sensitive need for support."),

    _m("M044", 236, "sms", "S044",
       "verandah post gave way in the wind, whole thing's leaning over the front steps now, kids walk past there every day",
       "Jabiru", "normal", "high",
       "Ongoing structural hazard on a route used daily by children — needs prompt remediation before it fails further."),

    _m("M045", 249, "phone", "S045",
       "Caller reports the only bridge into their community has been damaged by floodwater and is now considered unsafe to cross.",
       "Maningrida", "cut-off", "high",
       "Critical access infrastructure damaged, isolating the community — urgent systemic issue."),

    _m("M046", 263, "webform", "S046",
       "My mother is 81 and lives alone two doors down, I haven't been able to reach her by phone since yesterday evening and the lines have been unreliable.",
       "Tennant Creek", "normal", "high",
       "Welfare-check request for an elderly person, unrelated to the Top End flooding — urgent due to the vulnerability and duration of no contact, even without a weather driver."),

    _m("M047", 279, "sms", "S047",
       "no power since this arvo storm, freezer full of food for the week gonna spoil if its not back soon",
       "Palmerston", "normal", "high",
       "Time-limited risk of significant food loss — urgent to resolve within hours, not an immediate danger."),

    _m("M048", 291, "email", "S048",
       "The flooding has damaged the only access ramp to our property and my husband, who uses a wheelchair, currently cannot leave the house.",
       "Katherine", "limited", "high",
       "Accessibility infrastructure damage has effectively trapped a resident with a mobility disability — urgent, disability-specific access issue."),

    _m("M049", 305, "sms", "S049",
       "creek's come up over the low bridge, ambulance said they cant get through if we need one later tonight",
       "Peppimenarti", "limited", "high",
       "Pre-emptive warning that emergency access will fail if needed later — urgent contingency risk."),

    _m("M050", 318, "phone", "S050",
       "Caller reports significant water damage to insulin supply kept in a home fridge after a two-day power outage.",
       "Wadeye", "limited", "high",
       "Loss of essential medication supply due to prolonged outage — urgent to arrange replacement before it becomes a medical emergency."),

    _m("M051", 331, "webform", "S051",
       "Storm damage has exposed live wiring on the outside of our house and we have small children who play in the yard.",
       "Humpty Doo", "normal", "high",
       "Exposed electrical hazard in a space used by children — urgent safety issue requiring prompt attention."),

    _m("M052", 344, "sms", "S052",
       "still no word on when the road reopens, we're down to the last of our drinking water",
       "Daly River area", "cut-off", "high",
       "Isolation is approaching the point of a genuine supply crisis (drinking water) — urgent, trending toward critical if unresolved."),

    _m("M053", 358, "email", "S053",
       "Our roof has a large hole from the storm and heavy rain is forecast again tonight, we don't have anywhere else to go.",
       "Katherine", "limited", "high",
       "Ongoing shelter failure with further severe weather imminent — urgent to resolve before conditions worsen."),

    _m("M054", 372, "sms", "S054",
       "landline and mobile both down since yesterday, only got this message out cause a neighbour drove past with signal",
       "Borroloola", "cut-off", "high",
       "Total communications loss for the household — urgent in its own right (a household that cannot report further problems), consistent with the dropout-risk logic elsewhere in this system."),

    _m("M055", 389, "phone", "S055",
       "Caller states their diabetic teenage son is almost out of insulin and the pharmacy delivery has been delayed twice due to road closures.",
       "Katherine", "limited", "high",
       "Impending medication shortfall for a minor with a chronic condition — urgent, time-boxed before it becomes an emergency."),

    # ---------------------------------------------------------------
    # MEDIUM (40, +1 follow-up below) — ongoing issues affecting daily life, not danger
    # ---------------------------------------------------------------
    _m("M056", 22, "sms", "S056",
       "power has been out for a few hours, generator on standby",
       "Darwin", "normal", "medium",
       "Power outage of a few hours with a working contingency (generator) already in place — inconvenient, not an immediate risk."),

    _m("M057", 33, "webform", "S057",
       "We've had intermittent water pressure for the last two days, sometimes barely a trickle in the evenings.",
       "Palmerston", "normal", "medium",
       "Ongoing but non-acute utility issue affecting daily comfort, not a supply cut-off."),

    _m("M058", 46, "email", "S058",
       "I've called three times this week about my pension payment being short and haven't had a reply yet, this is getting frustrating.",
       "Darwin", "normal", "medium",
       "Escalating unresolved administrative complaint — not urgent in the safety sense, but repeated contact without response warrants timely follow-up."),

    _m("M059", 55, "sms", "S059",
       "bit of water come in under the back door last night, nothing major just soaked the mat",
       "Batchelor", "normal", "medium",
       "Minor storm-related water ingress with no structural or safety impact — worth logging, not urgent."),

    _m("M060", 68, "webform", "S060",
       "There's a large pothole that's filled with water on the corner of our street, a car nearly lost control there this morning.",
       "Katherine", "normal", "medium",
       "Road hazard with a near-miss already reported — meaningful risk if unaddressed, but no injury has occurred."),

    _m("M061", 79, "email", "S061",
       "We've had a rodent problem in the kitchen for about a week now, it's a health concern but nothing acute.",
       "Alice Springs", "normal", "medium",
       "Ongoing pest issue with a genuine but non-acute health dimension — unrelated to the Top End weather event."),

    _m("M062", 88, "sms", "S062",
       "internet's been down two days now, cant do my centrelink reporting online and worried about my payment",
       "Tennant Creek", "normal", "medium",
       "Loss of connectivity is affecting access to essential services (income support reporting) — a real but not safety-critical impact."),

    _m("M063", 101, "webform", "S063",
       "I have a specialist appointment next Tuesday and haven't received confirmation, I'm getting anxious it might have been cancelled.",
       "Darwin", "normal", "medium",
       "Administrative uncertainty causing genuine anxiety, but no immediate health or safety impact."),

    _m("M064", 114, "email", "S064",
       "This is the third overdue notice I've received for a bill I already paid, please can someone check your records.",
       "Palmerston", "normal", "medium",
       "Recurring billing dispute causing frustration — needs correction but is not time-critical."),

    _m("M065", 126, "sms", "S065",
       "fence blew down in the wind last night, dogs got out but we found them ok",
       "Jabiru", "normal", "medium",
       "Resolved minor incident (fence damage) reported for the record — no ongoing risk."),

    _m("M066", 137, "webform", "S066",
       "The streetlight outside our house has been out for two weeks and it's quite dark walking home from the bus stop.",
       "Katherine", "normal", "medium",
       "Ongoing safety-adjacent infrastructure issue (poor lighting) — worth prioritising over routine admin, not urgent."),

    _m("M067", 148, "sms", "S067",
       "power been out like 5 hrs now still no word when its back on",
       "Katherine", "normal", "medium",
       "Multi-hour outage with no ETA — a real inconvenience but no indication of danger or vulnerable dependents.",
       pair="FP3", style="informal"),

    _m("M068", 150, "email", "S068",
       "Our electricity supply has been disconnected for approximately five hours with no indication of a restoration timeframe.",
       "Katherine", "normal", "medium",
       "Same outage situation as M067, formally phrased — ongoing inconvenience, no safety indicators present.",
       pair="FP3", style="formal"),

    _m("M069", 159, "sms", "S069",
       "drain out front's completely blocked, whole yard's like a swamp now",
       "Humpty Doo", "normal", "medium",
       "Drainage failure causing property nuisance — needs attention, not urgent."),

    _m("M070", 167, "webform", "S070",
       "I submitted a complaint about noise from a neighbouring property two weeks ago and haven't heard anything since.",
       "Darwin", "normal", "medium",
       "Unresolved complaint with no update for two weeks — reasonable to chase up, not time-critical."),

    _m("M071", 176, "email", "S071",
       "The mobile reception here has been patchy since the storm, makes it hard to get through when I call.",
       "Nhulunbuy", "normal", "medium",
       "Degraded but not absent communications — an inconvenience worth logging given the wider weather event."),

    _m("M072", 184, "sms", "S072",
       "still waiting on someone to call back about the leak from last week, its not flooding just annoying now",
       "Palmerston", "normal", "medium",
       "Sender explicitly downgrades the urgency themselves — ongoing minor issue, follow-up is administrative."),

    _m("M073", 196, "webform", "S073",
       "Could someone confirm whether the community hall is still available for our meeting on Thursday given the weather?",
       "Batchelor", "normal", "medium",
       "Forward-looking logistics question tied to the weather event, but no immediate impact."),

    _m("M074", 205, "sms", "S074",
       "yard's flooded a bit but house is fine, just annoying getting to the car dry",
       "Katherine", "limited", "medium",
       "Localised, non-threatening flooding affecting convenience only — explicitly not affecting the dwelling itself."),

    _m("M075", 213, "email", "S075",
       "We've had ants getting into the pantry for a couple of weeks, probably from all the rain, nothing urgent.",
       "Darwin", "normal", "medium",
       "Minor pest issue plausibly linked to weather, sender frames it as non-urgent."),

    _m("M076", 221, "webform", "S076",
       "My last two payments have been the wrong amount and I'd like it looked into when possible.",
       "Alice Springs", "normal", "medium",
       "Billing discrepancy needing correction — administrative, not time-sensitive, unrelated to the weather event."),

    _m("M077", 230, "sms", "S077",
       "phone line crackly since the storm, can still make calls but hard to hear",
       "Jabiru", "normal", "medium",
       "Degraded service, not a full outage — worth noting given the broader event."),

    _m("M078", 244, "email", "S078",
       "I've been on hold or unanswered for three calls this week trying to update my address, could someone please assist.",
       "Palmerston", "normal", "medium",
       "Escalating administrative frustration from repeated unanswered contact — service-quality issue, not safety."),

    _m("M079", 252, "sms", "S079",
       "gutter's overflowing bad, water running down the wall a bit, not inside yet though",
       "Katherine", "normal", "medium",
       "Water ingress risk is developing but has not yet reached the interior — worth monitoring, not yet urgent."),

    _m("M080", 260, "webform", "S080",
       "The footpath near the shops has been slippery and uneven since the rain started, a few people have nearly slipped.",
       "Darwin", "normal", "medium",
       "Public hazard with near-misses reported but no injuries — worth prioritising over pure admin queries."),

    _m("M081", 269, "sms", "S081",
       "still no internet here 3 days now, missing my online centrelink appointment tomorrow if it's not back",
       "Wadeye", "limited", "medium",
       "Connectivity loss threatens a specific upcoming appointment — genuine but bounded impact."),

    _m("M082", 277, "email", "S082",
       "Our bin collection has been missed twice in a row and rubbish is starting to pile up, could this be fixed please.",
       "Tennant Creek", "normal", "medium",
       "Service-delivery complaint, unrelated to the weather event, no safety dimension."),

    _m("M083", 285, "sms", "S083",
       "mozzies are bad this year with all the standing water, worried about dengue round here",
       "Maningrida", "limited", "medium",
       "Public-health concern plausibly linked to flooding (mosquito-borne illness risk) — worth flagging for environmental health follow-up, not an acute case."),

    _m("M084", 294, "webform", "S084",
       "I'd like to query a late fee that was applied while I was without power and unable to make the payment online.",
       "Katherine", "limited", "medium",
       "Fee dispute directly tied to the outage — reasonable, not urgent."),

    _m("M085", 303, "email", "S085",
       "The community noticeboard information about road closures seems out of date, could it be refreshed?",
       "Batchelor", "normal", "medium",
       "Information-currency request tied to the event, low individual risk but has downstream value."),

    _m("M086", 311, "sms", "S086",
       "still a bit of water round the shed, nothing near the house, just letting you know",
       "Humpty Doo", "normal", "medium",
       "Explicitly low-impact status update — sender is proactively reassuring, not requesting urgent help."),

    _m("M087", 320, "webform", "S087",
       "I've noticed my last three letters from the department have gone to my old address despite updating it in April.",
       "Alice Springs", "normal", "medium",
       "Recurring administrative error needing correction — no urgency, unrelated to weather."),

    _m("M088", 329, "sms", "S088",
       "creek's up near the oval but nowhere near any houses, kids footy still went ahead this arvo",
       "Katherine", "normal", "medium",
       "Localised flooding with explicitly no impact on people or property — informational only."),

    _m("M089", 337, "email", "S089",
       "Could you please clarify whether flood-related payment extensions apply automatically or if I need to apply?",
       "Darwin", "normal", "medium",
       "Informational/process question prompted by the event, no immediate personal impact stated."),

    _m("M090", 346, "sms", "S090",
       "still a few puddles round but roads all open again here, thanks for the update earlier",
       "Batchelor", "normal", "medium",
       "Situation improving, sender is closing the loop — administrative/informational."),

    _m("M091", 355, "webform", "S091",
       "The bus shelter roof near our place has a hole letting rain through, minor but thought I'd flag it.",
       "Palmerston", "normal", "medium",
       "Minor public infrastructure defect, sender explicitly frames as minor."),

    _m("M092", 363, "email", "S092",
       "I wanted to follow up on a maintenance request from last month that still hasn't been actioned.",
       "Elliott", "normal", "medium",
       "Overdue routine maintenance follow-up, unrelated to weather event, no urgency indicators."),

    _m("M093", 374, "sms", "S093",
       "water's mostly gone down round our street now, just muddy, no damage to report",
       "Katherine", "normal", "medium",
       "Event resolving locally with no damage — informational close-out."),

    _m("M094", 381, "webform", "S094",
       "Could someone confirm when the community centre will reopen after being used as an evacuation point?",
       "Daly River area", "limited", "medium",
       "Forward-planning logistics question tied to the event, no immediate personal risk stated."),

    _m("M095", 390, "email", "S095",
       "My concession card renewal seems to be delayed, I sent the form in three weeks ago.",
       "Alice Springs", "normal", "medium",
       "Routine administrative delay, unrelated to weather, no urgency indicators."),

    # ---------------------------------------------------------------
    # LOW (55, +1 follow-up below) — routine, no time pressure or risk indicators
    # ---------------------------------------------------------------
    _m("M096", 6, "email", "S096",
       "Hi, just wondering when my community grant application renews. No rush.",
       "Darwin", "normal", "low",
       "Routine administrative query, no time pressure or risk indicators, sender explicitly notes 'no rush'."),

    _m("M097", 13, "webform", "S097",
       "Can you please tell me which forms I need for a change of address?",
       "Palmerston", "normal", "low",
       "Simple administrative request, no urgency indicators."),

    _m("M098", 18, "email", "S098",
       "The gutter on the eastern side of the property has a minor leak, not urgent, please attend when convenient.",
       "Darwin", "normal", "low",
       "Sender explicitly frames this as non-urgent, minor maintenance issue."),

    _m("M099", 29, "webform", "S099",
       "What are your office opening hours over the upcoming public holiday?",
       "Alice Springs", "normal", "low",
       "Routine informational query, no urgency indicators."),

    _m("M100", 37, "sms", "S100",
       "hey wen does my rego renewal thing come round again",
       "Tennant Creek", "normal", "low",
       "Routine renewal-date query, informal phrasing, no urgency indicators.",
       pair="FP4", style="informal"),

    _m("M101", 39, "webform", "S101",
       "Could you please advise the renewal date for my vehicle registration?",
       "Tennant Creek", "normal", "low",
       "Same routine renewal-date query as M100, formally phrased — no urgency indicators.",
       pair="FP4", style="formal"),

    _m("M102", 43, "email", "S102",
       "Just wanted to say thanks, the staff who helped me last month were fantastic and very patient.",
       "Darwin", "normal", "low",
       "Positive feedback, no action required, no urgency indicators."),

    _m("M103", 50, "webform", "S103",
       "Could I please get a copy of a form I submitted back in November?",
       "Katherine", "normal", "low",
       "Routine records request, no urgency indicators."),

    _m("M104", 54, "email", "S104",
       "Please remove me from the mailing list for the community newsletter, thanks.",
       "Palmerston", "normal", "low",
       "Simple opt-out administrative request."),

    _m("M105", 61, "sms", "S105",
       "just checking my application status when u get a chance no rush",
       "Yuendumu", "normal", "low",
       "Status check with sender explicitly indicating no time pressure."),

    _m("M106", 65, "webform", "S106",
       "Is it possible to pay my account by instalments going forward?",
       "Alice Springs", "normal", "low",
       "Routine process/eligibility question, no urgency indicators."),

    _m("M107", 70, "email", "S107",
       "The paint on the community sign near our street is peeling, purely cosmetic, no rush at all.",
       "Batchelor", "normal", "low",
       "Cosmetic issue explicitly flagged as non-urgent by the sender."),

    _m("M108", 75, "webform", "S108",
       "Could you send me the guidelines for the small business grant program please?",
       "Darwin", "normal", "low",
       "Routine information request, no urgency indicators."),

    _m("M109", 82, "sms", "S109",
       "hows the wait time on housing applications atm just wondering",
       "Katherine", "normal", "low",
       "General informational query, no urgency indicators."),

    _m("M110", 86, "email", "S110",
       "Wanted to compliment the webform, it was really easy to use this time, much better than before.",
       "Alice Springs", "normal", "low",
       "Positive feedback, no action required."),

    _m("M111", 90, "webform", "S111",
       "Can I update my preferred contact method to email instead of post?",
       "Tennant Creek", "normal", "low",
       "Routine account-preference update."),

    _m("M112", 95, "email", "S112",
       "The noise complaint I raised last month has been sorted, thanks for your help, no further action needed.",
       "Darwin", "normal", "low",
       "Complaint already resolved, informational close-out."),

    _m("M113", 99, "sms", "S113",
       "do i need an appointment or can i just walk in for the id form thing",
       "Palmerston", "normal", "low",
       "Routine process question, no urgency indicators."),

    _m("M114", 104, "webform", "S114",
       "Please could you update my surname on file following my recent marriage?",
       "Katherine", "normal", "low",
       "Routine records-update request."),

    _m("M115", 111, "email", "S115",
       "Is there a printed version of the seniors' concession guide available? Happy to wait for it in the post.",
       "Alice Springs", "normal", "low",
       "Routine information request, sender explicitly comfortable with a delay."),

    _m("M116", 116, "sms", "S116",
       "parking ticket i got last week was actually fine just wanted to confirm it went thru ok",
       "Darwin", "normal", "low",
       "Administrative confirmation request, no dispute or urgency."),

    _m("M117", 123, "webform", "S117",
       "Could you please unsubscribe this email address from all future notifications?",
       "Elliott", "normal", "low",
       "Simple opt-out request."),

    _m("M118", 131, "email", "S118",
       "I'd like to nominate a staff member for an appreciation award, she went above and beyond helping my dad.",
       "Katherine", "normal", "low",
       "Positive feedback / commendation, no action required beyond acknowledgement."),

    _m("M119", 139, "webform", "S119",
       "What's the best way to submit feedback on the new online portal design?",
       "Darwin", "normal", "low",
       "Routine meta/process question."),

    _m("M120", 145, "sms", "S120",
       "small crack in the footpath outside ours, tripped a bit but im fine, no rush to fix",
       "Batchelor", "normal", "low",
       "Minor hazard explicitly downplayed by the sender, no injury, no urgency."),

    _m("M121", 154, "email", "S121",
       "Could someone confirm my last payment was received, just for my own records?",
       "Palmerston", "normal", "low",
       "Routine confirmation request."),

    _m("M122", 161, "webform", "S122",
       "I'd like to update my emergency contact details on file when convenient.",
       "Alice Springs", "normal", "low",
       "Routine records update, no urgency indicators despite the word 'emergency' referring to a static field, not an event."),

    _m("M123", 169, "sms", "S123",
       "hows it going with the community garden proposal we sent in ages ago",
       "Katherine", "normal", "low",
       "General status check, no time pressure."),

    _m("M124", 174, "email", "S124",
       "The new bins are great, much easier to use than the old ones, just wanted to say so.",
       "Darwin", "normal", "low",
       "Positive feedback, no action required."),

    _m("M125", 182, "webform", "S125",
       "Please could you send me a receipt for a payment I made last week?",
       "Tennant Creek", "normal", "low",
       "Routine documentation request."),

    _m("M126", 190, "sms", "S126",
       "wat documents do i need to bring for the id renewal appointment",
       "Alice Springs", "normal", "low",
       "Routine process question."),

    _m("M127", 199, "email", "S127",
       "Could you clarify the eligibility criteria for the youth sports grant please?",
       "Palmerston", "normal", "low",
       "Routine information request."),

    _m("M128", 207, "webform", "S128",
       "I'd like to opt in to SMS reminders instead of phone calls for future appointments.",
       "Darwin", "normal", "low",
       "Routine contact-preference update."),

    _m("M129", 215, "sms", "S129",
       "just letting u know i moved house, new address coming thru the form soon no rush on ur end",
       "Katherine", "normal", "low",
       "Routine notification, sender explicitly indicates no urgency."),

    _m("M130", 223, "email", "S130",
       "Thanks for sorting my query so quickly last time, wanted to pass that on.",
       "Darwin", "normal", "low",
       "Positive feedback, no action required."),

    _m("M131", 232, "webform", "S131",
       "Is the community hall available to hire for a birthday party next month?",
       "Batchelor", "normal", "low",
       "Routine booking enquiry."),

    _m("M132", 240, "sms", "S132",
       "wen is the next intake for the training program u guys run",
       "Yuendumu", "normal", "low",
       "Routine informational query."),

    _m("M133", 247, "email", "S133",
       "Could you please confirm the postal address for lodging paper forms?",
       "Alice Springs", "normal", "low",
       "Routine information request."),

    _m("M134", 255, "webform", "S134",
       "I'd like to provide feedback that the wait music on the phone line is quite loud, minor thing.",
       "Darwin", "normal", "low",
       "Minor feedback explicitly framed as trivial."),

    _m("M135", 264, "sms", "S135",
       "got the letter thanks, all good, nothing needed from me right",
       "Katherine", "normal", "low",
       "Simple acknowledgement, no action required."),

    _m("M136", 271, "email", "S136",
       "Just checking whether the concession renewal I sent last month has been processed yet.",
       "Palmerston", "normal", "low",
       "Routine status check."),

    _m("M137", 280, "webform", "S137",
       "Could you please add a second contact number to my file?",
       "Tennant Creek", "normal", "low",
       "Routine records update."),

    _m("M138", 288, "sms", "S138",
       "hows the queue looking for appointments this week just curious",
       "Alice Springs", "normal", "low",
       "General informational query."),

    _m("M139", 296, "email", "S139",
       "Wanted to let you know the online chat feature worked really well when I used it yesterday.",
       "Darwin", "normal", "low",
       "Positive feedback, no action required."),

    _m("M140", 307, "webform", "S140",
       "Please could you re-send the confirmation email, I think I deleted the original by mistake.",
       "Katherine", "normal", "low",
       "Routine re-send request."),

    _m("M141", 315, "sms", "S141",
       "quick one, is the office open this sat morning or just weekdays",
       "Palmerston", "normal", "low",
       "Routine informational query."),

    _m("M142", 322, "email", "S142",
       "I'd like to update my preferred name on correspondence going forward, no rush.",
       "Darwin", "normal", "low",
       "Routine records update, explicitly no time pressure."),

    _m("M143", 333, "webform", "S143",
       "Could you clarify whether the community feedback session is still going ahead this month?",
       "Batchelor", "normal", "low",
       "Routine logistics question."),

    _m("M144", 341, "sms", "S144",
       "cheers for the quick reply last time just following up on the same thing again",
       "Katherine", "normal", "low",
       "Routine, low-stakes follow-up."),

    _m("M145", 349, "email", "S145",
       "Is there a fee waiver available for pensioners applying for a replacement card?",
       "Alice Springs", "normal", "low",
       "Routine eligibility question."),

    _m("M146", 361, "webform", "S146",
       "I noticed a small typo on the website FAQ page, thought I'd flag it, not urgent at all.",
       "Darwin", "normal", "low",
       "Trivial, explicitly non-urgent feedback."),

    _m("M147", 369, "sms", "S147",
       "just wanted to say thanks to the fella who helped me out on the phone yesterday, real patient bloke",
       "Elliott", "normal", "low",
       "Positive feedback, no action required."),

    _m("M148", 378, "email", "S148",
       "Could you please confirm my next renewal is not due until next year as I understood it?",
       "Tennant Creek", "normal", "low",
       "Routine confirmation request."),

    _m("M149", 385, "webform", "S149",
       "I'd like to be added to the waitlist for the next community workshop, whenever that is.",
       "Katherine", "normal", "low",
       "Routine, open-ended registration request."),

    _m("M150", 396, "sms", "S150",
       "no dramas here just wanted to confirm u got my form from last week thats all",
       "Palmerston", "normal", "low",
       "Simple confirmation request, no urgency indicators."),

    # ---------------------------------------------------------------
    # Silent follow-ups (deliberately omitted) — used to demonstrate
    # the dropout detector. Left as comments so it's clear the missing
    # message is intentional, not an authoring gap.
    #
    # S001 (M001, critical, t=4) never sends a follow-up -> should flag
    #   as dropout once the 2-hour critical threshold passes (t=124+).
    # S004 (M004, critical, t=15) never sends a follow-up -> flags
    #   after t=135.
    # S030 (M030, high, t=66) never follows up -> flags after the
    #   6-hour high threshold (t=426), near the end of the shift.
    #
    # Control cases (sender DOES follow up -> should NOT flag):
    # S003 sends M003 (t=11) then a relieved follow-up below (M151).
    # S011 sends M011 (t=105) then a follow-up below (M152).
    # ---------------------------------------------------------------

    _m("M151", 260, "sms", "S003",
       "power and phone back on now, water going down too, we're ok thanks for checking in",
       "Peppimenarti", "normal", "low",
       "Follow-up all-clear from a sender whose earlier message was critical — situation has resolved."),

    _m("M152", 210, "sms", "S011",
       "electrician came and cut power to that circuit, roof tarped for now, we're staying at my sisters tonight anyway",
       "Katherine", "normal", "medium",
       "Follow-up from a sender whose earlier message was critical — immediate hazard has been mitigated, though housing situation is still not fully resolved."),
]


def get_sample_messages():
    """Returns the demo dataset, filtering out placeholder/no-message rows."""
    return [m for m in SAMPLE_MESSAGES if m.get("raw_text")]


def get_sender_history(sender_id: str, up_to_time: datetime):
    """
    Returns all messages from a given sender up to a point in time,
    sorted oldest to newest — used by the dropout detector.
    """
    history = [
        m for m in SAMPLE_MESSAGES
        if m["sender_id"] == sender_id and m["timestamp"] <= up_to_time and m.get("raw_text")
    ]
    return sorted(history, key=lambda m: m["timestamp"])


def get_fairness_pairs():
    """
    Groups messages sharing a fairness_pair tag into
    {pair_id: {"informal": msg, "formal": msg}} for the fairness audit.
    """
    pairs = {}
    for m in SAMPLE_MESSAGES:
        if not m.get("fairness_pair"):
            continue
        pairs.setdefault(m["fairness_pair"], {})[m["fairness_style"]] = m
    return pairs
