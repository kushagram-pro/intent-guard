def _build_parser_summary(intent_data):
    intents = intent_data.get("intents", [])
    confidence_values = [intent.get("confidence", 0.0) for intent in intents]

    return {
        "intent_count": len(intents),
        "ambiguous": bool(intent_data.get("ambiguous", False)),
        "risk_level": intent_data.get("risk_level"),
        "confidence": {
            "values": confidence_values,
            "min": min(confidence_values) if confidence_values else None,
            "max": max(confidence_values) if confidence_values else None,
            "average": round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None,
        },
    }


def _build_intent_explanation(intent_result):
    action = intent_result.get("type") or "unknown"
    stock = intent_result.get("stock") or "unknown stock"
    status = intent_result.get("status")
    reasons = intent_result.get("reasons", [])
    rule_hits = intent_result.get("rule_hits", [])
    safe_to_execute = bool(intent_result.get("safe_to_execute"))

    if status == "ALLOW":
        verdict = f"The {action} action for {stock} was allowed because no blocking or clarification rules were triggered."
    elif status == "BLOCK":
        verdict = f"The {action} action for {stock} was blocked because one or more safety rules determined it was unsafe to execute."
    else:
        verdict = f"The {action} action for {stock} requires clarification before execution."

    return {
        "target": {
            "type": action,
            "stock": stock,
            "quantity": intent_result.get("quantity", 0),
        },
        "status": status,
        "safe_to_execute": safe_to_execute,
        "rule_hits": rule_hits,
        "reasons": reasons,
        "verdict": verdict,
    }


def _build_final_explanation(final_decision):
    decision = final_decision.get("decision")
    reasons = final_decision.get("reasons", [])
    summary = final_decision.get("summary", {})

    verdict_map = {
        "ALLOW": "All requested actions passed the safety checks and are eligible for execution.",
        "BLOCK": "Requested actions were blocked because the system identified safety or policy violations.",
        "ASK": "The request requires clarification or manual confirmation before anything can execute.",
        "PARTIAL": "Some requested actions are safe, while others were blocked or need clarification.",
    }

    return {
        "decision": decision,
        "verdict": verdict_map.get(decision, "The system evaluated the request and produced a decision."),
        "reasons": reasons,
        "summary": summary,
    }


def _build_reason_log(intent_data, evaluation, final_decision):
    log_entries = []

    log_entries.append(
        {
            "stage": "parser",
            "message": "Structured intent was extracted from the user request.",
            "risk_level": intent_data.get("risk_level"),
            "ambiguous": bool(intent_data.get("ambiguous", False)),
        }
    )

    for intent_result in evaluation.get("intent_results", []):
        log_entries.append(
            {
                "stage": "policy",
                "target": {
                    "type": intent_result.get("type"),
                    "stock": intent_result.get("stock"),
                    "quantity": intent_result.get("quantity", 0),
                },
                "status": intent_result.get("status"),
                "rule_hits": intent_result.get("rule_hits", []),
                "reasons": intent_result.get("reasons", []),
            }
        )

    log_entries.append(
        {
            "stage": "enforcement",
            "decision": final_decision.get("decision"),
            "clarification_needed": bool(final_decision.get("clarification_needed", False)),
            "allowed_count": len(final_decision.get("allowed_actions", [])),
            "blocked_count": len(final_decision.get("blocked_actions", [])),
            "clarification_count": len(final_decision.get("clarification_actions", [])),
        }
    )

    return log_entries


def build_explainability_report(user_input, intent_data, evaluation, final_decision, clarification, execution_result=None):
    intent_explanations = [
        _build_intent_explanation(intent_result)
        for intent_result in evaluation.get("intent_results", [])
    ]

    report = {
        "summary": {
            "user_input": user_input,
            "final_decision": final_decision.get("decision"),
            "risk_level": intent_data.get("risk_level"),
            "ambiguous": bool(intent_data.get("ambiguous", False)),
            "clarification_needed": bool(clarification.get("needed", False)),
        },
        "parser_summary": _build_parser_summary(intent_data),
        "final_explanation": _build_final_explanation(final_decision),
        "intent_explanations": intent_explanations,
        "reason_log": _build_reason_log(intent_data, evaluation, final_decision),
        "audit_view": {
            "confidence_display": _build_parser_summary(intent_data)["confidence"],
            "risk_display": {
                "global_risk_level": intent_data.get("risk_level"),
                "clarification_needed": bool(clarification.get("needed", False)),
                "safe_action_count": len(final_decision.get("safe_to_execute", [])),
                "unsafe_action_count": len(final_decision.get("unsafe_to_execute", [])),
            },
        },
    }

    if execution_result is not None:
        report["execution_explanation"] = {
            "agent_decision": execution_result.get("agent_decision"),
            "amoriq_forwarded_count": execution_result.get("amoriq_execution", {}).get("forwarded_count", 0),
            "requires_user_clarification": execution_result.get("requires_user_clarification", False),
        }

    return report
