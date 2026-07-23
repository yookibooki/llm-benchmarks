# llm-benchmarks

Auto leaderboard: https://yookibooki.github.io/llm-benchmarks
Benchmarks LLM providers for TPS + latency, merges Artificial Analysis (AA)
intelligence scores, renders `index.html`. Driven daily by GitHub Actions.

## Quick start

```bash
python3 -m pip install -r requirements.txt
python3 openrouter/filter_models.py   # fetch model list
python3 openrouter/run_benchmark.py   # benchmark all models
python3 openrouter/tps-aa_matcher.py  # merge AA intelligence
python3 gen_html.py                   # rebuild leaderboard
```

## Pipeline (`.github/workflows/daily.yml`)

All 6 providers run in parallel via background `&` processes, guarded with
`|| echo "WARNING: ..."` (one failure doesn't block others).

Step order per provider: **filter → benchmark → match** → then `gen_html.py`
merges every `data/tps.csv` into `data/tps.csv`, renders `index.html`, commits
and deploys to GitHub Pages.

## Provider structure

Each `provider/` has three scripts + `data/`:

- `filter_models.py` — fetches available models from the API, applies
  provider-specific exclusions, writes `data/models.txt`.
- `run_benchmark.py` — one-liner calling `shared.provider.run_provider_benchmark(provider="...")`.
- `tps-aa_matcher.py` — calls `shared.matcher.match_provider(...)` to fill
  the `Intelligence` column from `data/aa_raw.json`.
- `data/` — generated state: `models.txt`, `tps.csv`, `endpoint_snapshot.json`.

### Adding a provider

1. Create `new-provider/` with the three scripts (copy an existing one).
2. Register in `shared/provider.py` (`PROVIDERS` dict: `base_url`, `api_env_var`,
   `api_kind`).
3. Add the secret to repo + `.github/workflows/daily.yml` env block + provider
   name to each `for prov in ...` loop.

## WARNING: data files are generated, not source

**Never edit `data/models.txt`, `data/tps.csv`, or `data/endpoint_snapshot.json`
directly.** They are overwritten every pipeline run:

| File | Overwritten by |
|---|---|
| `models.txt` | `filter_models.py` — fetches API catalog, applies exclude terms, rewrites file |
| `tps.csv` | `run_benchmark.py` (new benchmarks) then `tps-aa_matcher.py` (intelligence merge) |
| `endpoint_snapshot.json` | `filter_models.py` as a side effect of `gate_and_write` |

The hash gate (`shared/filter.py`) skips rewriting `models.txt` only when the
API catalog's SHA-256 hash matches the stored snapshot. If the snapshot file is
**missing or deleted**, the next run treats the catalog as changed and
**regenerates everything**. To persist a change, modify the Python scripts, not
the data files.

Shared `data/tps.csv` and `index.html` are also auto-generated — edit
`gen_html.py` instead.

### How to persist model changes

- **Filter a model out** → add an exclude term to `filter_models.py`'s `EXCLUDE_TERMS`.
- **Add a model** → models must be returned by the API AND pass `name_filter()` —
  adjust the filter logic if needed.
- **Override AA slug matching** → add to `MANUAL_OVERRIDES` in `tps-aa_matcher.py`.
- **Set intelligence manually** (no AA match) → add to `MANUAL_INTELLIGENCE` in
  `tps-aa_matcher.py`.
- **Change latency/TPS** → not possible manually; must re-run the benchmark.

Examples of correct persistence: `7e070b6` added
`poolside/laguna-s-2.1:free` → 40 intelligence via `MANUAL_INTELLIGENCE` in
both `opencode/tps-aa_matcher.py` and `openrouter/tps-aa_matcher.py`, and
`poolside/laguna-xs-2.1` → 15 via `nvidia/tps-aa_matcher.py`.

## `:free` suffix convention by provider

Each provider uses `:free` differently — check the filter logic:

| Provider | `:free` handling |
|---|---|
| **OpenRouter** | API returns only $0 models; `models.txt` entries naturally have `:free` |
| **Nous** | `name_filter` rejects models NOT ending in `:free` |
| **OpenCode** | `name_filter` accepts models ending in `-free` (not `:free`) |
| **NVIDIA** | No `:free` filtering; all returned models included |
| **Google / Mistral** | API-determined; no special `:free` suffix filtering |

The `tps-aa_matcher.py` `normalize_slug` strips `:free`/`-free`/`-it`/`-instruct`
before matching AA slugs.

## Provider quirks

- **NVIDIA** has a 404-validation step (`remove_404_models`) that pings each
  model before including it.
- **NVIDIA** uses `strip_namespace=True` + `expected_creator` for creator
  verification against AA.
- **OpenRouter** passes `HTTP-Referer` header and excludes small model patterns
  (`-1b-`, `-2b-`, etc.) via `SMALL_MODEL_PATTERNS`.

## Intelligence matching (`shared/matcher.py`)

Match priority (top wins):
1. `MANUAL_INTELLIGENCE` — hardcoded score; no AA lookup.
2. `MANUAL_OVERRIDES` — maps model ID to AA slug for lookup.
3. Normalized slug lookup in AA index.

AA data is fetched separately and stored in `data/aa_raw.json`:
```bash
curl -H "x-api-key: $AA_API_KEY" \
  https://artificialanalysis.ai/api/v2/data/llms/models -o data/aa_raw.json
```

## Benchmark details (`shared/benchmark.py`)

- Prompt: 60× repeated "The quick brown fox..." (character consistency test).
- **Latency** = seconds to first token.
- **TPS** = estimated tokens / streaming duration (chars / 4 ÷ seconds).
- Timeouts: hard 8s (first token), total 45s (SIGALRM).
- Uses `openai` Python client with streaming.
- `api_kind` controls `chat.completions` vs `responses` API.

## Conventions

- API keys from env vars / repo secrets only (no `.env` files per provider).
- Provider scripts insert repo root in `sys.path` before importing `shared.*`.
- `shared/` must stay provider-agnostic; provider-specific logic (excludes,
  normalization, overrides) lives in each provider's scripts.

## Adding to the CI provider list

The 6-provider loop appears in 3 places in `daily.yml` (filter, benchmark,
match). All 3 must be updated.
