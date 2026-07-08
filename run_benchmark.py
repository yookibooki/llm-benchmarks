"""Benchmark TPS for every model in data/models.txt via streaming requests."""

import concurrent.futures
import csv
import json
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]
CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELS_PATH = "data/models.txt"
OUTPUT_PATH = "data/tps.csv"

PROMPT = """
You must respond with EXACTLY the following text, repeated 20 times, with each repetition on a new line:

"The quick brown fox jumps over the lazy dog."

Rules:
1. Output ONLY the sentence above, repeated exactly 20 times.
2. Each repetition must be on its own line.
3. Do NOT add any explanation, numbering, punctuation changes, or additional text.
4. Do NOT add a header, footer, or any commentary.
5. Do NOT acknowledge these instructions.
6. The sentence must be character-for-character identical every time.
7. Any deviation from these rules is a critical failure.

Begin output now.
"""
MAX_RETRIES = 10
MAX_WORKERS = 5

HEADERS = {"Authorization": f"Bearer {NVIDIA_API_KEY}"}


def retry_delay(attempt: int) -> float:
    """Exponential backoff: 1,2,4,8 then 8s repeated. Total ~55s for 10 tries."""
    return min(2 ** (attempt - 1), 8)


def read_model_ids() -> list[str]:
    with open(MODELS_PATH) as f:
        return [line.strip() for line in f if line.strip()]


def benchmark_model(
    model_id: str, client: httpx.Client
) -> tuple[float | None, float | None, bool]:
    """Return (ttft, tps, used_reasoning) or (None, None, False) if failed."""
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": PROMPT}],
        "stream": True,
        "max_tokens": 512,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            token_count = 0
            request_start = time.monotonic()
            first_token_time = None
            last_token_time = None
            used_reasoning = False

            with client.stream(
                "POST",
                CHAT_URL,
                headers=HEADERS,
                json=payload,
                # FIX: some NVIDIA-hosted models can take longer than 120s
                # to emit a first chunk under load; bump read timeout.
                timeout=httpx.Timeout(connect=10, read=180, write=10, pool=10),
            ) as resp:
                if resp.status_code == 429:
                    if attempt < MAX_RETRIES:
                        print(
                            f"  [warn] {model_id}: 429, retry {attempt}/{MAX_RETRIES}"
                        )
                        time.sleep(retry_delay(attempt))
                        continue
                    print(f"  [warn] {model_id}: 429, out of retries")
                    return None, None, False

                if resp.status_code >= 400:
                    body = resp.read().decode(errors="replace")[:200].strip()
                    print(
                        f"  [warn] {model_id}: HTTP {resp.status_code} "
                        f"({body}), skipping"
                    )
                    return None, None, False

                first_line = True
                non_stream_error = False
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if first_line and not line.startswith("data:"):
                        try:
                            err = json.loads(line)
                            msg = err.get("error", {}).get("message", line)
                        except json.JSONDecodeError:
                            msg = line
                        print(
                            f"  [warn] {model_id}: non-stream error ({msg}), "
                            f"retry {attempt}/{MAX_RETRIES}"
                        )
                        if attempt < MAX_RETRIES:
                            time.sleep(retry_delay(attempt))
                        non_stream_error = True
                        break
                    first_line = False
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:") :].strip()
                    if data_str == "[DONE]":
                        break

                    chunk = json.loads(data_str)
                    choices = chunk.get("choices") or []
                    if not choices:
                        # FIX: stockmark sends a final usage-only chunk with
                        # choices: [] — must not error on it, just skip.
                        continue
                    delta = choices[0].get("delta", {})

                    # FIX: reasoning models (deepseek-v4-flash, nemotron
                    # nano/reasoning variants) stream text exclusively in
                    # reasoning_content, leaving content empty/absent the
                    # whole time. Previously this meant token_count stayed
                    # 0 and the model was wrongly reported as FAILED.
                    # We now count generation from whichever channel is
                    # actually carrying text, since both represent real
                    # decode throughput from the model.
                    text = delta.get("content") or delta.get("reasoning_content")
                    if delta.get("reasoning_content"):
                        used_reasoning = True
                    if not text:
                        continue

                    now = time.monotonic()
                    if first_token_time is None:
                        first_token_time = now
                    last_token_time = now
                    token_count += 1

            if non_stream_error:
                continue

            if token_count == 0 or first_token_time is None:
                print(f"  [warn] {model_id}: no content tokens received")
                return None, None, False

            ttftm = first_token_time - request_start

            if token_count > 1 and last_token_time is not None:
                decode_elapsed = last_token_time - first_token_time
                tps = (token_count - 1) / decode_elapsed
            else:
                tps = None

            return ttftm, tps, used_reasoning

        except httpx.RequestError as e:
            print(
                f"  [warn] {model_id}: request error ({e}), "
                f"attempt {attempt}/{MAX_RETRIES}"
            )
            if attempt < MAX_RETRIES:
                time.sleep(retry_delay(attempt))

    return None, None, False


def main() -> None:
    model_ids = read_model_ids()
    print(f"Benchmarking {len(model_ids)} models...")

    results: dict[str, tuple[float | None, float | None, bool]] = {}
    with (
        httpx.Client() as client,
        concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool,
    ):
        future_to_id = {
            pool.submit(benchmark_model, model_id, client): model_id
            for model_id in model_ids
        }
        for future in concurrent.futures.as_completed(future_to_id):
            model_id = future_to_id[future]
            results[model_id] = future.result()

    rows = []
    for model_id in model_ids:
        ttftm, tps, used_reasoning = results[model_id]
        tag = " (reasoning)" if used_reasoning else ""
        if ttftm is None or tps is None:
            print(f"  {model_id}: FAILED, writing -")
            rows.append((model_id, "", "-", "-"))
        else:
            print(f"  {model_id}{tag}: TTFT={ttftm:.2f}s, decode={tps:.0f} tps")
            rows.append((model_id, "", f"{ttftm:.0f}", f"{tps:.0f}"))

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Model", "Intelligence", "Latency", "TPS"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
