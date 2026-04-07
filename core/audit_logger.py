import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent.parent
AUDIT_DIR = BASE_DIR / "logs"
AUDIT_FILE = AUDIT_DIR / "enforcement_audit.jsonl"


def new_trace_id():
    return f"trace-{uuid4()}"


def write_audit_log(event_type, trace_id, payload):
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "trace_id": trace_id,
        "payload": payload,
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
