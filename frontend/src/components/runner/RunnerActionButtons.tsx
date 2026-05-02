"use client";

import { Flag, Highlighter, NotebookPen } from "lucide-react";

import { Button } from "@/components/ui/button";

type RunnerActionButtonsProps = {
  bookmarked?: boolean;
  hasNote?: boolean;
  hasHighlight?: boolean;
  canHighlight?: boolean;
  labels: {
    mark: string;
    marked: string;
    note: string;
    highlight: string;
    highlightHint: string;
  };
  onToggleBookmark: () => void;
  onOpenNote: () => void;
  onHighlight: () => void;
};

export function RunnerActionButtons({
  bookmarked,
  hasNote,
  hasHighlight,
  canHighlight,
  labels,
  onToggleBookmark,
  onOpenNote,
  onHighlight,
}: RunnerActionButtonsProps) {
  return (
    <div className="flex items-center gap-1.5">
      <Button
        type="button"
        variant={bookmarked ? "default" : "ghost"}
        size="icon"
        className="h-9 w-9"
        onClick={onToggleBookmark}
        title={bookmarked ? labels.marked : labels.mark}
        aria-label={bookmarked ? labels.marked : labels.mark}
      >
        <Flag className="h-4 w-4" fill={bookmarked ? "currentColor" : "none"} />
      </Button>

      <Button
        type="button"
        variant={hasNote ? "secondary" : "ghost"}
        size="icon"
        className="h-9 w-9"
        onClick={onOpenNote}
        title={labels.note}
        aria-label={labels.note}
      >
        <NotebookPen className="h-4 w-4" />
      </Button>

      <Button
        type="button"
        variant={hasHighlight ? "secondary" : "ghost"}
        size="icon"
        className="h-9 w-9"
        onMouseDown={(event) => {
          event.preventDefault();
        }}
        onClick={onHighlight}
        title={canHighlight ? labels.highlight : labels.highlightHint}
        aria-label={canHighlight ? labels.highlight : labels.highlightHint}
      >
        <Highlighter className="h-4 w-4" />
      </Button>
    </div>
  );
}
