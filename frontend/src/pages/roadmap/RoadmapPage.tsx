"use client";

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Info,
  Map,
  PlayCircle,
  RefreshCw,
  Sparkles,
  Target,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  roadmapService,
  type RoadmapCurrent,
  type RoadmapSetEvidence,
  type RoadmapWeek,
} from "@src/services/roadmapService";

function statusLabel(status: string) {
  return status.replace(/_/g, " ") || "not started";
}

function statusClass(status: string) {
  const normalized = status.toLowerCase();

  if (normalized === "completed") return "bg-emerald-100 text-emerald-700";
  if (normalized === "in_progress") return "bg-blue-100 text-blue-700";
  if (normalized === "recommended") return "bg-amber-100 text-amber-700";
  return "bg-muted text-muted-foreground";
}

function completedPercent(roadmap: RoadmapCurrent) {
  if (roadmap.weeks.length === 0) return 0;
  const completed = roadmap.weeks.filter(
    (week) => week.status.toLowerCase() === "completed",
  ).length;

  return Math.round((completed / roadmap.weeks.length) * 100);
}

function weekPriority(week: RoadmapWeek) {
  if (week.status.toLowerCase() === "in_progress") return 0;
  if (week.status.toLowerCase() === "recommended") return 1;
  if (week.status.toLowerCase() === "not_started") return 2;
  return 3;
}

