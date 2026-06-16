"""Command line entrypoint for batch analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from compliance_nlp import analyze_directory, summarize_results


def main() -> None:
    results = analyze_directory(
        REPO_ROOT / "data" / "raw",
        output_path=REPO_ROOT / "outputs" / "analysis" / "results.json",
    )
    summary = summarize_results(results)
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
