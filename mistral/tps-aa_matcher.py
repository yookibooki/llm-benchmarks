import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import re

from shared.matcher import match_provider


def normalize_slug(slug: str) -> str:
    s = slug
    s = s.replace(".", "-")
    s = s.removesuffix("-it").removesuffix("-instruct")
    s = re.sub(r"-\d{4}$", "", s)
    s = s.removesuffix("-latest")
    return s


MANUAL_OVERRIDES: dict[str, str | None] = {
    "devstral-2512": "devstral-2",
    "devstral-latest": "devstral-2",
    "ministral-14b-2512": "ministral-3-14b",
    "ministral-14b-latest": "ministral-3-14b",
    "ministral-3b-2512": "ministral-3-3b",
    "ministral-3b-latest": "ministral-3-3b",
    "ministral-8b-2512": "ministral-3-8b",
    "ministral-8b-latest": "ministral-3-8b",
    "mistral-large-2512": "mistral-large-3",
    "mistral-large-latest": "mistral-large-3",
    "mistral-small-2603": "mistral-small-4",
    "mistral-small-latest": "mistral-small-4",
    "zai-glm-5-2": "glm-5-2",
}

MANUAL_INTELLIGENCE: dict[str, int] = {
    "codestral-2508": 11,
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
        overrides=MANUAL_OVERRIDES,
        manual_intel=MANUAL_INTELLIGENCE,
        models_path="mistral/data/models.txt",
        provider_name="mistral",
    )


if __name__ == "__main__":
    _main()
