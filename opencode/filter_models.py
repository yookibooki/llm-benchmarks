import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import httpx
from shared.config import require_api_key
from shared.filter import gate_and_write

MODELS_URL = "https://opencode.ai/zen/v1/models"
OUTPUT_PATH = "opencode/data/models.txt"
SNAPSHOT_PATH = "opencode/data/endpoint_snapshot.json"

EXTRA_KEEP = {"big-pickle"}


def get_model_ids() -> list[str]:
    key = require_api_key("opencode", "OPENCODE_API_KEY")
    resp = httpx.get(MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=30)
    resp.raise_for_status()
    models = resp.json().get("data", [])
    return [m["id"] for m in models]


def name_filter(model_id: str) -> bool:
    if model_id in EXTRA_KEEP:
        return True
    return model_id.endswith("-free")


def run() -> None:
    print("Fetching models from OpenCode Zen...")
    gate_and_write(
        "OpenCode",
        model_ids=get_model_ids(),
        output_path=OUTPUT_PATH,
        snapshot_path=SNAPSHOT_PATH,
        source_url=MODELS_URL,
        name_filter=name_filter,
    )


if __name__ == "__main__":
    run()
