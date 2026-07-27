import csv
import json
import math
import sys

AA_PATH = "data/aa_raw.json"


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


def match_provider(tps_path: str, *, normalize, overrides: dict[str, str | None] | None = None, manual_intel: dict[str, int] | None = None, strip_namespace: bool = False, expected_creator=None) -> None:
    manual_intel = manual_intel or {}
    overrides = overrides or {}
    aa_index = load_aa_index()
    print(f"Loaded {len(aa_index)} AA models with intelligence + creator")
    check_duplicate_targets(overrides)
    rows = read_rows(tps_path)
    if rows is None:
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
                continue
            entry = aa_index.get(ov)
            if entry is not None:
                row["Intelligence"] = str(math.ceil(entry["intelligence"]))
                matched += 1
                continue
            print(f"  [warn] {model}: override '{ov}' not in AA")
            warned += 1
            continue
        key = model.split("/", 1)[1] if strip_namespace and "/" in model else model
        entry = aa_index.get(key)
        if entry is None:
            norm = normalize(key)
            entry = aa_index.get(norm)
        if entry is None:
            print(f"  [warn] {model}: no AA match")
            unmatched += 1
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
