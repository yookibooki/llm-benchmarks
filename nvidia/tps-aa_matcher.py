import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.matcher import match_provider


def normalize_slug(slug: str) -> str:
    s = slug
    s = s.replace(".", "-")
    s = s.removesuffix("-it").removesuffix("-instruct")
    if s.startswith("nemotron-") or s.startswith("nvidia-nemotron-"):
        if not s.startswith("nvidia-"):
            s = "nvidia-" + s
    s = s.removesuffix("-v1").removesuffix("-v1-5")
    return s


SLUG_OVERRIDES: dict[str, str] = {
    "deepseek-v4-flash-0731": "deepseek-v4-flash",
    "deepseek-v4-pro-0813": "deepseek-v4-pro",
    "muse-glimmer-30b": "muse-glimmer",
    "mistral-nemotron": "mistral-medium-3",
    "nemotron-3-nano-omni-30b-a3b-reasoning": "nemotron-3-nano-omni-30b-a3b",
    "nemotron-3.5-lightning-30b-a3b": "nemotron-3-5-lightning",
}

SLUG_INTELLIGENCE: dict[str, int] = {
    "laguna-xs-2.1": 15,
}


def _main():
    match_provider(
        "nvidia/data/tps.csv",
        normalize=normalize_slug,
        manual_intel={**SLUG_OVERRIDES, **SLUG_INTELLIGENCE},
        models_path="nvidia/data/models.txt",
        provider_name="nvidia",
    )


if __name__ == "__main__":
    _main()
