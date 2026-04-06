CLARIFICATION_SYSTEM_PROMPT = """
User intent is ambiguous.

Ask a clarification question to make the action safe and explicit.
Do not proceed without clarity.

Example:
"What does 'good situation' mean? Please define price or condition."
"""


RULE_QUESTION_MAP = {
    "GLOBAL_AMBIGUITY": {
        "category": "intent_scope",
        "question_template": "Please restate the {action} instruction for {stock} in one explicit sentence with a measurable trigger.",
        "fields": ["action", "condition"],
        "examples": [
            "Buy {stock} if price drops below 180.",
            "Sell {stock} if price rises above 220.",
        ],
    },
    "RISK_LOW_CONFIDENCE": {
        "category": "intent_confirmation",
        "question_template": "Please confirm whether you want to {action} {stock}, and include the exact execution condition.",
        "fields": ["action", "condition"],
        "examples": [
            "Monitor {stock} and alert me if price drops below 180.",
            "Buy {stock} if price drops below 180.",
        ],
    },
    "RULE_MISSING_CONDITION": {
        "category": "missing_condition",
        "question_template": "What exact condition should trigger the {action} of {stock}? Please specify a price, percentage, or other measurable rule.",
        "fields": ["condition"],
        "examples": [
            "{action_cap} {stock} if price drops below 180.",
            "{action_cap} {stock} if it rises 5% from today's close.",
        ],
    },
    "RULE_VAGUE_CONDITION": {
        "category": "vague_condition",
        "question_template": "What does the current condition for {stock} mean in explicit terms? Please define a concrete trigger price, percentage, or rule.",
        "fields": ["condition"],
        "examples": [
            "{action_cap} {stock} if price drops below 180.",
            "{action_cap} {stock} if RSI goes below 30.",
        ],
    },
    "RULE_UNVERIFIABLE_CONDITION": {
        "category": "unverifiable_condition",
        "question_template": "Please rewrite the trigger for {stock} so it can be checked automatically. What exact threshold or metric should be used?",
        "fields": ["condition"],
        "examples": [
            "{action_cap} {stock} if price goes above 220.",
            "{action_cap} {stock} if volume increases by 20% over yesterday.",
        ],
    },
    "RISK_HIGH": {
        "category": "risk_confirmation",
        "question_template": "This request is high risk. Do you want to keep the {action} for {stock}, and if so, what exact trigger should be used?",
        "fields": ["confirmation", "condition"],
        "examples": [
            "Yes, {action} {stock} if price drops below 180.",
            "No, only monitor {stock} for now.",
        ],
    },
    "RULE_UNKNOWN_ACTION": {
        "category": "unknown_action",
        "question_template": "Should the action for {stock} be monitor, buy, or sell? Please choose one and provide the exact condition.",
        "fields": ["action", "condition"],
        "examples": [
            "Monitor {stock} and alert me if price drops below 180.",
            "Sell {stock} if price rises above 220.",
        ],
    },
}


def _format_example(example, action, stock):
    action_cap = action.capitalize()
    return example.format(action=action, action_cap=action_cap, stock=stock)


def _build_question(intent_result):
    action = intent_result.get("type") or "trade"
    stock = intent_result.get("stock") or "this stock"
    rule_hits = intent_result.get("rule_hits", [])

    for rule_id in rule_hits:
        template = RULE_QUESTION_MAP.get(rule_id)
        if not template:
            continue

        question = template["question_template"].format(action=action, stock=stock)
        examples = [
            _format_example(example, action, stock)
            for example in template.get("examples", [])
        ]

        return {
            "question": question,
            "category": template["category"],
            "missing_fields": template["fields"],
            "trigger_rule": rule_id,
            "examples": examples,
        }

    return {
        "question": f"Please clarify what you want to do with {stock}. State whether to monitor, buy, or sell and include an exact trigger.",
        "category": "general_clarification",
        "missing_fields": ["action", "condition"],
        "trigger_rule": "FALLBACK",
        "examples": [
            f"Monitor {stock} and alert me if price drops below 180.",
            f"Buy {stock} if price drops below 180.",
        ],
    }


def _dedupe_questions(questions):
    seen = set()
    deduped = []

    for question in questions:
        key = (
            question["target"]["type"],
            question["target"]["stock"],
            question["category"],
            question["question"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(question)

    return deduped


def build_clarification_plan(user_input, intent_data, evaluation, final_decision):
    if final_decision.get("decision") not in {"ASK", "PARTIAL", "BLOCK"}:
        return {
            "needed": False,
            "message": "",
            "questions": [],
            "summary": {
                "question_count": 0,
                "blocked_action_count": 0,
                "clarification_action_count": 0,
            },
        }

    questions = []
    for intent_result in evaluation.get("intent_results", []):
        if intent_result.get("status") not in {"ASK", "BLOCK", "AMBIGUOUS"}:
            continue

        question_payload = _build_question(intent_result)
        question_payload["target"] = {
            "type": intent_result.get("type"),
            "stock": intent_result.get("stock"),
        }
        questions.append(question_payload)

    questions = _dedupe_questions(questions)

    primary_question = questions[0]["question"] if questions else "Please clarify your request with an explicit action and measurable trigger."
    message = (
        "The request cannot be executed safely yet. "
        "Please answer the clarification questions below so the intent becomes explicit."
    )

    return {
        "needed": bool(questions),
        "message": message,
        "primary_question": primary_question,
        "questions": questions,
        "original_user_input": user_input,
        "summary": {
            "question_count": len(questions),
            "blocked_action_count": len(final_decision.get("blocked_actions", [])),
            "clarification_action_count": len(final_decision.get("clarification_actions", [])),
        },
    }
