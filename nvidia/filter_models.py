import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json
import httpx
from shared.config import require_api_key
from shared.filter import gate_and_write

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODELS_URL = f"{BASE_URL}/models"
OUTPUT_PATH = "nvidia/data/models.txt"
SNAPSHOT_PATH = "nvidia/data/endpoint_snapshot.json"
FOUR_O_FOUR_PATH = "nvidia/data/404s.txt"

CACHED_IDS_PATH = os.environ.get("NIM_CACHED_MODEL_IDS_PATH")

EXCLUDE_IDS = {
    "google/gemma-3n-e4b-it",
    "google/gemma-3n-e2b-it",
    "microsoft/phi-4-mini-instruct",
    "deepseek-ai/deepseek-v4-pro",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.3-70b-instruct",
    "minimaxai/minimax-m3",
    "mistralai/mistral-medium-3.5-128b",
    "nvidia/llama-3.1-nemotron-nano-8b-v1",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "nvidia/nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-mini-4b-instruct",
    "nvidia/nemotron-nano-12b-v2-vl",
    "nvidia/nvidia-nemotron-nano-9b-v2",
}


EXCLUDE_TERMS = [
    "-1b-", "-1b", "-2b-", "-2b", "-3b-", "-3b",
    "embed", "image", "vision", "video", "audio",
    "moderation", "rerank", "guard", "clip", "parse", "retriever", "deplot",
    "diffusion", "kosmos", "neva", "vila", "pii", "reward", "safety",
    "content-safety", "ising", "bge", "fuyu", "multimodal", "translate", "cosmos",
    "llama2", "llama3-chatqa", "codegemma", "codellama", "recurrentgemma",
]


def get_model_ids() -> list[str]:
    key = require_api_key("nvidia", "NVIDIA_API_KEY")
    headers = {"Authorization": f"Bearer {key}"}
    if CACHED_IDS_PATH and os.path.exists(CACHED_IDS_PATH):
        with open(CACHED_IDS_PATH) as f:
            ids = json.load(f)
        print(f"  using cached model list from {CACHED_IDS_PATH} ({len(ids)} models)")
        return ids
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


def run() -> None:
    print("Fetching model list from NVIDIA NIM...")
    all_ids = get_model_ids()
    name_filtered = [m for m in all_ids if name_filter(m)]
    print(f"  {len(name_filtered)} models after name filter")

    validated = remove_404_models(name_filtered)
    print(f"  {len(validated)} models after 404 filtering")

    gate_and_write(
        "NVIDIA",
        model_ids=validated,
        output_path=OUTPUT_PATH,
        snapshot_path=SNAPSHOT_PATH,
        source_url=MODELS_URL,
    )


if __name__ == "__main__":
    run()
