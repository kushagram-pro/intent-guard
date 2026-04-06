import json
from functools import lru_cache

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL


SYSTEM_PROMPT = """
You are a financial intent parser.

Break user input into multiple intents.
Identify:
- action type (monitor, buy, sell)
- stock/entity
- condition (if any)
- ambiguity
- confidence score (0-1)
- risk level (low, medium, high)

Return ONLY valid JSON.
Do not assume trading unless clearly implied.

Use this schema:
{
  "intents": [
    {
      "type": "monitor",
      "stock": "XYZ",
      "condition": "",
      "confidence": 0.0
    }
  ],
  "ambiguous": false,
  "risk_level": "low"
}
"""

MODEL_CANDIDATES = [
    GEMINI_MODEL,
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]

VALID_TYPES = {"monitor", "buy", "sell"}
VALID_RISK_LEVELS = {"low", "medium", "high"}


def _fallback_response(error_message=None):
    return {
        "intents": [],
        "ambiguous": True,
        "risk_level": "high",
        "error": error_message,
    }


def _extract_json(text):
    text = (text or "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start == -1 or json_end <= 0:
            raise ValueError("No JSON object found in Gemini response")
        return json.loads(text[json_start:json_end])


def _normalize_type(value):
    normalized = str(value or "").strip().lower().replace("_stock", "")
    if normalized in VALID_TYPES:
        return normalized
    if normalized in {"watch", "track"}:
        return "monitor"
    return ""


def _normalize_confidence(value):
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _normalize_risk_level(value):
    normalized = str(value or "").strip().lower()
    if normalized in VALID_RISK_LEVELS:
        return normalized
    return "medium"


def _normalize_intent(intent):
    if not isinstance(intent, dict):
        return None

    normalized = {
        "type": _normalize_type(intent.get("type")),
        "stock": str(intent.get("stock") or "").strip(),
        "condition": str(intent.get("condition") or "").strip(),
        "confidence": _normalize_confidence(intent.get("confidence")),
    }

    if not normalized["type"] or not normalized["stock"]:
        return None

    return normalized


def _normalize_response(payload):
    if not isinstance(payload, dict):
        return _fallback_response("Gemini returned a non-object response.")

    raw_intents = payload.get("intents") or []
    intents = []
    for item in raw_intents:
        normalized_intent = _normalize_intent(item)
        if normalized_intent:
            intents.append(normalized_intent)

    ambiguous = bool(payload.get("ambiguous", not intents))
    risk_level = _normalize_risk_level(payload.get("risk_level"))

    return {
        "intents": intents,
        "ambiguous": ambiguous if intents else True,
        "risk_level": risk_level if intents else "high",
    }


@lru_cache(maxsize=1)
def _list_generate_content_models():
    client = genai.Client(api_key=GEMINI_API_KEY)
    available_models = []

    for model in client.models.list():
        actions = getattr(model, "supported_actions", []) or []
        if "generateContent" in actions:
            model_name = getattr(model, "name", "")
            if model_name:
                available_models.append(model_name.removeprefix("models/"))

    return available_models


def _models_to_try():
    deduped_candidates = []
    for model_name in MODEL_CANDIDATES:
        if model_name and model_name not in deduped_candidates:
            deduped_candidates.append(model_name)

    try:
        available_models = _list_generate_content_models()
    except Exception:
        return deduped_candidates

    available_set = set(available_models)
    preferred_available = [model for model in deduped_candidates if model in available_set]

    if preferred_available:
        return preferred_available

    return available_models or deduped_candidates


def parse_intent(user_input):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Add it to .env or your shell environment.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    errors = []

    for model_name in _models_to_try():
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f"{SYSTEM_PROMPT}\nUser input: {user_input}",
            )
            return _normalize_response(_extract_json(response.text))
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")

    error_message = " | ".join(errors) if errors else "No Gemini models available for generateContent."
    print("Parsing error:", error_message)
    return _fallback_response(error_message=error_message)
