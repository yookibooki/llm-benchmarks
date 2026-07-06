import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

NIM_BASE = "https://integrate.api.nvidia.com/v1"
API_KEY = os.environ.get("NVIDIA_API_KEY", "")

ARTIFACT_ROOT = Path("artifacts")
ARTIFACT_ROOT.mkdir(exist_ok=True)


EXCLUDE_PATTERNS = [
    "embed", "image", "vision", "video", "audio", "moderation", "rerank", "guard",
    "vl", "clip", "omni", "parse", "retriever", "deplot", "diffusion", "kosmos",
    "neva", "vila", "pii", "reward", "safety", "content-safety", "ising",
    "bge", "fuyu", "multimodal", "translate", "cosmos",
]


def is_model_available(model_id, retries=1, timeout=20):
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                f"{NIM_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={"model": model_id, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                timeout=timeout,
            )
            if r.status_code == 200:
                return True
            if r.status_code == 503 and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return False
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return False
    return False


def get_models():
    r = requests.get(
        f"{NIM_BASE}/models", headers={"Authorization": f"Bearer {API_KEY}"}
    )
    r.raise_for_status()
    models = []
    for m in r.json()["data"]:
        model_id = m["id"]
        if any(x in model_id.lower() for x in EXCLUDE_PATTERNS):
            continue
        models.append(model_id)

    available = []
    for model_id in models:
        print(f"  Checking {model_id}...", end=" ", flush=True)
        if is_model_available(model_id):
            print("OK")
            available.append(model_id)
        else:
            print("404 - skipping")

    return available


def safe_name(model):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", model)


def run_aiperf(model):
    out_dir = ARTIFACT_ROOT / safe_name(model)
    cmd = [
        "aiperf",
        "profile",
        "-m",
        model,
        "-u",
        NIM_BASE,
        "--endpoint-type",
        "chat",
        "--streaming",
        "--api-key",
        API_KEY,
        "--tokenizer",
        "builtin",
        "--artifact-dir",
        str(out_dir),
        "--export-level",
        "summary",
        "--ui",
        "none",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return out_dir, result


def parse_summary(out_dir):
    f = out_dir / "profile_export_aiperf.json"
    if f.exists():
        data = json.loads(f.read_text())
        return {
            "output_token_throughput": data.get("output_token_throughput", {}).get("avg"),
            "ttft_p50": data.get("time_to_first_token", {}).get("p50"),
            "ttft_p99": data.get("time_to_first_token", {}).get("p99"),
            "request_error_rate": data.get("request_error_rate", {}).get("avg"),
        }

    jsonl = out_dir / "profile_export.jsonl"
    if not jsonl.exists():
        return None
    records = [json.loads(line) for line in jsonl.open() if line.strip()]
    if not records:
        return None
    latencies = [r["metrics"]["request_latency"]["value"] for r in records if "request_latency" in r.get("metrics", {})]
    tps_list = [r["metrics"]["e2e_output_token_throughput"]["value"] for r in records if "e2e_output_token_throughput" in r.get("metrics", {})]
    output_tokens = [r["metrics"]["output_token_count"]["value"] for r in records if "output_token_count" in r.get("metrics", {})]
    errors = sum(1 for r in records if r.get("metadata", {}).get("was_cancelled", False))
    return {
        "output_token_throughput": sum(tps_list) / len(tps_list) if tps_list else None,
        "ttft_p50": None,
        "ttft_p99": None,
        "request_error_rate": errors / len(records) if records else None,
    }


def main():
    models = get_models()
    print(f"Found {len(models)} models")

    results, failures = [], []

    for i, model in enumerate(models, 1):
        print(f"[{i}/{len(models)}] {model}")
        try:
            out_dir, proc = run_aiperf(model)
            if proc.returncode != 0:
                failures.append({"model": model, "error": proc.stderr[-500:]})
                continue
            metrics = parse_summary(out_dir)
            if metrics is None:
                failures.append({"model": model, "error": "no summary file produced"})
                continue
            results.append({"model": model, **metrics})
        except Exception as e:
            failures.append({"model": model, "error": str(e)})

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if results:
        results_path = ARTIFACT_ROOT / f"results_{timestamp}.csv"
        with open(results_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)
        print(f"Results written to {results_path}")

    if failures:
        failures_path = ARTIFACT_ROOT / f"failures_{timestamp}.csv"
        with open(failures_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["model", "error"])
            w.writeheader()
            w.writerows(failures)
        print(f"Failures written to {failures_path}")

    print(f"Done. {len(results)} succeeded, {len(failures)} failed.")


if __name__ == "__main__":
    main()
