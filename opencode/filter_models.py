import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import httpx
from shared.config import require_api_key
from shared.filter import gate_and_write

MODELS_URL = "https://opencode.ai/zen/v1/models"
OUTPUT_PATH = "opencode/data/models.txt"
SNAPSHOT_PATH = "opencode/data/endpoint_snapshot.json"

EXCLUDE_TERMS = [
    "embed", "rerank", "moderation", "tts", "stt", "whisper", "dall-e",
    "stable-diffusion", "midjourney", "content-safety", "safety", "guard",
    "lyria", "clip", "audio", "music",
    "laguna-s-2.1-free",
]


def fetch_model_ids() -> list[str]:
    key = require_api_key("opencode", "OPENCODE_API_KEY")
    resp = httpx.get(MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=30)
    resp.raise_for_status()
    models = resp.json().get("data", [])
    return [m["id"] for m in models]


def name_filter(model_id: str) -> bool:
    lower = model_id.lower()
    if any(term in lower for term in EXCLUDE_TERMS):
        return False
    if lower.endswith("-free") or "big-pickle" in lower:
        return True
    return False


if __name__ == "__main__":
    print("Fetching models from OpenCode...")
    gate_and_write(
        "OpenCode",
        model_ids=fetch_model_ids(),
        output_path=OUTPUT_PATH,
        snapshot_path=SNAPSHOT_PATH,
        source_url=MODELS_URL,
        name_filter=name_filter,
    )
