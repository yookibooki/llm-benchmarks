import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import httpx
from shared.config import require_api_key
from shared.filter import gate_and_write

MODELS_URL = "https://api.mistral.ai/v1/models"
OUTPUT_PATH = "mistral/data/models.txt"
SNAPSHOT_PATH = "mistral/data/endpoint_snapshot.json"

EXCLUDE_TERMS = [
    "embed", "fim", "ocr", "moderation", "tts", "stt", "realtime",
    "transcribe", "voxtral", "open-mistral-nemo",
    "labs-leanstral-1-5",
    "labs-leanstral-1-5-1",
]

SMALL_MODEL_PATTERNS = ["-1b-", "-1b.", "-1.2b-", "-1.3b-", "-2b-", "-2b."]


def fetch_chat_models() -> list[str]:
    key = require_api_key("mistral", "MISTRAL_API_KEY")
    resp = httpx.get(MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=30)
    resp.raise_for_status()
    models = resp.json().get("data", [])
    chat_models = []
    for m in models:
        model_id = m.get("id", "")
        caps = m.get("capabilities", {})
        if caps.get("completion_chat", False):
            chat_models.append(model_id)
    return sorted(set(chat_models))


def name_filter(model_id: str) -> bool:
    lower = model_id.lower()
    if any(term in lower for term in EXCLUDE_TERMS):
        return False
    if any(pat in lower for pat in SMALL_MODEL_PATTERNS):
        return False
    return True


if __name__ == "__main__":
    print("Fetching models from Mistral...")
    gate_and_write(
        "Mistral",
        model_ids=fetch_chat_models(),
        output_path=OUTPUT_PATH,
        snapshot_path=SNAPSHOT_PATH,
        source_url=MODELS_URL,
        name_filter=name_filter,
    )
