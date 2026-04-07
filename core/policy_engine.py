from config import CONFIDENCE_THRESHOLD
from core.policy_manifest import POLICY_RULES


VAGUE_TERMS = {
    "good",
    "best",
    "best time",
    "right time",
    "whenever",
    "sometime",
    "soon",
    "later",
    "if it looks nice",
    "if it feels right",
}

CONDITION_SIGNALS = (
    "below",
    "above",
    "under",
    "over",
    "less than",
    "greater than",
    "drops below",
    "rises above",
    "%",
    "percent",
    "price",
    "target",
    "stop loss",
)


def _has_vague_condition(condition):
    lowered = (condition or "").lower()
    return any(term in lowered for term in VAGUE_TERMS)


def _has_verifiable_condition(condition):
    lowered = (condition or "").lower()
    if any(signal in lowered for signal in CONDITION_SIGNALS):
        return True
    return any(char.isdigit() for char in lowered)


def _evaluate_monitor_intent(intent):
    result = {
        "type": intent.get("type"),
        "stock": intent.get("stock"),
        "quantity": intent.get("quantity", 0),
        "status": "ALLOW",
        "rule_hits": [],
        "reasons": [],
        "safe_to_execute": True,
    }

    if intent.get("confidence", 0.0) < CONFIDENCE_THRESHOLD:
        result["status"] = "ASK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RISK_LOW_CONFIDENCE")
        result["reasons"].append(POLICY_RULES["RISK_LOW_CONFIDENCE"]["reason"])

    return result


def _evaluate_trade_intent(intent, global_ambiguous, global_risk_level):
    result = {
        "type": intent.get("type"),
        "stock": intent.get("stock"),
        "quantity": intent.get("quantity", 1),
        "status": "ALLOW",
        "rule_hits": [],
        "reasons": [],
        "safe_to_execute": True,
    }

    condition = (intent.get("condition") or "").strip()
    confidence = intent.get("confidence", 0.0)

    if global_ambiguous:
        result["status"] = "ASK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("GLOBAL_AMBIGUITY")
        result["reasons"].append(POLICY_RULES["GLOBAL_AMBIGUITY"]["reason"])

    if confidence < CONFIDENCE_THRESHOLD:
        result["status"] = "ASK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RISK_LOW_CONFIDENCE")
        result["reasons"].append(POLICY_RULES["RISK_LOW_CONFIDENCE"]["reason"])

    if not condition:
        result["status"] = "BLOCK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RULE_MISSING_CONDITION")
        result["reasons"].append(POLICY_RULES["RULE_MISSING_CONDITION"]["reason"])
        return result

    if _has_vague_condition(condition):
        result["status"] = "BLOCK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RULE_VAGUE_CONDITION")
        result["reasons"].append(POLICY_RULES["RULE_VAGUE_CONDITION"]["reason"])
        return result

    if not _has_verifiable_condition(condition):
        result["status"] = "ASK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RULE_UNVERIFIABLE_CONDITION")
        result["reasons"].append(POLICY_RULES["RULE_UNVERIFIABLE_CONDITION"]["reason"])

    if global_risk_level == "high":
        result["status"] = "ASK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RISK_HIGH")
        result["reasons"].append(POLICY_RULES["RISK_HIGH"]["reason"])

    return result


def evaluate_intents(intent_data):
    intent_results = []
    global_ambiguous = bool(intent_data.get("ambiguous", False))
    global_risk_level = intent_data.get("risk_level", "high")

    for intent in intent_data.get("intents", []):
        intent_type = intent.get("type")

        if intent_type == "monitor":
            intent_results.append(_evaluate_monitor_intent(intent))
        elif intent_type in {"buy", "sell"}:
            intent_results.append(
                _evaluate_trade_intent(intent, global_ambiguous, global_risk_level)
            )
        else:
            intent_results.append(
                {
                    "type": intent_type,
                    "stock": intent.get("stock"),
                    "quantity": intent.get("quantity", 0),
                    "status": "ASK",
                    "rule_hits": ["RULE_UNKNOWN_ACTION"],
                    "reasons": [POLICY_RULES["RULE_UNKNOWN_ACTION"]["reason"]],
                    "safe_to_execute": False,
                }
            )

    return {
        "intent_results": intent_results,
        "global_ambiguous": global_ambiguous,
        "global_risk_level": global_risk_level,
        "intent_count": len(intent_results),
    }
