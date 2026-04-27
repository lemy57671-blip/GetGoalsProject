"use client";

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
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
  ArrowRight,
  BookOpen,
  Brain,
  Crown,
  Loader2,
  NotebookPen,
  TrendingUp,
} from "lucide-react";
import {
  dashboardService,
  type DashboardCourse,
  type DashboardOverviewView,
  type ProgressHistoryItem,
} from "@src/services/dashboardService";
import { useAuthSession } from "@src/hooks/useAuthSession";

const previewUserId = 1;

function formatMinutes(minutes: number) {
  if (minutes <= 0) return "0 phút";
  if (minutes < 60) return `${minutes} phút`;

  const hours = Math.floor(minutes / 60);
  const remain = minutes % 60;
  return remain > 0 ? `${hours}h ${remain}m` : `${hours}h`;
}

function formatDateTime(value?: string | null) {
  if (!value) return "Chưa có";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa có";

  return date.toLocaleString("vi-VN");
}

function formatRoadmapLabel(value?: string | null) {
  if (!value) return "N/A";

  return String(value).replace(/_/g, " ").replace(/\s+/g, " ").trim();
}

function formatWeekStatus(status?: string | null) {
  if (!status) return "not started";
  return status.replace(/_/g, " ");
}

function clampProgress(value: number) {
  return Math.min(Math.max(value || 0, 0), 100);
}

