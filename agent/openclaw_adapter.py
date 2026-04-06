class OpenClawAgent:
    def __init__(self, agent_id, name="OpenClaw"):
        self.agent_id = agent_id
        self.name = name

    def attempt_action(self, user_instruction):
        from app import process_input

        safety_result = process_input(user_instruction)
        execution_result = _build_execution_result(safety_result)

        return {
            "agent": {
                "id": self.agent_id,
                "name": self.name,
            },
            "attempt": {
                "instruction": user_instruction,
                "status": "INTERCEPTED",
            },
            "safety_result": safety_result,
            "execution_result": execution_result,
        }


def _build_execution_result(safety_result):
    final = safety_result.get("final", {})
    clarification = safety_result.get("clarification", {})
    decision = final.get("decision", "ASK")

    execution_log = []
    for action in final.get("allowed_actions", []):
        execution_log.append(
            {
                "action": action,
                "execution_status": "SIMULATED_EXECUTED",
                "message": "Action is safe and would be executed by the OpenClaw agent.",
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
        "can_execute_any_action": bool(final.get("allowed_actions")),
        "requires_user_clarification": clarification.get("needed", False),
        "execution_log": execution_log,
    }


def simulate_openclaw_agent(user_instruction, agent_id="openclaw-sim-001", name="OpenClaw Trader"):
    agent = OpenClawAgent(agent_id=agent_id, name=name)
    return agent.attempt_action(user_instruction)
