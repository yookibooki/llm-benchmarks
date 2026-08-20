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
    "nvidia/nemotron-3-nano-30b-a3b:free": "nvidia-nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b:free": "nvidia-nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b:free": "nvidia-nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3.5-lightning:free": "nemotron-3-5-lightning",
    "openai/gpt-oss-20b:free": "gpt-oss-20b",
    "cohere/north-mini-code:free": "north-mini-code",
    "inclusionai/ling-3.0-tiny:free": "ling-3-0-tiny",
}

MANUAL_INTELLIGENCE: dict[str, int] = {
    "dots-studio/dots-3-note-preview:free": 43,
}


if __name__ == "__main__":
    match_provider(
        "openrouter/data/tps.csv",
        normalize=normalize_slug,
        overrides=MANUAL_OVERRIDES,
        manual_intel=MANUAL_INTELLIGENCE,
        models_path="openrouter/data/models.txt",
        provider_name="openrouter",
    )
