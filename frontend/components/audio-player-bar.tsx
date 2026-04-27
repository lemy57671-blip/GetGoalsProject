"use client";

import { useMemo, useState } from "react";
import { Pause, Play, VolumeX } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";

type AudioPlayerBarProps = {
  className?: string;
  currentTimeSeconds?: number;
  durationSeconds?: number;
  initialProgress?: number;
  initialPlaying?: boolean;
  speedLabel?: string;
  src?: string;
};

const formatTime = (totalSeconds: number) => {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;

  return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
};

export function AudioPlayerBar({
  className,
  currentTimeSeconds = 0,
  durationSeconds = 18,
  initialProgress,
  initialPlaying = false,
  speedLabel = "1x",
  src,
}: AudioPlayerBarProps) {
  const safeDuration = Math.max(durationSeconds, 1);

  const startingProgress = useMemo(() => {
    if (typeof initialProgress === "number") {
      return Math.min(100, Math.max(0, initialProgress));
    }

    return Math.min(
      100,
      Math.max(0, (currentTimeSeconds / safeDuration) * 100),
    );
  }, [currentTimeSeconds, initialProgress, safeDuration]);

  const [isPlaying, setIsPlaying] = useState(initialPlaying);
  const [progress, setProgress] = useState(startingProgress);

  if (src) {
    return (
      <div
        className={cn(
          "rounded-[24px] border border-[#e5eaf4] bg-[#f5f9ff] p-3 shadow-[0_10px_28px_rgba(37,99,235,0.08)]",
          className,
        )}
      >
        <audio controls src={src} className="w-full">
          Your browser does not support the audio element.
        </audio>
      </div>
    );
  }

  const displayedCurrentTime = Math.round((progress / 100) * safeDuration);

  return (
    <div
      className={cn(
        "flex w-full flex-wrap items-center gap-3 rounded-[32px] border border-[#e5eaf4] bg-[#f5f9ff] px-4 py-3 shadow-[0_10px_28px_rgba(37,99,235,0.08)]",
        className,
      )}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={() => setIsPlaying((prev) => !prev)}
        className="size-11 shrink-0 rounded-full border border-[#e8eefc] bg-white text-[#2563eb] shadow-[0_4px_12px_rgba(37,99,235,0.18)] hover:bg-white hover:text-[#1d4ed8]"
      >
        {isPlaying ? (
          <Pause className="size-5 fill-current" />
        ) : (
          <Play className="size-5 fill-current" />
        )}
      </Button>

      <span className="min-w-fit text-sm font-medium tracking-tight text-[#1e3a8a]">
        {formatTime(displayedCurrentTime)} / {formatTime(safeDuration)}
      </span>

      <div className="min-w-[180px] flex-1 px-1">
        <Slider
          value={[progress]}
          max={100}
          step={1}
          onValueChange={([value]) => setProgress(value)}
          className="[&_[data-slot=slider-track]]:h-2 [&_[data-slot=slider-track]]:bg-[#d9e2f2] [&_[data-slot=slider-range]]:bg-[#93c5fd]/70 [&_[data-slot=slider-thumb]]:size-5 [&_[data-slot=slider-thumb]]:border-[5px] [&_[data-slot=slider-thumb]]:border-[#2563eb] [&_[data-slot=slider-thumb]]:bg-[#2563eb] [&_[data-slot=slider-thumb]]:shadow-none [&_[data-slot=slider-thumb]]:hover:ring-0 [&_[data-slot=slider-thumb]]:focus-visible:ring-0"
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <span className="inline-flex h-8 items-center rounded-full bg-white px-3 text-xs font-semibold text-[#2563eb] shadow-[0_2px_8px_rgba(37,99,235,0.10)]">
          {speedLabel}
        </span>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-8 shrink-0 rounded-full text-[#2563eb] hover:bg-white/90 hover:text-[#1d4ed8]"
        >
          <VolumeX className="size-4" />
        </Button>
      </div>
    </div>
  );
}
