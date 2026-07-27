import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.matcher import match_provider

def normalize_slug(slug: str) -> str:
    s = slug
    s = (
        s.removesuffix(":free")
        .removesuffix("-free")
        .removesuffix("-it")
        .removesuffix("-instruct")
    )
    s = s.replace(".", "-")
    return s

MANUAL_OVERRIDES: dict[str, str] = {
    "stepfun/step-3.7-flash:free": "step-3-7-flash",
    "tencent/hy3:free": "hy3",
}
MANUAL_INTELLIGENCE: dict[str, int] = {
    "inclusionai/ling-3.0-flash:free": 35,
    "poolside/laguna-s-2.1:free": 35,
    "poolside/laguna-m.1:free": 22,
    "poolside/laguna-xs-2.1:free": 15,
}

if __name__ == "__main__":
    match_provider(
        "nous/data/tps.csv",
        normalize=normalize_slug,
        overrides=MANUAL_OVERRIDES,
        manual_intel=MANUAL_INTELLIGENCE,
    )
