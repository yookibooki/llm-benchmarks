import csv
import sys
import types

import pytest


def _write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Model", "Provider", "Intelligence", "Latency", "TPS"])
        w.writeheader()
        w.writerows(rows)


def _read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def repo(tmp_path):
    d = tmp_path / "prov" / "data"
    d.mkdir(parents=True)
    return d


def test_pending_models_without_csv_returns_catalog(repo):
    from shared.pipeline import _pending_models

    models_path = repo / "models.txt"
    models_path.write_text("m1\nm2\n")
    pending = _pending_models(models_path, repo / "tps.csv")
    assert pending == ["m1", "m2"]


def test_pending_models_requeues_error_and_placeholder_rows(repo):
    from shared.pipeline import _pending_models

    (repo / "models.txt").write_text("ok1\nerr1\nplace1\nabsent1\n")
    _write_csv(repo / "tps.csv", [
        {"Model": "ok1", "Provider": "p", "Intelligence": "1", "Latency": "1.0", "TPS": "10"},
        {"Model": "err1", "Provider": "p", "Intelligence": "2", "Latency": "-", "TPS": "-"},
        {"Model": "place1", "Provider": "p", "Intelligence": "", "Latency": "-", "TPS": "-"},
    ])
    pending = _pending_models(repo / "models.txt", repo / "tps.csv")
    assert pending == ["absent1", "err1", "place1"]


def test_pending_models_ignores_extra_rows_for_measured_models(repo):
    from shared.pipeline import _pending_models

    (repo / "models.txt").write_text("m1\n")
    _write_csv(repo / "tps.csv", [
        {"Model": "m1", "Provider": "p", "Intelligence": "1", "Latency": "1.0", "TPS": "10"},
        {"Model": "m1", "Provider": "p", "Intelligence": "1", "Latency": "-", "TPS": "-"},
    ])
    assert _pending_models(repo / "models.txt", repo / "tps.csv") == []


def test_matcher_collapses_duplicate_model_rows(repo):
    import shared.matcher as m

    tps = repo / "tps.csv"
    _write_csv(tps, [
        {"Model": "m1", "Provider": "p", "Intelligence": "1", "Latency": "1.0", "TPS": "10"},
        {"Model": "m2", "Provider": "p", "Intelligence": "2", "Latency": "0.5", "TPS": "20"},
        {"Model": "m1", "Provider": "p", "Intelligence": "1", "Latency": "2.0", "TPS": "99"},
        {"Model": "m2", "Provider": "p", "Intelligence": "2", "Latency": "-", "TPS": "-"},
    ])
    rows = m.read_rows(str(tps))
    assert [r["Model"] for r in rows] == ["m1", "m2"]
    by_model = {r["Model"]: r for r in rows}
    assert by_model["m1"]["TPS"] == "99"
    assert by_model["m2"]["TPS"] == "20"


def test_provider_benchmark_replaces_row_without_duplicating(tmp_path, monkeypatch):
    import shared.provider as sp
    from shared.benchmark import BenchmarkResult

    d = tmp_path / "p" / "data"
    d.mkdir(parents=True)
    tps = d / "tps.csv"
    models_path = d / "subset.txt"
    models_path.write_text("m1\nm3\n")
    _write_csv(tps, [
        {"Model": "m1", "Provider": "p", "Intelligence": "1", "Latency": "1.0", "TPS": "10"},
        {"Model": "m2", "Provider": "p", "Intelligence": "2", "Latency": "0.5", "TPS": "20"},
        {"Model": "m1", "Provider": "p", "Intelligence": "1", "Latency": "9.0", "TPS": "111"},
    ])

    calls = []

    def fake_retry(model_id, provider, client, max_attempts=3):
        calls.append(model_id)
        return BenchmarkResult(model=model_id, provider="p", latency=0.2, tps=50)

    class FakeOpenAI:
        def __init__(self, **kwargs):
            pass

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = FakeOpenAI
    fake_openai.APIConnectionError = type("APIConnectionError", (Exception,), {})
    fake_openai.RateLimitError = type("RateLimitError", (Exception,), {})
    monkeypatch.setattr(sp, "_benchmark_with_retry", fake_retry)
    monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
    monkeypatch.setitem(sp.PROVIDERS, "p", {
        "base_url": "http://localhost", "api_env_var": "X_KEY",
    })
    monkeypatch.setenv("X_KEY", "k")
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    sp.run_provider_benchmark(provider="p", models_path=str(models_path))

    assert calls == ["m1", "m3"]
    rows = _read_csv(tps)
    assert len(rows) == 3
    by_model = {r["Model"]: r for r in rows}
    assert by_model["m1"]["TPS"] == "50"
    assert by_model["m2"]["TPS"] == "20"
    assert by_model["m3"]["TPS"] == "50"




def test_provider_benchmark_keeps_prior_measurement_on_failure(tmp_path, monkeypatch):
    import shared.provider as sp
    from shared.benchmark import BenchmarkResult

    d = tmp_path / "p" / "data"
    d.mkdir(parents=True)
    tps = d / "tps.csv"
    models_path = d / "subset.txt"
    models_path.write_text("m1\n")
    _write_csv(tps, [
        {"Model": "m1", "Provider": "p", "Intelligence": "1", "Latency": "1.0", "TPS": "10"},
    ])

    def fake_retry(model_id, provider, client, max_attempts=3):
        return BenchmarkResult(model=model_id, provider="p", error="boom")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            pass

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = FakeOpenAI
    fake_openai.APIConnectionError = type("APIConnectionError", (Exception,), {})
    fake_openai.RateLimitError = type("RateLimitError", (Exception,), {})
    monkeypatch.setattr(sp, "_benchmark_with_retry", fake_retry)
    monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
    monkeypatch.setitem(sp.PROVIDERS, "p", {
        "base_url": "http://localhost", "api_env_var": "X_KEY",
    })
    monkeypatch.setenv("X_KEY", "k")
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    sp.run_provider_benchmark(provider="p", models_path=str(models_path))

    rows = _read_csv(tps)
    assert len(rows) == 1
    assert rows[0]["TPS"] == "10"


def test_run_pipeline_renders_leaderboard(tmp_path, monkeypatch, capsys):
    from shared import pipeline

    def fake_render():
        print("render called")

    monkeypatch.setattr(pipeline, "run_filter", lambda p: None)
    monkeypatch.setattr(pipeline, "run_benchmark", lambda p, f: None)
    monkeypatch.setattr(pipeline, "fetch_aa", lambda: None)
    monkeypatch.setattr(pipeline, "run_match", lambda p: None)
    monkeypatch.setattr(pipeline, "render", fake_render)
    pipeline.run_pipeline(full=False)
    out = capsys.readouterr().out
    assert "render called" in out
