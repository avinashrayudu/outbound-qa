from __future__ import annotations

import csv
import json
from pathlib import Path

from .lint import Draft


def read_drafts(path: Path) -> list[Draft]:
    path = Path(path)
    if path.suffix == ".jsonl":
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    elif path.suffix == ".json":
        rows = json.loads(path.read_text())
    else:
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    return [Draft(id=str(r.get("id") or i), to=r.get("to", ""), subject=r.get("subject", ""),
                  body=r.get("body", "")) for i, r in enumerate(rows, start=1)]
