import csv
import importlib
import os
import sys
from pathlib import Path

from shared.csv_utils import has_measurements, latest_measured_row

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
        tps_path = REPO_ROOT / provider / "data" / "tps.csv"
        pending = _pending_models(REPO_ROOT / provider / "data" / "models.txt", tps_path)
        if not pending:
            print("  no models lacking measurements; skipping benchmark")
            return
        print(f"  benchmarking {len(pending)} models lacking measurements")
        subset_path = REPO_ROOT / provider / "data" / "_benchmark_subset.txt"
        with open(subset_path, "w") as f:
            f.write("".join(f"{m}\n" for m in sorted(pending)))
        try:
            run_provider_benchmark(provider=provider, models_path=str(subset_path))
        finally:
            subset_path.unlink(missing_ok=True)
    else:
        run_provider_benchmark(provider=provider)


def _pending_models(models_path: Path, tps_path: Path) -> list[str]:
    with open(models_path) as f:
        catalog = {line.strip() for line in f if line.strip()}
    if not tps_path.exists():
        return sorted(catalog)
    grouped: dict[str, list[dict]] = {}
    with open(tps_path, newline="") as f:
        for row in csv.DictReader(f):
            grouped.setdefault(row["Model"], []).append(row)
    pending = set()
    for model in catalog:
        rows = grouped.get(model)
        best = latest_measured_row(rows) if rows else None
        if best is None or not has_measurements(best):
            pending.add(model)
    return sorted(pending)


def run_match(provider: str) -> None:
    mm = _load_module(provider, "tps-aa_matcher")
    print(f"--- {provider} matcher ---")
    mm._main()


def render() -> None:
    import gen_html

    print("--- rendering leaderboard ---")
    gen_html.main()


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

    try:
        render()
    except Exception as e:
        print(f"WARNING: leaderboard render failed: {e}", file=sys.stderr)
        failures.append(f"gen_html: {e}")


    if failures:
        for f in failures:
            print(f"::warning::{f}")
        print(f"{len(failures)} provider step(s) failed — publishing with stale or partial data", file=sys.stderr)


if __name__ == "__main__":
    full = "--full" in sys.argv
    run_pipeline(full)
