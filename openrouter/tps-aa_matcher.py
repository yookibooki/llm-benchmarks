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


SLUG_OVERRIDES: dict[str, str] = {
    "cohere/north-mini-code:free": "north-mini-code",
    "google/gemma-4-26b-a4b-it:free": "gemma-4-26b-a4b",
    "inclusionai/ling-3.0-flash-fin:free": "ling-3-0-flash",
    "liquid/lfm-2.5-2.6b:free": "lfm2-5-2-6b",
    "minimax/minimax-m2.7:free": "minimax-m2-7",
    "minimax/minimax-m3:free": "minimax-m3",
    "nvidia/nemotron-3-super-120b-a12b:free": "nvidia-nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b:free": "nvidia-nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3.5-lightning:free": "nemotron-3-5-lightning",
    "openai/gpt-oss-20b:free": "gpt-oss-20b",
    "thinkingmachines/inkling-small:free": "inkling-small",
    "thinkingmachines/inkling:free": "inkling",
    "z-ai/glm-5.2:free": "glm-5-2",
}

SLUG_INTELLIGENCE: dict[str, int] = {
    "dots-studio/dots-3-note-preview:free": 43,
}


def _main():
    match_provider(
        "openrouter/data/tps.csv",
        normalize=normalize_slug,
        manual_intel={**SLUG_OVERRIDES, **SLUG_INTELLIGENCE},
        models_path="openrouter/data/models.txt",
        provider_name="openrouter",
    )


if __name__ == "__main__":
    _main()
