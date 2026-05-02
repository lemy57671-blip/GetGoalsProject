"use client";

import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";

export type IntegratedQuestionBarItem = {
  id: number | string;
  label: string;
  part?: number | null;
  current?: boolean;
  answered?: boolean;
  bookmarked?: boolean;
  hasNote?: boolean;
  hasHighlight?: boolean;
};

type IntegratedQuestionBarProps = {
  items: IntegratedQuestionBarItem[];
  currentLabel: string;
  answeredCount: number;
  markedCount: number;
  labels: {
    previous: string;
    next: string;
    questionList: string;
    answered: string;
    marked: string;
    notes: string;
    highlights: string;
    all: string;
    part: string;
    progress: string;
  };
  previousDisabled?: boolean;
  nextDisabled?: boolean;
  onPrevious: () => void;
  onNext: () => void;
  onSelect: (item: IntegratedQuestionBarItem) => void;
};

function StatusDot({ className }: { className: string }) {
  return <span className={`block h-1.5 w-1.5 rounded-full ${className}`} />;
}

export function IntegratedQuestionBar({
  items,
  currentLabel,
  answeredCount,
  markedCount,
  labels,
  previousDisabled,
  nextDisabled,
  onPrevious,
  onNext,
  onSelect,
}: IntegratedQuestionBarProps) {
  const parts = useMemo(
    () =>
      Array.from(
        new Set(
          items
            .map((item) => item.part)
            .filter((part): part is number => Number.isInteger(part) && Number(part) >= 1 && Number(part) <= 7),
        ),
      ).sort((left, right) => left - right),
    [items],
  );
  const [activePart, setActivePart] = useState<number | "all">("all");
  const visibleItems =
    activePart === "all" ? items : items.filter((item) => Number(item.part) === activePart);

  return (
    <div className="-mx-6 -mb-6 mt-2 rounded-b-xl border-t border-[#E2E8F0] bg-[#F8FAFC] px-4 py-3 sm:px-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onPrevious}
          disabled={previousDisabled}
          className="justify-center gap-2 md:min-w-32"
        >
          <ArrowLeft className="h-4 w-4" />
          {labels.previous}
        </Button>

        <div className="flex flex-wrap items-center justify-center gap-3 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">
            {labels.progress}: {currentLabel}
          </span>
          <span>{labels.answered} {answeredCount}</span>
          <span>{labels.marked} {markedCount}</span>
        </div>

        <Button
          type="button"
          size="sm"
          onClick={onNext}
          disabled={nextDisabled}
          className="justify-center gap-2 md:min-w-32"
        >
          {labels.next}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="mt-3 space-y-2">
        {parts.length > 1 ? (
          <div className="flex gap-2 overflow-x-auto pb-0.5 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
            <button
              type="button"
              onClick={() => setActivePart("all")}
              className={`shrink-0 rounded-full border px-3 py-1 text-xs font-medium transition ${
                activePart === "all"
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-white text-muted-foreground hover:border-primary/50"
              }`}
            >
              {labels.all}
            </button>
            {parts.map((part) => (
              <button
                key={part}
                type="button"
                onClick={() => setActivePart(part)}
                className={`shrink-0 rounded-full border px-3 py-1 text-xs font-medium transition ${
                  activePart === part
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-white text-muted-foreground hover:border-primary/50"
                }`}
              >
                {labels.part} {part}
              </button>
            ))}
          </div>
        ) : null}

        <div className="flex items-center gap-2">
          <span className="hidden shrink-0 text-xs font-medium text-muted-foreground sm:block">
            {labels.questionList}
          </span>
          <div className="flex flex-1 gap-1.5 overflow-x-auto py-1 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
            {visibleItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelect(item)}
                className={`relative flex h-8 min-w-8 shrink-0 items-center justify-center rounded-full border px-2 text-xs font-semibold transition ${
                  item.current
                    ? "scale-105 border-primary bg-primary text-primary-foreground shadow-sm ring-2 ring-primary/20"
                    : item.answered
                      ? "border-primary/20 bg-primary/10 text-primary hover:bg-primary/15"
                      : "border-[#CBD5E1] bg-white text-muted-foreground hover:border-primary/50"
                }`}
              >
                {item.label}
                {(item.bookmarked || item.hasNote || item.hasHighlight) && (
                  <span className="absolute -right-0.5 -top-0.5 flex gap-0.5">
                    {item.bookmarked ? <StatusDot className="bg-yellow-500" /> : null}
                    {item.hasNote ? <StatusDot className="bg-violet-500" /> : null}
                    {item.hasHighlight ? <StatusDot className="bg-orange-500" /> : null}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <StatusDot className="bg-primary" />
            {labels.answered}
          </span>
          <span className="flex items-center gap-1">
            <StatusDot className="bg-yellow-500" />
            {labels.marked}
          </span>
          <span className="flex items-center gap-1">
            <StatusDot className="bg-violet-500" />
            {labels.notes}
          </span>
          <span className="flex items-center gap-1">
            <StatusDot className="bg-orange-500" />
            {labels.highlights}
          </span>
        </div>
      </div>
    </div>
  );
}
