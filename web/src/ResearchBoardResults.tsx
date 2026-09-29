import type { Configuration, Mapping, Point } from "./types";

/** Match each published configuration, not merely its model name, to priced chart mappings. */
export function publishedResults(board: string, configurations: Configuration[], mappings: Mapping[], points: Point[]) {
  const byId = new Map(points.map((point) => [point.id, point]));
  const cheapest = new Map<string, Point>();
  for (const mapping of mappings) {
    if (mapping.board !== board) continue;
    const point = byId.get(mapping.point_id);
    if (!point) continue;
    const previous = cheapest.get(mapping.configuration_id);
    if (!previous || point.real_usd_per_mtok < previous.real_usd_per_mtok) cheapest.set(mapping.configuration_id, point);
  }
  return configurations.filter((entry) => entry.board === board)
    .sort((a, b) => b.score - a.score || a.configuration_id.localeCompare(b.configuration_id))
    .map((entry) => ({ entry, priced: cheapest.get(entry.configuration_id) ?? null }));
}

export default function ResearchBoardResults({
  board, configurations, mappings, points, zh,
}: {
  board: string;
  configurations: Configuration[];
  mappings: Mapping[];
  points: Point[];
  zh: boolean;
}) {
  const results = publishedResults(board, configurations, mappings, points);
  if (!results.length) return null;
  return (
    <details className="research-results" key={board} open={results.length <= 5}>
      <summary>{zh ? "公开成绩" : "Published results"} ({results.length})</summary>
      <p>{zh
        ? "所有公开配置均保留，包括没有精确匹配定价的 MLS 模型。缺少成绩不等于零；各模型评测框架与推理强度可能不同。横轴套餐价格并非评测成本。"
        : "All published configurations are included, even MLS models without an exact priced match. A missing result is not zero; harnesses and reasoning effort may differ. Plan prices are not evaluation costs."}</p>
      <div className="research-results-scroll" role="region" tabIndex={0} aria-label={zh ? "可滚动公开成绩" : "Scrollable published results"}>
        <table>
          <thead><tr>
            <th>{zh ? "模型 / 系统（原文）" : "Model / system (source label)"}</th>
            <th>{zh ? "框架与推理强度" : "Harness · effort"}</th>
            <th>{zh ? "成绩" : "Score"}</th>
            <th>{zh ? "最低收录价 / 百万 token" : "Lowest listed $/M tokens"}</th>
            <th>{zh ? "定价匹配" : "Priced match"}</th>
          </tr></thead>
          <tbody>
            {results.map(({ entry, priced }) => (
              <tr key={entry.configuration_id}>
                <td>{entry.source_model && entry.source_model !== entry.variant
                  ? <><strong>{entry.source_model}</strong><br /><small>{entry.variant}</small></>
                  : entry.variant || entry.source_model || entry.model || "—"}</td>
                <td>{[entry.agent_harness, entry.reasoning_effort].filter(Boolean).join(" · ") || "—"}</td>
                <td className="numeric">{Number(entry.score.toFixed(2))}{board === "weirdml_v3" ? "%" : " / 100"}</td>
                <td className="numeric">{priced ? `$${priced.real_usd_per_mtok.toPrecision(3)} · ${priced.plan}` : "—"}</td>
                <td>{priced ? (zh ? "已上图" : "Plotted") : (zh ? "无精确价格匹配" : "No exact price match")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
