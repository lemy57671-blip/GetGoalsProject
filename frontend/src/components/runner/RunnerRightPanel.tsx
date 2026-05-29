"use client";

import { useEffect, useRef } from "react";
import { BookOpen, Brain, CheckCircle2 } from "lucide-react";

import { ProFeatureGuard } from "@/components/pro-feature-guard";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ChatPanel } from "@src/components/chat/ChatPanel";

export type RunnerRightPanelTab = "notes" | "ai";

type RunnerRightPanelMessage = {
  role: "user" | "assistant";
  content: string;
};

type RunnerRightPanelProps = {
  activeTab: RunnerRightPanelTab;
  onTabChange: (tab: RunnerRightPanelTab) => void;
  labels: {
    notes: string;
    aiTutor: string;
    notesForQuestion: string;
    saveNote: string;
    saved: string;
    notePlaceholder: string;
    noQuestionSelected: string;
    askAiTutor: string;
    typeYourQuestion: string;
    loading: string;
  };
  noteValue: string;
  onNoteChange: (value: string) => void;
  onSaveNote: () => void;
  noteSaving?: boolean;
  noteSaved?: boolean;
  noteError?: string | null;
  noteDisabled?: boolean;
  messages: RunnerRightPanelMessage[];
  tutorValue: string;
  onTutorValueChange: (value: string) => void;
  onTutorSend: () => void;
  tutorLoading?: boolean;
};

export function RunnerRightPanel({
  activeTab,
  onTabChange,
  labels,
  noteValue,
  onNoteChange,
  onSaveNote,
  noteSaving,
  noteSaved,
  noteError,
  noteDisabled,
  messages,
  tutorValue,
  onTutorValueChange,
  onTutorSend,
  tutorLoading,
}: RunnerRightPanelProps) {
  const noteRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (activeTab === "notes") {
      window.setTimeout(() => noteRef.current?.focus(), 0);
    }
  }, [activeTab]);

  const tabClass = (tab: RunnerRightPanelTab) =>
    `flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${
      activeTab === tab
        ? "bg-white text-primary shadow-sm"
        : "text-muted-foreground hover:bg-white/70 hover:text-foreground"
    }`;

  return (
    <aside className="relative overflow-hidden rounded-xl border border-[#DDE7F7] bg-[#F7FAFF] shadow-sm">
      <div className="border-b border-[#DDE7F7] p-3">
        <div className="flex rounded-xl bg-[#EAF2FF] p-1">
          <button type="button" className={tabClass("notes")} onClick={() => onTabChange("notes")}>
            <BookOpen className="h-4 w-4" />
            {labels.notes}
          </button>
          <button type="button" className={tabClass("ai")} onClick={() => onTabChange("ai")}>
            <Brain className="h-4 w-4" />
            {labels.aiTutor}
          </button>
        </div>
      </div>

      <div className="min-h-[430px] p-4">
        {activeTab === "notes" ? (
          <div className="flex h-full min-h-[400px] flex-col">
            <div className="mb-3 flex items-start gap-2">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <BookOpen className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <h3 className="text-base font-semibold leading-tight text-foreground">
                  {labels.notesForQuestion}
                </h3>
                {noteDisabled ? (
                  <p className="mt-1 text-xs text-muted-foreground">{labels.noQuestionSelected}</p>
                ) : null}
              </div>
            </div>

            <Textarea
              ref={noteRef}
              value={noteValue}
              onChange={(event) => onNoteChange(event.target.value)}
              placeholder={labels.notePlaceholder}
              disabled={noteDisabled || noteSaving}
              className="min-h-[220px] flex-1 resize-none bg-white text-sm leading-relaxed"
            />

            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <Button
                type="button"
                size="sm"
                onClick={onSaveNote}
                disabled={noteDisabled || noteSaving || !noteValue.trim()}
              >
                {noteSaving ? labels.loading : labels.saveNote}
              </Button>

              {noteSaved ? (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {labels.saved}
                </span>
              ) : null}
            </div>

            {noteError ? <p className="mt-3 text-xs text-destructive">{noteError}</p> : null}
          </div>
        ) : (
          <ProFeatureGuard
            feature="aiChatUnlimited"
            compact
            title={labels.aiTutor}
            description={labels.askAiTutor}
          >
            <ChatPanel
              title={labels.askAiTutor}
              description={labels.typeYourQuestion}
              messages={messages}
              value={tutorValue}
              onValueChange={onTutorValueChange}
              onSend={onTutorSend}
              loading={tutorLoading}
              placeholder={labels.typeYourQuestion}
              className="h-[410px]"
            />
          </ProFeatureGuard>
        )}
      </div>
    </aside>
  );
}
