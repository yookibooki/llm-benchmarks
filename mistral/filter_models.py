import os
import re
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


def canonicalize_model(model_id: str) -> str:
    s = model_id.replace(".", "-")
    s = re.sub(r"-\d{4}$", "", s)
    s = s.removesuffix("-latest")
    return s


def _alias_priority(model_id: str) -> int:
    score = 0
    if model_id.endswith("-latest"):
        score += 10
    if "." not in model_id:
        score += 5
    return score


def deduplicate_aliases(model_ids: list[str]) -> list[str]:
    by_canon: dict[str, list[str]] = {}
    for model_id in model_ids:
        by_canon.setdefault(canonicalize_model(model_id), []).append(model_id)
    result = []
    for canon, aliases in by_canon.items():
        if len(aliases) == 1:
            result.append(aliases[0])
        else:
            best = max(aliases, key=_alias_priority)
            dropped = [a for a in aliases if a != best]
            print(f"  dedup: keeping '{best}', dropping {len(dropped)} alias(es): {dropped}")
            result.append(best)
    return result


if __name__ == "__main__":
    print("Fetching models from Mistral...")
    all_models = fetch_chat_models()
    filtered = [m for m in all_models if name_filter(m)]
    print(f"  {len(filtered)} survive name filter")
    deduped = deduplicate_aliases(filtered)
    print(f"  {len(deduped)} after alias deduplication")
    gate_and_write(
        "Mistral",
        model_ids=deduped,
        output_path=OUTPUT_PATH,
        snapshot_path=SNAPSHOT_PATH,
        source_url=MODELS_URL,
    )
