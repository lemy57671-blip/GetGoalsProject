"use client";

import { FormEvent, KeyboardEvent, ReactNode, useEffect, useMemo, useRef } from "react";
import { Brain, Loader2, Send, Sparkles } from "lucide-react";

type ChatRole = "assistant" | "user";

export type ChatPanelMessage = {
  role: ChatRole;
  content: string;
};

type ChatPanelProps = {
  title: string;
  description?: string;
  messages: ChatPanelMessage[];
  value: string;
  onValueChange: (value: string) => void;
  onSend: () => void;
  loading?: boolean;
  placeholder?: string;
  className?: string;
  messageListClassName?: string;
  composerMode?: "input" | "textarea";
  icon?: ReactNode;
};

function cleanText(value: string) {
  return value
    .replace(/\*\*/g, "")
    .replace(/^[`]+|[`]+$/g, "")
    .replace(/\r\n/g, "\n")
    .trim();
}

function useRenderedBlocks(content: string) {
  return useMemo(() => {
    const cleaned = cleanText(content);
    if (!cleaned) return [];
    return cleaned
      .split(/\n{2,}/)
      .map((block) => block.trim())
      .filter(Boolean);
  }, [content]);
}

function AssistantContent({ content }: { content: string }) {
  const blocks = useRenderedBlocks(content);

  return (
    <div className="space-y-2.5 whitespace-pre-wrap break-words">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
        const listLines = lines.filter((line) => /^[-•]\s+/.test(line));
        const optionLines = lines.filter((line) => /^[A-D]\.\s+/i.test(line));

        if (listLines.length === lines.length && lines.length > 0) {
          return (
            <ul key={blockIndex} className="space-y-1 pl-4">
              {lines.map((line, index) => (
                <li key={index} className="list-disc break-words leading-relaxed">
                  {line.replace(/^[-•]\s+/, "")}
                </li>
              ))}
            </ul>
          );
        }

        if (optionLines.length === lines.length && lines.length > 1) {
          return (
            <div key={blockIndex} className="space-y-1.5">
              {lines.map((line, index) => {
                const [label, ...rest] = line.split(".");
                return (
                  <div key={index} className="break-words rounded-lg bg-background/80 px-3 py-2 leading-relaxed">
                    <span className="mr-1 font-semibold text-primary">{label}.</span>
                    <span>{rest.join(".").trim()}</span>
                  </div>
                );
              })}
            </div>
          );
        }

        if (lines.length > 1) {
          return (
            <div key={blockIndex} className="space-y-1.5">
              {lines.map((line, index) => (
                <p key={index} className="break-words leading-relaxed">
                  {line}
                </p>
              ))}
            </div>
          );
        }

        return (
          <p key={blockIndex} className="break-words leading-relaxed">
            {block}
          </p>
        );
      })}
    </div>
  );
}

export function ChatMessageBubble({ message }: { message: ChatPanelMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[88%] overflow-hidden rounded-2xl px-3.5 py-2.5 text-sm shadow-sm ${
          isUser
            ? "rounded-br-md bg-primary text-primary-foreground"
            : "rounded-bl-md border border-[#DDE7F7] bg-[#F5F8FE] text-foreground"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words leading-relaxed">{cleanText(message.content)}</p>
        ) : (
          <AssistantContent content={message.content} />
        )}
      </div>
    </div>
  );
}

export function ChatMessageList({
  messages,
  loading,
  className,
}: {
  messages: ChatPanelMessage[];
  loading?: boolean;
  className?: string;
}) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const element = scrollRef.current;
    if (element) {
      element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
    }
  }, [messages, loading]);

  return (
    <div
      ref={scrollRef}
      className={`min-h-0 flex-1 overflow-y-auto rounded-xl border border-[#DDE7F7] bg-white p-3 ${className || ""}`}
    >
      <div className="space-y-3">
        {messages.map((message, index) => (
          <ChatMessageBubble key={`${message.role}-${index}`} message={message} />
        ))}
        {loading ? (
          <div className="flex justify-start">
            <div className="flex max-w-[88%] items-center gap-2 rounded-2xl rounded-bl-md border border-[#DDE7F7] bg-[#F5F8FE] px-3.5 py-2.5 text-sm text-muted-foreground shadow-sm">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              AI Tutor đang trả lời...
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function ChatComposer({
  value,
  onValueChange,
  onSend,
  loading,
  placeholder,
  mode = "input",
}: {
  value: string;
  onValueChange: (value: string) => void;
  onSend: () => void;
  loading?: boolean;
  placeholder?: string;
  mode?: "input" | "textarea";
}) {
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSend();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (mode === "input" || !event.shiftKey)) {
      event.preventDefault();
      onSend();
    }
  };

  const controlClass =
    "min-w-0 flex-1 border-0 bg-transparent text-sm leading-relaxed outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-70";

  return (
    <form onSubmit={submit} className="flex items-end gap-2 rounded-xl border border-[#D7E3F8] bg-white px-3 py-2 shadow-sm">
      {mode === "textarea" ? (
        <textarea
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={loading}
          rows={2}
          className={`${controlClass} max-h-28 resize-none`}
        />
      ) : (
        <input
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={loading}
          className={controlClass}
        />
      )}

      <button
        type="submit"
        disabled={loading || !value.trim()}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label="Gửi câu hỏi"
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
      </button>
    </form>
  );
}

export function ChatPanel({
  title,
  description,
  messages,
  value,
  onValueChange,
  onSend,
  loading,
  placeholder = "Nhập câu hỏi...",
  className,
  messageListClassName,
  composerMode = "input",
  icon,
}: ChatPanelProps) {
  return (
    <div className={`flex min-h-0 flex-col ${className || ""}`}>
      <div className="mb-3 flex items-start gap-2">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon || <Brain className="h-4 w-4" />}
        </div>
        <div className="min-w-0">
          <h3 className="text-base font-semibold leading-tight text-foreground">{title}</h3>
          {description ? <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p> : null}
        </div>
      </div>

      <ChatMessageList messages={messages} loading={loading} className={messageListClassName} />

      <div className="mt-3">
        <ChatComposer
          value={value}
          onValueChange={onValueChange}
          onSend={onSend}
          loading={loading}
          placeholder={placeholder}
          mode={composerMode}
        />
      </div>
    </div>
  );
}

export function AssistantMark() {
  return <Sparkles className="h-4 w-4" />;
}
