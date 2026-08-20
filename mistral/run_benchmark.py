import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.filter import gate_and_write
from shared.provider import run_provider_benchmark
from filter_models import (
    MODELS_URL,
    OUTPUT_PATH,
    SNAPSHOT_PATH,
    fetch_chat_models,
    name_filter,
    deduplicate_aliases,
)

if __name__ == "__main__":
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
    run_provider_benchmark(provider="mistral")
