/**
============================================================================
  TRANG THẺ GHI NHỚ - FLASHCARDS (FlashcardPage.tsx)
============================================================================
  Tệp này quản lý toàn bộ tính năng học từ vựng qua thẻ Flashcard.
  Nhiệm vụ chính:
  1. Tải danh sách các chủ đề từ vựng từ Backend.
  2. Hiển thị Menu chọn chủ đề với giao diện Card bắt mắt.
  3. Xử lý logic học tập: Lật thẻ (Flip), Chuyển thẻ (Next/Prev), Đánh dấu thuộc từ.
  4. Tạo hiệu ứng thị giác 3D bằng CSS Perspective.
  5. Theo dõi tiến độ hoàn thành bộ thẻ và hiển thị màn hình chúc mừng.
============================================================================
*/
"use client";

import { useState, useEffect, useRef } from "react";
import { 
  BookOpen, 
  ChevronLeft, 
  ChevronRight, 
  RotateCcw, 
  CheckCircle2, 
  Trophy,
  ArrowLeft,
  Loader2,
  Shuffle,
  Hash,
  Play,
  Volume2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiRequest, API_BASE_URL } from "@src/services/apiClient";

// Định nghĩa kiểu dữ liệu cho Chủ đề
export type FlashcardTopic = {
  id: number;
  code: string;
  title: string;
  description: string;
  icon?: string;
  color?: string;
};

// Định nghĩa kiểu dữ liệu cho Thẻ từ vựng
export type Flashcard = {
  id: number;
  word: string;
  pos: string;      // Loại từ: noun, verb, adj...
  phonetic: string; // Phiên âm
  meaning: string;  // Nghĩa tiếng Việt
  example?: string; // Ví dụ minh họa
};

