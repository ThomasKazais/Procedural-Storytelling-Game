import random
from typing import Dict, Any, List, Tuple
from collections import deque, defaultdict
from enhanced_passages import enhanced_passages
from llm import generate_ai_micro_choice, paraphrase_via_llm

import math

NOVELTY_BASE = 0.60                  # δύναμη εξερεύνησης στη μέση του γράφου
NOVELTY_DECAY = 6.0                  # το novelty μειώνεται καθώς προχωράει η ιστορία
NOVELTY_CAP_NEAR_TERMINAL = 0.35     # για σταθεροποίηση στο τέλος του παιχνιδιού
CLUSTER_EXIT_BONUS = 0.15            # ενθάρρυνση εξόδου από την ίδια περιοχή


def _novelty_term(depth: int, visit_counts: dict, nxt: str) -> float:
    v = visit_counts.get(nxt, 0)
    base = NOVELTY_BASE * (1.0 / (1.0 + v))
    return base * math.exp(-depth / NOVELTY_DECAY)

def _novelty_cap(depth: int) -> float:
    return NOVELTY_CAP_NEAR_TERMINAL * math.exp(-depth / NOVELTY_DECAY)


def _cluster_switch_mult(src: str, dst: str) -> float:
    a = _scene_group(src)
    b = _scene_group(dst)
    return (1.0 + CLUSTER_EXIT_BONUS) if (a and b and a != b) else 1.0

# ===================
# PLAYER STATE
# ===================
player_state: Dict[str, Any] = {
    "flags": {
        "has_map": False,
        "heard_red_stone": False
    },
    "inventory": {
        "gold": 5,
        "shiny_stone": False,
        "dagger": False,
        "red_stone": False,
        "pelt": 0,
        "silk": 0
    },
    "traits": {
        "greedy": 0,
        "brave": 1,
        "honor": 0
    },
    "relationships": {
        "elder": 0
    },
    "quests": {
        
    },
    "turn": 0
}

# Βάρη καταστάσεων προορισμού για προσαρμοστικό ρυθμό (soft reinforcement)
transition_weights: Dict[str, float] = {scene_id: 1.0 for scene_id in enhanced_passages.keys()}

MIN_PROB_FLOOR = 0.05
LEARNING_RATE = 0.25

# Παρακολούθηση για αποφυγή βρόγχων
RECENT_WINDOW = 8
recent_states = deque(maxlen=RECENT_WINDOW)

# Cooldowns επιλογών σε επίπεδο ακμής
choice_cooldowns: dict[tuple[str, str], int] = {}
DEFAULT_COOLDOWN = 3  # turns

# Cooldowns σε επίπεδο state (αποφυγή ping-pong φαινομένου)
state_cooldowns: dict[str, int] = {}
STATE_COOLDOWN = 3  # γυροι;

# Επισκέψεις για ενίσχυση του novelty (bonus εξερεύνησης)
visit_counts = defaultdict(int)

ai_generated_choices: Dict[tuple, Dict[str, Any]] = {}
AI_EXTRA_CHOICE_ENABLED = True
AI_MIN_CHOICES_TRIGGER = 2   
AI_EARLIEST_TURN = 1         

# βοηθητικές συναρτήσεις (ARC NUDGE) για το κύριο quest
ARC_EDGES = {
    ("village_outskirts", "enter_the_dark_forest"),
    ("enter_the_dark_forest", "mysterious_cave"),
    ("sneak_around_wolves", "mysterious_cave"),
    ("ridge_overlook", "enter_the_mine"),
    ("mysterious_cave", "enter_the_mine"),
    ("enter_the_mine", "search_deeper_for_gem"),
}


# ===================
# REQUIREMENTS ENGINE
# ===================

def _red_stone_active(st: Dict[str, Any]) -> bool:
    q = st.get("quests", {}).get("red_stone", None)
    return bool(q) and not q.get("completed", False)

def _arc_multiplier(src: str, dst: str, st: Dict[str, Any]) -> float:
    if not _red_stone_active(st):
        return 1.0
    return 1.25 if (src, dst) in ARC_EDGES else 1.0

