import csv
from pathlib import Path

import pytest


@pytest.fixture
def repo(tmp_path, monkeypatch):
    import shared.csv_utils as cu

    monkeypatch.setattr(cu, "REPO_ROOT", tmp_path)
    for prov in ("alpha", "beta"):
        d = tmp_path / prov / "data"
        d.mkdir(parents=True)
    return tmp_path


def _write_providers(root, alpha_rows, beta_rows):
    for prov, rows in (("alpha", alpha_rows), ("beta", beta_rows)):
        p = root / prov / "data" / "tps.csv"
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["Model", "Provider", "Intelligence", "Latency", "TPS"])
            w.writeheader()
            w.writerows(rows)


def test_merge_combines_all_providers(repo):
    from shared.csv_utils import merge_provider_csvs, read_benchmark_csv

    _write_providers(
        repo,
        alpha_rows=[
            {"Model": "a1", "Provider": "alpha", "Intelligence": "10", "Latency": "1.0", "TPS": "50"},
        ],
        beta_rows=[
            {"Model": "b1", "Provider": "beta", "Intelligence": "20", "Latency": "2.0", "TPS": "60"},
        ],
    )
    out = repo / "data" / "merged.csv"
    merge_provider_csvs([repo / "alpha", repo / "beta"], out)
    rows = read_benchmark_csv(out)
    assert {r["Model"] for r in rows} == {"a1", "b1"}
    assert len(rows) == 2


def test_merge_skips_missing_provider(repo):
    from shared.csv_utils import merge_provider_csvs, read_benchmark_csv

    _write_providers(
        repo,
        alpha_rows=[
            {"Model": "a1", "Provider": "alpha", "Intelligence": "10", "Latency": "1.0", "TPS": "50"},
        ],
        beta_rows=[],
    )
    out = repo / "data" / "merged.csv"
    merge_provider_csvs([repo / "alpha", repo / "beta"], out)
    rows = read_benchmark_csv(out)
    assert [r["Model"] for r in rows] == ["a1"]


def test_write_benchmark_csv_preserves_intelligence(repo):
    from shared.benchmark import BenchmarkResult
    from shared.csv_utils import write_benchmark_csv, read_benchmark_csv

    results = [BenchmarkResult(model="m1", provider="alpha", latency=1.0, tps=40.0)]
    intel = {"m1": "77"}
    out = repo / "alpha" / "data" / "tps.csv"
    write_benchmark_csv(out, results, intel)
    rows = read_benchmark_csv(out)
    assert rows[0]["Intelligence"] == "77"
    assert rows[0]["TPS"] == "40"


def test_has_measurements_requires_latency_and_tps():
    from shared.csv_utils import has_measurements

    assert has_measurements({"Latency": "1.0", "TPS": "50"}) is True
    assert has_measurements({"Latency": "-", "TPS": "50"}) is False
    assert has_measurements({"Latency": "1.0", "TPS": "-"}) is False
    assert has_measurements({"Latency": "", "TPS": ""}) is False
    assert has_measurements({}) is False


def test_read_benchmark_csv_missing_returns_empty(repo):
    from shared.csv_utils import read_benchmark_csv

    assert read_benchmark_csv(repo / "nope" / "data" / "tps.csv") == []
