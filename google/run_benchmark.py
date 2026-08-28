import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.provider import run_provider_benchmark

if __name__ == "__main__":
    run_provider_benchmark(provider="google")