def _req_has_flag(st: Dict[str, Any], flag: str) -> bool:
    return bool(st["flags"].get(flag, False))

def _req_not_flag(st: Dict[str, Any], flag: str) -> bool:
    return not bool(st["flags"].get(flag, False))

def _req_has_item(st: Dict[str, Any], item: str) -> bool:
    val = st["inventory"].get(item, False)
    if isinstance(val, bool):
        return val
    return (isinstance(val, (int, float)) and val > 0)

def _req_gte_item(st: Dict[str, Any], mapping: Dict[str, Any]) -> bool:
    for k, v in mapping.items():
        if st["inventory"].get(k, 0) < v:
            return False
    return True

def _req_gte_trait(st: Dict[str, Any], mapping: Dict[str, Any]) -> bool:
    for k, v in mapping.items():
        if st["traits"].get(k, 0) < v:
            return False
    return True

def _req_gte_rel(st: Dict[str, Any], mapping: Dict[str, Any]) -> bool:
    for k, v in mapping.items():
        if st["relationships"].get(k, 0) < v:
            return False
    return True

def _req_quest_active(st: Dict[str, Any], qid: str) -> bool:
    return qid in st["quests"] and not st["quests"][qid].get("completed", False)

def _req_quest_stage_at_least(st: Dict[str, Any], mapping: Dict[str, Any]) -> bool:
    for qid, stage in mapping.items():
        if st["quests"].get(qid, {}).get("stage", -1) < stage:
            return False
    return True

def _scene_group(state_id: str) -> str:
    if state_id in {"village_square","visit_blacksmiths_forge","notice_board",
                    "training_yard","greet_the_elder","elder_reveals_treasure_hint",
                    "ask_for_the_map_price"}:
        return "village"
    if state_id in {"village_outskirts","enter_the_dark_forest","fight_wolves",
                    "sneak_around_wolves","forest_camp","ridge_overlook"}:
        return "forest"
    if state_id in {"mysterious_cave","enter_the_mine","search_deeper_for_gem",
                    "fight_cave_spider","side_chamber"}:
        return "cave"
    if state_id in {"follow_the_road_to_another_town","capital_city_gates",
                    "explore_capital_streets"}:
        return "road"
    return "unknown"


def check_requires(st: Dict[str, Any], requires: List[Dict[str, Any]]) -> bool:
    if not requires:
        return True
    for cond in requires:
        if "has_flag" in cond and not _req_has_flag(st, cond["has_flag"]):
            return False
        if "not_flag" in cond and not _req_not_flag(st, cond["not_flag"]):
            return False
        if "has_item" in cond and not _req_has_item(st, cond["has_item"]):
            return False
        if "gte_item" in cond and not _req_gte_item(st, cond["gte_item"]):
            return False
        if "gte_trait" in cond and not _req_gte_trait(st, cond["gte_trait"]):
            return False
        if "gte_rel" in cond and not _req_gte_rel(st, cond["gte_rel"]):
            return False
        if "quest_active" in cond and not _req_quest_active(st, cond["quest_active"]):
            return False
        if "quest_stage_at_least" in cond and not _req_quest_stage_at_least(st, cond["quest_stage_at_least"]):
            return False
    return True

def soft_decay_transition_weights(factor=0.995):
    for k in transition_weights:
        transition_weights[k] = max(MIN_PROB_FLOOR, transition_weights[k] * factor)

# ===================
# EFFECTS ENGINE
# ===================
def _eff_set_flag(st: Dict[str, Any], mapping: Dict[str, Any]) -> None:
    for k, v in mapping.items():
        st["flags"][k] = bool(v)

def _eff_add_item(st: Dict[str, Any], mapping: Dict[str, Any]) -> None:
    for k, v in mapping.items():
        cur = st["inventory"].get(k, 0)
        if isinstance(cur, bool):
            cur = 1 if cur else 0
        st["inventory"][k] = max(0, cur + v)

