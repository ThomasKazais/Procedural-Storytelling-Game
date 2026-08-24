
from typing import Optional, Dict, Any, List, Tuple
import os
import json
import re
from functools import lru_cache

# Χρησιμοποιούμε OpenAI-compatible client ώστε να δουλεύει και με OpenRouter
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

TEMPERATURE = 0.3
MAX_TOKENS = 110
TOP_P = 0.7
FREQUENCY_PENALTY = 0.2
PRESENCE_PENALTY = 0.0

# Αναγνώριση κλειδιού από μεταβλητές περιβάλλοντος
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
OPENAI_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
# Το API key δεν αποθηκεύεται στον κώδικα. Ορίζεται μόνο ως environment variable.
# Σειρά fallback μοντέλων
MODEL_FALLBACK = [
    "mistralai/mistral-7b-instruct",
    "nousresearch/nous-hermes-2-mixtral",
    "gpt-3.5-turbo" 
]


_client = None
if OpenAI is not None and OPENAI_API_KEY:
    _client = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)

CACHE_VERSION = "v2"

STYLE_PRESETS = {
    "minimal": "Very brief. 1–3 short sentences. Plain, concrete verbs. No new facts.",
    "vivid": "2–3 sentences with light sensory detail. Still concise. No new lore.",
}

def _style_text(style: Optional[str]) -> str:
    if not style:
        style = "minimal"
    return STYLE_PRESETS.get(style, STYLE_PRESETS["minimal"])

def _make_system_prompt(base_prompt: str, tone: Optional[str], style: Optional[str]) -> str:
    tone_part = f" Use a {tone} tone." if tone else ""
    return (
        base_prompt.strip()
        + tone_part
        + " Paraphrase faithfully for a narrative game scene. "
          "Keep tense and POV consistent with the input. "
          "Avoid flowery language, metaphors, and long clauses. "
        + " "
        + _style_text(style)
        + f" [cache:{CACHE_VERSION}]"
    )

@lru_cache(maxsize=256)
def _cached_paraphrase(
    model: str,
    system_prompt: str,
    user_text: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    freq_penalty: float,
    pres_penalty: float,
) -> Optional[str]:
    """
    Cache key now includes decoding params so your changes take effect.
    """
    if _client is None:
        # Χωρίς client ,επιστρέφουμε None ώστε να το χειριστεί η paraphrase_via_llm
        return None

    try:
        resp = _client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=freq_penalty,
            presence_penalty=pres_penalty,
        )
        output = (resp.choices[0].message.content or "").strip()
        return output or None
    except Exception:

        return None

def paraphrase_via_llm(
    text: str,
    state: str,
    tone: Optional[str] = None,
    model: Optional[str] = None,
    style: Optional[str] = "minimal",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    ) -> str:
    """
    Paraphrase scene narration only (leave choices fixed).
    style: "minimal" (default) or "vivid".
    """
    if _client is None:
        return text

    base_prompt = f"You are narrating the scene '{state}'."
    system_prompt = _make_system_prompt(base_prompt, tone, style)

    t = TEMPERATURE if temperature is None else float(temperature)
    mt = MAX_TOKENS if max_tokens is None else int(max_tokens)

    model_to_use = model or MODEL_FALLBACK[0]
    tried = set()
    for m in [model_to_use] + MODEL_FALLBACK:
        if m in tried:
            continue
        tried.add(m)
        out = _cached_paraphrase(
            m, system_prompt, text, t, mt, TOP_P, FREQUENCY_PENALTY, PRESENCE_PENALTY
        )
        if out:
            return out
    return text

# ==============================
#  AI MICRO-CHOICE
# ==============================

# Επιτρεπόμενα effects και επόμενα states ανά ομάδα περιοχών
ALLOWED_EFFECT_TRAITS = {"brave", "honor", "greedy"}
ALLOWED_EFFECT_ITEMS = {"gold", "pelt", "silk", "shiny_stone"}
ALLOWED_FLAGS = {"heard_red_stone"} 

