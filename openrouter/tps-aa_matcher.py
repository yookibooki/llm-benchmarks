import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.matcher import match_provider


def normalize_slug(slug: str) -> str:
    s = slug
    s = s.removesuffix(":free")
    s = s.replace(".", "-")
    s = s.removesuffix("-it").removesuffix("-instruct")
    return s


MANUAL_OVERRIDES: dict[str, str | None] = {
    "google/gemma-4-26b-a4b-it:free": "gemma-4-26b-a4b",
    "google/gemma-4-31b-it:free": "gemma-4-31b",
    "meta-llama/llama-3.2-3b-instruct:free": "llama-3-2-instruct-3b",
    "meta-llama/llama-3.3-70b-instruct:free": "llama-3-3-instruct-70b",
    "nousresearch/hermes-3-llama-3.1-405b:free": "hermes-4-llama-3-1-405b-reasoning",
    "nvidia/nemotron-3-nano-30b-a3b:free": "nvidia-nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": "nemotron-3-nano-omni-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b:free": "nvidia-nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b:free": "nvidia-nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-nano-12b-v2-vl:free": "nvidia-nemotron-nano-12b-v2-vl-reasoning",
    "nvidia/nemotron-nano-9b-v2:free": "nvidia-nemotron-nano-9b-v2-reasoning",
    "openai/gpt-oss-120b:free": "gpt-oss-120b",
    "openai/gpt-oss-20b:free": "gpt-oss-20b",
    "qwen/qwen3-coder:free": "qwen3-coder-next",
    "qwen/qwen3-next-80b-a3b-instruct:free": "qwen3-next-80b-a3b-instruct",
    "tencent/hy3:free": "hy3",
    "cohere/north-mini-code:free": "north-mini-code",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free": "mistral-small-2402",
}

MANUAL_INTELLIGENCE: dict[str, int] = {
    "poolside/laguna-xs-2.1:free": 15,
    "poolside/laguna-m.1:free": 22,
    "poolside/laguna-s-2.1:free": 40,
}


if __name__ == "__main__":
    match_provider(
        "openrouter/data/tps.csv",
        normalize=normalize_slug,
        overrides=MANUAL_OVERRIDES,
        manual_intel=MANUAL_INTELLIGENCE,
    )
