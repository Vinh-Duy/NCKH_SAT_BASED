"""Compare both configurations, retaining both spans and checking agreement."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.benchmark_products import main

if __name__ == "__main__":
    main(comparison=True)