ALLOWED_NEXT_BY_GROUP = {
    "village": ["village_square", "notice_board", "training_yard", "visit_blacksmiths_forge", "village_outskirts"],
    "forest": ["enter_the_dark_forest", "mysterious_cave", "forest_camp", "ridge_overlook", "village_outskirts"],
    "cave":   ["mysterious_cave", "enter_the_mine", "side_chamber", "enter_the_dark_forest"],
    "road":   ["follow_the_road_to_another_town", "capital_city_gates", "explore_capital_streets", "village_square"],
}

def _json_only(s: str) -> str:
    """Extract first JSON object from a string; fallback to '{}'."""
    m = re.search(r"\{.*\}", s, flags=re.S)
    return m.group(0) if m else "{}"

def _validate_ai_choice(d: Dict[str, Any], group: str) -> Optional[Dict[str, Any]]:
    if not isinstance(d, dict): return None
    text = d.get("text")
    nxt = d.get("next")
    effects = d.get("effects", [])
    if not isinstance(text, str) or not text.strip(): return None
    if not isinstance(nxt, str) or nxt not in ALLOWED_NEXT_BY_GROUP.get(group, []): return None
    if not isinstance(effects, list): effects = []

    safe_effects: List[Dict[str, Any]] = []
    for eff in effects:
        if not isinstance(eff, dict): continue
        if "add_trait" in eff and isinstance(eff["add_trait"], dict):
            k, v = next(iter(eff["add_trait"].items()))
            if k in ALLOWED_EFFECT_TRAITS and isinstance(v, int) and -1 <= v <= 1:
                safe_effects.append({"add_trait": {k: v}})
        elif "add_item" in eff and isinstance(eff["add_item"], dict):
            k, v = next(iter(eff["add_item"].items()))
            if k in ALLOWED_EFFECT_ITEMS and isinstance(v, int) and -1 <= v <= 2:
                safe_effects.append({"add_item": {k: v}})
        elif "set_flag" in eff and isinstance(eff["set_flag"], dict):
            k, v = next(iter(eff["set_flag"].items()))
            if k in ALLOWED_FLAGS and isinstance(v, bool):
                safe_effects.append({"set_flag": {k: v}})
        # Αγνοούμε οτιδήποτε άλλο για ασφάλεια

    return {"text": text.strip()[:80], "next": nxt, "effects": safe_effects}

def generate_ai_micro_choice(
    state_id: str,
    group: str,
    tone: Optional[str],
    player_snapshot: Dict[str, Any],
    temperature: float = 0.5,
    max_tokens: int = 140,
) -> Optional[Dict[str, Any]]:
    """
    Ask the model for ONE safe micro-choice (JSON only).
    Returns a validated dict or None.
    """
    if _client is None:
        return None

    # Μικρό snapshot κατάστασης - δεν στέλνουμε ολόκληρο το state
    inv = player_snapshot.get("inventory", {})
    traits = player_snapshot.get("traits", {})
    flags = player_snapshot.get("flags", {})
    allowed_next = ALLOWED_NEXT_BY_GROUP.get(group, [])

    system = (
        "You generate a single, short game choice label and minimal effect."
        " Keep it grounded in a medieval-fantasy tone."
        " Return STRICT JSON only with keys: text, next, effects."
        " No new items or named entities. No combat or big rewards."
    )
    user = {
        "state": state_id,
        "tone": tone or "default",
        "group": group,
        "allowed_next": allowed_next,
        "inventory": {k: inv.get(k) for k in ALLOWED_EFFECT_ITEMS if k in inv},
        "traits": {k: traits.get(k, 0) for k in ALLOWED_EFFECT_TRAITS},
        "flags": {k: flags.get(k, False) for k in ALLOWED_FLAGS},
        "rules": {
            "text": "≤ 6 words, actionable (e.g., 'Inspect strange tracks').",
            "effects": "0–2 tiny effects: add_trait ±1, add_item −1..+2, set_flag true/false (allowed lists only).",
            "next": "MUST be one of allowed_next.",
            "style": "No exclamation spam, no lore dumps."
        }
    }

    try:
        resp = _client.chat.completions.create(
            model="mistralai/mistral-7b-instruct",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.7,
            frequency_penalty=0.2,
            presence_penalty=0.0,
        )
        raw = resp.choices[0].message.content
        data = json.loads(_json_only(raw))
        return _validate_ai_choice(data, group)
    except Exception as e:
        print("AI micro-choice error:", e)
        return None