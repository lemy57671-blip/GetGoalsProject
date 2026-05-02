"use client";

import { useEffect, useRef } from "react";
import { BookOpen, CheckCircle2, Highlighter } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type RunnerNotebookHighlight = {
  id: number;
  selectedText: string;
};

type RunnerNotebookPanelProps = {
  noteValue: string;
  onNoteChange: (value: string) => void;
  onSaveNote: () => void;
  highlights?: RunnerNotebookHighlight[];
  focusKey?: number;
  saving?: boolean;
  saved?: boolean;
  disabled?: boolean;
  error?: string | null;
  labels: {
    notebook: string;
    notesForQuestion: string;
    saveNote: string;
    saved: string;
    notePlaceholder: string;
    noQuestionSelected: string;
    loading: string;
    highlights: string;
  };
};

export function RunnerNotebookPanel({
  noteValue,
  onNoteChange,
  onSaveNote,
  highlights = [],
  focusKey,
  saving,
  saved,
  disabled,
  error,
  labels,
}: RunnerNotebookPanelProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (focusKey !== undefined) {
      textareaRef.current?.focus();
    }
  }, [focusKey]);

  return (
    <Card className="rounded-2xl border-[#DDE7F7] bg-white shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base text-foreground">
          <BookOpen className="h-4 w-4 text-primary" />
          {labels.notebook}
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          {disabled ? labels.noQuestionSelected : labels.notesForQuestion}
        </p>
      </CardHeader>

      <CardContent className="space-y-3">
        <Textarea
          ref={textareaRef}
          value={noteValue}
          onChange={(event) => onNoteChange(event.target.value)}
          placeholder={labels.notePlaceholder}
          disabled={disabled || saving}
          className="min-h-[116px] resize-none bg-[#F8FBFF] text-sm leading-relaxed"
        />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <Button
            type="button"
            size="sm"
            onClick={onSaveNote}
            disabled={disabled || saving || !noteValue.trim()}
          >
            {saving ? labels.loading : labels.saveNote}
          </Button>

          {saved ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {labels.saved}
            </span>
          ) : null}
        </div>

        {error ? <p className="text-xs text-destructive">{error}</p> : null}

        {highlights.length > 0 ? (
          <div className="space-y-2 border-t border-[#E6EDF8] pt-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <Highlighter className="h-3.5 w-3.5 text-amber-600" />
              {labels.highlights}
            </div>
            <div className="max-h-24 space-y-1.5 overflow-y-auto pr-1">
              {highlights.slice(0, 4).map((highlight) => (
                <div
                  key={highlight.id}
                  className="rounded-lg bg-yellow-50 px-3 py-2 text-xs leading-relaxed text-yellow-900"
                >
                  {highlight.selectedText}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
