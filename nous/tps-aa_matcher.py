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


SLUG_INTELLIGENCE: dict[str, int] = {
    "laguna-s-2.1:free": 33,
    "laguna-xs-2.1:free": 15,
}


def _main():
    match_provider(
        "nous/data/tps.csv",
        normalize=normalize_slug,
        manual_intel=SLUG_INTELLIGENCE,
        models_path="nous/data/models.txt",
        provider_name="nous",
    )


if __name__ == "__main__":
    _main()
