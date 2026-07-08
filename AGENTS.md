# nvidia-nim-benchmarks
Auto leaderboard: https://yookibooki.github.io/nvidia-nim-benchmarks
Benchmarks NIM chat models for TPS, renders static leaderboard. Runs via GH Actions.
> This project uses `uv` as package manager.

## Tree
```
AGENTS.md, filter_models.py, run_benchmark.py, tps-aa_matcher.py, index.html, pyproject.toml, uv.lock, LICENSE, .gitignore, .env
data/{endpoint_snapshot.json, models.txt, tps.csv, aa_raw.json}
.github/workflows/daily.yml
```

## Pipeline (daily.yml)
1. Cron trigger (daily at 17:00 UTC) or manual dispatch.
2. Diff `data/endpoint_snapshot.json` hash vs live `integrate.api.nvidia.com/v1/models`.
3. Match → `run_benchmark.py` (existing `models.txt`).
4. Diff → `filter_models.py` → new `models.txt` → `run_benchmark.py`.
5. `run_benchmark.py` → `data/tps.csv`.
6. Commit changed files; push triggers Pages rebuild.

## Intelligence index
Manually maintained in `data/tps.csv` under the `intelligence` column.
Edit `tps.csv` directly to add/update intelligence for models.

## Fetch AA data
```bash
curl -H "x-api-key: $AA_API_KEY" https://artificialanalysis.ai/api/v2/data/llms/models -o data/aa_raw.json
```

## Match AA intelligence
```bash
python tps-aa_matcher.py
```
