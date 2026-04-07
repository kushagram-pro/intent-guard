POLICY_RULES = {
    "GLOBAL_AMBIGUITY": {
        "severity": "ask",
        "reason": "The overall request is ambiguous and needs clarification.",
    },
    "RISK_LOW_CONFIDENCE": {
        "severity": "ask",
        "reason": "Intent confidence is below the required threshold.",
    },
    "RULE_MISSING_CONDITION": {
        "severity": "block",
        "reason": "Trades require an explicit execution condition.",
    },
    "RULE_VAGUE_CONDITION": {
        "severity": "block",
        "reason": "The execution condition is too vague for a financial trade.",
    },
    "RULE_UNVERIFIABLE_CONDITION": {
        "severity": "ask",
        "reason": "The execution condition is not specific enough to verify.",
    },
    "RISK_HIGH": {
        "severity": "ask",
        "reason": "High-risk trade instructions require manual confirmation.",
    },
    "RULE_UNKNOWN_ACTION": {
        "severity": "ask",
        "reason": "Unknown financial action type requires clarification.",
    },
}
