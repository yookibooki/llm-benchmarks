import json

import pytest


@pytest.fixture
def repo(tmp_path, monkeypatch):
    import shared.matcher as m

    monkeypatch.setattr(m, "REPO_ROOT", tmp_path)
    (tmp_path / "data").mkdir(parents=True)
    return tmp_path


def _aa_index_file(repo, entries):
    data = {
        "data": [
            {
                "slug": slug,
                "evaluations": {"artificial_analysis_intelligence_index": intel},
                "model_creator": {"slug": creator},
            }
            for slug, intel, creator in entries
        ]
    }
    p = repo / "data" / "aa_raw.json"
    p.write_text(json.dumps(data))
    return str(p)


def _write_tps(repo, rows, prov="p"):
    import csv

    p = repo / "data" / "tps.csv"
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Model", "Provider", "Intelligence", "Latency", "TPS"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return str(p)


def _read_intel(repo):
    import csv

    with open(repo / "data" / "tps.csv") as f:
        return {r["Model"]: r["Intelligence"] for r in csv.DictReader(f)}


def test_manual_intelligence_wins(repo):
    import shared.matcher as m

    aa = _aa_index_file(repo, [("some-slug", 50, "c")])
    tps = _write_tps(repo, [{"Model": "m1", "Provider": "p", "Intelligence": "", "Latency": "-", "TPS": "-"}])
    m.match_provider(tps, normalize=lambda s: s, manual_intel={"m1": 42}, aa_path=aa)
    assert _read_intel(repo)["m1"] == "42"


def test_override_used_when_set(repo):
    import shared.matcher as m

    aa = _aa_index_file(repo, [("target-slug", 33, "c")])
    tps = _write_tps(repo, [{"Model": "m1", "Provider": "p", "Intelligence": "", "Latency": "-", "TPS": "-"}])
    m.match_provider(tps, normalize=lambda s: s, overrides={"m1": "target-slug"}, aa_path=aa)
    assert _read_intel(repo)["m1"] == "33"


def test_direct_slug_match(repo):
    import shared.matcher as m

    aa = _aa_index_file(repo, [("myslug", 21, "c")])
    tps = _write_tps(repo, [{"Model": "myslug", "Provider": "p", "Intelligence": "", "Latency": "-", "TPS": "-"}])
    m.match_provider(tps, normalize=lambda s: s, aa_path=aa)
    assert _read_intel(repo)["myslug"] == "21"


def test_normalized_slug_match(repo):
    import shared.matcher as m

    aa = _aa_index_file(repo, [("my-model", 15, "c")])
    tps = _write_tps(repo, [{"Model": "my.model:free", "Provider": "p", "Intelligence": "", "Latency": "-", "TPS": "-"}])

    def normalize(s):
        return s.removesuffix(":free").replace(".", "-")

    m.match_provider(tps, normalize=normalize, aa_path=aa)
    assert _read_intel(repo)["my.model:free"] == "15"


def test_no_match_leaves_dash(repo):
    import shared.matcher as m

    aa = _aa_index_file(repo, [("other", 10, "c")])
    tps = _write_tps(repo, [{"Model": "unmatched-model", "Provider": "p", "Intelligence": "", "Latency": "-", "TPS": "-"}])
    m.match_provider(tps, normalize=lambda s: s, aa_path=aa)
    assert _read_intel(repo)["unmatched-model"] == "-"


def test_ensure_catalog_models_added_with_dash(repo):
    import shared.matcher as m
    import csv

    (repo / "data" / "models.txt").write_text("catalog-model\n")
    aa = _aa_index_file(repo, [("other", 10, "c")])
    tps = _write_tps(repo, [{"Model": "existing", "Provider": "p", "Intelligence": "5", "Latency": "1", "TPS": "10"}])
    m.match_provider(tps, normalize=lambda s: s, models_path=str(repo / "data" / "models.txt"), provider_name="p", aa_path=aa)
    with open(tps) as f:
        models = {r["Model"] for r in csv.DictReader(f)}
    assert "catalog-model" in models
    assert "existing" in models
