import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.matcher import match_provider


def normalize_slug(slug: str) -> str:
    s = slug
    s = s.removesuffix("-latest")
    s = s.removesuffix("-free").removesuffix(":free")
    s = s.replace(".", "-")
    s = s.removesuffix("-it").removesuffix("-instruct")
    return s


SLUG_OVERRIDES: dict[str, str] = {
    "devstral-latest": "devstral-2",
    "ministral-14b-latest": "ministral-3-14b",
    "ministral-3b-latest": "ministral-3-3b",
    "ministral-8b-latest": "ministral-3-8b",
}

SLUG_INTELLIGENCE: dict[str, int] = {
    "codestral-latest": 11,
    "mistral-code-agent-latest": 19,
    "mistral-code-latest": 15,
    "mistral-vibe-cli-fast": 13,
    "mistral-vibe-cli-with-tools": 19,
    "mistral-vibe-cli-latest": 21,
}


def _main():
    match_provider(
        "mistral/data/tps.csv",
        normalize=normalize_slug,
        manual_intel={**SLUG_OVERRIDES, **SLUG_INTELLIGENCE},
        models_path="mistral/data/models.txt",
        provider_name="mistral",
    )


if __name__ == "__main__":
    _main()
