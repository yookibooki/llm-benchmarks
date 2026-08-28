def _chunk(delta=None, usage=None):
    class Delta:
        def __init__(s, c):
            s.content = c

    class Choice:
        def __init__(s, d):
            s.delta = d

    class Chunk:
        pass

    c = Chunk()
    if delta is not None:
        c.choices = [Choice(Delta(delta))]
    else:
        c.choices = []
    c.usage = usage
    return c


def _usage(ct):
    class U:
        def __init__(s):
            s.completion_tokens = ct

    return U()


def _sentences(n=60):
    return ["The quick brown fox jumps over the lazy dog.\n"] * n


def _fake_client(chunks):
    import types as t

    class Chat:
        def create(self, **kw):
            assert kw["stream_options"] == {"include_usage": True}
            return iter(chunks)

    class Client:
        def __init__(self):
            self.chat = t.SimpleNamespace(completions=Chat())

    return Client()


def test_uses_real_usage_tokens(tmp_path):
    import shared.benchmark as b

    chunks = [_chunk(delta=s) for s in _sentences()] + [_chunk(usage=_usage(780))]
    res = b.benchmark("m", _fake_client(chunks), "p")
    assert res.error is None
    assert res.token_source == "usage"
    assert res.tps is not None and res.tps > 0


def test_falls_back_to_chars_when_no_usage(tmp_path):
    import shared.benchmark as b

    chunks = [_chunk(delta=s) for s in _sentences()]
    res = b.benchmark("m", _fake_client(chunks), "p")
    assert res.error is None
    assert res.token_source == "chars/4"
    assert res.tps is not None and res.tps > 0


def test_rejects_missing_benchmark_text(tmp_path):
    import shared.benchmark as b

    chunks = [_chunk(delta="unrelated output\n")]
    res = b.benchmark("m", _fake_client(chunks), "p")
    assert res.error is not None
    assert "expected benchmark text" in res.error


def test_from_row_roundtrip():
    from shared.benchmark import BenchmarkResult

    r = BenchmarkResult.from_row(
        {"Model": "a", "Provider": "p", "Intelligence": "5", "Latency": "1.2", "TPS": "99"}
    )
    assert r.model == "a" and r.latency == 1.2 and r.tps == 99
    r2 = BenchmarkResult.from_row(
        {"Model": "a", "Provider": "p", "Intelligence": "-", "Latency": "-", "TPS": "-"}
    )
    assert r2.latency is None and r2.tps is None
