"""Archive one dated WeirdML v3 prepared-data snapshot as benchmark configurations.

Manual refresh (never called during the reproducible build):
  python scripts/import_weirdml.py --output data/research/scores-weirdml-v3-YYYY-MM-DD.json
Review the diff, then append the filename to compute.SCORE_FILES. Do not overwrite old evidence.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "https://htihle.github.io/assets/data/weirdml_v3.json"
BOARD_URL = "https://htihle.github.io/weirdml.html"
BOARD = "weirdml_v3"


def archive(prepared: dict, raw: bytes) -> dict:
    assert prepared["schema_version"] == 1 and prepared["mode"] == "real"
    assert prepared["task_count"] == 11 and prepared["configuration_count"] == 15
    assert prepared["overall_axis"] == {"kind": "equivalent_tokens", "start": 500000, "limit": 50000000}
    assert prepared["uncertainty"]["confidence"] == 0.95
    generated = datetime.fromisoformat(prepared["generated"].replace("Z", "+00:00"))
    assert generated.tzinfo is not None
    seen = set()
    scores = []
    for item in prepared["models"]:
        # Explicit provider/model slugs from the benchmark's prepared data; no display-name guessing.
        slug = item["slug"]
        assert slug.count("/") == 1, slug
        model = slug.split("/", 1)[1]  # Keep unpriced source rows for the published-results table.
        assert item["id"] not in seen and item["synthetic"] is False
        assert set(item["configurations"]) == {c["id"] for c in prepared["configurations"]}
        assert 0 <= item["interval"][0] <= item["score"] <= item["interval"][1] <= 1
        seen.add(item["id"])
        score = 100 * item["score"]
        low, high = (100 * v for v in item["interval"])
        harness = item["harnesses"]
        assert harness and len({h["name"] for h in harness}) == 1
        scores.append({
            "boardId": BOARD, "model": model, "variantLabel": item["name"],
            "score": score, "secondary": {
                "agentHarness": harness[0]["name"], "harnessVersions": [h["version"] for h in harness],
                "reasoningEffort": item["reasoning_effort"],
                "ciMinus": score - low, "ciPlus": high - score,
                "ciMethod": "Approximate 95% run-uncertainty interval, partially pooled; see primary source assumptions",
                "meanCostUsdPerTask": item["mean_api_cost_usd"],
                "runs": item["runs"], "sourceId": item["id"], "sourceSlug": slug,
                "meanFinalBest": item["mean_final_best"],
            }, "source": BOARD_URL, "checkedAt": generated.date().isoformat(),
        })
    for required in ("gpt-6-astra", "gpt-6-sol", "gpt-6-luna", "claude-opus-5.5"):
        assert any(row["model"] == required for row in scores), required
    assert not any(row["model"] == "claude-sonnet-5.5" for row in scores)
    return {
        "collectedAt": datetime.now(timezone.utc).date().isoformat(),
        "generatedAt": prepared["generated"], "sourceCommit": prepared["source_commit"],
        "sourceSha256": hashlib.sha256(raw).hexdigest(), "sourcePreparedData": SOURCE,
        "taskCount": prepared["task_count"], "configurationCount": prepared["configuration_count"],
        "unit": "Official score (%) = 80% normalized area under best-so-far effective score on a log equivalent-token axis (500k–50M), plus 20% final best. Equal weight per task; hinted/hintless twins split their task weight. Effective scores are not raw accuracy. Runs on distinct Codex CLI / Claude Code / other harnesses are reference configurations, not product-plan measurements. Source mean API cost per run is not the chart's subscription $/MTok x coordinate.",
        "boards": [{"boardId": BOARD, "name": "WeirdML v3", "metric": "Official score %", "url": BOARD_URL, "snapshotDate": generated.date().isoformat()}],
        "excludedSourceModels": prepared.get("excluded_models", []),
        "scores": scores,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New dated snapshot file; refuses to overwrite")
    parser.add_argument("--input", type=Path, help="Read locally cached primary prepared-data JSON instead of fetching")
    args = parser.parse_args()
    raw = args.input.read_bytes() if args.input else urlopen(SOURCE, timeout=30).read()
    prepared = json.loads(raw)
    result = archive(prepared, raw)
    if args.output.exists():
        parser.error(f"refusing to overwrite existing snapshot: {args.output}")
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Archived {len(result['scores'])} official configurations (including unpriced models) from {SOURCE} into {args.output}")


if __name__ == "__main__":
    main()