def _eff_set_item(st: Dict[str, Any], mapping: Dict[str, Any]) -> None:
    for k, v in mapping.items():
        st["inventory"][k] = v

def _eff_add_trait(st: Dict[str, Any], mapping: Dict[str, Any]) -> None:
    for k, v in mapping.items():
        st["traits"][k] = st["traits"].get(k, 0) + v

def _eff_add_rel(st: Dict[str, Any], mapping: Dict[str, Any]) -> None:
    for k, v in mapping.items():
        st["relationships"][k] = st["relationships"].get(k, 0) + v

def _eff_quest_add(st: Dict[str, Any], mapping: Dict[str, Any]) -> None:
    qid = mapping.get("id")
    stage = mapping.get("stage", 0)
    if not qid:
        return

    quests = st.setdefault("quests", {})
    existing = quests.get(qid)


    if existing is None:
        quests[qid] = {"stage": stage, "completed": False}
        return

    try:
        existing_stage = int(existing.get("stage", 0))
    except Exception:
        existing_stage = 0

    try:
        incoming_stage = int(stage)
    except Exception:
        incoming_stage = existing_stage

    existing["stage"] = max(existing_stage, incoming_stage)

    existing["completed"] = bool(existing.get("completed", False))

def _eff_quest_stage(st: Dict[str, Any], mapping: Dict[str, Any]) -> None:
    qid = mapping.get("id")
    stage = mapping.get("stage")
    if qid and qid in st["quests"] and stage is not None:
        st["quests"][qid]["stage"] = stage

def _eff_quest_complete(st: Dict[str, Any], qid: str) -> None:
    if qid in st["quests"]:
        st["quests"][qid]["completed"] = True

def apply_effects(st: Dict[str, Any], effects: List[Dict[str, Any]]) -> List[str]:
    msgs: List[str] = []
    if not effects:
        return msgs
    for eff in effects:
        if "msg" in eff:
            m = eff["msg"]
            if isinstance(m, str):
                if m.strip():
                    msgs.append(m.strip())
            elif isinstance(m, (list, tuple)):
                for x in m:
                    if isinstance(x, str) and x.strip():
                        msgs.append(x.strip())
        if "set_flag" in eff:
            _eff_set_flag(st, eff["set_flag"])
            msgs.append(f"Flag(s) updated: {list(eff['set_flag'].keys())}")
        if "add_item" in eff:
            _eff_add_item(st, eff["add_item"])
            for k, v in eff["add_item"].items():
                if v != 0:
                    msgs.append(f"{'Gained' if v>0 else 'Spent'} {abs(v)} {k}.")
        if "set_item" in eff:
            _eff_set_item(st, eff["set_item"])
            msgs.append(f"Items set: {list(eff['set_item'].keys())}")
        if "add_trait" in eff:
            _eff_add_trait(st, eff["add_trait"])
            msgs.append("Your disposition shifts.")
        if "add_rel" in eff:
            _eff_add_rel(st, eff["add_rel"])
            msgs.append("Your relationships changed.")
        if "quest_add" in eff:
            _eff_quest_add(st, eff["quest_add"])
            msgs.append(f"New quest started: {eff['quest_add'].get('id')}")
        if "quest_stage" in eff:
            _eff_quest_stage(st, eff["quest_stage"])
            msgs.append(f"Quest advanced: {eff['quest_stage'].get('id')} → stage {eff['quest_stage'].get('stage')}")
        if "quest_complete" in eff:
            _eff_quest_complete(st, eff["quest_complete"])
            msgs.append(f"Quest completed: {eff['quest_complete']}")
    return msgs

