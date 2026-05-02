"use client";

import { BookOpen, Check, Flag, Highlighter, NotebookPen } from "lucide-react";

type QuestionNavigatorItem = {
  id: number | string;
  label: string;
  part?: number | null;
  section?: "Listening" | "Reading" | string | null;
  current?: boolean;
  answered?: boolean;
  bookmarked?: boolean;
  hasNote?: boolean;
  hasHighlight?: boolean;
};

type QuestionBottomNavigatorProps = {
  title: string;
  items: QuestionNavigatorItem[];
  labels: {
    answered: string;
    bookmarked: string;
    note: string;
    highlight: string;
    unanswered: string;
    listening?: string;
    reading?: string;
    part?: string;
  };
  groupByPart?: boolean;
  onSelect: (item: QuestionNavigatorItem) => void;
};

function getSection(part?: number | null) {
  if (!part) return "Other";
  return part <= 4 ? "Listening" : "Reading";
}

function QuestionButton({
  item,
  onSelect,
}: {
  item: QuestionNavigatorItem;
  onSelect: (item: QuestionNavigatorItem) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(item)}
      className={`relative flex h-10 min-w-10 items-center justify-center rounded-full border px-3 text-sm font-semibold transition ${
        item.current
          ? "border-primary bg-primary text-primary-foreground shadow-sm"
          : item.answered
            ? "border-primary/30 bg-primary/10 text-primary hover:bg-primary/15"
            : "border-border bg-white text-muted-foreground hover:border-primary/50"
      }`}
    >
      {item.label}
      {(item.bookmarked || item.hasNote || item.hasHighlight) && (
        <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-white shadow-sm ring-1 ring-border">
          {item.bookmarked ? (
            <Flag className="h-2.5 w-2.5 text-yellow-600" fill="currentColor" />
          ) : item.hasNote ? (
            <NotebookPen className="h-2.5 w-2.5 text-primary" />
          ) : (
            <Highlighter className="h-2.5 w-2.5 text-amber-600" />
          )}
        </span>
      )}
    </button>
  );
}

export function QuestionBottomNavigator({
  title,
  items,
  labels,
  groupByPart = false,
  onSelect,
}: QuestionBottomNavigatorProps) {
  const sections = groupByPart
    ? ["Listening", "Reading"].map((section) => ({
        section,
        items: items.filter((item) => getSection(item.part) === section),
      }))
    : [{ section: "", items }];

  return (
    <div className="rounded-2xl border border-[#DDE7F7] bg-white p-3 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-primary" />
          <p className="text-sm font-semibold text-foreground">{title}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <Check className="h-3 w-3 text-primary" />
            {labels.answered}
          </span>
          <span className="flex items-center gap-1">
            <Flag className="h-3 w-3 text-yellow-600" fill="currentColor" />
            {labels.bookmarked}
          </span>
          <span className="flex items-center gap-1">
            <NotebookPen className="h-3 w-3 text-primary" />
            {labels.note}
          </span>
          <span className="flex items-center gap-1">
            <Highlighter className="h-3 w-3 text-amber-600" />
            {labels.highlight}
          </span>
        </div>
      </div>

      <div className="max-h-52 space-y-3 overflow-y-auto">
        {sections.map(({ section, items: sectionItems }) =>
          sectionItems.length > 0 ? (
            <div key={section || "all"} className="space-y-2">
              {groupByPart && (
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {section === "Listening" ? labels.listening || section : labels.reading || section}
                </p>
              )}
              {groupByPart ? (
                Array.from(new Set(sectionItems.map((item) => item.part || 0))).map((part) => (
                  <div key={`${section}-${part}`} className="space-y-1.5">
                    <p className="text-xs font-medium text-muted-foreground">
                      {labels.part || "Part"} {part || "?"}
                    </p>
                    <div className="flex gap-2 overflow-x-auto pb-1">
                      {sectionItems
                        .filter((item) => (item.part || 0) === part)
                        .map((item) => (
                          <QuestionButton key={item.id} item={item} onSelect={onSelect} />
                        ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {sectionItems.map((item) => (
                    <QuestionButton key={item.id} item={item} onSelect={onSelect} />
                  ))}
                </div>
              )}
            </div>
          ) : null,
        )}
      </div>
    </div>
  );
}

export type { QuestionNavigatorItem };
