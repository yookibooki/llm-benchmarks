import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.matcher import match_provider

NAMESPACE_TO_CREATOR: dict[str, str] = {
    "abacusai": "abacus",
    "ai21": "ai21-labs",
    "cohere": "cohere",
    "deepseek-ai": "deepseek",
    "google": "google",
    "meta": "meta",
    "microsoft": "azure",
    "minimaxai": "minimax",
    "mistralai": "mistral",
    "moonshotai": "kimi",
    "nvidia": "nvidia",
    "openai": "openai",
    "qwen": "alibaba",
    "sarvamai": "sarvam",
    "stepfun-ai": "stepfun",
    "thinkingmachines": "thinking-machines",
    "poolside": "poolside",
    "upstage": "upstage",
    "z-ai": "zai",
}


def normalize_slug(slug: str) -> str:
    s = slug
    s = s.replace(".", "-")
    s = s.removesuffix("-it").removesuffix("-instruct")
    if s.startswith("nemotron-") or s.startswith("nvidia-nemotron-"):
        if not s.startswith("nvidia-"):
            s = "nvidia-" + s
    s = s.removesuffix("-v1").removesuffix("-v1-5")
    return s


def expected_creator(model_id: str) -> str | None:
    if "/" not in model_id:
        return None
    namespace = model_id.split("/", 1)[0]
    return NAMESPACE_TO_CREATOR.get(namespace)


MANUAL_OVERRIDES: dict[str, str] = {
    "deepseek-v4-flash-0731": "deepseek-v4-flash",
    "llama-3.1-8b-instruct": "llama-3-1-instruct-8b",
    "llama-3.3-nemotron-super-49b-v1": "llama-3-3-nemotron-super-49b",
    "muse-glimmer-30b": "muse-glimmer",
    "nemotron-3-nano-omni-30b-a3b-reasoning": "nemotron-3-nano-omni-30b-a3b",
    "nemotron-3-super-120b-a12b": "nvidia-nemotron-3-super-120b-a12b",
    "nemotron-3-ultra-550b-a55b": "nvidia-nemotron-3-ultra-550b-a55b",
    "nemotron-3.5-lightning-30b-a3b": "nemotron-3-5-lightning",
    "mistral-nemotron": "mistral-medium-3",
}

MANUAL_INTELLIGENCE: dict[str, int] = {
    "poolside/laguna-xs-2.1": 15,
}


if __name__ == "__main__":
    match_provider(
        "nvidia/data/tps.csv",
        normalize=normalize_slug,
        overrides=MANUAL_OVERRIDES,
        manual_intel=MANUAL_INTELLIGENCE,
        strip_namespace=True,
        expected_creator=expected_creator,
        models_path="nvidia/data/models.txt",
        provider_name="nvidia",
    )
