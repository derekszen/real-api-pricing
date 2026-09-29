import { useEffect, useRef, useState } from "react";
import { CaretDown, List } from "@phosphor-icons/react";

export const boardCategories = [
  { id: "general", en: "General & design", zh: "通用与设计", boards: ["aa_intelligence_index", "open_design_arena"] },
  { id: "coding", en: "Coding", zh: "编程", boards: ["terminal_bench_4", "aa_terminal_bench_4", "arena_code", "arena_agent_mode", "aa_coding_agent_index", "deepswe_1_1"] },
  { id: "ml", en: "ML", zh: "机器学习", boards: ["weirdml_v3", "mls_bench_lite_maintainer"] },
] as const;

/** This focused navigation intentionally excludes unrelated science/paper boards. */
export function categorizedBoards(ids: string[]) {
  const present = new Set(ids);
  return boardCategories.map((category) => ({
    id: category.id,
    en: category.en,
    zh: category.zh,
    boards: category.boards.filter((id) => present.has(id)),
  })).filter((category) => category.boards.length);
}

export default function BoardPicker({
  ids, selected, labels, zh, onSelect,
}: {
  ids: string[];
  selected: string;
  labels: Record<string, string>;
  zh: boolean;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const categories = categorizedBoards(ids);

  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(null);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);

  return (
    <div ref={root} className="board-tabs" role="group" aria-label={zh ? "按类别选择榜单" : "Choose leaderboard by category"}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node)) setOpen(null);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          setOpen(null);
          root.current?.querySelector<HTMLButtonElement>(`[data-category="${open}"]`)?.focus();
        }
      }}>
      {categories.map((category) => {
        const active = category.boards.some((id) => id === selected);
        const expanded = open === category.id;
        return (
          <div key={category.id} className="board-category"
            onMouseEnter={() => {
              if (window.matchMedia?.("(hover: hover)").matches) setOpen(category.id);
            }}
            onMouseLeave={() => setOpen(null)}>
            <button type="button" data-category={category.id}
              className={active ? "board-category-trigger selected" : "board-category-trigger"}
              aria-expanded={expanded} aria-controls={expanded ? `board-options-${category.id}` : undefined}
              aria-label={`${zh ? category.zh : category.en}: ${active ? labels[selected] : (zh ? "选择榜单" : "Choose leaderboard")}`}
              onClick={() => setOpen(expanded ? null : category.id)}>
              <List size={15} aria-hidden="true" />
              <span className="board-category-title">{zh ? category.zh : category.en}</span>
              {active && <span className="board-category-current">{labels[selected]}</span>}
              <CaretDown size={12} aria-hidden="true" />
            </button>
            {expanded && (
              <div id={`board-options-${category.id}`} className="board-options" role="group" aria-label={zh ? category.zh : category.en}>
                {category.boards.map((id) => (
                  <button type="button" key={id} className={id === selected ? "board-option selected" : "board-option"}
                    aria-current={id === selected ? "true" : undefined}
                    onClick={() => {
                      onSelect(id);
                      setOpen(null);
                      root.current?.querySelector<HTMLButtonElement>(`[data-category="${category.id}"]`)?.focus();
                    }}>
                    {labels[id] || id}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