def elder_dialogue(st: Dict[str, Any]) -> str:
    """Traits/flags/quest-aware Elder response, lightly enriched by the LLM."""
    lines = []
    honor = st["traits"].get("honor", 0)
    greedy = st["traits"].get("greedy", 0)
    rel = st["relationships"].get("elder", 0)
    red = st["quests"].get("red_stone", {})
    heard = st["flags"].get("heard_red_stone", False)

    if rel >= 1 or honor >= 1:
        lines.append("The elder smiles kindly. 'You carry yourself with care.'")
    if greedy >= 2 and honor <= 0:
        lines.append("The elder frowns. 'Gold can blind even a sharp eye.'")
    if heard and red.get("stage", -1) >= 1:
        lines.append("He reminds you: 'Wolves at dusk, a cave with a faint glow—tread carefully.'")
    if red.get("completed", False):
        lines.append("He nods, relieved. 'You did well to return with the stone.'")
    if not lines:
        lines.append("He strokes his beard. 'Our village keeps many small truths in the quiet.'")

    base = " ".join(lines)
    return paraphrase_via_llm(base, "elder_dialogue", tone="reverent", style="minimal")

def merchant_dialogue(st: Dict[str, Any]) -> str:
    """Contextual Merchant line about the map / trade, LLM-polished."""
    gold = st["inventory"].get("gold", 0)
    has_map = st["flags"].get("has_map", False)
    shiny = bool(st["inventory"].get("shiny_stone", False))
    heard = st["flags"].get("heard_red_stone", False)

    if has_map:
        base = "The merchant chuckles. 'You already have the parchment—may it guide you well.'"
    elif gold >= 5:
        base = "He eyes your pouch. 'Five coins and the map is yours.'"
    elif shiny:
        base = "He rubs his chin. 'That shiny stone could seal a fair trade.'"
    else:
        base = "He spreads his hands. 'Five gold or a worthy trinket. Rumor says the cave lies past the wolves.'"
        if not heard:
            base += " 'Ask the elder if you want a clearer lead.'"
    return paraphrase_via_llm(base, "merchant_dialogue", tone="merchant", style="minimal")

