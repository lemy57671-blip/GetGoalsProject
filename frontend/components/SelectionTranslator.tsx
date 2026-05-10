import React, { useState, useEffect, useRef } from "react";
import { Languages, X, Loader2, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiRequest, API_BASE_URL } from "@src/services/apiClient";
import { useLocation } from "react-router-dom";
import { useLanguage } from "@src/contexts/LanguageContext";

export function SelectionTranslator() {
  const location = useLocation();
  const { t } = useLanguage();
  const isPracticePage = location.pathname.startsWith("/practice");
  const [selection, setSelection] = useState<{ text: string; x: number; y: number } | null>(null);
  const [translation, setTranslation] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseUp = (e: MouseEvent) => {
      // Chỉ hoạt động trên trang Practice
      if (!isPracticePage) return;

      // Đợi một chút để browser cập nhật selection
      setTimeout(() => {
        const selectionObj = window.getSelection();
        const selectedText = selectionObj?.toString().trim();
        
        if (selectedText && selectedText.length > 0) {
          // Chỉ hiện nếu bôi đen từ 2 ký tự trở lên
          if (selectedText.length < 2) return;

          // Lấy tọa độ chính xác của đoạn văn bản được bôi đen
          const range = selectionObj?.getRangeAt(0);
          const rect = range?.getBoundingClientRect();

          if (rect) {
            // Nếu bôi đen từ mới khác từ đang hiện, xóa bản dịch cũ
            if (selectedText !== selection?.text) {
              setTranslation(null);
            }

            setSelection({
              text: selectedText,
              x: rect.left + window.scrollX,
              y: rect.bottom + window.scrollY,
            });
            setIsPopupOpen(true);
          }
        } else if (isPopupOpen && popupRef.current && !popupRef.current.contains(e.target as Node)) {
          // Click ra ngoài thì đóng
          closePopup();
        }
      }, 10);
    };

    document.addEventListener("mouseup", handleMouseUp);
    return () => document.removeEventListener("mouseup", handleMouseUp);
  }, [isPopupOpen, selection, isPracticePage]);

  // Tự động dịch khi có text mới
  useEffect(() => {
    if (isPracticePage && selection?.text && isPopupOpen && !translation && !isLoading) {
      handleTranslate();
    }
  }, [selection?.text, isPopupOpen, isPracticePage]);

  const closePopup = () => {
    setIsPopupOpen(false);
    setSelection(null);
    setTranslation(null);
    setIsLoading(false);
    setCopied(false);
  };

  const handleTranslate = async () => {
    if (!selection?.text) return;
    
    setIsLoading(true);
    setTranslation(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: selection.text }),
      });
      
      if (!response.ok) throw new Error("Translation failed");
      const data = await response.json();
      setTranslation(data.translated_text);
    } catch (error) {
      console.error("Translation error:", error);
      setTranslation("Lỗi dịch thuật. Vui lòng thử lại sau.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    if (translation) {
      navigator.clipboard.writeText(translation);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!isPopupOpen || !selection) return null;

  return (
    <div 
      ref={popupRef}
      className="absolute z-[9999] animate-in fade-in zoom-in duration-200"
      style={{ 
        left: `${Math.min(selection.x, window.innerWidth - 320)}px`, 
        top: `${selection.y + 10}px` 
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="bg-card border border-border shadow-2xl rounded-2xl overflow-hidden w-[300px] flex flex-col">
        {/* Header */}
        <div className="bg-muted/50 px-4 py-2 flex items-center justify-between border-b border-border">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <Languages className="w-3.5 h-3.5" />
            {t("selection.quickLookupTitle")}
          </div>
          <button 
            onClick={closePopup}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          <div className="text-sm text-muted-foreground italic line-clamp-3 bg-muted/20 p-2 rounded-lg border border-border/40">
            "{selection.text}"
          </div>

          {!translation && !isLoading && (
            <Button 
              size="sm" 
              className="w-full rounded-xl font-bold"
              onClick={handleTranslate}
            >
              Dịch sang Tiếng Việt
            </Button>
          )}

          {isLoading && (
            <div className="flex flex-col items-center justify-center py-4 space-y-2">
              <Loader2 className="w-6 h-6 text-primary animate-spin" />
              <p className="text-xs text-muted-foreground animate-pulse">Đang dịch bằng AI...</p>
            </div>
          )}

          {translation && (
            <div className="space-y-2 animate-in slide-in-from-top-2 duration-300">
              <div className="text-sm font-medium leading-relaxed bg-primary/5 p-3 rounded-xl border border-primary/10">
                {translation}
              </div>
              <div className="flex justify-end">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-8 px-2 text-xs text-muted-foreground hover:text-primary rounded-lg"
                  onClick={handleCopy}
                >
                  {copied ? (
                    <><Check className="w-3 h-3 mr-1" /> Đã chép</>
                  ) : (
                    <><Copy className="w-3 h-3 mr-1" /> Sao chép</>
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
