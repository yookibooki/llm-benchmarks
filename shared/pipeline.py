import csv
import importlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import partial
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
            name = row.get("Model")
            if not name:
                continue
            grouped.setdefault(name, []).append(row)
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
    try:
        resp = httpx.get(AA_URL, headers={"x-api-key": key}, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"  WARNING: AA fetch failed: {e}; using stale data", file=sys.stderr)
        return
    AA_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    AA_RAW_PATH.write_text(resp.text)
    lines = resp.text.count("\n") + 1
    print(f"Fetched {lines} lines of AA data")


def _run_step(step, label: str, provider: str) -> str | None:
    try:
        step(provider)
    except SystemExit as e:
        print(f"WARNING: {provider} {label} failed: {e}", file=sys.stderr)
        return f"{provider} {label}: {e}"
    except Exception as e:
        print(f"WARNING: {provider} {label} failed: {e}", file=sys.stderr)
        return f"{provider} {label}: {e}"
    return None


def _run_step_parallel(step, providers: list[str], label: str) -> list[str]:
    if len(providers) <= 1:
        results = [_run_step(step, label, p) for p in providers]
    else:
        with ThreadPoolExecutor(max_workers=len(providers)) as ex:
            futures = [ex.submit(_run_step, step, label, p) for p in providers]
            results = [f.result() for f in futures]
    return [f for f in results if f]


def _run_step_all(step, providers: list[str]) -> None:
    if len(providers) <= 1:
        for p in providers:
            step(p)
        return
    with ThreadPoolExecutor(max_workers=len(providers)) as ex:
        futures = [ex.submit(step, p) for p in providers]
        for f in futures:
            f.result()


def run_pipeline(full: bool, providers: list[str] | None = None) -> None:
    from shared.provider import PROVIDERS

    selected = list(providers) if providers is not None else list(PROVIDERS)
    failures: list[str] = []

    failures += _run_step_parallel(run_filter, selected, "filter")
    failures += _run_step_parallel(partial(run_benchmark, full=full), selected, "benchmark")

    fetch_aa()

    failures += _run_step_parallel(run_match, selected, "matcher")

    try:
        render()
    except SystemExit as e:
        print(f"WARNING: leaderboard render failed: {e}", file=sys.stderr)
        failures.append(f"gen_html: {e}")
    except Exception as e:
        print(f"WARNING: leaderboard render failed: {e}", file=sys.stderr)
        failures.append(f"gen_html: {e}")


    if failures:
        for f in failures:
            print(f"::warning::{f}")
        print(f"{len(failures)} provider step(s) failed — publishing with stale or partial data", file=sys.stderr)


def _all_providers() -> list[str]:
    from shared.provider import PROVIDERS

    return list(PROVIDERS)


def _parse_provider_arg(argv: list[str]) -> list[str] | None:
    if "--provider" not in argv:
        return None
    idx = argv.index("--provider")
    if idx + 1 >= len(argv):
        sys.exit("--provider requires a value")
    name = argv[idx + 1]
    known = _all_providers()
    if name not in known:
        sys.exit(f"Unknown provider '{name}'. Known: {sorted(known)}")
    return [name]


if __name__ == "__main__":
    argv = sys.argv[1:]
    full = "--full" in argv
    providers = _parse_provider_arg(argv)

    if "--filter-only" in argv:
        _run_step_all(run_filter, providers or _all_providers())
    elif "--benchmark-only" in argv:
        if providers is None:
            sys.exit("--benchmark-only requires --provider")
        _run_step_all(partial(run_benchmark, full=full), providers)
    elif "--match-only" in argv:
        _run_step_all(run_match, providers or _all_providers())
    elif "--render-only" in argv:
        render()
    elif "--fetch-aa-only" in argv:
        fetch_aa()
    else:
        run_pipeline(full, providers)
