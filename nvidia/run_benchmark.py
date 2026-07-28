import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json
import httpx
from shared.config import require_api_key

from shared.filter import gate_changed, write_models
from shared.provider import run_provider_benchmark

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODELS_URL = f"{BASE_URL}/models"
SNAPSHOT_PATH = "nvidia/data/endpoint_snapshot.json"
MODELS_PATH = "nvidia/data/models.txt"
FOUR_O_FOUR_PATH = "nvidia/data/404s.txt"

EXCLUDE_IDS = {
    "google/gemma-3n-e4b-it",
    "google/gemma-3n-e2b-it",
    "microsoft/phi-4-mini-instruct",
}

EXCLUDE_TERMS = [
    "-1b-", "-1b", "-2b-", "-2b", "-3b-", "-3b",
    "embed", "image", "vision", "video", "audio",
    "moderation", "rerank", "guard", "clip", "parse", "retriever", "deplot",
    "diffusion", "kosmos", "neva", "vila", "pii", "reward", "safety",
    "content-safety", "ising", "bge", "fuyu", "multimodal", "translate", "cosmos",
    "llama2", "llama3-chatqa", "codegemma", "codellama", "recurrentgemma",
]


def get_model_ids(headers: dict) -> list[str]:
    cached = os.environ.get("NIM_CACHED_MODEL_IDS_PATH")
    if cached and os.path.exists(cached):
        with open(cached) as f:
            return json.load(f)
    resp = httpx.get(MODELS_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    return [m["id"] for m in resp.json()["data"]]


def name_filter(model_id: str) -> bool:
    if model_id in EXCLUDE_IDS:
        return False
    lower = model_id.lower()
    return not any(term in lower for term in EXCLUDE_TERMS)


def remove_404_models(model_ids: list[str]) -> list[str]:
    if not os.path.exists(FOUR_O_FOUR_PATH):
        return model_ids
    with open(FOUR_O_FOUR_PATH) as f:
        known_404s = {line.strip() for line in f if line.strip()}
    if not known_404s:
        return model_ids
    valid = [m for m in model_ids if m not in known_404s]
    skipped = len(model_ids) - len(valid)
    if skipped:
        print(f"  skipped {skipped} known-404 models")
    return valid


if __name__ == "__main__":
    key = require_api_key("nvidia", "NVIDIA_API_KEY")
    headers = {"Authorization": f"Bearer {key}"}

    all_ids = get_model_ids(headers)
    name_filtered = [m for m in all_ids if name_filter(m)]
    print(f"  {len(name_filtered)} models after name filter")

    changed, _ = gate_changed(SNAPSHOT_PATH, name_filtered, MODELS_URL)
    if changed:
        validated = remove_404_models(name_filtered)
        print(f"  {len(validated)} models after 404 validation")
        write_models(MODELS_PATH, validated)
        print("  wrote updated models.txt")
    else:
        print("  catalog unchanged; using existing models.txt")

    run_provider_benchmark(provider="nvidia")
