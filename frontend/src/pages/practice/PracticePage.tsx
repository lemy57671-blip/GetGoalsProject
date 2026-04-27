"use client";

import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  BookOpen,
  Check,
  CircleDot,
  Headphones,
  Layers3,
  Play,
  Sparkles,
  Volume2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Difficulty,
  PracticeMode,
  SKILL_PACKS,
  SkillFilter,
  SkillPack,
  TOEIC_PARTS,
  ViewMode,
} from "@src/data/practice";
import {
  roadmapService,
  type RoadmapWeekSetsResponse,
} from "@src/services/roadmapService";
import {
  toeicService,
  ToeicPartItem,
  ToeicRecommendations,
} from "@src/services/toeicService";

type QuestionCountMode = "adaptive" | "30" | "60" | "100" | "200";

function parsePositiveInteger(value: string | null) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function getPartIdFromNumber(part: number) {
  return `part${part}`;
}

function getPartNumberFromId(partId: string) {
  const value = Number(partId.replace("part", ""));
  return Number.isFinite(value) ? value : 1;
}

function formatRoadmapLabel(value?: string | null) {
  if (!value) return "N/A";
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function PracticePage() {
  const [searchParams] = useSearchParams();
  const roadmapWeekId = parsePositiveInteger(searchParams.get("roadmapWeekId"));
  const [viewMode, setViewMode] = useState<ViewMode>("part");
  const [skillFilter, setSkillFilter] = useState<SkillFilter>("all");
  const [selectedParts, setSelectedParts] = useState<string[]>(["part1"]);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [practiceMode, setPracticeMode] = useState<PracticeMode>("exam");
  const [questionCountMode, setQuestionCountMode] =
    useState<QuestionCountMode>("adaptive");
  const [toeicParts, setToeicParts] = useState<ToeicPartItem[]>(
    TOEIC_PARTS.map((part) => ({
      ...part,
      number: Number(part.id.replace("part", "")),
      audioReady: false,
      testsAvailable: [],
    })),
  );
  const [recommendations, setRecommendations] =
    useState<ToeicRecommendations | null>(null);
  const [isLoadingToeic, setIsLoadingToeic] = useState(true);
  const [toeicError, setToeicError] = useState<string | null>(null);
  const [roadmapWeek, setRoadmapWeek] =
    useState<RoadmapWeekSetsResponse | null>(null);
  const [isLoadingRoadmapWeek, setIsLoadingRoadmapWeek] = useState(false);
  const [roadmapWeekError, setRoadmapWeekError] = useState<string | null>(null);

  const filteredParts = useMemo(() => {
    if (skillFilter === "all") return toeicParts;
    return toeicParts.filter((part) => part.tag === skillFilter);
  }, [skillFilter, toeicParts]);

  const filteredSkillPacks = useMemo(() => {
    if (skillFilter === "all") return SKILL_PACKS;
    return SKILL_PACKS.filter((skill) => skill.tag === skillFilter);
  }, [skillFilter]);

  const totalSelectedQuestions = useMemo(() => {
    return toeicParts.filter((part) => selectedParts.includes(part.id)).reduce(
      (sum, part) => sum + part.count,
      0,
    );
  }, [selectedParts, toeicParts]);

  const selectedPartsCount = selectedParts.length;
  const selectedSkillPacks = useMemo(() => {
    return SKILL_PACKS.filter((skill) =>
      skill.parts.every((partId) => selectedParts.includes(partId)),
    );
  }, [selectedParts]);

  const runnerSearch = useMemo(() => {
    const parts = toeicParts
      .filter((part) => selectedParts.includes(part.id))
      .map((part) => part.number);
    const selectedCount =
      questionCountMode === "adaptive"
        ? Math.min(Math.max(totalSelectedQuestions || 30, 30), 200)
        : Number(questionCountMode);

    return new URLSearchParams({
      parts: parts.join(","),
      difficulty,
      mode: practiceMode,
      count: String(selectedCount),
    }).toString();
  }, [
    difficulty,
    practiceMode,
    questionCountMode,
    selectedParts,
    toeicParts,
    totalSelectedQuestions,
  ]);

  useEffect(() => {
    let cancelled = false;

    async function loadToeic() {
      setIsLoadingToeic(true);
      setToeicError(null);

      try {
        const [summary, recommended] = await Promise.all([
          toeicService.getSummary(),
          toeicService.getRecommendationsForCurrentUser(),
        ]);

        if (cancelled) return;

        if (summary.parts.length > 0) {
          setToeicParts(summary.parts);
          setSelectedParts((current) => {
            const available = new Set(summary.parts.map((part) => part.id));
            const kept = current.filter((partId) => available.has(partId));
            return kept.length > 0 ? kept : [summary.parts[0].id];
          });
        }

        setRecommendations(recommended);
        if (recommended?.recommendedPacks?.length) {
          const recommendedPartIds = recommended.recommendedPacks
            .map((pack) => getPartIdFromNumber(pack.part))
            .filter((partId, index, array) => array.indexOf(partId) === index);

          if (recommendedPartIds.length > 0) {
            setSelectedParts((current) =>
              current.length > 1 || current[0] !== "part1"
                ? current
                : recommendedPartIds,
            );
          }
        }
      } catch (error) {
        if (!cancelled) {
          setToeicError(
            error instanceof Error
              ? error.message
              : "Could not load TOEIC data from the backend.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoadingToeic(false);
        }
      }
    }

    loadToeic();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const partParam = parsePositiveInteger(searchParams.get("part"));
    const typeParam = searchParams.get("type")?.trim().toLowerCase();
    const skillParam = searchParams.get("skill")?.trim().toLowerCase();

    if (partParam && partParam >= 1 && partParam <= 7) {
      setSelectedParts([getPartIdFromNumber(partParam)]);
      setViewMode("part");
      return;
    }

    if (typeParam === "listening" || typeParam === "reading") {
      setSkillFilter(typeParam);
      setSelectedParts(
        TOEIC_PARTS.filter((part) => part.tag === typeParam).map(
          (part) => part.id,
        ),
      );
      setViewMode("part");
      return;
    }

    if (skillParam) {
      const matchingSkill = SKILL_PACKS.find((skill) =>
        [skill.id, skill.name.toLowerCase()].includes(skillParam),
      );

      if (matchingSkill) {
        setSelectedParts(matchingSkill.parts);
        setSkillFilter(matchingSkill.tag);
        setViewMode("skill");
      }
    }
  }, [searchParams]);

  useEffect(() => {
    if (!roadmapWeekId) {
      setRoadmapWeek(null);
      setRoadmapWeekError(null);
      setIsLoadingRoadmapWeek(false);
      return;
    }

    let cancelled = false;

    async function loadRoadmapWeek() {
      setIsLoadingRoadmapWeek(true);
      setRoadmapWeekError(null);

      try {
        const data = await roadmapService.getWeekSets(roadmapWeekId);
        if (cancelled) return;

        setRoadmapWeek(data);
        void roadmapService.startWeek(roadmapWeekId).catch(() => null);
      } catch (error) {
        if (!cancelled) {
          setRoadmapWeek(null);
          setRoadmapWeekError(
            error instanceof Error
              ? error.message
              : "Could not load this roadmap week.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoadingRoadmapWeek(false);
        }
      }
    }

    void loadRoadmapWeek();

    return () => {
      cancelled = true;
    };
  }, [roadmapWeekId]);

  const togglePart = (partId: string) => {
    setSelectedParts((prev) =>
      prev.includes(partId)
        ? prev.filter((id) => id !== partId)
        : [...prev, partId],
    );
  };

  const isSkillSelected = (skill: SkillPack) => {
    return skill.parts.every((partId) => selectedParts.includes(partId));
  };

  const toggleSkill = (skill: SkillPack) => {
    const selected = isSkillSelected(skill);

    setSelectedParts((prev) => {
      if (selected) {
        return prev.filter((partId) => !skill.parts.includes(partId));
      }

      return Array.from(new Set([...prev, ...skill.parts]));
    });
  };

  const clearSelection = () => {
    setSelectedParts([]);
  };

  const selectAllVisible = () => {
    setSelectedParts((prev) => {
      const merged = new Set([
        ...prev,
        ...(viewMode === "part"
          ? filteredParts.map((part) => part.id)
          : filteredSkillPacks.flatMap((skill) => skill.parts)),
      ]);
      return Array.from(merged);
    });
  };

  const skillButtonClass = (value: SkillFilter) =>
    skillFilter === value
      ? "border-[#7FB3FF] bg-[#A6C8FF] text-[#0F172A]"
      : "border-border bg-background text-foreground hover:border-[#7FB3FF]/60 hover:bg-[#F4F8FF]";

  const segmentedButtonClass = (active: boolean) =>
    active
      ? "bg-white text-[#0F172A] shadow-sm"
      : "text-slate-600 hover:text-slate-900";

  const difficultyButtonClass = (value: Difficulty) =>
    difficulty === value
      ? "bg-[#A6C8FF] text-[#0F172A]"
      : "text-foreground hover:bg-[#F4F8FF]";

  const modeButtonClass = (value: PracticeMode) =>
    practiceMode === value
      ? "bg-[#78AFFF] text-white"
      : "text-foreground hover:bg-[#F4F8FF]";

  if (roadmapWeekId) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">
              Weekly suggested sets
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Chon mot set trong roadmap week truoc khi vao runner.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link to="/dashboard">Back to dashboard</Link>
          </Button>
        </div>

        {isLoadingRoadmapWeek ? (
          <Card className="rounded-[24px] border-border shadow-sm">
            <CardContent className="p-6 text-sm text-muted-foreground">
              Loading roadmap week...
            </CardContent>
          </Card>
        ) : roadmapWeekError ? (
          <Card className="rounded-[24px] border-border shadow-sm">
            <CardContent className="p-6 text-sm text-destructive">
              {roadmapWeekError}
            </CardContent>
          </Card>
        ) : roadmapWeek ? (
          <>
            <Card className="rounded-[24px] border-border shadow-sm">
              <CardHeader>
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <CardTitle>
                      Week {roadmapWeek.weekNumber}: {roadmapWeek.title}
                    </CardTitle>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {roadmapWeek.description}
                    </p>
                  </div>
                  <Badge variant="outline">{roadmapWeek.status}</Badge>
                </div>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Focus skill
                  </p>
                  <p className="mt-2 font-semibold">
                    {formatRoadmapLabel(roadmapWeek.focusSkill)}
                  </p>
                </div>
                <div className="rounded-2xl border p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Focus part
                  </p>
                  <p className="mt-2 font-semibold">
                    {roadmapWeek.focusPart
                      ? `Part ${roadmapWeek.focusPart}`
                      : "Mixed"}
                  </p>
                </div>
                <div className="rounded-2xl border p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Weak subskills
                  </p>
                  <p className="mt-2 font-semibold">
                    {roadmapWeek.subskills?.length
                      ? roadmapWeek.subskills.map(formatRoadmapLabel).join(", ")
                      : "Adaptive mixed review"}
                  </p>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {roadmapWeek.suggestedSets.map((setItem) => (
                <Card
                  key={setItem.id}
                  className="rounded-[24px] border-border shadow-sm"
                >
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <CardTitle className="text-lg">
                          {setItem.title}
                        </CardTitle>
                        <p className="mt-2 text-sm text-muted-foreground">
                          {setItem.description}
                        </p>
                      </div>
                      <Badge variant="secondary">{setItem.difficulty}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-3 text-sm text-muted-foreground">
                      <div>
                        Focus:{" "}
                        <span className="font-medium text-foreground">
                          {formatRoadmapLabel(setItem.focusSkill)}
                        </span>
                      </div>
                      <div>
                        Part:{" "}
                        <span className="font-medium text-foreground">
                          {setItem.focusPart
                            ? `Part ${setItem.focusPart}`
                            : "Mixed"}
                        </span>
                      </div>
                      <div>
                        Questions:{" "}
                        <span className="font-medium text-foreground">
                          {setItem.questionCount}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {(setItem.tags || []).map((tag) => (
                        <Badge key={`${setItem.id}-${tag}`} variant="outline">
                          {formatRoadmapLabel(tag)}
                        </Badge>
                      ))}
                    </div>

                    <Button
                      asChild
                      className="w-full rounded-xl bg-[#5B9BFF] text-white hover:bg-[#4A8EF7]"
                    >
                      <Link
                        to={roadmapService.getPracticeUrl(
                          roadmapWeek.weekId,
                          setItem,
                        )}
                      >
                        <Play className="mr-2 h-4 w-4" />
                        Start this set
                      </Link>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="rounded-[24px] border-border shadow-sm">
        <CardHeader className="pb-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full text-primary">
              <CircleDot className="h-5 w-5" />
            </div>

            <div>
              <CardTitle className="text-3xl font-bold tracking-tight text-foreground">
                Tạo bài luyện tập
              </CardTitle>
              <p className="mt-2 text-base text-muted-foreground">
                Tùy chỉnh bài luyện theo nhu cầu của bạn
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {(isLoadingToeic || toeicError) && (
            <div className="rounded-2xl border border-[#E7EEF9] bg-[#F8FBFF] px-4 py-3 text-sm text-muted-foreground">
              {isLoadingToeic
                ? "Loading TOEIC question bank from FastAPI..."
                : `Using local fallback because TOEIC API failed: ${toeicError}`}
            </div>
          )}

          {recommendations && recommendations.recommendedPacks.length > 0 && (
            <div className="rounded-2xl border border-[#DCEBFF] bg-[#F4F8FF] px-4 py-3">
              <p className="text-sm font-semibold text-foreground">
                FastAPI recommendations: {recommendations.track}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {recommendations.reason}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {recommendations.recommendedPacks.slice(0, 3).map((pack) => (
                  <Badge key={pack.id} variant="secondary">
                    Part {pack.part}: {pack.suggestedQuestionCount} cau
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-full bg-[#EEF4FF] p-1">
            <div className="grid grid-cols-2 gap-1">
              <button
                type="button"
                onClick={() => setViewMode("skill")}
                className={`rounded-full px-4 py-2.5 text-sm font-semibold transition ${segmentedButtonClass(
                  viewMode === "skill",
                )}`}
              >
                Theo kỹ năng
              </button>

              <button
                type="button"
                onClick={() => setViewMode("part")}
                className={`rounded-full px-4 py-2.5 text-sm font-semibold transition ${segmentedButtonClass(
                  viewMode === "part",
                )}`}
              >
                Theo Part TOEIC
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setSkillFilter("all");
                selectAllVisible();
              }}
              className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${skillButtonClass("all")}`}
            >
              Full Test
            </button>

            <button
              type="button"
              onClick={() => setSkillFilter("listening")}
              className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${skillButtonClass("listening")}`}
            >
              Listening
            </button>

            <button
              type="button"
              onClick={() => setSkillFilter("reading")}
              className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${skillButtonClass("reading")}`}
            >
              Reading
            </button>

            <button
              type="button"
              onClick={clearSelection}
              className="px-2 text-sm font-semibold text-slate-700 transition hover:text-slate-900"
            >
              Bỏ chọn tất cả
            </button>
          </div>

          {viewMode === "part" ? (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredParts.map((part) => {
                const isSelected = selectedParts.includes(part.id);

                return (
                  <button
                    key={part.id}
                    type="button"
                    onClick={() => togglePart(part.id)}
                    className={`flex w-full items-center justify-between rounded-[22px] border px-4 py-4 text-left transition-all ${
                      isSelected
                        ? "border-[#7FB3FF] bg-[#A6C8FF] text-[#0F172A] shadow-[0_4px_14px_rgba(166,200,255,0.35)]"
                        : "border-border bg-background hover:border-[#7FB3FF]/60 hover:bg-[#F4F8FF]"
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <div
                        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
                          isSelected
                            ? "border-[#5B9BFF] bg-[#5B9BFF] text-white"
                            : "border-border bg-white"
                        }`}
                      >
                        {isSelected && <Check className="h-3.5 w-3.5" />}
                      </div>

                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-[18px] font-semibold leading-none">
                            {part.name}
                          </span>

                          <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-0.5 text-xs font-medium text-slate-700">
                            {part.tag === "listening" ? (
                              <Headphones className="h-3 w-3" />
                            ) : (
                              <BookOpen className="h-3 w-3" />
                            )}
                            {part.tag}
                          </span>
                        </div>

                        <p className="mt-1 text-sm text-slate-700">
                          {part.description}
                        </p>
                      </div>
                    </div>

                    <span className="shrink-0 text-sm font-medium text-slate-700">
                      {part.count} câu
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredSkillPacks.map((skill) => {
                const selected = isSkillSelected(skill);

                return (
                  <button
                    key={skill.id}
                    type="button"
                    onClick={() => toggleSkill(skill)}
                    className={`w-full rounded-[22px] border px-4 py-4 text-left transition-all ${
                      selected
                        ? "border-[#7FB3FF] bg-[#A6C8FF] text-[#0F172A] shadow-[0_4px_14px_rgba(166,200,255,0.35)]"
                        : "border-border bg-background hover:border-[#7FB3FF]/60 hover:bg-[#F4F8FF]"
                    }`}
                  >
                    <div className="flex min-w-0 items-start gap-4">
                      <div
                        className={`mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
                          selected
                            ? "border-[#5B9BFF] bg-[#5B9BFF] text-white"
                            : "border-border bg-white"
                        }`}
                      >
                        {selected && <Check className="h-3.5 w-3.5" />}
                      </div>

                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-[18px] font-semibold leading-none">
                            {skill.name}
                          </span>

                          <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-0.5 text-xs font-medium text-slate-700">
                            {skill.tag === "listening" ? (
                              <Headphones className="h-3 w-3" />
                            ) : (
                              <BookOpen className="h-3 w-3" />
                            )}
                            {skill.tag}
                          </span>

                          <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-0.5 text-xs font-medium text-slate-700">
                            <Layers3 className="h-3 w-3" />
                            {skill.parts
                              .map((partId) => getPartNumberFromId(partId))
                              .join(", ")}
                          </span>
                        </div>

                        <p className="mt-2 text-sm text-slate-700">
                          {skill.description}
                        </p>

                        <div className="mt-3 flex flex-wrap gap-2">
                          {skill.focus.map((item) => (
                            <span
                              key={`${skill.id}-${item}`}
                              className="rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-slate-700"
                            >
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          <div className="grid gap-8 border-t border-border pt-6 lg:grid-cols-2">
            <div className="space-y-3">
              <h3 className="text-base font-semibold text-foreground">
                Độ khó
              </h3>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setDifficulty("easy")}
                  className={`rounded-xl px-4 py-2 text-sm font-medium transition ${difficultyButtonClass("easy")}`}
                >
                  Dễ
                </button>

                <button
                  type="button"
                  onClick={() => setDifficulty("medium")}
                  className={`rounded-xl px-4 py-2 text-sm font-medium transition ${difficultyButtonClass("medium")}`}
                >
                  Trung bình
                </button>

                <button
                  type="button"
                  onClick={() => setDifficulty("hard")}
                  className={`rounded-xl px-4 py-2 text-sm font-medium transition ${difficultyButtonClass("hard")}`}
                >
                  Khó
                </button>

                <button
                  type="button"
                  onClick={() => setDifficulty("mixed")}
                  className={`rounded-xl px-4 py-2 text-sm font-medium transition ${difficultyButtonClass("mixed")}`}
                >
                  Hỗn hợp
                </button>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-base font-semibold text-foreground">
                Chế độ luyện tập
              </h3>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setPracticeMode("exam")}
                  className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${modeButtonClass("exam")}`}
                >
                  <Volume2 className="h-4 w-4" />
                  Exam
                </button>

                <button
                  type="button"
                  onClick={() => setPracticeMode("smart")}
                  className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${modeButtonClass("smart")}`}
                >
                  <Sparkles className="h-4 w-4" />
                  Smart
                </button>
              </div>
            </div>
          </div>

          <div className="space-y-3 border-t border-border pt-6">
            <h3 className="text-base font-semibold text-foreground">
              Số lượng câu hỏi
            </h3>

            <div className="flex flex-wrap gap-2">
              {[
                {
                  value: "adaptive",
                  label: `Theo lựa chọn (${Math.min(Math.max(totalSelectedQuestions || 30, 30), 200)} câu)`,
                },
                { value: "30", label: "30 câu" },
                { value: "60", label: "60 câu" },
                { value: "100", label: "100 câu" },
                { value: "200", label: "Full 200 câu" },
              ].map((item) => (
                <button
                  key={item.value}
                  type="button"
                  onClick={() =>
                    setQuestionCountMode(item.value as QuestionCountMode)
                  }
                  className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                    questionCountMode === item.value
                      ? "bg-[#A6C8FF] text-[#0F172A]"
                      : "text-foreground hover:bg-[#F4F8FF]"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <p className="text-xs text-muted-foreground">
              Nếu một Part không đủ số câu theo mức yêu cầu, FastAPI sẽ trả về tối đa số câu đang có trong ngân hàng câu hỏi.
            </p>
          </div>

          <div className="flex flex-col gap-4 border-t border-border pt-6 md:flex-row md:items-center md:justify-between">
            <div className="text-sm text-muted-foreground">
              {viewMode === "skill" ? (
                <>
                  Đã chọn{" "}
                  <span className="font-semibold text-foreground">
                    {selectedSkillPacks.length}
                  </span>{" "}
                  nhóm kỹ năng •{" "}
                  <span className="font-semibold text-foreground">
                    {selectedPartsCount}
                  </span>{" "}
                  part nguồn •{" "}
                  <span className="font-semibold text-foreground">
                    {totalSelectedQuestions}
                  </span>{" "}
                  câu nguồn
                </>
              ) : (
                <>
                  Đã chọn{" "}
                  <span className="font-semibold text-foreground">
                    {selectedPartsCount}
                  </span>{" "}
                  Part •{" "}
                  <span className="font-semibold text-foreground">
                    {totalSelectedQuestions}
                  </span>{" "}
                  câu
                </>
              )}
            </div>

            <Button
              asChild
              disabled={selectedParts.length === 0}
              className="h-12 rounded-xl bg-[#5B9BFF] px-6 text-white hover:bg-[#4A8EF7]"
            >
              <Link
                to={`/practice/runner?${runnerSearch}`}
                onClick={(event) => {
                  if (selectedParts.length === 0) {
                    event.preventDefault();
                  }
                }}
              >
                <Play className="mr-2 h-4 w-4" />
                Bắt đầu luyện tập
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="rounded-[24px] border-border shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Tóm tắt cấu hình</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-center justify-between">
              <span>Chế độ xem</span>
              <Badge variant="secondary">
                {viewMode === "skill" ? "Theo kỹ năng" : "Theo Part TOEIC"}
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span>Lọc kỹ năng</span>
              <Badge variant="secondary">
                {skillFilter === "all"
                  ? "Tất cả"
                  : skillFilter === "listening"
                    ? "Listening"
                    : "Reading"}
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span>Độ khó</span>
              <Badge variant="secondary">
                {difficulty === "easy"
                  ? "Dễ"
                  : difficulty === "medium"
                    ? "Trung bình"
                    : difficulty === "hard"
                      ? "Khó"
                      : "Hỗn hợp"}
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span>Chế độ</span>
              <Badge variant="secondary">
                {practiceMode === "exam" ? "Exam" : "Smart"}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[24px] border-border shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Part đã chọn</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {selectedParts.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Chưa chọn part nào.
              </p>
            ) : (
              toeicParts.filter((part) => selectedParts.includes(part.id)).map(
                (part) => (
                  <div
                    key={part.id}
                    className="flex items-center justify-between rounded-xl border border-[#E7EEF9] bg-[#F8FBFF] px-4 py-3"
                  >
                    <div>
                      <p className="font-medium text-foreground">{part.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {part.description}
                      </p>
                    </div>

                    <Badge variant="secondary">{part.count} câu</Badge>
                  </div>
                ),
              )
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
