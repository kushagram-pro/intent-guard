def evaluate_intents(intent_data):
    results = []

    for intent in intent_data.get("intents", []):
        decision = {
            "type": intent.get("type"),
            "status": "ALLOWED",
            "reason": []
        }

        intent_type = intent.get("type")
        condition = intent.get("condition", "").lower()
        confidence = intent.get("confidence", 0)

        # RULE 1: Monitoring is always safe
        if intent_type == "monitor_stock":
            decision["status"] = "ALLOWED"

        #  RULE 2: Trading rules
        elif intent_type in ["buy_stock", "sell_stock"]:

            # No condition
            if not condition:
                decision["status"] = "BLOCKED"
                decision["reason"].append("No condition provided for trade")

            # Vague condition
            elif any(word in condition for word in ["good", "best", "right time", "whenever"]):
                decision["status"] = "BLOCKED"
                decision["reason"].append("Vague condition not allowed in financial decisions")

        # RULE 3: Low confidence
        if confidence < 0.75:
            decision["status"] = "AMBIGUOUS"
            decision["reason"].append("Low confidence in intent")

        results.append(decision)

    return results