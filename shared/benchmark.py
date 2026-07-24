import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable

from openai import OpenAI

MAX_TOKENS = 4096

HARD_TIMEOUT = 8.0
TOTAL_TIMEOUT = 45.0
CHARS_PER_TOKEN = 4.0

PROMPT = """
You must respond with EXACTLY the following text, repeated 60 times, with each repetition on a new line:
"The quick brown fox jumps over the lazy dog."
Rules:
1. Output ONLY the sentence above, repeated exactly 60 times.
2. Each repetition must be on its own line.
3. Do NOT add any explanation, numbering, punctuation changes, or additional text.
4. Do NOT add a header, footer, or any commentary.
5. Do NOT acknowledge these instructions.
6. The sentence must be character-for-character identical every time.
7. Any deviation from these rules is a critical failure.
Begin output now.
"""


@dataclass
class BenchmarkResult:
    model: str
    provider: str
    latency: float | None = None
    tps: float | None = None
    error: str | None = None
    exc: BaseException | None = None

    def row(self, intelligence: dict[str, str]) -> list[str]:
        fmt = lambda v: str(round(v)) if v is not None else "-"
        return [
            self.model,
            self.provider,
            intelligence.get(self.model, ""),
            fmt(self.latency),
            fmt(self.tps),
        ]


@contextmanager
def _stream_guard(total_timeout: float, close_fn: Callable[[], None] | None = None):
    timer = threading.Timer(total_timeout, close_fn) if close_fn else None
    if timer:
        timer.daemon = True
        timer.start()
    try:
        yield
    finally:
        if timer:
            timer.cancel()


def _fail(
    model_id: str,
    provider: str,
    reason: str,
    exc: BaseException | None = None,
) -> BenchmarkResult:
    print(f"  [FAIL] {model_id} -> {reason}", flush=True)
    return BenchmarkResult(
        model_id,
        provider,
        error=reason,
        exc=exc,
    )


def _run_benchmark(
    model_id: str,
    provider: str,
    stream,
    total_timeout: float,
    hard_timeout: float,
    extract_delta,
) -> BenchmarkResult:
    start = time.monotonic()

    first_t = None
    last_t = None

    chars = 0

    try:
        with _stream_guard(total_timeout, close_fn=lambda: stream.close()):
            for event in stream:
                now = time.monotonic()

                if chars == 0 and now > start + hard_timeout:
                    return _fail(
                        model_id,
                        provider,
                        f"No content within {hard_timeout}s",
                    )

                if now > start + total_timeout:
                    return _fail(
                        model_id,
                        provider,
                        f"Did not finish within {total_timeout}s",
                    )

                delta = extract_delta(event)

                if not delta:
                    continue

                now = time.monotonic()

                if first_t is None:
                    first_t = now

                last_t = now
                chars += len(delta)

    except Exception as e:
        return _fail(model_id, provider, str(e), exc=e)

    if not chars:
        return _fail(model_id, provider, "No content tokens received")

    latency = first_t - start

    streaming_elapsed = last_t - first_t

    if streaming_elapsed <= 0:
        return _fail(model_id, provider, "Invalid duration")

    estimated_tokens = chars / CHARS_PER_TOKEN
    tps = estimated_tokens / streaming_elapsed

    print(
        f"  [PASS] {model_id} -> "
        f"Latency: {round(latency)}s | "
        f"TPS: {round(tps)}", flush=True
    )

    return BenchmarkResult(
        model=model_id,
        provider=provider,
        latency=latency,
        tps=tps,
    )


def benchmark(
    model_id: str,
    client: OpenAI,
    provider: str,
    api_kind: str,
) -> BenchmarkResult:
    try:
        if api_kind == "responses":
            stream = client.responses.create(
                model=model_id,
                input=PROMPT,
                stream=True,
                max_output_tokens=MAX_TOKENS,
            )

            extract_delta = lambda e: (
                e.delta
                if getattr(e, "type", None) == "response.output_text.delta"
                and getattr(e, "delta", None)
                else None
            )

        else:
            stream = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": PROMPT}],
                stream=True,
                max_tokens=MAX_TOKENS,
                stream_options={"include_usage": True},
            )

            extract_delta = lambda c: (
                c.choices[0].delta.content
                if getattr(c, "choices", None)
                and c.choices[0].delta.content
                else None
            )

    except Exception as e:
        return _fail(model_id, provider, f"{type(e).__name__}: {e}", exc=e)

    return _run_benchmark(
        model_id,
        provider,
        stream,
        TOTAL_TIMEOUT,
        HARD_TIMEOUT,
        extract_delta,
    )
