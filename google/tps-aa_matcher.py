import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.matcher import match_provider


def normalize_slug(slug: str) -> str:
    s = slug.lower()
    s = s.removesuffix("-it")
    s = s.replace(".", "-")
    if s.startswith("gemini-") and "-preview" not in s and "-pro-" not in s:
        s = s + "-preview"
    return s


SLUG_OVERRIDES: dict[str, str] = {
    "gemini-3.5-flash-lite": "gemini-3-5-flash-lite",
}


def _main():
    match_provider(
        "google/data/tps.csv",
        normalize=normalize_slug,
        manual_intel=SLUG_OVERRIDES,
        models_path="google/data/models.txt",
        provider_name="google",
    )


if __name__ == "__main__":
    _main()
