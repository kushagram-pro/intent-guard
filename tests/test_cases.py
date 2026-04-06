import unittest
from unittest.mock import patch

from app import process_input
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


class DecisionFlowTests(unittest.TestCase):
    def test_vague_buy_request_requires_clarification(self):
        intent_data = {
            "intents": [
                {"type": "monitor", "stock": "XYZ", "condition": "", "confidence": 0.95},
                {"type": "buy", "stock": "XYZ", "condition": "whenever the situation is good", "confidence": 0.9},
            ],
            "ambiguous": True,
            "risk_level": "medium",
        }

        evaluation = evaluate_intents(intent_data)
        final = enforce_decision(evaluation, intent_data["ambiguous"])

        self.assertEqual(evaluation[0]["status"], "ALLOWED")
        self.assertEqual(evaluation[1]["status"], "BLOCKED")
        self.assertEqual(final["decision"], "ASK_USER")
        self.assertIn("monitor", final["allowed_actions"])
        self.assertIn("buy", final["blocked_actions"])

    @patch("app.parse_intent")
    def test_process_input_returns_phase_one_shape(self, mock_parse_intent):
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
        self.assertEqual(result["intent_data"]["intents"][0]["type"], "sell")


if __name__ == "__main__":
    unittest.main()
