import csv
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / path
    return p


def write_benchmark_csv(output_path: str | Path, results: list, intelligence: dict[str, str] | None = None) -> None:
    if intelligence is None:
        intelligence = {}
    output_path = _resolve(output_path)
    os.makedirs(output_path.parent, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with open(tmp_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Model", "Provider", "Intelligence", "Latency", "TPS"])
        writer.writerows(r.row(intelligence) for r in results)
    os.replace(tmp_path, output_path)


def read_benchmark_csv(csv_path: str | Path) -> list[dict]:
    csv_path = _resolve(csv_path)
    if not csv_path.exists():
        return []
    with open(csv_path) as f:
        return list(csv.DictReader(f))


def has_measurements(row: dict) -> bool:
    lat = row.get("Latency", "")
    tps = row.get("TPS", "")
    return lat not in ("", "-", None) and tps not in ("", "-", None)


def latest_measured_row(rows: list[dict] | None) -> dict | None:
    if not rows:
        return None
    measured = [r for r in rows if has_measurements(r)]
    if measured:
        return measured[-1]
    return rows[-1]


def merge_provider_csvs(provider_dirs: list[str | Path], output_path: str | Path) -> None:
    all_rows = []
    for provider_dir in provider_dirs:
        csv_path = _resolve(Path(provider_dir) / "data" / "tps.csv")
        if csv_path.exists():
            all_rows.extend(read_benchmark_csv(csv_path))
    if not all_rows:
        print("[warn] No data found in any provider directories")
        return
    fieldnames = ["Model", "Provider", "Intelligence", "Latency", "TPS"]
    output_path = _resolve(output_path)
    os.makedirs(output_path.parent, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with open(tmp_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    os.replace(tmp_path, output_path)
    print(f"Merged {len(all_rows)} rows from {len(provider_dirs)} providers into {output_path}")
