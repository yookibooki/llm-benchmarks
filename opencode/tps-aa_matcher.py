import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.matcher import match_provider


def normalize_slug(slug: str) -> str:
    s = slug
    s = s.removesuffix(":free").removesuffix("-free").removesuffix("-it").removesuffix("-instruct")
    s = s.replace(".", "-")
    return s


MANUAL_OVERRIDES: dict[str, str] = {
    "big-pickle": "glm-4-7",
    "deepseek-v4-flash-free": "deepseek-v4-flash",
    "hy3-free": "hy3",
    "mimo-v2.5-free": "mimo-v2-5-pro",
    "nemotron-3-ultra-free": "nvidia-nemotron-3-ultra-550b-a55b",
    "north-mini-code-free": "north-mini-code",
}


MANUAL_INTELLIGENCE: dict[str, int] = {
    "laguna-s-2.1-free": 40,
}


if __name__ == "__main__":
    match_provider(
        "opencode/data/tps.csv",
        normalize=normalize_slug,
        overrides=MANUAL_OVERRIDES,
        manual_intel=MANUAL_INTELLIGENCE,
    )
