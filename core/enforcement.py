def enforce_decision(evaluated_intents,overall):
    output= {
        "decision": "",
        "allowed_actions": [],
        "blocked_actions": [],
        "reason": [],
        "clarification_needed": False
    }

    if overall:
        output["clarification_needed"] = True
        output["reason"].append("Intent parsing is ambiguous and needs clarification.")

    for item in evaluated_intents:
        if item["status"] == "ALLOWED":
            output["allowed_actions"].append(item["type"])
        elif item["status"] == "BLOCKED":
            output["blocked_actions"].append(item["type"])
            output["reason"].extend(item["reason"]) 
        elif item["status"] == "AMBIGUOUS":
            output["clarification_needed"] = True
            output["reason"].extend(item["reason"])
    
    #FINAL DECISION LOGIC
    if output["clarification_needed"]:
        output["decision"] = "ASK_USER"
    
    elif output["allowed_actions"] and output["blocked_actions"]:
        output["decision"] = "PARTIAL_APPROVAL"
    
    elif output["blocked_actions"]:
        output["decision"] = "BLOCKED"

    else:
        output["decision"] = "ALLOWED"
    
    return output
