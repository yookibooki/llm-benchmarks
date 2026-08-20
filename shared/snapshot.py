import hashlib
import json
import os
from typing import Any


def model_list_hash(model_ids: list[str]) -> str:
    normalized = "\n".join(sorted(model_ids))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def read_snapshot(snapshot_path: str) -> dict[str, Any]:
    if not os.path.exists(snapshot_path):
        return {}
    try:
        with open(snapshot_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def write_snapshot(snapshot_path: str, model_ids: list[str], source: str) -> str:
    snapshot_hash = model_list_hash(model_ids)
    os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
    snapshot = {
        "hash": snapshot_hash,
        "count": len(model_ids),
        "source": source,
    }
    with open(snapshot_path, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")
    return snapshot_hash


def catalog_changed(snapshot_path: str, model_ids: list[str]) -> bool:
    previous = read_snapshot(snapshot_path)
    return previous.get("hash") != model_list_hash(model_ids)
