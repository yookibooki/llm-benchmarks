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
    "meituan/longcat-2.0:free": "longcat-2-0",
    "upstage/solar-pro4:free": "solar-pro4",
}
MANUAL_INTELLIGENCE: dict[str, int] = {
    "poolside/laguna-s-2.1:free": 33,
    "poolside/laguna-xs-2.1:free": 15,
}

def _main():
    match_provider(
        "nous/data/tps.csv",
        normalize=normalize_slug,
        overrides=MANUAL_OVERRIDES,
        manual_intel=MANUAL_INTELLIGENCE,
        models_path="nous/data/models.txt",
        provider_name="nous",
    )


if __name__ == "__main__":
    _main()
