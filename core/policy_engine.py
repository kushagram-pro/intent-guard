from config import CONFIDENCE_THRESHOLD


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
        "status": "ALLOW",
        "rule_hits": [],
        "reasons": [],
        "safe_to_execute": True,
    }

    if intent.get("confidence", 0.0) < CONFIDENCE_THRESHOLD:
        result["status"] = "ASK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RISK_LOW_CONFIDENCE")
        result["reasons"].append("Monitoring intent confidence is below the required threshold.")

    return result


def _evaluate_trade_intent(intent, global_ambiguous, global_risk_level):
    result = {
        "type": intent.get("type"),
        "stock": intent.get("stock"),
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
        result["reasons"].append("The overall request is ambiguous and needs clarification.")

    if confidence < CONFIDENCE_THRESHOLD:
        result["status"] = "ASK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RISK_LOW_CONFIDENCE")
        result["reasons"].append("Trade intent confidence is below the required threshold.")

    if not condition:
        result["status"] = "BLOCK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RULE_MISSING_CONDITION")
        result["reasons"].append("Trades require an explicit execution condition.")
        return result

    if _has_vague_condition(condition):
        result["status"] = "BLOCK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RULE_VAGUE_CONDITION")
        result["reasons"].append("The execution condition is too vague for a financial trade.")
        return result

    if not _has_verifiable_condition(condition):
        result["status"] = "ASK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RULE_UNVERIFIABLE_CONDITION")
        result["reasons"].append("The execution condition is not specific enough to verify.")

    if global_risk_level == "high":
        result["status"] = "ASK"
        result["safe_to_execute"] = False
        result["rule_hits"].append("RISK_HIGH")
        result["reasons"].append("High-risk trade instructions require manual confirmation.")

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
                    "status": "ASK",
                    "rule_hits": ["RULE_UNKNOWN_ACTION"],
                    "reasons": ["Unknown financial action type requires clarification."],
                    "safe_to_execute": False,
                }
            )

    return {
        "intent_results": intent_results,
        "global_ambiguous": global_ambiguous,
        "global_risk_level": global_risk_level,
        "intent_count": len(intent_results),
    }
