"""Archive the MLS-Bench maintainers' live MLS-Bench-Lite leaderboard.

Manual research snapshot only; the build uses dated archives without network access.
  python scripts/import_mls_bench_lite.py --output data/research/scores-mls-bench-lite-YYYY-MM-DD.json
Review each new dated archive; never overwrite an earlier snapshot. Model labels are
verbatim source labels, NOT inferred project/API model identifiers.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://mls-bench.com/leaderboard"
BOARD = "mls_bench_lite_maintainer"
HEADERS = ["#", "Model", "Harness", "Performance"]


class LeaderboardParser(HTMLParser):
    """Read the server-rendered table, keeping model, harness and effort cells separate."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.table is not None:
                raise ValueError("nested leaderboard table")
            self.table = {"headers": [], "rows": []}
        elif self.table is not None:
            if tag == "tr":
                self.row = []
            elif tag in ("th", "td") and self.row is not None:
                self.cell = []

    def handle_data(self, data):
        if self.cell is not None and data.strip():
            self.cell.append(data.strip())

    def handle_endtag(self, tag):
        if self.table is None:
            return
        if tag in ("th", "td") and self.cell is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                if self.row[0] and self.row[0][0] == "#":
                    self.table["headers"] = [" ".join(cell) for cell in self.row]
                else:
                    self.table["rows"].append(self.row)
            self.row = None
        elif tag == "table":
            self.tables.append(self.table)
            self.table = None


def extract(html: str) -> list[dict]:
    if "MLS-Bench-Lite Score" not in html or "Harbor with a 5-hour exploration budget" not in html:
        raise ValueError("missing official Lite leaderboard or evaluation protocol")
    parser = LeaderboardParser()
    parser.feed(html)
    tables = [table for table in parser.tables if table["headers"] == HEADERS]
    if len(tables) != 1:
        raise ValueError("expected exactly one MLS-Bench-Lite leaderboard table")
    rows = []
    for cells in tables[0]["rows"]:
        if len(cells) != 4 or len(cells[1]) != 2 or cells[1][1] not in ("Open", "Closed"):
            raise ValueError(f"unexpected leaderboard row: {cells}")
        rank, (name, availability), harness, performance = cells
        if not rank or not re.fullmatch(r"\d+", rank[0]) or len(rank) != 1:
            raise ValueError(f"invalid rank: {rank}")
        if not harness or harness[0] not in ("Claude Code", "Codex", "Kimi-Code"):
            raise ValueError(f"unknown harness: {harness}")
        extras = harness[1:]
        effort = extras.pop(0) if extras and extras[0] in ("max", "xhigh", "high", "medium", "low") else None
        fallback = " ".join(extras).replace(" ", "") == "(withfallback)" if extras else False
        if extras and not fallback:
            raise ValueError(f"unknown harness options: {harness}")
        if len(performance) != 1 or not re.fullmatch(r"\d+(?:\.\d+)?", performance[0]):
            raise ValueError(f"invalid performance: {performance}")
        score = float(performance[0])
        if not 0 <= score <= 100:
            raise ValueError(f"out-of-range performance: {score}")
        rows.append({"rank": int(rank[0]), "model": name, "availability": availability,
                     "agentHarness": harness[0], "reasoningEffort": effort,
                     "fallback": fallback, "score": score})
    if len(rows) < 15 or len({row["model"] for row in rows}) != len(rows):
        raise ValueError("missing or duplicate leaderboard rows")
    if [row["rank"] for row in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("nonsequential leaderboard ranks")
    if rows != sorted(rows, key=lambda row: -row["score"]):
        raise ValueError("leaderboard not sorted by performance")
    return rows


def archive(raw: bytes, collected: str) -> dict:
    rows = extract(raw.decode("utf-8"))
    return {
        "collectedAt": collected, "source": URL, "sourceSha256": hashlib.sha256(raw).hexdigest(),
        "unit": "Maintainer-displayed normalized task-performance points (0–100 presentation), not percentage of tasks passed or Pass@1. The 30-task Lite track is evaluated with Harbor and a five-hour exploration budget per agent. Harness and effort vary by row; do not treat these as matched-harness comparisons. Model names remain verbatim source labels, not API identity mappings.",
        "taskCount": 30, "explorationHoursPerAgent": 5, "evaluationPlatform": "Harbor",
        "methodologySources": ["https://mls-bench.com/blog", "https://arxiv.org/html/2605.08678v1"],
        "boards": [{"boardId": BOARD, "name": "MLS-Bench-Lite (maintainer live leaderboard)",
                    "metric": "Normalized task performance (source points)", "url": URL,
                    "snapshotDate": collected}],
        "scores": [{"boardId": BOARD, "model": row["model"], "variantLabel": row["model"],
                    "score": row["score"],
                    "secondary": {key: row[key] for key in ("rank", "availability", "agentHarness", "reasoningEffort", "fallback")},
                    "source": URL, "checkedAt": collected} for row in rows],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--input", type=Path, help="Use a saved official HTML response instead of fetching")
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"refusing to overwrite: {args.output}")
    raw = args.input.read_bytes() if args.input else urlopen(Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
    result = archive(raw, datetime.now(timezone.utc).date().isoformat())
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Archived {len(result['scores'])} maintainer MLS-Bench-Lite rows at {args.output}")


if __name__ == "__main__":
    main()