export function RoadmapPage() {
  const [roadmap, setRoadmap] = useState<RoadmapCurrent | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [startingWeekId, setStartingWeekId] = useState<number | null>(null);
  const [completingWeekId, setCompletingWeekId] = useState<number | null>(null);
  const [setEvidence, setSetEvidence] = useState<
    Record<string, RoadmapSetEvidence>
  >({});
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  async function loadRoadmap() {
    setIsLoading(true);
    setError(null);
    setEvidenceError(null);

    try {
      const [current, evidence] = await Promise.all([
        roadmapService.getCurrent(),
        loadSetEvidence(),
      ]);
      setRoadmap(current);
      setSetEvidence(evidence);
    } catch (error) {
      setRoadmap(null);
      setError(
        error instanceof Error
          ? error.message
          : "Could not load roadmap data from FastAPI.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function loadSetEvidence() {
    setIsLoadingEvidence(true);

    try {
      return await roadmapService.getSetEvidence();
    } catch (error) {
      setEvidenceError(
        error instanceof Error
          ? error.message
          : "Could not load roadmap attempt evidence.",
      );
      return {};
    } finally {
      setIsLoadingEvidence(false);
    }
  }

  useEffect(() => {
    void loadRoadmap();
  }, []);

  async function handleGenerateRoadmap() {
    setIsGenerating(true);
    setActionError(null);

    try {
      const generated = await roadmapService.generateCurrent();
      setRoadmap(generated);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Could not generate roadmap.",
      );
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleStartWeek(weekId: number) {
    setStartingWeekId(weekId);
    setActionError(null);

    try {
      const updatedWeek = await roadmapService.startWeek(weekId);
      setRoadmap((current) =>
        current
          ? {
              ...current,
              weeks: current.weeks.map((week) =>
                week.id === updatedWeek.id ? updatedWeek : week,
              ),
            }
          : current,
      );
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Could not start this week.",
      );
    } finally {
      setStartingWeekId(null);
    }
  }

  async function handleCompleteWeek(weekId: number) {
    setCompletingWeekId(weekId);
    setActionError(null);

    try {
      await roadmapService.completeWeek(weekId);
      await loadRoadmap();
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Could not complete this week.",
      );
    } finally {
      setCompletingWeekId(null);
    }
  }

  const completion = roadmap ? completedPercent(roadmap) : 0;
  const nextWeeks = roadmap
    ? [...roadmap.weeks].sort(
        (left, right) =>
          weekPriority(left) - weekPriority(right) ||
          left.weekNumber - right.weekNumber,
      )
    : [];
  const activeWeek = nextWeeks[0];

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="rounded-[28px] border border-border bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.16),_transparent_35%),linear-gradient(135deg,#F8FAFF_0%,#EEFDF7_100%)] p-6 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <Badge className="mb-3 bg-primary/10 text-primary hover:bg-primary/10">
                FastAPI roadmap
              </Badge>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">
                Learning roadmap
              </h1>
              <p className="mt-2 max-w-2xl text-muted-foreground">
                Your active weekly plan is loaded from the FastAPI roadmap API.
                Start with the recommended week, then practice the suggested
                TOEIC sets.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                variant="outline"
                className="rounded-2xl border-border bg-white/80"
                onClick={() => void loadRoadmap()}
                disabled={isLoading}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
              {!roadmap && (
                <Button
                  className="rounded-2xl bg-primary text-primary-foreground"
                  onClick={() => void handleGenerateRoadmap()}
                  disabled={isGenerating || isLoading}
                >
                  <Sparkles className="mr-2 h-4 w-4" />
                  {isGenerating ? "Generating..." : "Generate roadmap"}
                </Button>
              )}
            </div>
          </div>
        </div>

        {(isLoading || error || actionError || !roadmap) && (
          <Card className="border-[#E7EEF9] bg-[#F8FBFF]">
            <CardContent className="py-4 text-sm text-muted-foreground">
              {isLoading
                ? "Loading roadmap data from FastAPI..."
                : error
                  ? `Could not load roadmap data: ${error}`
                  : actionError
                    ? `Roadmap action failed: ${actionError}`
                    : "No active roadmap yet. Generate one to create an 8-week plan from your latest practice analytics."}
            </CardContent>
          </Card>
        )}

        {roadmap && (isLoadingEvidence || evidenceError) && (
          <Card className="border-[#E7EEF9] bg-[#F8FBFF]">
            <CardContent className="py-4 text-sm text-muted-foreground">
              {isLoadingEvidence
                ? "Loading recent attempt evidence from FastAPI..."
                : `Could not load attempt evidence: ${evidenceError}`}
            </CardContent>
          </Card>
        )}

        {roadmap && (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <Card className="rounded-3xl border-border bg-card shadow-sm">
                <CardContent className="flex items-center gap-4 pt-6">
                  <div className="rounded-2xl bg-[#EEF4FF] p-3">
                    <Map className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Plan</p>
                    <p className="text-xl font-bold text-foreground">
                      {roadmap.totalWeeks} weeks
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-3xl border-border bg-card shadow-sm">
                <CardContent className="flex items-center gap-4 pt-6">
                  <div className="rounded-2xl bg-[#EEF4FF] p-3">
                    <Target className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Focus skill</p>
                    <p className="text-xl font-bold text-foreground">
                      {roadmap.weakestSkillLabel || "TOEIC foundation"}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-3xl border-border bg-card shadow-sm">
                <CardContent className="flex items-center gap-4 pt-6">
                  <div className="rounded-2xl bg-[#EEF4FF] p-3">
                    <CalendarDays className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Current week</p>
                    <p className="text-xl font-bold text-foreground">
                      Week {activeWeek?.weekNumber || 1}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-3xl border-border bg-card shadow-sm">
                <CardContent className="flex items-center gap-4 pt-6">
                  <div className="rounded-2xl bg-[#EEF4FF] p-3">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Completed</p>
                    <p className="text-xl font-bold text-foreground">
                      {completion}%
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="rounded-3xl border-border bg-card shadow-sm">
              <CardHeader>
                <CardTitle>{roadmap.title}</CardTitle>
                <CardDescription>
                  Source: {roadmap.sourceType}. Based on attempt{" "}
                  {roadmap.basedOnAttemptId || "not available"}.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Progress value={completion} className="h-3" />
                <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
                  <span>Weakest part: {roadmap.weakestPart || "N/A"}</span>
                  <span>Updated: {new Date(roadmap.updatedAtUtc).toLocaleString()}</span>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-5">
              {roadmap.weeks.map((week) => (
                <Card
                  key={week.id}
                  className="rounded-3xl border-border bg-card shadow-sm"
                >
                  <CardHeader>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <Badge variant="outline">Week {week.weekNumber}</Badge>
                          <Badge className={statusClass(week.status)}>
                            {statusLabel(week.status)}
                          </Badge>
                          <Badge variant="secondary">
                            <Clock3 className="mr-1 h-3 w-3" />
                            {week.estimatedMinutes}m
                          </Badge>
                        </div>
                        <CardTitle>{week.title}</CardTitle>
                        <CardDescription className="mt-2 max-w-3xl">
                          {week.description}
                        </CardDescription>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {["recommended", "not_started"].includes(
                          week.status.toLowerCase(),
                        ) && (
                          <Button
                            className="rounded-2xl"
                            onClick={() => void handleStartWeek(week.id)}
                            disabled={startingWeekId === week.id}
                          >
                            <PlayCircle className="mr-2 h-4 w-4" />
                            {startingWeekId === week.id ? "Starting..." : "Start week"}
                          </Button>
                        )}

                        {week.status.toLowerCase() === "in_progress" && (
                          <Button
                            variant="outline"
                            className="rounded-2xl border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 hover:text-emerald-800"
                            onClick={() => void handleCompleteWeek(week.id)}
                            disabled={completingWeekId === week.id}
                          >
                            <CheckCircle2 className="mr-2 h-4 w-4" />
                            {completingWeekId === week.id
                              ? "Completing..."
                              : "Complete week"}
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex flex-wrap gap-2">
                      {(week.subskills.length > 0
                        ? week.subskills
                        : [week.focusSkill || "TOEIC foundation"]
                      ).map((label) => (
                        <Badge key={label} variant="secondary">
                          {label}
                        </Badge>
                      ))}
                    </div>

                    <div className="grid gap-3 lg:grid-cols-3">
                      {week.suggestedSets.map((set) => (
                        (() => {
                          const evidence =
                            setEvidence[roadmapService.getEvidenceKey(week.id, set.id)];

                          return (
                            <div
                              key={set.id}
                              className="rounded-2xl border border-border bg-[#F8FBFF] p-4"
                            >
                              <div className="mb-2 flex items-center justify-between gap-2">
                                <p className="font-semibold text-foreground">
                                  {set.title}
                                </p>
                                <Badge variant="outline">{set.difficulty}</Badge>
                              </div>
                              <p className="min-h-10 text-sm text-muted-foreground">
                                {set.description}
                              </p>

                              <div className="mt-3 rounded-xl border border-border bg-white/75 px-3 py-2 text-xs">
                                {evidence ? (
                                  <div className="space-y-1">
                                    <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                                      Attempt found
                                    </Badge>
                                    <p className="text-muted-foreground">
                                      Attempt #{evidence.attemptId} -{" "}
                                      {Math.round(evidence.accuracy)}% -{" "}
                                      {evidence.correctCount}/{evidence.totalQuestions} correct
                                    </p>
                                    <p className="flex gap-1.5 text-muted-foreground">
                                      <Info className="mt-0.5 h-3 w-3 shrink-0" />
                                      Soft evidence from attempt metadata, not official
                                      completion proof.
                                    </p>
                                  </div>
                                ) : (
                                  <div className="space-y-1">
                                    <Badge variant="secondary">
                                      No matching recent attempt yet
                                    </Badge>
                                    <p className="flex gap-1.5 text-muted-foreground">
                                      <Info className="mt-0.5 h-3 w-3 shrink-0" />
                                      Read-only signal only. Completion is still manual.
                                    </p>
                                  </div>
                                )}
                              </div>

                              <div className="mt-4 flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">
                                  {set.questionCount} questions
                                </span>
                                <Button size="sm" asChild>
                                  <Link to={roadmapService.getPracticeUrl(week.id, set)}>
                                    Practice
                                    <ArrowRight className="ml-2 h-4 w-4" />
                                  </Link>
                                </Button>
                              </div>
                            </div>
                          );
                        })()
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
