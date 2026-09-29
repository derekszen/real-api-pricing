"""Check WeirdML v3 provenance, exact-model mappings and missing-score behavior."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
archive = json.loads((ROOT / "data/research/scores-weirdml-v3-2026-09-29.json").read_text())
points = json.loads((ROOT / "derived/points.json").read_text())
configs = json.loads((ROOT / "derived/benchmark-configurations.json").read_text())
mappings = json.loads((ROOT / "derived/benchmark-points.json").read_text())
assert archive["generatedAt"] == "2026-09-29T07:08:03Z"
assert archive["sourceCommit"] == "19bc37d"
assert archive["sourcePreparedData"] == "https://htihle.github.io/assets/data/weirdml_v3.json"
assert archive["taskCount"] == 11 and archive["configurationCount"] == 15
assert len(archive["scores"]) == 14
assert archive["sourceSha256"] == "7ad78838e827a19a14e56f9ffbafb1f13a93b56931a3ddfe90534e126e0e8a2b"
assert any(s["model"] == "claude-opus-4.5" for s in archive["scores"])  # Unpriced official model remains visible.
expected = {"gpt-6-astra": 42.22023136363636, "claude-opus-5.5": 31.20028142857143,
            "gpt-6-sol": 19.731756666666666, "gpt-6-luna": 7.874124242424242}
for model, score in expected.items():
    rows = [s for s in archive["scores"] if s["model"] == model]
    assert len(rows) == 1 and abs(rows[0]["score"] - score) < 1e-9
    assert rows[0]["secondary"]["reasoningEffort"] == "xhigh"
    assert rows[0]["secondary"]["ciMinus"] >= 0 and rows[0]["secondary"]["ciPlus"] >= 0
    assert all(abs(p["weirdml_v3__score"] - score) < 1e-9 for p in points["points"] if p["model"] == model)
assert "weirdml_v3" in points["boards"]
assert not any(s["model"] == "claude-sonnet-5.5" for s in archive["scores"])
assert all(p["weirdml_v3__score"] is None for p in points["points"] if p["model"] == "claude-sonnet-5.5")
assert len([c for c in configs if c["board"] == "weirdml_v3"]) == len(archive["scores"])
assert all(m["mapping_kind"] == "agent_configuration_reference" for m in mappings if m["board"] == "weirdml_v3")
print("PASS: WeirdML v3 source snapshot, score units, effort, exact-model plan references and missing Sonnet")
