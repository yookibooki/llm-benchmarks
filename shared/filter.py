import os
from shared.snapshot import catalog_changed, write_snapshot


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


def gate_and_write(label: str, *, model_ids: list[str], output_path: str, snapshot_path: str, source_url: str, name_filter=None) -> None:
    print(f"  {len(model_ids)} models returned")
    if name_filter is not None:
        model_ids = [m for m in model_ids if name_filter(m)]
        print(f"  {len(model_ids)} survive name filter")
    changed, model_ids = gate_changed(snapshot_path, model_ids, source_url)
    if not changed:
        print("  catalog unchanged since last run; skipping filter")
        return
    write_models(output_path, model_ids)
