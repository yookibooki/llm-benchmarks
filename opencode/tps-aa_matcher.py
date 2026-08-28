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


MANUAL_OVERRIDES: dict[str, str] = {}

MANUAL_INTELLIGENCE: dict[str, int] = {}


def _main():
    match_provider(
        "opencode/data/tps.csv",
        normalize=normalize_slug,
        overrides=MANUAL_OVERRIDES,
        manual_intel=MANUAL_INTELLIGENCE,
        models_path="opencode/data/models.txt",
        provider_name="opencode",
    )


if __name__ == "__main__":
    _main()
