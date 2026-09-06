from __future__ import annotations

import signal
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

MAX_TOKENS = 4096

HARD_TIMEOUT = 15.0
TOTAL_TIMEOUT = 45.0
CHARS_PER_TOKEN = 4.0

EXPECTED_TEXT = "The quick brown fox jumps over the lazy dog."


def _validate_content(text: str) -> bool:
    return "quick brown fox" in text.lower()

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
    token_source: str | None = None

    def row(self, intelligence: dict[str, str]) -> list[str]:
        fmt_tps = lambda v: str(round(v)) if v is not None else "-"
        fmt_lat = lambda v: (
            "-" if v is None
            else (f"{v:.1f}" if v < 10 else str(round(v)))
        )
        return [
            self.model,
            self.provider,
            intelligence.get(self.model, ""),
            fmt_lat(self.latency),
            fmt_tps(self.tps),
        ]

    @classmethod
    def from_row(cls, row: dict) -> "BenchmarkResult":
        def _num(v):
            if v in ("", "-", None):
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        return cls(
            model=row.get("Model", ""),
            provider=row.get("Provider", ""),
            latency=_num(row.get("Latency")),
            tps=_num(row.get("TPS")),
        )


class _BenchmarkTimeout(Exception):
    pass


@contextmanager
def _total_timeout_guard(total_timeout: float):
    if threading.current_thread() is threading.main_thread() and hasattr(signal, "SIGALRM"):
        old_handler = signal.getsignal(signal.SIGALRM)

        def _handler(signum, frame):
            raise _BenchmarkTimeout(f"Benchmark exceeded {total_timeout}s total timeout")

        signal.signal(signal.SIGALRM, _handler)
        signal.setitimer(signal.ITIMER_REAL, total_timeout)
        try:
            yield
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        yield


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


def _close_stream(stream) -> None:
    try:
        close = getattr(stream, "close", None)
        if callable(close):
            close()
    except Exception:
        pass


def _run_benchmark(
    model_id: str,
    provider: str,
    stream,
    total_timeout: float,
    hard_timeout: float,
    extract_delta,
    extract_usage,
) -> BenchmarkResult:
    start = time.monotonic()

    first_t = None
    last_t = None

    chars = 0
    full_text: list[str] = []
    expired = {"fired": False}

    def _expire() -> None:
        expired["fired"] = True
        _close_stream(stream)

    timer = threading.Timer(total_timeout, _expire)
    timer.daemon = True
    timer.start()

    try:
        with _total_timeout_guard(total_timeout):
            for event in stream:
                now = time.monotonic()

                if chars == 0 and now > start + hard_timeout:
                    return _fail(
                        model_id,
                        provider,
                        f"No content within {hard_timeout}s",
                    )

                if now > start + total_timeout or expired["fired"]:
                    return _fail(
                        model_id,
                        provider,
                        f"Did not finish within {total_timeout}s",
                    )

                delta = extract_delta(event)

                if not delta:
                    continue

                full_text.append(delta)

                now = time.monotonic()

                if first_t is None:
                    first_t = now

                last_t = now
                chars += len(delta)

    except _BenchmarkTimeout as e:
        return _fail(model_id, provider, str(e), exc=e)
    except Exception as e:
        return _fail(model_id, provider, str(e), exc=e)
    finally:
        timer.cancel()

    if expired["fired"]:
        return _fail(model_id, provider, f"Did not finish within {total_timeout}s")

    if not chars:
        return _fail(model_id, provider, "No content tokens received")

    response_text = "".join(full_text)
    if not _validate_content(response_text):
        return _fail(
            model_id,
            provider,
            "Response did not contain expected benchmark text",
        )

    latency = first_t - start

    streaming_elapsed = last_t - first_t

    if streaming_elapsed <= 0:
        return _fail(model_id, provider, "Invalid duration")

    usage_tokens = extract_usage()
    token_source = "usage"
    if usage_tokens is None or usage_tokens <= 0:
        usage_tokens = chars / CHARS_PER_TOKEN
        token_source = "chars/4"
    tps = usage_tokens / streaming_elapsed

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
        token_source=token_source,
    )


def benchmark(
    model_id: str,
    client: OpenAI,
    provider: str,
) -> BenchmarkResult:
    try:
        stream = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": PROMPT}],
            stream=True,
            max_tokens=MAX_TOKENS,
            stream_options={"include_usage": True},
        )

        state = {"usage": None}

        def extract_delta(c):
            state["usage"] = getattr(c, "usage", None)
            choices = getattr(c, "choices", None)
            if choices and getattr(choices[0].delta, "content", None):
                return choices[0].delta.content
            return None

        def extract_usage():
            u = state["usage"]
            return getattr(u, "completion_tokens", None) if u else None

    except Exception as e:
        return _fail(model_id, provider, f"{type(e).__name__}: {e}", exc=e)

    return _run_benchmark(
        model_id,
        provider,
        stream,
        TOTAL_TIMEOUT,
        HARD_TIMEOUT,
        extract_delta,
        extract_usage,
    )
