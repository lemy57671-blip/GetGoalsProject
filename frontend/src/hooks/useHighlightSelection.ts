"use client";

import { useCallback, useState } from "react";

export type HighlightSelectionTarget = "question" | "option" | "passage" | "explanation";

export type HighlightSelection = {
  selectedText: string;
  targetType: HighlightSelectionTarget;
  targetKey?: string | null;
  startOffset?: number | null;
  endOffset?: number | null;
};

function normalizeTargetType(value?: string): HighlightSelectionTarget {
  if (value === "option" || value === "passage" || value === "explanation") {
    return value;
  }
  return "question";
}

function getSelectionElement(node: Node): HTMLElement | null {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.parentElement;
  }
  return node instanceof HTMLElement ? node : null;
}

export function useHighlightSelection() {
  const [selection, setSelection] = useState<HighlightSelection | null>(null);

  const captureSelection = useCallback(() => {
    const browserSelection = window.getSelection();
    if (!browserSelection || browserSelection.rangeCount === 0) {
      return null;
    }

    const selectedText = browserSelection.toString().trim();
    if (!selectedText) {
      return null;
    }

    const range = browserSelection.getRangeAt(0);
    const element = getSelectionElement(range.commonAncestorContainer);
    const target = element?.closest("[data-highlight-target]") as HTMLElement | null;
    if (!target || !target.closest("[data-highlight-root]")) {
      return null;
    }

    const nextSelection: HighlightSelection = {
      selectedText,
      targetType: normalizeTargetType(target.dataset.highlightTarget),
      targetKey: target.dataset.highlightKey || null,
      startOffset: range.startOffset,
      endOffset: range.endOffset,
    };

    setSelection(nextSelection);
    return nextSelection;
  }, []);

  const clearSelection = useCallback(() => {
    setSelection(null);
    window.getSelection()?.removeAllRanges();
  }, []);

  return {
    selection,
    captureSelection,
    clearSelection,
    hasSelection: Boolean(selection?.selectedText.trim()),
  };
}
