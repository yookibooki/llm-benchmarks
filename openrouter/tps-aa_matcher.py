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
    "nvidia/nemotron-3-nano-30b-a3b:free": "nvidia-nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": "nemotron-3-nano-omni-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b:free": "nvidia-nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b:free": "nvidia-nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-nano-12b-v2-vl:free": "nvidia-nemotron-nano-12b-v2-vl-reasoning",
    "nvidia/nemotron-nano-9b-v2:free": "nvidia-nemotron-nano-9b-v2-reasoning",
    "openai/gpt-oss-20b:free": "gpt-oss-20b",
    "cohere/north-mini-code:free": "north-mini-code",
}

MANUAL_INTELLIGENCE: dict[str, int] = {
    "inclusionai/ling-3.0-flash:free": 26,
    "poolside/laguna-xs-2.1:free": 15,
    "poolside/laguna-m.1:free": 22,
    "poolside/laguna-s-2.1:free": 33,
}


if __name__ == "__main__":
    match_provider(
        "openrouter/data/tps.csv",
        normalize=normalize_slug,
        overrides=MANUAL_OVERRIDES,
        manual_intel=MANUAL_INTELLIGENCE,
    )
