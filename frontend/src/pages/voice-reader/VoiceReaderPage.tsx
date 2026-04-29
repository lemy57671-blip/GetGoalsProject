import { useState, useEffect, useRef } from "react";
import { 
  Volume2, 
  Loader2,
  History,
  PlayCircle,
  Trash2,
  ChevronRight,
  Headphones
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { apiRequest, API_BASE_URL } from "@src/services/apiClient";

type Voice = {
  id: string;
  name: string;
  lang: string;
  gender: string;
};

type Lookup = {
  text: string;
  voice: string;
  voiceId: string;
  timestamp: number;
};

export function VoiceReaderPage() {
  const [text, setText] = useState("");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState("en-US-AriaNeural");
  const [isLoadingVoices, setIsLoadingVoices] = useState(true);
  const [isReading, setIsReading] = useState(false);
  const [lookups, setLookups] = useState<Lookup[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    async function init() {
      try {
        const data = await apiRequest<{ voices: Voice[] }>("/api/tts/voices");
        setVoices(data.voices);
      } catch (error) {
        console.error("Failed to load voices:", error);
      } finally {
        setIsLoadingVoices(false);
      }

      const saved = localStorage.getItem("getgoals.voice_history");
      if (saved) {
        try {
          setLookups(JSON.parse(saved));
        } catch (e) {
          setLookups([]);
        }
      }
    }
    init();
  }, []);

  const saveToHistory = (newText: string, voiceId: string) => {
    const newLookup: Lookup = {
      text: newText,
      voice: voices.find(v => v.id === voiceId)?.name || voiceId,
      voiceId: voiceId,
      timestamp: Date.now()
    };
    const updated = [newLookup, ...lookups.filter(l => l.text !== newText)].slice(0, 10);
    setLookups(updated);
    localStorage.setItem("getgoals.voice_history", JSON.stringify(updated));
  };

  const handleRead = async (customText?: string, customVoice?: string) => {
    const textToRead = customText || text;
    const voiceToUse = customVoice || selectedVoice;
    if (!textToRead.trim()) return;
    
    setIsReading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/tts/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: textToRead.trim(), voice: voiceToUse })
      });

      if (!response.ok) throw new Error("TTS generation failed");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = url;
        audioRef.current.play();
      } else {
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.play();
      }
      
      audioRef.current!.onended = () => {
        setIsReading(false);
        URL.revokeObjectURL(url);
      };
      audioRef.current!.onerror = () => {
        setIsReading(false);
        URL.revokeObjectURL(url);
      };

      if (!customText) saveToHistory(textToRead.trim(), voiceToUse);
    } catch (error) {
      console.error("TTS Error:", error);
      setIsReading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12 animate-in fade-in duration-700">
      {/* HEADER SECTION */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center">
            <Headphones className="w-6 h-6 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Voice Reader</h1>
        </div>
        <p className="text-muted-foreground">Type any word or sentence and hear it pronounced with a natural voice.</p>
      </div>

      {/* INPUT SECTION */}
      <div className="grid gap-6">
        <Card className="border-border/40 shadow-xl bg-card/50 backdrop-blur-md rounded-[32px] overflow-hidden">
          <CardContent className="p-0">
            {/* TEXTAREA AREA */}
            <div className="p-6 pb-2">
              <Textarea 
                placeholder="Type a word or sentence... (e.g., 'The meeting starts at 9 AM')"
                className="min-h-[180px] w-full p-4 text-xl leading-relaxed border-0 focus-visible:ring-0 bg-transparent resize-none placeholder:text-muted-foreground/20"
                value={text}
                onChange={(e) => setText(e.target.value)}
                maxLength={500}
              />
            </div>

            {/* VOICE SELECTION ROW */}
            <div className="px-6 py-4 border-t border-border/40 flex flex-col gap-3 bg-muted/5">
              <label className="text-sm font-bold text-muted-foreground">Voice Selection</label>
              <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                <SelectTrigger className="w-full h-12 rounded-xl bg-background border-border/40 shadow-sm text-lg">
                  <SelectValue placeholder="Select a voice" />
                </SelectTrigger>
                <SelectContent className="rounded-xl shadow-2xl">
                  {voices.map((v) => (
                    <SelectItem key={v.id} value={v.id} className="text-base py-3">{v.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* ACTION BAR (SPEAK BUTTON) */}
            <div className="px-6 py-4 border-t border-border/40 bg-muted/20 flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                <span className={text.length >= 500 ? "text-red-500 font-bold" : ""}>{text.length}</span> / 500
              </span>
              
              <Button 
                className="rounded-full px-12 h-14 text-lg font-bold shadow-2xl shadow-primary/30 bg-primary hover:bg-primary/90 transition-all hover:scale-105 active:scale-95"
                disabled={!text.trim() || isReading}
                onClick={() => handleRead()}
              >
                {isReading ? (
                  <Loader2 className="w-6 h-6 animate-spin" />
                ) : (
                  <>
                    <Volume2 className="w-6 h-6 mr-3" /> Speak
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* HISTORY SECTION */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <History className="w-5 h-5 text-primary" /> Recent Lookups
            </h3>
            {lookups.length > 0 && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => {setLookups([]); localStorage.removeItem("getgoals.voice_history");}} 
                className="text-muted-foreground hover:text-red-500 rounded-xl"
              >
                <Trash2 className="w-4 h-4 mr-2" /> Clear All
              </Button>
            )}
          </div>

          {lookups.length === 0 ? (
            <Card className="border-border/40 bg-card/20 rounded-[24px] border-dashed">
              <CardContent className="p-12 text-center">
                <div className="mx-auto w-12 h-12 bg-muted/50 rounded-full flex items-center justify-center mb-4">
                  <History className="w-6 h-6 text-muted-foreground/30" />
                </div>
                <p className="text-muted-foreground text-sm">Your lookup history will appear here</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-3">
              {lookups.map((lookup, i) => (
                <div 
                  key={i}
                  className="flex items-center justify-between p-4 rounded-2xl bg-card/40 border border-border/20 hover:border-primary/30 hover:bg-muted/30 transition-all cursor-pointer group"
                  onClick={() => {
                    setText(lookup.text);
                    setSelectedVoice(lookup.voiceId);
                    handleRead(lookup.text, lookup.voiceId);
                  }}
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-10 h-10 bg-background rounded-xl flex items-center justify-center shrink-0 shadow-sm group-hover:bg-primary/10 transition-colors">
                      <PlayCircle className="w-5 h-5 text-muted-foreground group-hover:text-primary" />
                    </div>
                    <div className="flex-1 min-w-0 pr-4">
                      <p className="font-medium text-foreground leading-snug break-words group-hover:text-primary transition-colors">
                        {lookup.text}
                      </p>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">{lookup.voice}</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground/20 group-hover:text-primary transition-colors" />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
