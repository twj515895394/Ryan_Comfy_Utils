import json
from datetime import datetime, timezone
from pathlib import Path


def create_session_record(
    workspace: Path,
    runner: str,
    skill_id: str,
    context_payload: dict,
) -> dict:
    record = {
        "runner": runner,
        "skill_id": skill_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (workspace / "metadata.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (workspace / "context.json").write_text(
        json.dumps(context_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record