def maybe_inject_ai_choice(passage_id: str, st: Dict[str, Any], tone: str | None, choices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not AI_EXTRA_CHOICE_ENABLED:
        return choices
    if st.get("turn", 0) < AI_EARLIEST_TURN:
        return choices
    if len(choices) >= AI_MIN_CHOICES_TRIGGER:
        return choices
    snapshot_key = (
        passage_id,
        # flags που επηρεάζουν την πορεία της ιστορίας
        bool(st.get("flags", {}).get("heard_red_stone", False)),
        int(st.get("inventory", {}).get("gold", 0) >= 3),
        int(st.get("traits", {}).get("brave", 0)),
    )

    # Αν έχουμε ήδη παράγει για αυτό το context, επαναχρησιμοποιούμε (αν δεν είναι duplicate)
    if snapshot_key in ai_generated_choices:
        cached = ai_generated_choices[snapshot_key]
        if not any((c.get("text") == cached.get("text") and c.get("next") == cached.get("next")) for c in choices):
            return choices + [cached]
        return choices


    group = _scene_group(passage_id)
    snapshot = {
        "inventory": st.get("inventory", {}),
        "traits": st.get("traits", {}),
        "flags": st.get("flags", {}),
    }
    ai_ch = generate_ai_micro_choice(passage_id, group, tone, snapshot)
    if ai_ch:
        ai_generated_choices[snapshot_key] = ai_ch
        if not any((c.get("text") == ai_ch.get("text") and c.get("next") == ai_ch.get("next")) for c in choices):
            return choices + [ai_ch]
    return choices

def _event_fired_key(passage_id: str, idx: int) -> str:
    return f"_evfired::{passage_id}::{idx}"

def enter_state(passage_id: str, st: Dict[str, Any]) -> List[str]:
    """
    Apply event effects exactly once when entering a state.
    Returns any messages generated by those effects.
    """
    data = enhanced_passages.get(passage_id, {})
    if not data:
        return []

    msgs: List[str] = []
    flags = st.setdefault("flags", {})

    for i, ev in enumerate(data.get("events", [])):
        cond = ev.get("condition")
        if callable(cond) and cond(st):
            key = _event_fired_key(passage_id, i)
            if flags.get(key, False):
                continue  # already fired once
            flags[key] = True

            ev_effs = ev.get("effects") or []
            if ev_effs:
                msgs.extend(apply_effects(st, ev_effs))

    return msgs

# ===================
# PASSAGE RENDERING
# ===================
def get_storylet_passage(passage_id: str, st: Dict[str, Any]) -> Dict[str, Any]:
    data = enhanced_passages[passage_id]
    text_parts = [data.get("base_text", "")]
    tone = data.get("tone")

    for ev in data.get("events", []):
        cond = ev.get("condition")
        if callable(cond) and cond(st):
            text_parts.append(ev.get("inject", ""))

    available_choices: List[Dict[str, Any]] = []
    for ch in data.get("choices", []):
        cond_ok = True
        if "requires" in ch:
            cond_ok = check_requires(st, ch["requires"])
        cond_lambda = ch.get("condition")
        if cond_ok and callable(cond_lambda):
            cond_ok = bool(cond_lambda(st))
        if cond_ok:
            available_choices.append({
                "text": ch["text"],
                "next": ch["next"],
                "effects": ch.get("effects", []),
                "dynamic_msg": ch.get("dynamic_msg"),
                "cooldown": ch.get("cooldown", DEFAULT_COOLDOWN)
            })

    available_choices = maybe_inject_ai_choice(passage_id, st, tone, available_choices)

    return {
        "tone": tone,
        "text": "\n".join(tp for tp in text_parts if tp),
        "choices": available_choices
    }

# ===================
# WEIGHTED SELECTION + LOOP AVOIDANCE
# ===================
def bump_transition_weight(next_state: str):
    global transition_weights
    for k in list(transition_weights.keys()):
        if k == next_state:
            transition_weights[k] = transition_weights.get(k, 1.0) + LEARNING_RATE
        else:
            transition_weights[k] = max(MIN_PROB_FLOOR, transition_weights.get(k, 1.0) * (1.0 - LEARNING_RATE/10))

def is_loopy_transition(src: str, dst: str) -> bool:
    if not recent_states:
        return False
    if len(recent_states) >= 1 and recent_states[-1] == dst:
        return True
    return list(recent_states).count(dst) >= 2

def cooldown_remaining(src: str, dst: str) -> int:
    return max(0, choice_cooldowns.get((src, dst), 0))

def apply_cooldowns_decay():
    for key in list(choice_cooldowns.keys()):
        choice_cooldowns[key] = max(0, choice_cooldowns[key] - 1)
        if choice_cooldowns[key] == 0:
            choice_cooldowns.pop(key, None)
    for s in list(state_cooldowns.keys()):
        state_cooldowns[s] = max(0, state_cooldowns[s] - 1)
        if state_cooldowns[s] == 0:
            state_cooldowns.pop(s, None)


def order_choices_by_weight(src_state: str, choices: List[Dict[str, Any]], st: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Scores choices using:
      - base transition weight (your soft reinforcement),
      - loop penalty,
      - edge cooldown penalty,
      - novelty bonus (prefer less-visited destinations),
      - small arc nudge along the red_stone spine (when active).

    'st' is optional for back-compat; we fall back to global player_state.
    """
    if st is None:
        # Συμβατότητα με παλιές κλήσεις (χρησιμοποιούμε το globar player_state) αν δεν δόθηκε
        try:
            current_st = player_state
        except NameError:
            current_st = {}
    else:
        current_st = st

    depth = int(current_st.get("turn",0))

    def score(ch: Dict[str, Any]) -> float:
        dst = ch["next"]
        base = transition_weights.get(dst, 1.0)

        # ποινές για βρόγχους και cooldowns
        penalty = 1.0
        if is_loopy_transition(src_state, dst):
            penalty *= 0.25
        cd = cooldown_remaining(src_state, dst)
        if cd > 0:
            penalty *= max(0.2, 1.0 - 0.2 * cd)

        if state_cooldowns.get(dst, 0) > 0:
            penalty *= 0.85

        # novelty με όριο στο τέλος του παιχνιδιού
        n = _novelty_term(depth, visit_counts, dst)
        n = min(n, _novelty_cap(depth))
        novelty_mult = 1.0 + n  

        # πολλαπλασιαστής εξόδου απο την ίδια περιοχή
        cluster_mult = _cluster_switch_mult(src_state, dst)

        # επιπλέον αποφυγή στο πήγαινε-έλα
        if _scene_group(src_state) == "road" and _scene_group(dst) == "road":
            penalty *= 0.75

        # ηπια ώθηση για το κυριο quest
        arc = _arc_multiplier(src_state, dst, current_st)

        # Αν ο παίκτης έχει αρκετό gold ενισχύουμαι την επιλογή αγοράς dagger
        if src_state == "visit_blacksmiths_forge":
            can_afford = current_st.get("inventory", {}).get("gold", 0) >= 3
            has_dagger = bool(current_st.get("inventory", {}).get("dagger", False))
            if can_afford and not has_dagger:
                # εντοπισμός της επιλογής αγοράς μέσω των effects
                effs = ch.get("effects", [])
                is_buy = any(("set_item" in e and e["set_item"].get("dagger") is True) for e in effs)
                if is_buy:
                    # ήπια αλλα σαφής ενίσχυση
                    return (base * penalty * novelty_mult * cluster_mult * arc) * 1.50
        
        # Αν είμαστε στο δρόμο και δεν έχουμε ακούσει την "φήμη" ,μικρή ώθηση προς το να βγει εκτός χωριού για το quest
        if _scene_group(src_state) == "road" and not current_st.get("flags", {}).get("heard_red_stone", False):
            if ch["next"] in ("village_outskirts", "village_square"):
                return (base * penalty * novelty_mult * cluster_mult * arc) * 1.25

        return base * penalty * novelty_mult * cluster_mult * arc

    return sorted(choices, key=score, reverse=True)

# ===================
# QUEST GENERATOR (stub)
# ===================
def generate_quest(st: Dict[str, Any]) -> Dict[str, Any]:
    targets = ["mysterious_cave", "visit_blacksmiths_forge", "capital_city_gates"]
    target = random.choice(targets)
    reward_gold = random.choice([2,3,4])
    return {"id": f"side_{target}", "stage": 0, "target": target, "reward": {"gold": reward_gold}}

# ===================
# PUBLIC API
# ===================
def init_game() -> None:
    pass

def tick_turn(st: Dict[str, Any], current_state: str | None = None) -> None:
    st["turn"] += 1
    apply_cooldowns_decay()
    # ήπια μείωση βαρών κάθε 5 γύρους για να αποφύγουμε υπερβολική καθοδήγηση
    if st["turn"] % 5 == 0:
        soft_decay_transition_weights(0.99)
    if current_state:
        recent_states.append(current_state)
        visit_counts[current_state] = visit_counts.get(current_state, 0) + 1

def apply_choice_and_advance(st: Dict[str, Any], src_state: str, choice: Dict[str, Any]) -> Tuple[str, List[str]]:
    messages: List[str] = []

    # δυναμικός διάλογος που αξιολογείται τη στιγμή της επιλογής
    dyn = choice.get("dynamic_msg")
    if dyn == "elder_dialogue":
        try:
            messages.append(elder_dialogue(st))
        except Exception:
            messages.append("The elder murmurs something you can't quite catch.")
    elif dyn == "merchant_dialogue":
        try:
            messages.append(merchant_dialogue(st))
        except Exception:
            messages.append("The merchant hums, lost in thought.")

    # εφαρμογή κανονικών (στατικών) effects
    messages += apply_effects(st, choice.get("effects", []))
    next_state = choice["next"]
    # Εφαρμογή των on-enter events
    messages.extend(enter_state(next_state, st))
    bump_transition_weight(next_state)
    cool = int(choice.get("cooldown", DEFAULT_COOLDOWN))
    choice_cooldowns[(src_state, next_state)] = max(0, cool)
    state_cooldowns[src_state] = max(state_cooldowns.get(src_state, 0), STATE_COOLDOWN)
    return next_state, messages
