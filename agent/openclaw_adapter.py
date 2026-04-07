from agent.amoriq_adapter import simulate_financial_execution
from core.audit_logger import new_trace_id, write_audit_log
from core.explainability_engine import build_explainability_report


class OpenClawAgent:
    def __init__(self, agent_id, name="OpenClaw", execution_mode="simulation"):
        self.agent_id = agent_id
        self.name = name
        self.execution_mode = execution_mode

    def attempt_action(self, user_instruction):
        from app import process_input

        trace_id = new_trace_id()
        safety_result = process_input(user_instruction)
        execution_result = _build_execution_result(safety_result, self.execution_mode)
        explainability = build_explainability_report(
            user_instruction,
            safety_result.get("intent_data", {}),
            safety_result.get("evaluation", {}),
            safety_result.get("final", {}),
            safety_result.get("clarification", {}),
            execution_result,
        )
        write_audit_log(
            event_type="openclaw_execution_attempt",
            trace_id=trace_id,
            payload={
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "execution_mode": self.execution_mode,
                "instruction": user_instruction,
                "final_decision": safety_result.get("final", {}).get("decision"),
                "allowed_actions": safety_result.get("final", {}).get("allowed_actions", []),
                "blocked_actions": safety_result.get("final", {}).get("blocked_actions", []),
                "clarification_actions": safety_result.get("final", {}).get("clarification_actions", []),
                "execution_result": execution_result,
            },
        )

        return {
            "trace_id": trace_id,
            "agent": {
                "id": self.agent_id,
                "name": self.name,
                "execution_mode": self.execution_mode,
            },
            "attempt": {
                "instruction": user_instruction,
                "status": "INTERCEPTED",
            },
            "safety_result": safety_result,
            "execution_result": execution_result,
            "explainability": explainability,
        }


def _build_execution_result(safety_result, execution_mode):
    final = safety_result.get("final", {})
    clarification = safety_result.get("clarification", {})
    decision = final.get("decision", "ASK")
    allowed_actions = final.get("allowed_actions", [])
    if allowed_actions:
        amoriq_result = simulate_financial_execution(allowed_actions, execution_mode=execution_mode)
    else:
        infrastructure = "Alpaca Paper" if execution_mode == "paper" else "Amoriq SIM"
        amoriq_result = {
            "infrastructure": infrastructure,
            "forwarded_count": 0,
            "records": [],
            "mode": execution_mode,
        }

    execution_log = []
    for action in allowed_actions:
        matching_record = next(
            (record for record in amoriq_result["records"] if record["action"] == action),
            None,
        )
        record_status = (matching_record or {}).get("status")
        if record_status == "FORWARDED":
            execution_status = (
                "FORWARDED_TO_ALPACA_PAPER"
                if amoriq_result.get("mode") == "paper"
                else "FORWARDED_TO_AMORIQ"
            )
            message = (
                "Action is safe and has been forwarded to Alpaca paper trading."
                if amoriq_result.get("mode") == "paper"
                else "Action is safe and has been forwarded to Amoriq financial infrastructure."
            )
        elif record_status == "MONITOR_ONLY":
            execution_status = "REGISTERED_MONITOR"
            message = "Monitoring intent was registered. No trade order was sent."
        else:
            execution_status = "PAPER_EXECUTION_FAILED"
            message = (
                matching_record.get("message")
                if matching_record
                else "Execution failed after safety approval."
            )
        execution_log.append(
            {
                "action": action,
                "execution_status": execution_status,
                "message": message,
                "amoriq_order_id": matching_record["order_id"] if matching_record else None,
            }
        )

    for action in final.get("blocked_actions", []):
        execution_log.append(
            {
                "action": action,
                "execution_status": "INTERCEPTED_BLOCKED",
                "message": "Action was intercepted and blocked by the financial safety system.",
            }
        )

    for action in final.get("clarification_actions", []):
        execution_log.append(
            {
                "action": action,
                "execution_status": "INTERCEPTED_NEEDS_CLARIFICATION",
                "message": "Action was intercepted pending user clarification.",
            }
        )

    return {
        "agent_decision": decision,
        "execution_mode": execution_mode,
        "can_execute_any_action": bool(final.get("allowed_actions")),
        "requires_user_clarification": clarification.get("needed", False),
        "amoriq_execution": amoriq_result,
        "execution_log": execution_log,
    }


def simulate_openclaw_agent(
    user_instruction,
    agent_id="openclaw-sim-001",
    name="OpenClaw Trader",
    execution_mode="simulation",
):
    agent = OpenClawAgent(agent_id=agent_id, name=name, execution_mode=execution_mode)
    return agent.attempt_action(user_instruction)
