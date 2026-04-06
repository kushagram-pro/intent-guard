from config import CONFIDENCE_THRESHOLD


ACTION_ALIASES = {
    "monitor_stock": "monitor",
    "buy_stock": "buy",
    "sell_stock": "sell",
}


def evaluate_intents(intent_data):
    results = []
    for intent in intent_data["intents"]:
        intent_type = ACTION_ALIASES.get(intent["type"], intent["type"])
        decision = {
            "type": intent_type,
            "status": "ALLOWED",
            "reason": []
        }

        #Rule1: Monitoring is always safe
        if intent_type == "monitor":
            decision["status"] = "ALLOWED"

        #Rule2: Trading requires explicit conditions
        elif intent_type in ["buy", "sell"]:
            condition = (intent.get("condition") or "").lower()
            if not condition or "good" in condition or "best time" in condition:
                decision["status"] = "BLOCKED"
                decision["reason"].append("Condition is too vague or positive without specifics.")
            else:                
                decision["status"] = "ALLOWED"

        #Rule3: Low confidence ->ambiguous
        if intent["confidence"] < CONFIDENCE_THRESHOLD:
            decision["status"] = "AMBIGUOUS"
            decision["reason"].append("Low confidence in intent.")

        results.append(decision)
        
    return results
