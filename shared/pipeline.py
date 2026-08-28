import importlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

AA_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
AA_RAW_PATH = REPO_ROOT / "data" / "aa_raw.json"


def _load_module(provider: str, suffix: str):
    return importlib.import_module(f"{provider}.{suffix}")


def run_filter(provider: str) -> None:
    fm = _load_module(provider, "filter_models")
    print(f"--- {provider} filter ---")
    fm.run()


def run_benchmark(provider: str, full: bool) -> None:
    from shared.provider import run_provider_benchmark

    print(f"--- {provider} benchmark (full={full}) ---")
    if not full:
        models_path = REPO_ROOT / provider / "data" / "models.txt"
        with open(models_path) as f:
            current = {line.strip() for line in f if line.strip()}
        tps_path = REPO_ROOT / provider / "data" / "tps.csv"
        existing: set[str] = set()
        if tps_path.exists():
            import csv

            with open(tps_path, newline="") as f:
                existing = {r["Model"] for r in csv.DictReader(f)}
        new = current - existing
        if not new:
            print(f"  no new models; skipping benchmark")
            return
        print(f"  benchmarking {len(new)} new models (keeping {len(current & existing)} existing rows)")
        # Benchmark only the new models. run_provider_benchmark preserves
        # existing tps.csv rows, and models.txt is left intact so the matcher
        # and gen_html reconcile do not prune models that already have data.
        subset_path = REPO_ROOT / provider / "data" / "_benchmark_subset.txt"
        with open(subset_path, "w") as f:
            for model_id in sorted(new):
                f.write(f"{model_id}\n")
        try:
            run_provider_benchmark(provider=provider, models_path=str(subset_path))
        finally:
            subset_path.unlink(missing_ok=True)
    else:
        run_provider_benchmark(provider=provider)

def run_match(provider: str) -> None:
    mm = _load_module(provider, "tps-aa_matcher")
    print(f"--- {provider} matcher ---")
    mm._main()


def fetch_aa() -> None:
    key = os.environ.get("AA_API_KEY", "")
    if not key:
        print("  no AA_API_KEY; skipping AA refresh", file=sys.stderr)
        return
    import httpx

    print("--- fetching AA model data ---")
    resp = httpx.get(AA_URL, headers={"x-api-key": key}, timeout=60)
    resp.raise_for_status()
    AA_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    AA_RAW_PATH.write_text(resp.text)
    lines = resp.text.count("\n") + 1
    print(f"Fetched {lines} lines of AA data")


def run_pipeline(full: bool) -> None:
    from shared.provider import PROVIDERS

    providers = list(PROVIDERS)
    failures: list[str] = []

    for prov in providers:
        try:
            run_filter(prov)
        except Exception as e:
            print(f"WARNING: {prov} filter failed: {e}", file=sys.stderr)
            failures.append(f"{prov} filter: {e}")

    for prov in providers:
        try:
            run_benchmark(prov, full)
        except Exception as e:
            print(f"WARNING: {prov} benchmark failed: {e}", file=sys.stderr)
            failures.append(f"{prov} benchmark: {e}")

    fetch_aa()

    for prov in providers:
        try:
            run_match(prov)
        except Exception as e:
            print(f"WARNING: {prov} matcher failed: {e}", file=sys.stderr)
            failures.append(f"{prov} matcher: {e}")

    if failures:
        for f in failures:
            print(f"::warning::{f}")
        print(f"{len(failures)} provider step(s) failed — publishing with stale or partial data", file=sys.stderr)


if __name__ == "__main__":
    full = "--full" in sys.argv
    run_pipeline(full)
