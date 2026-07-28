import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import httpx
from shared.config import require_api_key
from shared.filter import gate_and_write

MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OUTPUT_PATH = "google/data/models.txt"
SNAPSHOT_PATH = "google/data/endpoint_snapshot.json"

KEEP_MODELS = [
    "gemini-3.1-flash-lite",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
]


def fetch_chat_models() -> list[str]:
    key = require_api_key("google", "GOOGLE_API_KEY")
    resp = httpx.get(MODELS_URL, params={"key": key}, timeout=30)
    resp.raise_for_status()
    models = resp.json().get("models", [])
    chat_models = []
    for m in models:
        name = m.get("name", "")
        supported = m.get("supportedGenerationMethods", [])
        if "generateContent" in supported:
            model_id = name.split("/")[-1] if "/" in name else name
            if model_id in KEEP_MODELS:
                chat_models.append(model_id)
    return sorted(chat_models)


if __name__ == "__main__":
    print("Fetching models from Google AI Studio...")
    gate_and_write(
        "Google",
        model_ids=fetch_chat_models(),
        output_path=OUTPUT_PATH,
        snapshot_path=SNAPSHOT_PATH,
        source_url=MODELS_URL,
    )
