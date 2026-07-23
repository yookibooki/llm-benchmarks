import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import httpx
from shared.config import require_api_key
from shared.filter import gate_and_write

MODELS_URL = "https://inference-api.nousresearch.com/v1/models"
OUTPUT_PATH = "nous/data/models.txt"
SNAPSHOT_PATH = "nous/data/endpoint_snapshot.json"

EXCLUDE_TERMS = [
    "embed", "rerank", "moderation", "tts", "stt", "whisper", "dall-e",
    "stable-diffusion", "midjourney", "content-safety", "safety", "guard",
    "lyria", "clip", "audio", "music", "safeguard",
    "poolside/laguna",
]


def fetch_model_ids() -> list[str]:
    key = require_api_key("nous", "NOUS_API_KEY")
    resp = httpx.get(MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=30)
    resp.raise_for_status()
    models = resp.json().get("data", [])
    return [m["id"] for m in models]


def name_filter(model_id: str) -> bool:
    if not model_id.endswith(":free"):
        return False
    lower = model_id.lower()
    if any(term in lower for term in EXCLUDE_TERMS):
        return False
    return True


if __name__ == "__main__":
    print("Fetching models from Nous Research...")
    gate_and_write(
        "Nous",
        model_ids=fetch_model_ids(),
        output_path=OUTPUT_PATH,
        snapshot_path=SNAPSHOT_PATH,
        source_url=MODELS_URL,
        name_filter=name_filter,
    )
