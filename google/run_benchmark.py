import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import httpx
from shared.config import require_api_key
from shared.filter import gate_and_write
from shared.provider import run_provider_benchmark

MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OUTPUT_PATH = "google/data/models.txt"
SNAPSHOT_PATH = "google/data/endpoint_snapshot.json"

KEEP_MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemma-4-26b-a4b-it", "gemma-4-31b-it"]


def fetch_models() -> list[str]:
    key = require_api_key("google", "GOOGLE_API_KEY")
    resp = httpx.get(MODELS_URL, params={"key": key}, timeout=30)
    resp.raise_for_status()
    chat = []
    for m in resp.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            mid = (m["name"].split("/")[-1] if "/" in m["name"] else m["name"])
            if mid in KEEP_MODELS:
                chat.append(mid)
    return sorted(chat)


if __name__ == "__main__":
    gate_and_write("Google", model_ids=fetch_models(),
        output_path=OUTPUT_PATH, snapshot_path=SNAPSHOT_PATH, source_url=MODELS_URL)
    run_provider_benchmark(provider="google")
