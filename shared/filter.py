import os
import sys
from shared.snapshot import catalog_changed, write_snapshot

MIN_MODELS = 2
QUORUM_RATIO = 0.5


def gate_changed(snapshot_path: str, model_ids: list[str], source_url: str) -> tuple[bool, list[str]]:
    model_ids = sorted(model_ids)
    if not catalog_changed(snapshot_path, model_ids):
        return False, model_ids
    snapshot_hash = write_snapshot(snapshot_path, model_ids, source_url)
    print(f"  catalog hash={snapshot_hash[:12]}")
    return True, model_ids


def write_models(output_path: str, model_ids: list[str]) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        for model_id in sorted(model_ids):
            f.write(f"{model_id}\n")
    print(f"Wrote {len(model_ids)} model ids to {output_path}")


def _quorum_check(new_ids: list[str], output_path: str, label: str) -> None:
    if not os.path.exists(output_path):
        return
    with open(output_path) as f:
        old_count = sum(1 for line in f if line.strip())
    if old_count == 0:
        return
    ratio = len(new_ids) / old_count
    if ratio < QUORUM_RATIO:
        print(
            f"  [WARN] {label}: catalog shrank from {old_count} to {len(new_ids)} "
            f"({ratio:.0%}) — possible endpoint issue",
            file=sys.stderr,
        )


def gate_and_write(label: str, *, model_ids: list[str], output_path: str, snapshot_path: str, source_url: str, name_filter=None) -> None:
    print(f"  {label}: {len(model_ids)} models returned")
    if name_filter is not None:
        model_ids = [m for m in model_ids if name_filter(m)]
        print(f"  {label}: {len(model_ids)} survive name filter")

    if len(model_ids) < MIN_MODELS:
        print(
            f"  [ERROR] {label}: only {len(model_ids)} models after filtering — "
            f"refusing to write catalog (possible endpoint/API issue)",
            file=sys.stderr,
        )
        sys.exit(1)

    changed, model_ids = gate_changed(snapshot_path, model_ids, source_url)

    if not changed and os.path.exists(output_path):
        print(f"  {label}: catalog unchanged and output exists; skipping filter")
        return

    _quorum_check(model_ids, output_path, label)
    write_models(output_path, model_ids)
