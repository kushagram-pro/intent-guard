# Financial Intent Safety Engine

This project now covers four phases:

- Phase 1: Gemini-powered structured intent parsing
- Phase 2: Financial policy checks
- Phase 3: Enforcement engine and final safety decisioning
- Phase 4: Clarification engine for ambiguous or unsafe requests

## Phase 3 goal

Given structured intent and financial rules, decide what actions are safe to execute.

The enforcement engine combines:

- LLM-parsed intent output
- risk and ambiguity signals
- financial policy checks
- final execution-safe action routing

## Phase 4 goal

Handle ambiguity intelligently by asking for exactly the missing details required to make a request safe and explicit.

The clarification engine:

- analyzes blocked and ambiguous actions
- maps rule failures to targeted follow-up questions
- asks for measurable triggers instead of generic clarification
- suggests examples that convert vague intent into executable instructions
- refuses to proceed until the missing details are made explicit

## Final decisions

The core brain now returns one of:

- `ALLOW`: all parsed actions are safe to execute
- `BLOCK`: actions are unsafe and must not execute
- `ASK`: clarification or manual confirmation is required
- `PARTIAL`: some actions are safe, some are blocked or need clarification

## Output structure

```json
{
  "intent_data": {
    "intents": [
      {
        "type": "buy",
        "stock": "AAPL",
        "condition": "if price drops below 180",
        "confidence": 0.96
      }
    ],
    "ambiguous": false,
    "risk_level": "medium"
  },
  "evaluation": {
    "intent_results": [
      {
        "type": "buy",
        "stock": "AAPL",
        "status": "ALLOW",
        "rule_hits": [],
        "reasons": [],
        "safe_to_execute": true
      }
    ],
    "global_ambiguous": false,
    "global_risk_level": "medium",
    "intent_count": 1
  },
  "final": {
    "decision": "ALLOW",
    "allowed_actions": [
      {
        "type": "buy",
        "stock": "AAPL"
      }
    ],
    "blocked_actions": [],
    "clarification_actions": [],
    "reasons": [],
    "clarification_needed": false,
    "safe_to_execute": [
      {
        "type": "buy",
        "stock": "AAPL"
      }
    ],
    "unsafe_to_execute": [],
    "summary": {
      "intent_count": 1,
      "global_risk_level": "medium",
      "global_ambiguous": false
    }
  },
  "clarification": {
    "needed": false,
    "system_prompt": "User intent is ambiguous. Ask a clarification question to make the action safe and explicit. Do not proceed without clarity.",
    "message": "",
    "questions": [],
    "summary": {
      "question_count": 0,
      "blocked_action_count": 0,
      "clarification_action_count": 0
    }
  }
}
```

## Safety logic

- Monitoring intents are generally allowed unless confidence is too low.
- Trades without explicit conditions are blocked.
- Trades with vague conditions are blocked.
- Trades with non-verifiable conditions are escalated with `ASK`.
- High-risk trades require confirmation.
- Globally ambiguous requests require clarification before trade execution.
- Mixed outcomes across intents return `PARTIAL`.
- Ambiguous or blocked intents produce targeted clarification questions.
- Vague phrases are converted into explicit follow-up prompts asking for price, percentage, or measurable criteria.

## Clarification examples

Input:

```text
Buy XYZ whenever the situation is good
```

Clarification output can ask:

```text
What does the current condition for XYZ mean in explicit terms? Please define a concrete trigger price, percentage, or rule.
```

And provide examples like:

```text
Buy XYZ if price drops below 180.
Buy XYZ if RSI goes below 30.
```

## Setup

1. Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the CLI:

```bash
python app.py
```
