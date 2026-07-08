"""Merge AA intelligence into data/tps.csv."""

import csv
import json
import math

TPS_PATH = "data/tps.csv"
AA_PATH = "data/aa_raw.json"


def load_aa_index(path: str) -> dict[str, dict]:
    """Build {slug: {intelligence, creator}} from AA data."""
    with open(path) as f:
        data = json.load(f)["data"]
    index: dict[str, dict] = {}
    for m in data:
        slug = m["slug"]
        intelligence = m.get("evaluations", {}).get("artificial_analysis_intelligence_index")
        creator = (m.get("model_creator") or {}).get("slug")
        if intelligence is None or not creator:
            continue
        # Keep highest intelligence if duplicate slugs exist
        prev = index.get(slug)
        if prev is None or intelligence > prev["intelligence"]:
            index[slug] = {"intelligence": intelligence, "creator": creator}
    return index


def normalize_slug(slug: str) -> str:
    """Normalize a NIM slug to match AA naming conventions."""
    s = slug
    # Dot → dash in version numbers (e.g. qwen3.5 → qwen3-5, minimax-m2.7 → minimax-m2-7)
    s = s.replace(".", "-")
    # Strip trailing -it and -instruct suffixes (NIM adds these, AA often omits)
    s = s.removesuffix("-it").removesuffix("-instruct")
    # Add nvidia- prefix for nvidia-only models not already prefixed
    if s.startswith("nemotron-") or s.startswith("nvidia-nemotron-"):
        if not s.startswith("nvidia-"):
            s = "nvidia-" + s
    # Strip version suffixes like -v1, -v1.5 (NIM uses these, AA often drops them)
    # e.g. nvidia-nemotron-nano-9b-v2-v1 → nvidia-nemotron-nano-9b-v2
    s = s.removesuffix("-v1").removesuffix("-v1-5")
    return s


# Manual overrides for slugs that can't be normalized automatically.
# A manual override intentionally bypasses the namespace/creator check below:
# e.g. NIM ships "meta/llama-3.1-nemotron-nano-8b-v1" but AA's matching model
# is owned by nvidia. Override entries signal "trust me, this is right".
MANUAL_OVERRIDES: dict[str, str] = {
    # llama instruct: AA puts size before instruct
    "llama-3.1-70b-instruct": "llama-3-1-instruct-70b",
    "llama-3.1-8b-instruct": "llama-3-1-instruct-8b",
    "llama-3.3-70b-instruct": "llama-3-3-instruct-70b",
    "llama-3.2-3b-instruct": "llama-3-2-instruct-3b",
    "llama-3.2-1b-instruct": "llama-3-2-instruct-1b",
    # llama-4-maverick: AA has no size info
    "llama-4-maverick-17b-128e-instruct": "llama-4-maverick",
    # nemotron: add nvidia- prefix, some not in AA
    "llama-3.1-nemotron-nano-8b-v1": "llama-3-1-nemotron-nano-4b-reasoning",
    "llama-3.1-nemotron-nano-vl-8b-v1": "llama-3-1-nemotron-nano-4b-reasoning",
    "llama-3.3-nemotron-super-49b-v1": "llama-3-3-nemotron-super-49b",
    "llama-3.3-nemotron-super-49b-v1.5": "llama-3-3-nemotron-super-49b",
    "nemotron-3-nano-30b-a3b": "nvidia-nemotron-3-nano-30b-a3b",
    "nemotron-3-nano-omni-30b-a3b-reasoning": "nemotron-3-nano-omni-30b-a3b",
    "nemotron-3-super-120b-a12b": "nvidia-nemotron-3-super-120b-a12b",
    "nemotron-3-ultra-550b-a55b": "nvidia-nemotron-3-ultra-550b-a55b",
    "nemotron-mini-4b-instruct": "nvidia-nemotron-nano-9b-v2",
    "nemotron-nano-12b-v2-vl": "nvidia-nemotron-nano-12b-v2-vl",
    "nvidia-nemotron-nano-9b-v2-v1": "nvidia-nemotron-nano-9b-v2",
    # mistral: strip date/size suffixes
    "ministral-14b-instruct-2512": "ministral-3-14b",
    "mistral-large-3-675b-instruct-2512": "mistral-large-3",
    "mistral-medium-3.5-128b": "mistral-medium-3-5",
    "mistral-nemotron": "mistral-medium-3",
    "mistral-small-4-119b-2603": "mistral-small-4",
    # mixtral: AA uses base name
    "mixtral-8x7b-instruct-v0.1": "mixtral-8x7b-instruct",
    # sarvam: AA uses reasoning variant
    "sarvam-m": "sarvam-m-reasoning",
}


# Map NIM namespace (the bit before "/") to expected AA creator slug.
# NIM namespaces models by the org that published to NIM, which is usually
# but not always the model's actual creator. Used only for soft validation.
NAMESPACE_TO_CREATOR: dict[str, str] = {
    "01-ai": "ai2",
    "abacusai": "abacus",
    "ai21": "ai21-labs",
    "baichuan": "baidu",
    "cohere": "cohere",
    "deepseek-ai": "deepseek",
    "google": "google",
    "meta": "meta",
    "microsoft": "openai",  # phi family listed under openai in AA
    "minimaxai": "minimax",
    "mistralai": "mistral",
    "moonshotai": "kimi",
    "nvidia": "nvidia",
    "openai": "openai",
    "qwen": "alibaba",
    "sarvamai": "sarvam",
    "stepfun-ai": "stepfun",
    "stockmark": "motif-technologies",
    "upstage": "upstage",
    "z-ai": "zai",
}


def expected_creator(model_id: str) -> str | None:
    """Best-guess AA creator slug for a NIM model id, or None if unknown."""
    if "/" not in model_id:
        return None
    namespace = model_id.split("/", 1)[0]
    return NAMESPACE_TO_CREATOR.get(namespace)


def main():
    aa_index = load_aa_index(AA_PATH)
    print(f"Loaded {len(aa_index)} AA models with intelligence + creator")

    with open(TPS_PATH) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("No rows in tps.csv; nothing to do.")
        return
    fieldnames = list(rows[0].keys())

    matched = 0
    warned = 0
    unmatched = 0
    for row in rows:
        model = row["Model"]
        slug = model.split("/", 1)[1] if "/" in model else model

        override = MANUAL_OVERRIDES.get(slug)
        if override:
            entry = aa_index.get(override)
            if entry is None:
                print(f"  [warn] {model}: override '{override}' not in AA")
                warned += 1
                continue
            row["Intelligence"] = str(math.ceil(entry['intelligence']))
            matched += 1
            continue

        entry = aa_index.get(slug)
        matched_slug = slug
        if entry is None:
            norm = normalize_slug(slug)
            entry = aa_index.get(norm)
            if entry is not None:
                matched_slug = norm

        if entry is None:
            print(f"  [warn] {model}: no AA match")
            unmatched += 1
            continue

        expected = expected_creator(model)
        if expected and entry["creator"] != expected:
            print(f"  [warn] {model}: creator mismatch ({expected} vs {entry['creator']})")
            warned += 1

        row["Intelligence"] = str(math.ceil(entry['intelligence']))
        matched += 1

    with open(TPS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Updated {matched}/{len(rows)} models in {TPS_PATH} "
        f"(warned={warned}, unmatched={unmatched})"
    )


if __name__ == "__main__":
    main()
