import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import httpx
from shared.config import require_api_key
from shared.filter import gate_and_write

MODELS_URL = "https://openrouter.ai/api/v1/models"
OUTPUT_PATH = "openrouter/data/models.txt"
SNAPSHOT_PATH = "openrouter/data/endpoint_snapshot.json"

EXCLUDE_TERMS = [
    "embed", "rerank", "moderation", "openrouter/free", "tts", "stt",
    "whisper", "dall-e", "stable-diffusion", "midjourney", "content-safety",
    "safety", "guard", "lyria", "clip", "audio", "music",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "poolside/laguna-m.1:free",
    "poolside/laguna-s-2.1:free",
    "poolside/laguna-xs-2.1:free",
]

SMALL_MODEL_PATTERNS = ["-1b-", "-1b.", "-1.2b-", "-1.3b-", "-2b-", "-2b."]


def get_model_ids() -> list[str]:
    key = require_api_key("openrouter", "OPENROUTER_API_KEY")
    resp = httpx.get(MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=30)
    resp.raise_for_status()
    models = resp.json().get("data", [])
    free_models = []
    for m in models:
        model_id = m.get("id", "")
        pricing = m.get("pricing", {})
        prompt_price = float(pricing.get("prompt", "1") or "1")
        completion_price = float(pricing.get("completion", "1") or "1")
        if prompt_price == 0 and completion_price == 0:
            arch = m.get("architecture", {})
            output_mods = arch.get("output_modalities", [])
            if "text" in output_mods or not output_mods:
                free_models.append(model_id)
    return sorted(free_models)


def name_filter(model_id: str) -> bool:
    lower = model_id.lower()
    if any(term in lower for term in EXCLUDE_TERMS):
        return False
    normalized = lower.replace(":", "-")
    if any(pat in normalized for pat in SMALL_MODEL_PATTERNS):
        return False
    return True


def run() -> None:
    print("Fetching free models from OpenRouter...")
    gate_and_write(
        "OpenRouter",
        model_ids=get_model_ids(),
        output_path=OUTPUT_PATH,
        snapshot_path=SNAPSHOT_PATH,
        source_url=MODELS_URL,
        name_filter=name_filter,
    )


if __name__ == "__main__":
    run()
