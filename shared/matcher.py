import csv
import json
import math
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AA_PATH = str(REPO_ROOT / "data" / "aa_raw.json")


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / path
    return p


def _load_catalog(model_ids_path: str | None) -> list[str] | None:
    if not model_ids_path:
        return None
    path = _resolve(model_ids_path)
    if not path.exists():
        return None
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def _ensure_catalog_models(
    rows: list[dict],
    model_ids_path: str | None,
    provider_name: str | None,
) -> list[dict]:
    catalog = _load_catalog(model_ids_path)
    if catalog is None:
        return rows
    existing = {r["Model"] for r in rows}
    missing = set(catalog) - existing
    if not missing:
        return rows
    fieldnames = list(rows[0].keys()) if rows else [
        "Model", "Provider", "Intelligence", "Latency", "TPS",
    ]
    if not provider_name and rows:
        provider_name = rows[0].get("Provider", "")
    for model in sorted(missing):
        row = {fn: "-" for fn in fieldnames}
        row["Model"] = model
        if provider_name:
            row["Provider"] = provider_name
        row["Intelligence"] = ""
        row["Latency"] = "-"
        row["TPS"] = "-"
        rows.append(row)
    print(f"  Added {len(missing)} catalog models missing from tps.csv")
    return rows


def load_aa_index(path: str = AA_PATH) -> dict[str, dict]:
    with open(path) as f:
        data = json.load(f)["data"]
    index: dict[str, dict] = {}
    for m in data:
        slug = m["slug"]
        intelligence = m.get("evaluations", {}).get("artificial_analysis_intelligence_index")
        creator = (m.get("model_creator") or {}).get("slug")
        if intelligence is None or not creator:
            continue
        prev = index.get(slug)
        if prev is None or intelligence > prev["intelligence"]:
            index[slug] = {"intelligence": intelligence, "creator": creator}
    return index


def read_rows(tps_path: str) -> list[dict] | None:
    try:
        with open(tps_path) as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"No {tps_path} found, skipping.")
        return None
    if not rows:
        print("No rows in tps.csv; nothing to do.")
        return None
    return rows


def write_rows(tps_path: str, rows: list[dict]) -> None:
    fieldnames = list(rows[0].keys())
    with open(tps_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def check_duplicate_targets(overrides: dict[str, str | None]) -> None:
    targets: dict[str, list[str]] = {}
    for key, target in overrides.items():
        if target is None:
            continue
        targets.setdefault(target, []).append(key)
    for target, keys in targets.items():
        if len(keys) > 1:
            print(f"  [warn] MANUAL_OVERRIDES: {keys} all map to '{target}' — verify this isn't a copy-paste error", file=sys.stderr)


_MISSING = object()


def _lookup_override(overrides, model, strip_namespace):
    if model in overrides:
        return overrides[model]
    if strip_namespace and "/" in model:
        slug = model.split("/", 1)[1]
        if slug in overrides:
            return overrides[slug]
    return _MISSING


def match_provider(tps_path: str, *, normalize, overrides: dict[str, str | None] | None = None, manual_intel: dict[str, int] | None = None, strip_namespace: bool = False, expected_creator=None, models_path: str | None = None, provider_name: str | None = None, aa_path: str | None = None) -> None:
    manual_intel = manual_intel or {}
    overrides = overrides or {}
    aa_index = load_aa_index() if aa_path is None else load_aa_index(aa_path)
    print(f"Loaded {len(aa_index)} AA models with intelligence + creator")
    check_duplicate_targets(overrides)
    rows = read_rows(tps_path)
    if rows is None:
        rows = []

    rows = _ensure_catalog_models(rows, models_path, provider_name)
    if not rows:
        print("No rows; nothing to do.")
        return
    matched = unmatched = warned = skipped = 0
    for row in rows:
        model = row["Model"]
        manual = manual_intel.get(model)
        if manual is not None:
            row["Intelligence"] = str(manual)
            matched += 1
            continue
        ov = _lookup_override(overrides, model, strip_namespace)
        if ov is not _MISSING:
            if ov is None:
                skipped += 1
                row["Intelligence"] = "-"
                continue
            entry = aa_index.get(ov)
            if entry is not None:
                row["Intelligence"] = str(math.ceil(entry["intelligence"]))
                matched += 1
                continue
            print(f"  [warn] {model}: override '{ov}' not in AA")
            warned += 1
            row["Intelligence"] = "-"
            continue
        key = model.split("/", 1)[1] if strip_namespace and "/" in model else model
        entry = aa_index.get(key)
        if entry is None:
            norm = normalize(key)
            entry = aa_index.get(norm)
        if entry is None:
            print(f"  [warn] {model}: no AA match")
            unmatched += 1
            row["Intelligence"] = "-"
            continue
        if expected_creator is not None:
            exp = expected_creator(model)
            if exp and entry["creator"] != exp:
                print(f"  [warn] {model}: creator mismatch ({exp} vs {entry['creator']})")
                warned += 1
        row["Intelligence"] = str(math.ceil(entry["intelligence"]))
        matched += 1
    write_rows(tps_path, rows)
    print(f"Updated {matched}/{len(rows)} models in {tps_path} (warned={warned}, unmatched={unmatched}, skipped={skipped})")
