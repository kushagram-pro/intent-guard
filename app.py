import json

from models.intent_parser import parse_intent
from core.policy_engine import evaluate_intents
from core.enforcement import enforce_decision

def process_input(user_input):
    intent_data = parse_intent(user_input)

    evaluated = evaluate_intents(intent_data)

    final_decision = enforce_decision(
        evaluated,
        intent_data["ambiguous"]
    )

    return {
        "intent_data": intent_data,
        "evaluation": evaluated,
        "final": final_decision
    }


if __name__ == "__main__":
    user_input = input("Enter instruction: ")
    result = process_input(user_input)
    print(json.dumps(result, indent=2))
