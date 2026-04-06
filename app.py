import json

from agent.openclaw_adapter import simulate_openclaw_agent
from core.ambiguity_checker import build_clarification_plan
from core.enforcement import enforce_decision
from core.explainability_engine import build_explainability_report
from models.intent_parser import parse_intent
from core.policy_engine import evaluate_intents

def process_input(user_input):
    intent_data = parse_intent(user_input)

    evaluated = evaluate_intents(intent_data)

    final_decision = enforce_decision(
        evaluated,
        intent_data["ambiguous"]
    )
    clarification = build_clarification_plan(
        user_input,
        intent_data,
        evaluated,
        final_decision,
    )

    return {
        "intent_data": intent_data,
        "evaluation": evaluated,
        "final": final_decision,
        "clarification": clarification,
        "explainability": build_explainability_report(
            user_input,
            intent_data,
            evaluated,
            final_decision,
            clarification,
        ),
    }


if __name__ == "__main__":
    user_input = input("Enter instruction: ")
    result = simulate_openclaw_agent(user_input)
    print(json.dumps(result, indent=2))
