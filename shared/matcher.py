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


def match_provider(tps_path: str, *, normalize, manual_intel: dict[str, str | int] | None = None, models_path: str | None = None, provider_name: str | None = None, aa_path: str | None = None) -> None:
    manual_intel = manual_intel or {}
    aa_index = load_aa_index() if aa_path is None else load_aa_index(aa_path)
    print(f"Loaded {len(aa_index)} AA models with intelligence + creator")
    rows = read_rows(tps_path)
    if rows is None:
        rows = []

    rows = _ensure_catalog_models(rows, models_path, provider_name)
    if not rows:
        print("No rows; nothing to do.")
        return
    matched = unmatched = warned = 0
    for row in rows:
        model = row["Model"]
        key = model.split("/", 1)[1] if "/" in model else model
        override = manual_intel.get(key, manual_intel.get(model))
        if override is not None:
            if isinstance(override, int):
                row["Intelligence"] = str(override)
                matched += 1
                continue
            entry = aa_index.get(override)
            if entry is not None:
                row["Intelligence"] = str(math.ceil(entry["intelligence"]))
                matched += 1
                continue
            print(f"  [warn] {model}: override '{override}' not in AA")
            warned += 1
            row["Intelligence"] = "-"
            continue
        entry = aa_index.get(key)
        if entry is None:
            norm = normalize(key)
            entry = aa_index.get(norm)
        if entry is None:
            print(f"  [warn] {model}: no AA match")
            unmatched += 1
            row["Intelligence"] = "-"
            continue
        row["Intelligence"] = str(math.ceil(entry["intelligence"]))
        matched += 1
    write_rows(tps_path, rows)
    print(f"Updated {matched}/{len(rows)} models in {tps_path} (warned={warned}, unmatched={unmatched})")
