# llm-benchmarks

LLM provider TPS/latency benchmarks + Artificial Analysis (AA) intelligence scores → `index.html` leaderboard. Runs daily via GitHub Actions (`.github/workflows/daily.yml`).

## Quick start

```bash
uv run openrouter/filter_models.py   # refresh model catalog
uv run openrouter/tps-aa_matcher.py  # merge AA intelligence
uv run gen_html.py                   # rebuild leaderboard
```

## Rules

- **NEVER run `run_benchmark.py` or `shared.benchmark` locally** — CI-only; burns paid API quota. `filter_models.py`, `tps-aa_matcher.py`, `gen_html.py` are safe locally.
- **NEVER edit generated files**: `*/data/models.txt`, `*/data/tps.csv`, `*/data/endpoint_snapshot.json`, root `data/tps.csv`, `index.html`. Edit the generating script instead.
- **No comments/docstrings in code, ever.** Fix the code instead.
- Persist changes via scripts:
  - Exclude models → exclude lists in `filter_models.py`
  - Fix AA slug match → `SLUG_OVERRIDES` in `tps-aa_matcher.py`
  - Set intelligence w/o AA → `SLUG_INTELLIGENCE` in `tps-aa_matcher.py`
  - Latency/TPS → not editable; benchmark re-run only
- Benchmark failures never remove a model; only absence from the API catalog does (pruned by `gen_html.py`).

## Pipeline (daily.yml)

Refresh AA data → filter → benchmark → match → render (`gen_html.main()` called from `run_pipeline()`), then CI commits + deploys. All 6 providers run concurrently (one thread per provider per step, via `ThreadPoolExecutor`) with per-step exception collection in `shared/pipeline.py`: a failed provider step logs a `::warning::` and the pipeline publishes with stale/partial data. Steps run in phase order (filter → benchmark → AA fetch → match → render); step-only CLI modes (`--filter-only`, `--benchmark-only`, `--match-only`) parallelize providers the same way but crash on error. Incremental runs (non-Monday) benchmark only models whose latest CSV row lacks Latency/TPS; Monday runs (`--full`) re-benchmark everything. Benchmarks write incrementally per model; transient errors retried ×3 with backoff.

### Add a provider

1. Copy an existing provider dir (3 scripts).
2. Register in `shared/provider.py` `PROVIDERS` (`base_url`, `api_env_var`, optional `default_headers`).
3. Add secret to repo + `daily.yml` env.

## Provider structure

Each `provider/`: `filter_models.py` (API catalog → exclude → `data/models.txt` + snapshot), `run_benchmark.py` (one-liner → `shared.provider.run_provider_benchmark`), `tps-aa_matcher.py` (→ `shared.matcher.match_provider`), `data/`.

Hash gate: `models.txt` rewritten only when catalog SHA-256 differs from snapshot; missing snapshot = full regen.

## Matching (`shared/matcher.py`)

Priority: `SLUG_INTELLIGENCE` → `SLUG_OVERRIDES` → normalized slug lookup (`:free`/`-free`/`-it`/`-instruct` stripped). Duplicate model rows collapse to the latest measured row; endpoint models missing benchmark data get `-` rows so none are absent.

AA data: CI fetches via `AA_API_KEY` → `data/aa_raw.json`. Manual:
```bash
curl -H "x-api-key: $AA_API_KEY" https://artificialanalysis.ai/api/v2/data/llms/models -o data/aa_raw.json
```

## Benchmark (`shared/benchmark.py`)

Prompt: 60× "The quick brown fox...". Latency = time to first token. TPS = usage tokens (fallback chars/4) ÷ stream seconds. Timeouts: 15s first content, 45s total. Content validated. `openai` client, streaming.

## Quirks

- `:free`: OpenRouter = all $0; Nous = requires `:free` suffix; NVIDIA/Google/Mistral = no filter. OpenCode = `-free` suffix or `EXTRA_KEEP`.
- NVIDIA: 404 skip list (`nvidia/data/404s.txt`); matcher requires an AA creator slug.
- OpenRouter: `HTTP-Referer` header, excludes `SMALL_MODEL_PATTERNS`.
