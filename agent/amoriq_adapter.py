import os

import httpx


class AmoriqSimulator:
    def __init__(self, infrastructure_name="Amoriq SIM"):
        self.infrastructure_name = infrastructure_name

    def forward_approved_actions(self, actions):
        execution_records = []

        for index, action in enumerate(actions, start=1):
            action_type = (action or {}).get("type")
            stock = (action or {}).get("stock")
            if action_type == "monitor":
                execution_records.append(
                    {
                        "order_id": None,
                        "infrastructure": self.infrastructure_name,
                        "action": action,
                        "status": "MONITOR_ONLY",
                        "message": f"Monitoring intent registered for {stock}. No trade order sent.",
                    }
                )
                continue

            execution_records.append(
                {
                    "order_id": f"amq-sim-{index:03d}",
                    "infrastructure": self.infrastructure_name,
                    "action": action,
                    "status": "FORWARDED",
                    "message": "Approved action forwarded to Amoriq financial infrastructure.",
                }
            )

        return {
            "infrastructure": self.infrastructure_name,
            "forwarded_count": len([r for r in execution_records if r.get("status") == "FORWARDED"]),
            "records": execution_records,
            "mode": "simulation",
        }


class AlpacaPaperExecutor:
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY", "").strip()
        self.secret_key = os.getenv("ALPACA_SECRET_KEY", "").strip()
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets").rstrip("/")

    @property
    def configured(self):
        return bool(self.api_key and self.secret_key)

    def forward_approved_actions(self, actions):
        if not self.configured:
            raise RuntimeError("Alpaca paper credentials are not configured.")

        execution_records = []
        headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=12.0) as client:
            for action in actions:
                action_type = (action or {}).get("type")
                symbol = (action or {}).get("stock")
                if action_type == "monitor":
                    execution_records.append(
                        {
                            "order_id": None,
                            "infrastructure": "Alpaca Paper",
                            "action": action,
                            "status": "MONITOR_ONLY",
                            "message": f"Monitoring intent registered for {symbol}. No trade order sent.",
                        }
                    )
                    continue
                if action_type not in {"buy", "sell"} or not symbol:
                    execution_records.append(
                        {
                            "order_id": None,
                            "infrastructure": "Alpaca Paper",
                            "action": action,
                            "status": "SKIPPED_UNSUPPORTED",
                            "message": "Action type is unsupported for paper execution.",
                        }
                    )
                    continue

                payload = {
                    "symbol": symbol.upper(),
                    "qty": "1",
                    "side": action_type,
                    "type": "market",
                    "time_in_force": "day",
                }
                response = client.post(f"{self.base_url}/v2/orders", headers=headers, json=payload)
                if response.status_code >= 400:
                    execution_records.append(
                        {
                            "order_id": None,
                            "infrastructure": "Alpaca Paper",
                            "action": action,
                            "status": "FAILED",
                            "message": f"Paper order rejected: {response.text[:240]}",
                        }
                    )
                    continue

                order = response.json()
                execution_records.append(
                    {
                        "order_id": order.get("id"),
                        "infrastructure": "Alpaca Paper",
                        "action": action,
                        "status": "FORWARDED",
                        "message": "Approved action forwarded to Alpaca paper trading API.",
                    }
                )

        return {
            "infrastructure": "Alpaca Paper",
            "forwarded_count": len([r for r in execution_records if r.get("status") == "FORWARDED"]),
            "records": execution_records,
            "mode": "paper",
        }


def simulate_amoriq_execution(actions):
    executor = AlpacaPaperExecutor()
    if executor.configured:
        try:
            return executor.forward_approved_actions(actions)
        except Exception as exc:
            fallback = AmoriqSimulator().forward_approved_actions(actions)
            fallback["warning"] = f"Paper execution failed, reverted to simulation: {exc}"
            return fallback
    return AmoriqSimulator().forward_approved_actions(actions)
