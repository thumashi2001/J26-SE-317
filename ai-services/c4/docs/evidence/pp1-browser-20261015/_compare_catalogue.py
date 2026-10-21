"""One-off: compare frozen v1 catalogue IDs to current C1 practice keys."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]  # .../J26-SE-317
sys.path.insert(0, str(ROOT / "ai-services" / "c4"))

from catalogues.c1_practice_full_2026_10 import ORDERED_TOPICS, catalogue_hash  # noqa: E402

pq = (ROOT / "backend/src/modules/c1/data/practiceQuestions.js").read_text(encoding="utf-8")
# Keys may be re-exported; also read content/index TOPICS if needed
keys = set(re.findall(r"^\s*([a-z0-9_]+)\s*:", pq, flags=re.M))
# Prefer importing via listing PRACTICE_QUESTIONS usage in supportedTopics — read content modules
content = ROOT / "backend/src/modules/c1/data/content"
if content.is_dir():
    # topic ids appear as object keys in module exports; use ORDERED from index
    idx = (content / "index.js").read_text(encoding="utf-8")
    # fallback: count practiceQuestions Object.keys via node elsewhere
    pass

v1 = list(ORDERED_TOPICS)
print("v1_count", len(v1))
print("v1_hash", catalogue_hash())
# Load C1 keys from practiceQuestions by running a tiny node helper
import subprocess

node = subprocess.check_output(
    [
        "node",
        "--input-type=module",
        "-e",
        "import { PRACTICE_QUESTIONS } from './backend/src/modules/c1/data/practiceQuestions.js'; console.log(Object.keys(PRACTICE_QUESTIONS).join('\\n'));",
    ],
    cwd=str(ROOT),
    text=True,
)
c1 = [t for t in node.splitlines() if t.strip()]
print("c1_count", len(c1))
only_c1 = sorted(set(c1) - set(v1))
only_v1 = sorted(set(v1) - set(c1))
print("intersection", len(set(c1) & set(v1)))
print("only_c1", only_c1)
print("only_v1", only_v1)
