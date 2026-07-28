import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.filter import gate_and_write
from shared.provider import run_provider_benchmark
from filter_models import MODELS_URL, OUTPUT_PATH, SNAPSHOT_PATH, fetch_chat_models, name_filter

if __name__ == "__main__":
    gate_and_write("Mistral", model_ids=fetch_chat_models(),
        output_path=OUTPUT_PATH, snapshot_path=SNAPSHOT_PATH,
        source_url=MODELS_URL, name_filter=name_filter)
    run_provider_benchmark(provider="mistral")
