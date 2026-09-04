import sys


def test_fmt_number_formats_by_magnitude():
    import gen_html as g

    assert g._fmt_number("-") == "-"
    assert g._fmt_number("") == "-"
    assert g._fmt_number(None) == "-"
    assert g._fmt_number("0.23") == "0.2"
    assert g._fmt_number("9.9") == "9.9"
    assert g._fmt_number("123.4") == "123"


def test_has_intelligence():
    import gen_html as g

    assert g._has_intelligence({"Intelligence": "5"}) is True
    assert g._has_intelligence({"Intelligence": "-"}) is False
    assert g._has_intelligence({"Intelligence": ""}) is False


def test_build_sort_key_measured_beats_unmeasured_high_intel():
    import gen_html as g

    measured_low = {"Intelligence": "5", "Latency": "1.0", "TPS": "50", "Provider": "p", "Model": "m"}
    unmeasured_high = {"Intelligence": "99", "Latency": "-", "TPS": "-", "Provider": "p", "Model": "m"}
    assert g.build_sort_key(measured_low) < g.build_sort_key(unmeasured_high)


def test_build_sort_key_intelligence_descending_within_measured():
    import gen_html as g

    a = {"Intelligence": "10", "Latency": "1.0", "TPS": "50", "Provider": "p", "Model": "a"}
    b = {"Intelligence": "90", "Latency": "1.0", "TPS": "50", "Provider": "p", "Model": "b"}
    assert g.build_sort_key(b) < g.build_sort_key(a)


def test_reconcile_adds_missing_and_prunes_stale(tmp_path, monkeypatch):
    import gen_html as g

    monkeypatch.setattr(g, "PROVIDER_NAMES", ["alpha"])
    monkeypatch.setattr(g, "REPO_ROOT", tmp_path)
    prov = "alpha"
    d = tmp_path / prov / "data"
    d.mkdir(parents=True)
    (d / "models.txt").write_text("keep1\nkeep2\nnewmodel\n")

    rows = [
        {"Model": "keep1", "Provider": prov, "Intelligence": "5", "Latency": "1", "TPS": "10"},
        {"Model": "stale", "Provider": prov, "Intelligence": "5", "Latency": "1", "TPS": "10"},
    ]
    g.reconcile_with_catalogs(rows)
    models = {r["Model"] for r in rows}
    assert "newmodel" in models
    assert "stale" not in models
    assert "keep1" in models


def test_reconcile_does_not_rewrite_merged_file(tmp_path, monkeypatch):
    import gen_html as g

    monkeypatch.setattr(g, "PROVIDER_NAMES", ["alpha"])
    monkeypatch.setattr(g, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(g, "MERGED_PATH", str(tmp_path / "data" / "tps.csv"))
    (tmp_path / "data").mkdir(parents=True)
    merged = tmp_path / "data" / "tps.csv"
    merged.write_text("sentinel")

    prov = "alpha"
    d = tmp_path / prov / "data"
    d.mkdir(parents=True)
    (d / "models.txt").write_text("m1\n")

    rows = [{"Model": "m1", "Provider": prov, "Intelligence": "5", "Latency": "1", "TPS": "10"}]
    g.reconcile_with_catalogs(rows)
    assert merged.read_text() == "sentinel"