export function DashboardPage() {
  const { user: currentUser, displayName } = useAuthSession();
  const userId = currentUser?.id ?? previewUserId;
  const [overview, setOverview] = useState<DashboardOverviewView | null>(null);
  const [courses, setCourses] = useState<DashboardCourse[]>([]);
  const [history, setHistory] = useState<ProgressHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      try {
        setLoading(true);
        setError("");

        const [overviewData, historyData, coursesData] = await Promise.all([
          dashboardService.getOverview(),
          dashboardService.getProgressHistory(7),
          dashboardService.getCourses(userId).catch(() => []),
        ]);

        if (!active) return;

        setOverview(overviewData);
        setHistory(historyData);
        setCourses(coursesData);
      } catch (requestError) {
        if (!active) return;

        setError(
          requestError instanceof Error
            ? requestError.message
            : "Không tải được dashboard.",
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadDashboard();

    return () => {
      active = false;
    };
  }, [userId]);

  const latestDiagnostic = overview?.latestDiagnostic
    ? {
        score: overview.latestDiagnostic.estimatedScore,
        levelName: overview.latestDiagnostic.estimatedLevel,
        accuracy: overview.recentAccuracy,
        weakSubskills: overview.latestDiagnostic.weakSubskills || [],
        submittedAtUtc: overview.latestDiagnostic.submittedAtUtc,
      }
    : null;

  const maxStudyMinutes = useMemo(
    () => Math.max(...history.map((item) => item.studyMinutes), 1),
    [history],
  );

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        Đang tải bảng điều khiển...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Tổng quan học tập
          </h1>
          <p className="mt-1 text-muted-foreground">
            {currentUser
              ? `Tổng hợp mới nhất dành cho ${displayName}.`
              : "Theo dõi tiến độ học tập và các nội dung cần ưu tiên."}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button asChild variant="outline">
            <Link to="/placement-test">Làm placement test</Link>
          </Button>
          <Button asChild>
            <Link to="/progress">Xem tiến độ chi tiết</Link>
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="rounded-3xl border-border bg-card shadow-sm">
          <CardContent className="flex items-center gap-4 pt-6">
            <div className="rounded-2xl bg-primary/10 p-3 text-primary">
              <BookOpen className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">
                Buổi luyện đã lưu
              </p>
              <p className="text-2xl font-bold">
                {overview?.totalPracticeAttempts ?? 0}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-border bg-card shadow-sm">
          <CardContent className="flex items-center gap-4 pt-6">
            <div className="rounded-2xl bg-emerald-500/10 p-3 text-emerald-600">
              <TrendingUp className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Accuracy gần đây</p>
              <p className="text-2xl font-bold">
                {Math.round(overview?.recentAccuracy ?? 0)}%
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-border bg-card shadow-sm">
          <CardContent className="flex items-center gap-4 pt-6">
            <div className="rounded-2xl bg-yellow-500/10 p-3 text-yellow-600">
              <Brain className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">
                Tổng thời gian học
              </p>
              <p className="text-2xl font-bold">
                {formatMinutes(overview?.totalStudyMinutes ?? 0)}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-border bg-card shadow-sm">
          <CardContent className="flex items-center gap-4 pt-6">
            <div className="rounded-2xl bg-orange-500/10 p-3 text-orange-600">
              <NotebookPen className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Review đang chờ</p>
              <p className="text-2xl font-bold">
                {overview?.pendingReviewCount ?? 0}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-3xl border-border shadow-sm">
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Roadmap 8 tuần</CardTitle>
            <CardDescription>
              Mở từng tuần để xem gợi ý và bắt đầu luyện tập trong trang
              practice.
            </CardDescription>
          </div>
          <Button asChild variant="outline">
            <Link to="/placement-test">Làm mới lộ trình</Link>
          </Button>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border bg-muted/20 p-4">
              <p className="text-sm text-muted-foreground">Weakest skill</p>
              <p className="mt-2 text-lg font-bold">
                {overview?.activeRoadmap?.weakestSkillLabel ||
                  overview?.weakestSkill?.skill ||
                  "Chưa có dữ liệu"}
              </p>
              <p className="text-sm text-muted-foreground">
                Tập trung cải thiện trong lộ trình hiện tại.
              </p>
            </div>

            <div className="rounded-2xl border bg-muted/20 p-4">
              <p className="text-sm text-muted-foreground">Weakest part</p>
              <p className="mt-2 text-lg font-bold">
                {overview?.activeRoadmap?.weakestPart
                  ? `Part ${overview.activeRoadmap.weakestPart}`
                  : overview?.weakestPart
                    ? `Part ${overview.weakestPart.part}`
                    : "Chưa có dữ liệu"}
              </p>
              <p className="text-sm text-muted-foreground">
                {overview?.activeRoadmap?.analytics?.topWeakSubskills?.length
                  ? `Top weak subskills: ${overview.activeRoadmap.analytics.topWeakSubskills
                      .slice(0, 3)
                      .map(formatRoadmapLabel)
                      .join(", ")}`
                  : "Placement test sẽ cập nhật những nội dung cần ưu tiên tiếp theo."}
              </p>
            </div>
          </div>

          {overview?.activeRoadmap?.weeks?.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {overview.activeRoadmap.weeks.map((week) => (
                <Link
                  key={week.id}
                  to={`/practice?roadmapWeekId=${week.id}`}
                  className="group rounded-3xl border border-border bg-card p-5 transition hover:border-primary/40 hover:bg-primary/5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Badge variant="secondary">Week {week.weekNumber}</Badge>
                      <h3 className="mt-3 text-base font-semibold group-hover:text-primary">
                        {week.title}
                      </h3>
                    </div>
                    <Badge variant="outline">
                      {formatWeekStatus(week.status)}
                    </Badge>
                  </div>

                  <p className="mt-3 text-sm text-muted-foreground">
                    {week.description}
                  </p>

                  <div className="mt-4 space-y-2 text-sm text-muted-foreground">
                    <div>
                      Focus skill:{" "}
                      <span className="font-medium text-foreground">
                        {formatRoadmapLabel(week.focusSkill)}
                      </span>
                    </div>
                    <div>
                      Focus part:{" "}
                      <span className="font-medium text-foreground">
                        {week.focusPart ? `Part ${week.focusPart}` : "Mixed"}
                      </span>
                    </div>
                    <div>
                      Sets:{" "}
                      <span className="font-medium text-foreground">
                        {week.suggestedSets?.length || 0}
                      </span>
                    </div>
                    <div>
                      Estimated:{" "}
                      <span className="font-medium text-foreground">
                        {week.estimatedMinutes} mins
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
              Chưa có lộ trình phù hợp. Hãy làm placement test để nhận kế
              hoạch học tập cá nhân hóa.
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="h-full rounded-3xl border-border shadow-sm">
          <CardHeader>
            <CardTitle>Diagnostic gần nhất</CardTitle>
            <CardDescription>
              {latestDiagnostic
                ? "Được cập nhật từ bài đánh giá gần nhất của bạn."
                : "Làm placement test để cập nhật mức điểm và kỹ năng cần ưu tiên."}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex h-[calc(100%-88px)] flex-col space-y-4">
            {latestDiagnostic ? (
              <>
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">
                      Điểm ước lượng
                    </p>
                    <p className="text-3xl font-bold">
                      {latestDiagnostic.score}
                    </p>
                  </div>
                  <Badge>{latestDiagnostic.levelName ?? "Diagnostic"}</Badge>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span>Accuracy gần đây</span>
                    <span>{Math.round(latestDiagnostic.accuracy)}%</span>
                  </div>
                  <Progress value={latestDiagnostic.accuracy || 0} className="h-2" />
                </div>

                <div className="flex flex-wrap gap-2">
                  {latestDiagnostic.weakSubskills.length > 0 ? (
                    latestDiagnostic.weakSubskills.slice(0, 4).map((item) => (
                      <Badge key={item} variant="outline">
                        {formatRoadmapLabel(item)}
                      </Badge>
                    ))
                  ) : (
                    <Badge variant="outline">Chưa có weak subskill</Badge>
                  )}
                </div>

                <p className="text-xs text-muted-foreground">
                  Cập nhật: {formatDateTime(latestDiagnostic.submittedAtUtc)}
                </p>
              </>
            ) : (
              <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                Điểm mục tiêu hiện tại:{" "}
                <strong>{currentUser?.targetScore || "750"}</strong>. Hoàn
                thành placement test để nhận phân tích mới nhất.
              </div>
            )}

            <div className="mt-auto">
              <Button asChild className="w-full">
                <Link to="/placement-test">
                  {latestDiagnostic
                    ? "Làm lại placement test"
                    : "Bắt đầu placement test"}
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="h-full rounded-3xl border-border shadow-sm">
          <CardHeader>
            <CardTitle>Mock test gần nhất</CardTitle>
            <CardDescription>
              Tổng hợp từ bài test gần nhất của bạn.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex h-[calc(100%-88px)] flex-col">
            {overview?.latestMockTest ? (
              <div className="space-y-4">
                <div>
                  <p className="font-semibold">
                    {overview.latestMockTest.title || "Mock test"}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Cập nhật:{" "}
                    {formatDateTime(overview.latestMockTest.submittedAtUtc)}
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-2xl border p-3 text-center">
                    <p className="text-xs text-muted-foreground">Total</p>
                    <p className="text-xl font-bold">
                      {overview.latestMockTest.totalScaledScore}
                    </p>
                  </div>
                  <div className="rounded-2xl border p-3 text-center">
                    <p className="text-xs text-muted-foreground">Listening</p>
                    <p className="text-xl font-bold">
                      {overview.latestMockTest.listeningScaledScore}
                    </p>
                  </div>
                  <div className="rounded-2xl border p-3 text-center">
                    <p className="text-xs text-muted-foreground">Reading</p>
                    <p className="text-xl font-bold">
                      {overview.latestMockTest.readingScaledScore}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                Bạn chưa hoàn thành bài mock test nào.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="h-full rounded-3xl border-border bg-gradient-to-br from-primary/5 to-transparent shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Crown className="h-5 w-5 text-yellow-500" />
              Tăng tốc với Pro
            </CardTitle>
            <CardDescription>
              Mở rộng trải nghiệm học tập với nhiều tính năng hỗ trợ và phân
              tích sâu hơn.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex h-[calc(100%-88px)] flex-col">
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>Buổi học chủ động hơn với AI tutor theo lỗi sai thật</li>
              <li>Mock test full và analytics sâu hơn</li>
              <li>Review queue và notebook cá nhân hóa</li>
            </ul>

            <div className="mt-auto">
              <Button asChild className="mt-4 w-full">
                <Link to="/pricing">
                  Xem bảng giá
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {courses.length > 0 ? (
        <Card className="rounded-3xl border-border shadow-sm">
          <CardHeader>
            <CardTitle>Khóa học đang theo dõi</CardTitle>
            <CardDescription>
              Dữ liệu lấy từ endpoint dashboard courses của FastAPI.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {courses.slice(0, 3).map((course) => (
              <div key={course.id} className="rounded-2xl border p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{course.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {course.author}
                    </p>
                  </div>
                  <Badge variant="outline">{course.rating.toFixed(1)}</Badge>
                </div>
                <div className="mt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Progress</span>
                    <span>{clampProgress(course.progress)}%</span>
                  </div>
                  <Progress value={clampProgress(course.progress)} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <Card className="rounded-3xl border-border shadow-sm">
        <CardHeader>
          <CardTitle>Nhịp học 7 ngày gần nhất</CardTitle>
          <CardDescription>
            Theo dõi số phút học và số lần luyện tập trong từng ngày.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-7">
            {history.map((item) => (
              <div key={item.date} className="rounded-2xl border p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium">{item.date.slice(5)}</p>
                  <Badge variant="secondary">{item.attemptsCount} lượt</Badge>
                </div>

                <div className="mt-4 h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-primary"
                    style={{
                      width: `${Math.max(
                        (item.studyMinutes / maxStudyMinutes) * 100,
                        item.studyMinutes > 0 ? 10 : 0,
                      )}%`,
                    }}
                  />
                </div>

                <p className="mt-3 text-2xl font-bold">{item.studyMinutes}</p>
                <p className="text-xs text-muted-foreground">
                  phút - accuracy {Math.round(item.accuracy)}%
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
