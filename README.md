<!-- Final Version -->

# Financial Intent Safety Engine

This project now covers seven phases:

- Phase 1: Gemini-powered structured intent parsing
- Phase 2: Financial policy checks
- Phase 3: Enforcement engine and final safety decisioning
- Phase 4: Clarification engine for ambiguous or unsafe requests
- Phase 5: OpenClaw agent simulation and interception layer
- Phase 6: Amoriq-style simulated financial execution layer
- Phase 7: Explainability engine for auditable decision reasoning

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

## Phase 5 goal

Simulate real OpenClaw agent behavior while ensuring every attempted action is intercepted and validated before execution.

The OpenClaw layer:

- simulates an agent attempting monitor, buy, or sell actions
- routes every instruction through parsing, policy, enforcement, and clarification
- intercepts unsafe actions before execution
- simulates execution only for actions marked safe
- produces an execution log showing what was executed, blocked, or paused for clarification

## Phase 6 goal

Show realistic financial execution by forwarding only approved actions into an Amoriq mock infrastructure.

The Amoriq layer:

- accepts only approved actions from the OpenClaw agent layer
- simulates forwarding orders into financial infrastructure
- assigns mock order IDs for forwarded actions
- never executes blocked or clarification-required actions
- records a realistic execution trail for downstream auditing

## Phase 7 goal

Explain every decision in a clear, auditable way.

The explainability engine:

- shows parser confidence and risk level
- explains why each action was allowed, blocked, or sent for clarification
- records rule hits and human-readable reasons
- produces reason logs across parser, policy, and enforcement stages
- provides an audit-friendly summary for judges, reviewers, and demos

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
    "message": "",
    "questions": [],
    "summary": {
      "question_count": 0,
      "blocked_action_count": 0,
      "clarification_action_count": 0
    }
  },
  "execution_result": {
    "agent_decision": "ALLOW",
    "can_execute_any_action": true,
    "requires_user_clarification": false,
    "amoriq_execution": {
      "infrastructure": "Amoriq SIM",
      "forwarded_count": 1,
      "records": [
        {
          "order_id": "amq-sim-001",
          "infrastructure": "Amoriq SIM",
          "action": {
            "type": "buy",
            "stock": "AAPL"
          },
          "status": "FORWARDED",
          "message": "Approved action forwarded to Amoriq financial infrastructure."
        }
      ]
    },
    "execution_log": [
      {
        "action": {
          "type": "buy",
          "stock": "AAPL"
        },
        "execution_status": "FORWARDED_TO_AMORIQ",
        "message": "Action is safe and has been forwarded to Amoriq financial infrastructure.",
        "amoriq_order_id": "amq-sim-001"
      }
    ]
  },
  "explainability": {
    "summary": {
      "user_input": "Buy AAPL if price drops below 180",
      "final_decision": "ALLOW",
      "risk_level": "medium",
      "ambiguous": false,
      "clarification_needed": false
    },
    "parser_summary": {
      "intent_count": 1,
      "ambiguous": false,
      "risk_level": "medium",
      "confidence": {
        "values": [0.96],
        "min": 0.96,
        "max": 0.96,
        "average": 0.96
      }
    },
    "final_explanation": {
      "decision": "ALLOW",
      "verdict": "All requested actions passed the safety checks and are eligible for execution.",
      "reasons": []
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
- Every major decision now includes confidence display, risk display, and auditable reason logs.

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
ALPACA_API_KEY=your_paper_key_optional
ALPACA_SECRET_KEY=your_paper_secret_optional
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the CLI:

```bash
python app.py
```

## OpenClaw behavior

When you run the CLI now, it simulates an OpenClaw agent attempting the action.

Example flow:

1. Agent proposes: `Buy AAPL if price drops below 180`
2. Your safety system parses intent
3. Financial rules evaluate risk and ambiguity
4. Enforcement decides `ALLOW`, `BLOCK`, `ASK`, or `PARTIAL`
5. OpenClaw execution is simulated only for allowed actions
6. Approved actions are forwarded to the Amoriq simulation layer

## Hackathon compliance checklist

- Intent validation and policy enforcement are separate layers (`models/intent_parser.py` -> `core/policy_engine.py` -> `core/enforcement.py`).
- Policies are structured and deterministic via `core/policy_manifest.py` rule IDs and enforced statuses (`ALLOW`, `BLOCK`, `ASK`, `PARTIAL`).
- OpenClaw integration is active in `agent/openclaw_adapter.py` and all actions are intercepted before execution.
- Real action execution uses paper infrastructure:
  - If Alpaca paper credentials are configured, allowed buy/sell actions are sent to Alpaca paper API.
  - If not configured (or if paper API fails), execution safely falls back to Amoriq simulation mode.
- Unauthorized actions are blocked before execution and logged with reasons and rule hits.
- Every OpenClaw attempt is written as an immutable audit record to `logs/enforcement_audit.jsonl` with a `trace_id`.
- No human approval loop exists inside runtime enforcement; allowed actions flow directly to execution path.

## Judging criteria mapping

- Enforcement strength
  - Unauthorized, vague, high-risk, and unverifiable instructions are deterministically intercepted before execution.
  - Runtime enforcement happens after parsing and before OpenClaw can forward any action.
- Architecture clarity
  - Reasoning is separated from execution:
    - `models/intent_parser.py` handles LLM reasoning.
    - `core/policy_engine.py` handles structured policy evaluation.
    - `core/enforcement.py` handles final execution eligibility.
    - `agent/amoriq_adapter.py` handles paper/simulated trade forwarding.
- OpenClaw integration
  - `agent/openclaw_adapter.py` simulates OpenClaw attempting autonomous actions and routes them through the enforcement layer every time.
- Real financial use case
  - Allowed `buy` and `sell` actions can be forwarded to Alpaca paper trading.
  - Monitoring intents are registered without placing orders.
  - The system is designed to stop unauthorized trades, scope ambiguity, and unsafe execution.
- Auditability
  - Each intercepted attempt receives a trace ID and is logged with execution outcome and decision rationale.

## Alpaca paper trading

1. Copy `.env.example` to `.env`.
2. Fill in:
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
   - `ALPACA_BASE_URL=https://paper-api.alpaca.markets`
3. In the web UI OpenClaw page, set mode to `paper`.
4. Any action that survives enforcement will be forwarded to Alpaca paper trading.

If Alpaca paper mode is requested without credentials, the runtime now raises a clear configuration error instead of silently pretending to be in paper mode.
