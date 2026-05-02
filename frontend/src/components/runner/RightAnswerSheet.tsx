"use client";

import { useMemo, useState } from "react";
import { BookOpen, Check, Flag, Highlighter, NotebookPen } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type RightAnswerSheetItem = {
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

type AnswerSheetFilter = "all" | "unanswered" | "answered" | "marked" | "hasNote" | "hasHighlight";

type RightAnswerSheetProps = {
  items: RightAnswerSheetItem[];
  answeredCount: number;
  totalCount: number;
  groupByPart?: boolean;
  labels: {
    title: string;
    answered: string;
    unanswered: string;
    all: string;
    marked: string;
    hasNote: string;
    hasHighlight: string;
    listening: string;
    reading: string;
    part: string;
  };
  onSelect: (item: RightAnswerSheetItem) => void;
};

const filters: AnswerSheetFilter[] = ["all", "unanswered", "answered", "marked", "hasNote", "hasHighlight"];

function getSection(part?: number | null) {
  if (!part) return "Other";
  return part <= 4 ? "Listening" : "Reading";
}

function QuestionButton({
  item,
  onSelect,
}: {
  item: RightAnswerSheetItem;
  onSelect: (item: RightAnswerSheetItem) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(item)}
      className={`relative flex h-9 min-w-9 items-center justify-center rounded-full border px-2 text-xs font-semibold transition ${
        item.current
          ? "border-primary bg-primary text-primary-foreground shadow-sm ring-2 ring-primary/20"
          : item.answered
            ? "border-primary/30 bg-primary/10 text-primary hover:bg-primary/15"
            : "border-[#CBD5E1] bg-white text-muted-foreground hover:border-primary/50"
      }`}
    >
      {item.label}
      {(item.bookmarked || item.hasNote || item.hasHighlight) && (
        <span className="absolute -right-0.5 -top-0.5 flex gap-0.5 rounded-full bg-white p-0.5 shadow-sm ring-1 ring-border">
          {item.bookmarked ? <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" /> : null}
          {item.hasNote ? <span className="h-1.5 w-1.5 rounded-full bg-violet-500" /> : null}
          {item.hasHighlight ? <span className="h-1.5 w-1.5 rounded-full bg-orange-500" /> : null}
        </span>
      )}
    </button>
  );
}

export function RightAnswerSheet({
  items,
  answeredCount,
  totalCount,
  groupByPart = false,
  labels,
  onSelect,
}: RightAnswerSheetProps) {
  const [activeFilter, setActiveFilter] = useState<AnswerSheetFilter>("all");

  const filteredItems = useMemo(
    () =>
      items.filter((item) => {
        if (activeFilter === "all") return true;
        if (activeFilter === "unanswered") return !item.answered;
        if (activeFilter === "answered") return item.answered;
        if (activeFilter === "marked") return item.bookmarked;
        if (activeFilter === "hasNote") return item.hasNote;
        return item.hasHighlight;
      }),
    [activeFilter, items],
  );

  const groupedSections = groupByPart
    ? ["Listening", "Reading"].map((section) => ({
        section,
        items: filteredItems.filter((item) => getSection(item.part) === section),
      }))
    : [{ section: "", items: filteredItems }];

  const filterLabel = (filter: AnswerSheetFilter) => {
    if (filter === "all") return labels.all;
    if (filter === "unanswered") return labels.unanswered;
    if (filter === "answered") return labels.answered;
    if (filter === "marked") return labels.marked;
    if (filter === "hasNote") return labels.hasNote;
    return labels.hasHighlight;
  };

  return (
    <Card className="rounded-2xl border-[#DDE7F7] bg-white shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base text-foreground">
          <BookOpen className="h-4 w-4 text-primary" />
          {labels.title}
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          {labels.answered} {answeredCount} / {totalCount}
        </p>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          {filters.map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setActiveFilter(filter)}
              className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
                activeFilter === filter
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-[#F8FAFC] text-muted-foreground hover:border-primary/50"
              }`}
            >
              {filterLabel(filter)}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3 border-y border-[#E6EDF8] py-2 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <Check className="h-3 w-3 text-primary" />
            {labels.answered}
          </span>
          <span className="flex items-center gap-1">
            <Flag className="h-3 w-3 text-yellow-600" fill="currentColor" />
            {labels.marked}
          </span>
          <span className="flex items-center gap-1">
            <NotebookPen className="h-3 w-3 text-violet-600" />
            {labels.hasNote}
          </span>
          <span className="flex items-center gap-1">
            <Highlighter className="h-3 w-3 text-orange-600" />
            {labels.hasHighlight}
          </span>
        </div>

        <div className="max-h-[42vh] min-h-48 space-y-4 overflow-y-auto pr-1">
          {groupedSections.map(({ section, items: sectionItems }) =>
            sectionItems.length > 0 ? (
              <div key={section || "all"} className="space-y-2">
                {groupByPart ? (
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {section === "Listening" ? labels.listening : labels.reading}
                  </p>
                ) : null}

                {groupByPart
                  ? Array.from(new Set(sectionItems.map((item) => item.part || 0))).map((part) => (
                      <div key={`${section}-${part}`} className="space-y-1.5">
                        <p className="text-xs font-medium text-muted-foreground">
                          {labels.part} {part || "?"}
                        </p>
                        <div className="grid grid-cols-6 gap-1.5">
                          {sectionItems
                            .filter((item) => (item.part || 0) === part)
                            .map((item) => (
                              <QuestionButton key={item.id} item={item} onSelect={onSelect} />
                            ))}
                        </div>
                      </div>
                    ))
                  : (
                    <div className="grid grid-cols-6 gap-1.5">
                      {sectionItems.map((item) => (
                        <QuestionButton key={item.id} item={item} onSelect={onSelect} />
                      ))}
                    </div>
                  )}
              </div>
            ) : null,
          )}
        </div>
      </CardContent>
    </Card>
  );
}
