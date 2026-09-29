"""Verify the isolated official MLS-Bench-Lite research snapshot and HTML parser."""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from import_mls_bench_lite import BOARD, URL, archive, extract  # noqa: E402

snapshot = json.loads((ROOT / "data/research/scores-mls-bench-lite-2026-09-29.json").read_text())
assert snapshot["source"] == URL == snapshot["boards"][0]["url"]
assert snapshot["sourceSha256"] == "213cfa65b4147f3e6990a70345b0d96157425417a375741f6b9718eba1f2cdaf"
assert snapshot["collectedAt"] == snapshot["boards"][0]["snapshotDate"] == "2026-09-29"
assert snapshot["taskCount"] == 30 and snapshot["evaluationPlatform"] == "Harbor"
assert snapshot["explorationHoursPerAgent"] == 5
assert snapshot["methodologySources"] == ["https://mls-bench.com/blog", "https://arxiv.org/html/2605.08678v1"]
assert "not percentage of tasks passed" in snapshot["unit"]
assert "Normalized task performance" in snapshot["boards"][0]["metric"]
rows = snapshot["scores"]
assert len(rows) == 16 and [r["secondary"]["rank"] for r in rows] == list(range(1, 17))
assert all(r["boardId"] == BOARD and r["source"] == URL and r["checkedAt"] == "2026-09-29" for r in rows)
assert all(r["model"] == r["variantLabel"] and 0 <= r["score"] <= 100 for r in rows)
assert [r["score"] for r in rows] == sorted((r["score"] for r in rows), reverse=True)
by_name = {r["model"]: r for r in rows}
assert len(by_name) == len(rows)
assert (by_name["Claude Fable 5.1"]["score"], by_name["Claude Fable 5.1"]["secondary"]["agentHarness"],
        by_name["Claude Fable 5.1"]["secondary"]["reasoningEffort"]) == (50.3, "Claude Code", "max")
assert (by_name["GPT-6 Astra"]["score"], by_name["GPT-6 Astra"]["secondary"]["agentHarness"],
        by_name["GPT-6 Astra"]["secondary"]["reasoningEffort"]) == (50.0, "Codex", "max")
assert by_name["Claude Fable 5"]["secondary"]["fallback"] is True
assert by_name["Claude Opus 5"]["score"] == 49.8
assert "Claude Opus 5.5" not in by_name  # Opus 5 is a distinct model; do not substitute it.

# Integration: retain all 16 source rows, but plot only exact reviewed served-model matches.
points = json.loads((ROOT / "derived/points.json").read_text())
configs = json.loads((ROOT / "derived/benchmark-configurations.json").read_text())
assert points["boards"][BOARD]["metric"] == "Normalized task performance (source points)"
assert len([c for c in configs if c["board"] == BOARD]) == 16
assert any(c["model"] is None and c["variant"] == "DeepSeek-V4 Pro Preview" for c in configs)
for model, expected in (("gpt-6-astra", 50.0), ("claude-fable-5.1", 50.3)):
    assert all(p[BOARD + "__score"] == expected for p in points["points"] if p["model"] == model)
assert all(p[BOARD + "__score"] is None for p in points["points"] if p["model"] == "claude-opus-5.5")

# Synthetic server-rendered table tests parser boundaries without a network dependency.
html_rows = []
for r in rows:
    s = r["secondary"]
    effort = f"<span>{escape(s['reasoningEffort'])}</span>" if s["reasoningEffort"] else ""
    fallback = "<span>(with fallback)</span>" if s["fallback"] else ""
    html_rows.append(
        f"<tr><td>{s['rank']}</td><td><span>{escape(r['model'])}</span><span>{s['availability']}</span></td>"
        f"<td><span>{escape(s['agentHarness'])}{effort}{fallback}</span></td><td>{r['score']:.1f}</td></tr>"
    )
html = ("<p>MLS-Bench-Lite Score. The evaluation is based on Harbor with a 5-hour exploration budget "
        "for each agent.</p><table><thead><tr><th>#</th><th>Model</th><th>Harness</th>"
        "<th>Performance</th></tr></thead><tbody>" + "".join(html_rows) + "</tbody></table>")
parsed = extract(html)
assert [(r["model"], r["score"], r["agentHarness"], r["reasoningEffort"], r["fallback"]) for r in parsed] == [
    (r["model"], r["score"], r["secondary"]["agentHarness"], r["secondary"]["reasoningEffort"],
     r["secondary"]["fallback"]) for r in rows]
assert archive(html.encode(), "2026-09-29")["scores"] == rows
for invalid in [html.replace("Harbor with a 5-hour", "Other platform with a 5-hour"),
                html.replace("GPT-6 Astra", "Claude Fable 5.1"),
                html.replace("<td>50.0</td>", "<td>500.0</td>"),
                html.replace("<td>3</td>", "<td>8</td>", 1)]:
    try:
        extract(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("malformed official leaderboard was accepted")
print("PASS: official MLS-Bench-Lite snapshot, 16 source-labelled rows, focus models and parser guards")
