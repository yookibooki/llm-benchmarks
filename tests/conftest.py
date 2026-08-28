import csv
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _stub_openai():
    if "openai" in sys.modules:
        return
    fake = types.ModuleType("openai")
    fake.OpenAI = type("OpenAI", (), {"__init__": lambda self, **kw: None})
    fake.APIConnectionError = type("APIConnectionError", (Exception,), {})
    fake.RateLimitError = type("RateLimitError", (Exception,), {})
    fake.APITimeoutError = type("APITimeoutError", (Exception,), {})
    fake.APIStatusError = type("APIStatusError", (Exception,), {})
    sys.modules["openai"] = fake


_stub_openai()
