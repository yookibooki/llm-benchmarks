import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.matcher import match_provider


def normalize_slug(slug: str) -> str:
    s = slug
    s = s.removesuffix("-free").removesuffix(":free")
    s = s.replace(".", "-")
    s = s.removesuffix("-it").removesuffix("-instruct")
    return s


SLUG_OVERRIDES: dict[str, str] = {
    "mimo-v2.5-free": "mimo-v2-5-0424",
    "muse-spark-1.2-contributor-free": "muse-spark-1-2",
    "nemotron-3-ultra-free": "nvidia-nemotron-3-ultra-550b-a55b",
}

SLUG_INTELLIGENCE: dict[str, int] = {
    "laguna-s-2.1-free": 33,
    "big-pickle": 57,
}


def _main():
    match_provider(
        "opencode/data/tps.csv",
        normalize=normalize_slug,
        manual_intel={**SLUG_OVERRIDES, **SLUG_INTELLIGENCE},
        models_path="opencode/data/models.txt",
        provider_name="opencode",
    )


if __name__ == "__main__":
    _main()
