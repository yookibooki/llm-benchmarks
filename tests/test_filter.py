import json
from pathlib import Path

import pytest


@pytest.fixture
def repo(tmp_path):
    return tmp_path


def test_gate_skips_unchanged_catalog(repo):
    import shared.filter as sf

    snap = repo / "endpoint_snapshot.json"
    models = ["b", "a", "c"]
    sf.write_snapshot(str(snap), models, "http://x")

    changed, written = sf.gate_changed(str(snap), sorted(models), "http://x")
    assert changed is False
    assert written == sorted(models)


def test_gate_detects_change(repo):
    import shared.filter as sf

    snap = repo / "endpoint_snapshot.json"
    sf.write_snapshot(str(snap), ["a", "b"], "http://x")

    changed, written = sf.gate_changed(str(snap), ["a", "b", "c"], "http://x")
    assert changed is True
    assert written == ["a", "b", "c"]


def test_gate_rewrites_snapshot_on_change(repo):
    import shared.filter as sf

    snap = repo / "endpoint_snapshot.json"
    sf.write_snapshot(str(snap), ["a"], "http://x")
    sf.gate_changed(str(snap), ["a", "b"], "http://x")
    stored = json.loads(snap.read_text())
    assert stored["count"] == 2


def test_quorum_warns_on_shrink(capsys, repo):
    import shared.filter as sf

    out = repo / "models.txt"
    out.write_text("\n".join(["a", "b", "c", "d", "e"]))
    sf._quorum_check(["a", "b"], str(out), "test")
    captured = capsys.readouterr()
    assert "shrank" in captured.err


def test_quorum_silent_when_growing(capsys, repo):
    import shared.filter as sf

    out = repo / "models.txt"
    out.write_text("a\nb")
    sf._quorum_check(["a", "b", "c", "d"], str(out), "test")
    captured = capsys.readouterr()
    assert "shrank" not in captured.err


def test_gate_and_write_refuses_too_few(capsys, repo):
    import shared.filter as sf

    with pytest.raises(SystemExit):
        sf.gate_and_write(
            "test",
            model_ids=["only-one"],
            output_path=str(repo / "models.txt"),
            snapshot_path=str(repo / "snap.json"),
            source_url="http://x",
        )
