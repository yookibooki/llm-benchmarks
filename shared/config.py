import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def require_api_key(provider: str, env_var: str) -> str:
    key = os.environ.get(env_var, "")
    if not key:
        sys.exit(
            f"Missing {env_var}. Set it in the environment."
        )
    return key