export function FlashcardPage() {
  // --- QUẢN LÝ TRẠNG THÁI (STATE) ---
  const [topics, setTopics] = useState<FlashcardTopic[]>([]); // Danh sách chủ đề
  const [loadingTopics, setLoadingTopics] = useState(true);   // Trạng thái tải chủ đề
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null); // Chủ đề đang chọn
  
  const [allCards, setAllCards] = useState<Flashcard[]>([]);  // Toàn bộ thẻ trong chủ đề
  const [cards, setCards] = useState<Flashcard[]>([]);        // Danh sách thẻ thực tế đang học (sau khi random/limit)
  const [loadingCards, setLoadingCards] = useState(false);    // Trạng thái tải thẻ
  const [isConfiguring, setIsConfiguring] = useState(false);  // Đang ở màn hình cấu hình
  
  // Cấu hình học tập
  const [isRandom, setIsRandom] = useState(false);
  const [wordLimit, setWordLimit] = useState<number>(0);      // 0 nghĩa là học tất cả
  const [isAutoPlay, setIsAutoPlay] = useState(true);         // Tự động phát âm thanh
  
  const [currentIndex, setCurrentIndex] = useState(0);        // Vị trí thẻ hiện tại
  const [isFlipped, setIsFlipped] = useState(false);         // Thẻ đang lật hay không
  const [learnedCount, setLearnedCount] = useState(0);        // Số từ đã thuộc
  const [isFinished, setIsFinished] = useState(false);        // Đã xong bộ thẻ chưa
  const [isStarted, setIsStarted] = useState(false);          // Đã bắt đầu học chưa
  const [ttsMessage, setTtsMessage] = useState<string | null>(null);
  const [speakingWord, setSpeakingWord] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const activeObjectUrlRef = useRef<string | null>(null);
  const audioRequestIdRef = useRef(0);
  const audioUrlCacheRef = useRef<Map<string, { url: string; source: string }>>(new Map());
  const speechUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const resolveAudioUrl = (value: string) => {
    if (/^(https?:|blob:|data:)/i.test(value)) return value;
    return `${API_BASE_URL}${value.startsWith("/") ? value : `/${value}`}`;
  };

  const stopCurrentAudio = () => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      speechUtteranceRef.current = null;
    }
    const currentAudio = audioRef.current;
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.onended = null;
      currentAudio.onerror = null;
      currentAudio.oncanplaythrough = null;
      currentAudio.removeAttribute("src");
      currentAudio.load();
      audioRef.current = null;
    }
    if (activeObjectUrlRef.current) {
      URL.revokeObjectURL(activeObjectUrlRef.current);
      activeObjectUrlRef.current = null;
    }
  };

  const parseTtsError = async (response: Response) => {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      try {
        const payload = await response.json();
        const detail = payload?.detail;
        if (detail && typeof detail === "object") {
          return String(detail.provider_error || detail.message || payload?.message || `TTS failed with status ${response.status}`);
        }
        return String(detail || payload?.message || `TTS failed with status ${response.status}`);
      } catch {
        return `TTS failed with status ${response.status}`;
      }
    }
    const text = await response.text().catch(() => "");
    return text || `TTS failed with status ${response.status}`;
  };

  const loadFlashcardAudioUrl = async (word: string) => {
    const cacheKey = word.trim().toLowerCase();
    const cached = audioUrlCacheRef.current.get(cacheKey);
    if (cached) return cached;

    const response = await fetch(`${API_BASE_URL}/api/tts/flashcard`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ word, text: word, voice: "en-US-AriaNeural" }),
    });

    if (!response.ok) {
      throw new Error(await parseTtsError(response));
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const payload = await response.json();
      const audioUrl = payload?.audio_url || payload?.audioUrl || payload?.url;
      if (!audioUrl) {
        throw new Error("TTS response did not include audio_url.");
      }
      const resolvedUrl = resolveAudioUrl(String(audioUrl));
      const result = {
        url: resolvedUrl,
        source: String(payload?.source || (payload?.cached ? "cache" : "generated")),
      };
      audioUrlCacheRef.current.set(cacheKey, result);
      return result;
    }

    const blob = await response.blob();
    if (!blob.size || !/^audio\//i.test(blob.type || "")) {
      throw new Error(`TTS response is not a usable audio file (${blob.type || "unknown"}).`);
    }
    return { url: URL.createObjectURL(blob), source: "generated" };
  };

  const speakWithBrowserFallback = (word: string, requestId: number, reason?: unknown) => {
    if (requestId !== audioRequestIdRef.current) return false;
    if (typeof window === "undefined" || !("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
      console.error("Flashcard TTS source=failed", { word, reason });
      return false;
    }

    stopCurrentAudio();
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = "en-US";
    utterance.rate = 0.9;
    utterance.pitch = 1;
    speechUtteranceRef.current = utterance;

    utterance.onend = () => {
      if (requestId === audioRequestIdRef.current && speechUtteranceRef.current === utterance) {
        speechUtteranceRef.current = null;
        setSpeakingWord(null);
      }
    };
    utterance.onerror = (event) => {
      if (requestId === audioRequestIdRef.current && speechUtteranceRef.current === utterance) {
        console.error("Flashcard TTS source=failed", { word, reason, speechError: event.error });
        speechUtteranceRef.current = null;
        setSpeakingWord(null);
        setTtsMessage("Không phát được âm thanh cho từ này.");
      }
    };

    console.info("Flashcard TTS source=browser_fallback", { word, reason });
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    return true;
  };

  /**
   * HÀM ĐỌC TỪ VỰNG
   */
  const speakWord = async (word: string) => {
    const normalizedWord = word.trim();
    if (!normalizedWord) return;

    const requestId = ++audioRequestIdRef.current;
    stopCurrentAudio();
    setSpeakingWord(normalizedWord);
    setTtsMessage(null);

    try {
      const audioResult = await loadFlashcardAudioUrl(normalizedWord);
      if (requestId !== audioRequestIdRef.current) {
        if (audioResult.url.startsWith("blob:")) URL.revokeObjectURL(audioResult.url);
        return;
      }

      const audio = new Audio();
      audio.preload = "auto";
      audio.src = audioResult.url;
      audioRef.current = audio;
      if (audioResult.url.startsWith("blob:")) {
        activeObjectUrlRef.current = audioResult.url;
      }

      await new Promise<void>((resolve, reject) => {
        const timeout = window.setTimeout(() => resolve(), 2500);
        audio.oncanplaythrough = () => {
          window.clearTimeout(timeout);
          resolve();
        };
        audio.onerror = () => {
          window.clearTimeout(timeout);
          reject(new Error("Không tải được file âm thanh."));
        };
        audio.load();
      });

      if (requestId !== audioRequestIdRef.current) {
        stopCurrentAudio();
        return;
      }

      audio.onended = () => {
        if (audioRef.current === audio) {
          stopCurrentAudio();
          setSpeakingWord(null);
        }
      };
      audio.onerror = () => {
        if (audioRef.current === audio) {
          console.error("Playback error: audio element failed to load", audioResult.url);
          if (!speakWithBrowserFallback(normalizedWord, requestId, "audio_element_error")) {
            setTtsMessage("Không phát được âm thanh cho từ này.");
            stopCurrentAudio();
            setSpeakingWord(null);
          }
        }
      };

      await audio.play();
      console.info("Flashcard TTS source=" + audioResult.source, { word: normalizedWord, url: audioResult.url });
    } catch (error) {
      console.error("TTS Error:", error);
      if (requestId === audioRequestIdRef.current) {
        if (!speakWithBrowserFallback(normalizedWord, requestId, error)) {
          setTtsMessage("Không phát được âm thanh cho từ này.");
          stopCurrentAudio();
          setSpeakingWord(null);
        }
      }
    }
  };

  useEffect(() => {
    return () => {
      audioRequestIdRef.current += 1;
      stopCurrentAudio();
    };
  }, []);

  /**
   * EFFECT: Tự động đọc khi chuyển thẻ
   */
  useEffect(() => {
    // Chỉ đọc khi: Đã bắt đầu, Không phải màn hình cấu hình, Chưa kết thúc, Và có bật AutoPlay
    if (isStarted && !isConfiguring && !isFinished && isAutoPlay && cards[currentIndex]) {
      // Đợi một chút để hiệu ứng chuyển thẻ mượt mà rồi mới đọc
      const timer = setTimeout(() => {
        speakWord(cards[currentIndex].word);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [currentIndex, isStarted, isAutoPlay, isConfiguring, isFinished]);

  /**
   * EFFECT: Tải danh sách chủ đề khi lần đầu vào trang
   */
  useEffect(() => {
    async function fetchTopics() {
      try {
        const data = await apiRequest<FlashcardTopic[]>("/api/flashcards/topics");
        setTopics(data);
      } catch (error) {
        console.error("Lỗi khi lấy danh sách chủ đề:", error);
      } finally {
        setLoadingTopics(false);
      }
    }
    fetchTopics();
  }, []);

  // Lấy thông tin chủ đề và thẻ hiện tại để hiển thị
  const currentTopic = topics.find(t => t.code === selectedTopicId);
  const currentCard = cards[currentIndex];

  /**
   * CHỌN CHỦ ĐỀ - TẢI DỮ LIỆU NHƯNG CHƯA HỌC NGAY
   */
  const handleSelectTopic = async (topicCode: string) => {
    audioRequestIdRef.current += 1;
    stopCurrentAudio();
    setTtsMessage(null);
    setSpeakingWord(null);
    setSelectedTopicId(topicCode);
    setLoadingCards(true);
    setIsConfiguring(true);
    setIsStarted(false);
    setIsFinished(false);

    try {
      const data = await apiRequest<Flashcard[]>(`/api/flashcards/topics/${topicCode}/cards`);
      setAllCards(data);
      setWordLimit(data.length); // Mặc định là học hết
    } catch (error) {
      console.error("Lỗi khi lấy danh sách thẻ từ:", error);
      setAllCards([]);
    } finally {
      setLoadingCards(false);
    }
  };

  /**
   * BẮT ĐẦU HỌC VỚI CẤU HÌNH ĐÃ CHỌN
   */
  const startLearning = () => {
    let finalCards = [...allCards];

    // 1. Xử lý Random
    if (isRandom) {
      finalCards.sort(() => Math.random() - 0.5);
    }

    // 2. Xử lý Giới hạn số từ
    if (wordLimit > 0 && wordLimit < finalCards.length) {
      finalCards = finalCards.slice(0, wordLimit);
    }

    setCards(finalCards);
    setCurrentIndex(0);
    setIsFlipped(false);
    setLearnedCount(0);
    setIsStarted(true);
    setIsConfiguring(false);
  };

  /** CHUYỂN SANG THẺ TIẾP THEO */
  const handleNext = () => {
    if (currentIndex < cards.length - 1) {
      setTtsMessage(null);
      setCurrentIndex(prev => prev + 1);
      setIsFlipped(false);
    } else {
      audioRequestIdRef.current += 1;
      stopCurrentAudio();
      setIsFinished(true);
    }
  };

  /** QUAY LẠI THẺ TRƯỚC */
  const handlePrev = () => {
    if (currentIndex > 0) {
      setTtsMessage(null);
      setCurrentIndex(prev => prev - 1);
      setIsFlipped(false);
    }
  };

  /** LẬT THẺ ĐỂ XEM NGHĨA */
  const handleFlip = () => {
    setIsFlipped(!isFlipped);
  };

  /** ĐÁNH DẤU THUỘC TỪ */
  const handleMarkAsLearned = () => {
    setLearnedCount(prev => prev + 1);
    handleNext();
  };

  /** QUAY LẠI DANH SÁCH CHỦ ĐỀ */
  const reset = () => {
    audioRequestIdRef.current += 1;
    stopCurrentAudio();
    setTtsMessage(null);
    setSpeakingWord(null);
    setSelectedTopicId(null);
    setAllCards([]);
    setCards([]);
    setCurrentIndex(0);
    setIsFlipped(false);
    setIsFinished(false);
    setIsConfiguring(false);
    setIsStarted(false);
  };

  // HIỂN THỊ LOADING KHI TẢI CHỦ ĐỀ
  if (loadingTopics) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
      </div>
    );
  }

  // --- GIAO DIỆN 1: CHỌN CHỦ ĐỀ ---
  if (!selectedTopicId) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tight">Thẻ từ vựng (Flashcards)</h1>
          <p className="text-muted-foreground">Chọn một chủ đề để bắt đầu ôn tập từ vựng.</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {topics.map((topic) => (
            <Card 
              key={topic.id} 
              className="group cursor-pointer overflow-hidden border-border transition-all hover:border-primary/50 hover:shadow-lg rounded-[24px]"
              onClick={() => handleSelectTopic(topic.code)}
            >
              <div className={`h-2 ${topic.color || 'bg-primary'}`} />
              
              <CardHeader className="flex flex-row items-center gap-4 space-y-0">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted text-2xl">
                  {topic.icon || '📚'}
                </div>
                <div className="flex-1">
                  <CardTitle className="text-xl group-hover:text-primary transition-colors">
                    {topic.title}
                  </CardTitle>
                </div>
              </CardHeader>
              
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2">
                  {topic.description}
                </p>
                <Button className="mt-4 w-full rounded-xl" variant="outline">
                  Bắt đầu học
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // HIỂN THỊ LOADING KHI TẢI THẺ
  if (loadingCards) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
      </div>
    );
  }

  // --- GIAO DIỆN 2: CẤU HÌNH HỌC TẬP ---
  if (isConfiguring) {
    return (
      <div className="max-w-md mx-auto space-y-8 animate-in zoom-in duration-300 pt-8">
        <div className="text-center space-y-2">
          <div className="mx-auto w-20 h-20 bg-primary/10 rounded-3xl flex items-center justify-center text-4xl mb-4">
            {currentTopic?.icon || '📚'}
          </div>
          <h2 className="text-3xl font-bold">{currentTopic?.title}</h2>
          <p className="text-muted-foreground">Tùy chỉnh trước khi bắt đầu</p>
        </div>

        <Card className="rounded-[32px] border-border/50 shadow-xl overflow-hidden">
          <CardContent className="p-8 space-y-8">
            {/* THÔNG TIN TỔNG QUAN */}
            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-2xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-background rounded-xl flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground font-medium uppercase">Tổng số từ</p>
                  <p className="text-lg font-bold">{allCards.length} từ vựng</p>
                </div>
              </div>
            </div>

            {/* CẤU HÌNH RANDOM */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="random-mode" className="text-base font-semibold flex items-center gap-2">
                  <Shuffle className="w-4 h-4 text-primary" /> Trình tự ngẫu nhiên
                </Label>
                <p className="text-xs text-muted-foreground">Xáo trộn thứ tự các thẻ</p>
              </div>
              <Switch 
                id="random-mode" 
                checked={isRandom} 
                onCheckedChange={setIsRandom}
              />
            </div>

            {/* CẤU HÌNH AUTO PLAY */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="auto-play" className="text-base font-semibold flex items-center gap-2">
                  <Volume2 className="w-4 h-4 text-primary" /> Tự động phát âm thanh
                </Label>
                <p className="text-xs text-muted-foreground">Phát âm khi chuyển sang thẻ mới</p>
              </div>
              <Switch 
                id="auto-play" 
                checked={isAutoPlay} 
                onCheckedChange={setIsAutoPlay}
              />
            </div>

            {/* CẤU HÌNH GIỚI HẠN */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="word-limit" className="text-base font-semibold flex items-center gap-2">
                    <Hash className="w-4 h-4 text-primary" /> Số từ cần học
                  </Label>
                  <p className="text-xs text-muted-foreground">Chọn số lượng từ bạn muốn ôn</p>
                </div>
                <Badge variant="secondary" className="text-sm px-3 py-1 rounded-lg">
                  {wordLimit} từ
                </Badge>
              </div>
              
              <div className="grid grid-cols-5 gap-2">
                {[10, 20, 50, 100].map(val => (
                  <Button 
                    key={val}
                    variant={wordLimit === val ? "default" : "outline"}
                    className="rounded-xl h-10 text-xs"
                    disabled={val > allCards.length}
                    onClick={() => setWordLimit(val)}
                  >
                    {val}
                  </Button>
                ))}
                <Button 
                  variant={wordLimit === allCards.length ? "default" : "outline"}
                  className="rounded-xl h-10 text-xs"
                  onClick={() => setWordLimit(allCards.length)}
                >
                  Tất cả
                </Button>
              </div>
            </div>

            <div className="pt-4 flex gap-3">
              <Button onClick={reset} variant="ghost" className="rounded-2xl flex-1 h-12">
                Hủy
              </Button>
              <Button onClick={startLearning} className="rounded-2xl flex-[2] h-12 text-lg font-bold shadow-lg shadow-primary/20">
                <Play className="w-5 h-5 mr-2" /> Bắt đầu
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // --- GIAO DIỆN 3: HOÀN THÀNH BỘ THẺ ---
  if (isFinished) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center space-y-6 text-center animate-in zoom-in duration-500">
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-primary/10">
          <Trophy className="h-12 w-12 text-primary" />
        </div>
        <div className="space-y-2">
          <h2 className="text-3xl font-bold">Hoàn thành!</h2>
          <p className="text-muted-foreground max-w-xs">
            Bạn đã hoàn thành chủ đề <span className="font-semibold text-foreground">{currentTopic?.title}</span>.
          </p>
        </div>
        <div className="flex gap-4">
          <Button onClick={reset} variant="outline" className="rounded-xl">
            Quay lại chủ đề
          </Button>
          <Button onClick={() => handleSelectTopic(selectedTopicId!)} className="rounded-xl">
            <RotateCcw className="mr-2 h-4 w-4" /> Học lại
          </Button>
        </div>
      </div>
    );
  }

  // --- GIAO DIỆN 4: TRÌNH CHẠY FLASHCARD (RUNNER) ---
  const progress = ((currentIndex + 1) / cards.length) * 100;

  return (
    <div className="max-w-2xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-500">
      {/* HEADER CỦA TRÌNH CHẠY */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => setIsConfiguring(true)} className="rounded-xl hover:bg-muted">
          <ArrowLeft className="mr-2 h-4 w-4" /> Thoát
        </Button>
        <div className="text-center">
          <p className="text-sm font-medium text-muted-foreground">{currentTopic?.title}</p>
          <p className="text-xs text-muted-foreground uppercase tracking-widest mt-1">
            {currentIndex + 1} / {cards.length}
          </p>
        </div>
        <div className="w-24" />
      </div>

      {/* THANH TIẾN ĐỘ */}
      <Progress value={progress} className="h-2 rounded-full" />

      {/* THẺ 3D - HIỆU ỨNG LẬT CHÍNH */}
      <div 
        className="relative h-96 w-full cursor-pointer perspective-1000"
        onClick={handleFlip}
      >
        <div 
          className={`relative h-full w-full transition-transform duration-500 preserve-3d ${isFlipped ? 'rotate-y-180' : ''}`}
        >
          {/* MẶT TRƯỚC: TỪ TIẾNG ANH */}
          <div className="absolute inset-0 backface-hidden">
            <Card className="h-full flex flex-col items-center justify-center p-8 text-center border-2 border-primary/20 shadow-xl rounded-[32px]">
              <Badge variant="outline" className="absolute top-6 left-6 text-primary uppercase tracking-widest">
                {currentCard.pos}
              </Badge>
              <div className="flex flex-col items-center gap-4">
                <h2 className="text-5xl font-bold tracking-tight text-foreground">
                  {currentCard.word}
                </h2>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={(e) => { e.stopPropagation(); speakWord(currentCard.word); }}
                  className="rounded-full w-12 h-12 p-0 hover:bg-primary/10 group/vol"
                  disabled={speakingWord === currentCard.word}
                >
                  {speakingWord === currentCard.word ? (
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  ) : (
                    <Volume2 className="w-6 h-6 text-primary group-hover/vol:scale-125 transition-transform" />
                  )}
                </Button>
              </div>
              <p className="mt-4 text-xl text-muted-foreground font-mono italic">
                {currentCard.phonetic}
              </p>
              {ttsMessage ? (
                <p className="mt-3 text-sm text-destructive">{ttsMessage}</p>
              ) : null}
              <p className="mt-12 text-sm text-muted-foreground animate-pulse">
                Chạm để xem nghĩa
              </p>
            </Card>
          </div>

          {/* MẶT SAU: NGHĨA VÀ VÍ DỤ */}
          <div className="absolute inset-0 backface-hidden rotate-y-180">
            <Card className="h-full flex flex-col items-center justify-center p-8 text-center border-2 border-primary/20 bg-primary/5 shadow-xl rounded-[32px]">
              <div className="space-y-6">
                <div>
                  <p className="text-sm font-medium uppercase tracking-widest text-primary mb-2">Ý nghĩa</p>
                  <h3 className="text-3xl font-bold text-foreground">
                    {currentCard.meaning}
                  </h3>
                </div>
                
                {currentCard.example && (
                  <div className="pt-6 border-t border-primary/10">
                    <p className="text-sm font-medium uppercase tracking-widest text-primary mb-2">Ví dụ</p>
                    <p className="text-lg italic text-muted-foreground leading-relaxed">
                      "{currentCard.example}"
                    </p>
                  </div>
                )}
              </div>
              <p className="absolute bottom-6 text-sm text-muted-foreground">
                Chạm để quay lại
              </p>
            </Card>
          </div>
        </div>
      </div>

      {/* CÁC NÚT ĐIỀU KHIỂN */}
      <div className="flex items-center justify-between gap-4">
        <Button 
          variant="outline" 
          size="lg" 
          onClick={handlePrev}
          disabled={currentIndex === 0}
          className="rounded-2xl h-14 w-14 p-0"
        >
          <ChevronLeft className="h-6 w-6" />
        </Button>

        <Button 
          className="flex-1 h-14 rounded-2xl text-lg font-semibold bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/20"
          onClick={handleMarkAsLearned}
        >
          <CheckCircle2 className="mr-2 h-5 w-5" />
          Đã thuộc từ này
        </Button>

        <Button 
          variant="outline" 
          size="lg" 
          onClick={handleNext}
          className="rounded-2xl h-14 w-14 p-0"
        >
          <ChevronRight className="h-6 w-6" />
        </Button>
      </div>

      {/* CSS CHO HIỆU ỨNG 3D */}
      <style>{`
        .perspective-1000 {
          perspective: 1000px;
        }
        .preserve-3d {
          transform-style: preserve-3d;
        }
        .backface-hidden {
          backface-visibility: hidden;
        }
        .rotate-y-180 {
          transform: rotateY(180deg);
        }
      `}</style>
    </div>
  );
}
