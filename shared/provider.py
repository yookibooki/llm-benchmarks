import csv
import os
import sys
import time
from pathlib import Path

from shared.benchmark import BenchmarkResult
from shared.csv_utils import latest_measured_row

REPO_ROOT = Path(__file__).resolve().parent.parent

PROVIDERS: dict[str, dict] = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_env_var": "NVIDIA_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_env_var": "OPENROUTER_API_KEY",
        "default_headers": {"HTTP-Referer": "https://github.com/yookibooki/llm-benchmarks"},
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_env_var": "GOOGLE_API_KEY",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "api_env_var": "MISTRAL_API_KEY",
    },
    "nous": {
        "base_url": "https://inference-api.nousresearch.com/v1",
        "api_env_var": "NOUS_API_KEY",
    },
    "opencode": {
        "base_url": "https://opencode.ai/zen/v1",
        "api_env_var": "OPENCODE_API_KEY",
    },
}


def load_model_ids(models_path: str) -> list[str]:
    if not os.path.exists(models_path):
        sys.exit(f"Can't find the model list at '{models_path}'. Run filter_models.py first.")
    with open(models_path) as f:
        ids = [line.strip() for line in f if line.strip()]
    if not ids:
        sys.exit(f"'{models_path}' exists but has no model names in it.")
    return ids


def _load_existing_rows(output_path: str) -> list[dict]:
    if not os.path.exists(output_path):
        return []
    with open(output_path, newline="") as f:
        return list(csv.DictReader(f))


def _load_intelligence(output_path: str) -> dict[str, str]:
    return {
        r["Model"]: r["Intelligence"]
        for r in _load_existing_rows(output_path)
        if r.get("Intelligence") not in ("", "-", None)
    }


def _keep_prior(results: list[BenchmarkResult], model_id: str, result) -> bool:
    if result.error is None:
        return False
    return any(r.model == model_id and r.tps is not None for r in results)


def _seed_results(existing_rows: list[dict]) -> list[BenchmarkResult]:
    grouped: dict[str, list[dict]] = {}
    for row in existing_rows:
        grouped.setdefault(row["Model"], []).append(row)
    seeded = []
    for rows in grouped.values():
        best = latest_measured_row(rows)
        if best is not None:
            seeded.append(BenchmarkResult.from_row(best))
    return seeded


def _benchmark_with_retry(
    model_id: str,
    provider: str,
    client,
    max_attempts: int = 3,
):
    from openai import APIConnectionError, RateLimitError
    from shared.benchmark import benchmark

    result = None
    for attempt in range(max_attempts):
        result = benchmark(
            model_id=model_id, client=client, provider=provider,
        )
        if result.error is None:
            return result
        if (
            isinstance(result.exc, (APIConnectionError, RateLimitError))
            and attempt < max_attempts - 1
        ):
            delay = 2 ** attempt
            print(
                f"  {model_id} failed ({result.error}); retrying in {delay}s "
                f"[attempt {attempt + 1}/{max_attempts}]",
                flush=True,
            )
            time.sleep(delay)
        else:
            return result
    return result


def run_provider_benchmark(*, provider: str, models_path: str | None = None) -> None:
    from openai import OpenAI
    from shared.config import require_api_key
    from shared.csv_utils import write_benchmark_csv

    cfg = PROVIDERS.get(provider)
    if cfg is None:
        sys.exit(f"Unknown provider '{provider}'. Add it to shared.provider.PROVIDERS.")

    models_path = models_path or str(REPO_ROOT / provider / "data" / "models.txt")
    output_path = str(REPO_ROOT / provider / "data" / "tps.csv")

    key = require_api_key(provider, cfg["api_env_var"])
    client_kwargs = {
        "base_url": cfg["base_url"],
        "api_key": key,
        "timeout": 60.0,
        "max_retries": 0,
        "default_headers": cfg.get("default_headers") or {},
    }
    client = OpenAI(**client_kwargs)
    model_ids = load_model_ids(models_path)

    print(f"Starting benchmark for {len(model_ids)} models...", flush=True)

    existing_rows = _load_existing_rows(output_path)
    existing_intelligence = _load_intelligence(output_path)

    results = _seed_results(existing_rows)

    for model_id in model_ids:
        result = _benchmark_with_retry(
            model_id, provider, client,
        )
        if _keep_prior(results, model_id, result):
            continue
        results = [r for r in results if r.model != model_id]
        results.append(result)
        write_benchmark_csv(output_path, results, existing_intelligence)

    print(f"\nCompleted. Wrote results to {output_path}")
