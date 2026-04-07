def _classify_final_decision(intent_results):
    statuses = [item.get("status") for item in intent_results]

    if not statuses:
        return "ASK"

    has_allow = "ALLOW" in statuses or "ALLOWED" in statuses
    has_block = "BLOCK" in statuses or "BLOCKED" in statuses
    has_ask = "ASK" in statuses or "AMBIGUOUS" in statuses

    if has_block and (has_allow or has_ask):
        return "PARTIAL"
    if has_block:
        return "BLOCK"
    if has_ask and has_allow:
        return "PARTIAL"
    if has_ask:
        return "ASK"
    return "ALLOW"


def enforce_decision(evaluation, overall_ambiguous):
    intent_results = evaluation.get("intent_results", [])

    output = {
        "decision": "",
        "allowed_actions": [],
        "blocked_actions": [],
        "clarification_actions": [],
        "reasons": [],
        "clarification_needed": False,
        "executable_actions": [],
        "non_executable_actions": [],
        "safe_to_execute": [],
        "unsafe_to_execute": [],
        "decision_basis": {
            "has_allowed_actions": False,
            "has_blocked_actions": False,
            "has_clarification_actions": False,
        },
        "summary": {
            "intent_count": evaluation.get("intent_count", len(intent_results)),
            "global_risk_level": evaluation.get("global_risk_level"),
            "global_ambiguous": bool(overall_ambiguous),
        },
    }

    if overall_ambiguous:
        output["clarification_needed"] = True
        output["reasons"].append("Intent parsing is ambiguous and needs clarification.")

    for item in intent_results:
        action_label = {
            "type": item.get("type"),
            "stock": item.get("stock"),
            "quantity": item.get("quantity", 0),
        }
        status = item.get("status")

        if item.get("safe_to_execute"):
            output["safe_to_execute"].append(action_label)
            output["executable_actions"].append(action_label)
        else:
            output["unsafe_to_execute"].append(action_label)
            output["non_executable_actions"].append(action_label)

        if status in {"ALLOW", "ALLOWED"}:
            output["allowed_actions"].append(action_label)
        elif status in {"BLOCK", "BLOCKED"}:
            output["blocked_actions"].append(action_label)
            output["reasons"].extend(item.get("reasons", []))
        elif status in {"ASK", "AMBIGUOUS"}:
            output["clarification_actions"].append(action_label)
            output["clarification_needed"] = True
            output["reasons"].extend(item.get("reasons", []))

    output["decision"] = _classify_final_decision(intent_results)
    output["decision_basis"]["has_allowed_actions"] = bool(output["allowed_actions"])
    output["decision_basis"]["has_blocked_actions"] = bool(output["blocked_actions"])
    output["decision_basis"]["has_clarification_actions"] = bool(output["clarification_actions"])

    if output["decision"] in {"ASK", "PARTIAL"}:
        output["clarification_needed"] = True

    output["reasons"] = list(dict.fromkeys(output["reasons"]))
    return output
