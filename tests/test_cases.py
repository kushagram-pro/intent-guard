import unittest
from unittest.mock import patch

from app import process_input
from core.ambiguity_checker import build_clarification_plan
from core.enforcement import enforce_decision
from core.policy_engine import evaluate_intents
from models.intent_parser import _normalize_response


class IntentParserNormalizationTests(unittest.TestCase):
    def test_normalizes_action_aliases_and_clamps_confidence(self):
        payload = {
            "intents": [
                {
                    "type": "buy_stock",
                    "stock": "AAPL",
                    "condition": "below 180",
                    "confidence": 1.5,
                }
            ],
            "ambiguous": False,
            "risk_level": "HIGH",
        }

        result = _normalize_response(payload)

        self.assertEqual(result["intents"][0]["type"], "buy")
        self.assertEqual(result["intents"][0]["confidence"], 1.0)
        self.assertEqual(result["risk_level"], "high")

    def test_drops_incomplete_intents_and_marks_response_ambiguous(self):
        payload = {
            "intents": [
                {
                    "type": "monitor",
                    "stock": "",
                    "condition": "",
                    "confidence": 0.9,
                }
            ],
            "ambiguous": False,
            "risk_level": "low",
        }

        result = _normalize_response(payload)

        self.assertEqual(result["intents"], [])
        self.assertTrue(result["ambiguous"])
        self.assertEqual(result["risk_level"], "high")


class PolicyAndEnforcementTests(unittest.TestCase):
    def test_monitor_intent_is_allowed(self):
        intent_data = {
            "intents": [
                {"type": "monitor", "stock": "AAPL", "condition": "", "confidence": 0.94}
            ],
            "ambiguous": False,
            "risk_level": "low",
        }

        evaluation = evaluate_intents(intent_data)
        final = enforce_decision(evaluation, intent_data["ambiguous"])

        self.assertEqual(evaluation["intent_results"][0]["status"], "ALLOW")
        self.assertEqual(final["decision"], "ALLOW")

    def test_vague_trade_is_blocked(self):
        intent_data = {
            "intents": [
                {"type": "buy", "stock": "XYZ", "condition": "whenever the situation is good", "confidence": 0.92}
            ],
            "ambiguous": False,
            "risk_level": "medium",
        }

        evaluation = evaluate_intents(intent_data)
        final = enforce_decision(evaluation, intent_data["ambiguous"])

        self.assertEqual(evaluation["intent_results"][0]["status"], "BLOCK")
        self.assertEqual(final["decision"], "BLOCK")

    def test_high_risk_trade_requires_clarification(self):
        intent_data = {
            "intents": [
                {"type": "buy", "stock": "NVDA", "condition": "if price drops below 800", "confidence": 0.96}
            ],
            "ambiguous": False,
            "risk_level": "high",
        }

        evaluation = evaluate_intents(intent_data)
        final = enforce_decision(evaluation, intent_data["ambiguous"])

        self.assertEqual(evaluation["intent_results"][0]["status"], "ASK")
        self.assertEqual(final["decision"], "ASK")

    def test_mixed_allowed_and_blocked_actions_return_partial(self):
        evaluation = {
            "intent_results": [
                {
                    "type": "monitor",
                    "stock": "AAPL",
                    "status": "ALLOW",
                    "rule_hits": [],
                    "reasons": [],
                    "safe_to_execute": True,
                },
                {
                    "type": "buy",
                    "stock": "TSLA",
                    "status": "BLOCK",
                    "rule_hits": ["RULE_VAGUE_CONDITION"],
                    "reasons": ["The execution condition is too vague for a financial trade."],
                    "safe_to_execute": False,
                },
            ],
            "global_ambiguous": False,
            "global_risk_level": "medium",
            "intent_count": 2,
        }

        final = enforce_decision(evaluation, False)

        self.assertEqual(final["decision"], "PARTIAL")
        self.assertEqual(len(final["allowed_actions"]), 1)
        self.assertEqual(len(final["blocked_actions"]), 1)

    def test_clarification_engine_generates_targeted_question_for_vague_condition(self):
        intent_data = {
            "intents": [
                {"type": "buy", "stock": "XYZ", "condition": "whenever the situation is good", "confidence": 0.92}
            ],
            "ambiguous": False,
            "risk_level": "medium",
        }

        evaluation = evaluate_intents(intent_data)
        final = enforce_decision(evaluation, intent_data["ambiguous"])
        clarification = build_clarification_plan(
            "Buy XYZ whenever the situation is good",
            intent_data,
            evaluation,
            final,
        )

        self.assertTrue(clarification["needed"])
        self.assertGreaterEqual(clarification["summary"]["question_count"], 1)
        self.assertIn("concrete trigger", clarification["primary_question"].lower())
        self.assertEqual(clarification["questions"][0]["trigger_rule"], "RULE_VAGUE_CONDITION")

    def test_allow_decision_does_not_request_clarification(self):
        intent_data = {
            "intents": [
                {"type": "buy", "stock": "AAPL", "condition": "if price drops below 180", "confidence": 0.95}
            ],
            "ambiguous": False,
            "risk_level": "medium",
        }

        evaluation = evaluate_intents(intent_data)
        final = enforce_decision(evaluation, intent_data["ambiguous"])
        clarification = build_clarification_plan(
            "Buy AAPL if price drops below 180",
            intent_data,
            evaluation,
            final,
        )

        self.assertFalse(clarification["needed"])
        self.assertEqual(clarification["summary"]["question_count"], 0)

    @patch("app.parse_intent")
    def test_process_input_returns_phase_three_shape(self, mock_parse_intent):
        mock_parse_intent.return_value = {
            "intents": [
                {"type": "sell", "stock": "TSLA", "condition": "if it falls below 150", "confidence": 0.91}
            ],
            "ambiguous": False,
            "risk_level": "medium",
        }

        result = process_input("Sell TSLA if it falls below 150")

        self.assertIn("intent_data", result)
        self.assertIn("evaluation", result)
        self.assertIn("final", result)
        self.assertIn("intent_results", result["evaluation"])
        self.assertIn("decision", result["final"])
        self.assertIn("safe_to_execute", result["final"])
        self.assertIn("decision_basis", result["final"])
        self.assertIn("clarification", result)


if __name__ == "__main__":
    unittest.main()
