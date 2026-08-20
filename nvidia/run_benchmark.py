import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.filter import gate_and_write
from shared.provider import run_provider_benchmark
from filter_models import (
    MODELS_URL,
    OUTPUT_PATH,
    SNAPSHOT_PATH,
    get_model_ids,
    name_filter,
    remove_404_models,
)

if __name__ == "__main__":
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
    run_provider_benchmark(provider="nvidia")
