"use client";

import { useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Brain,
  Calendar,
  ChevronRight,
  Clock,
  FileText,
  Headphones,
  History,
  Play,
  Sparkles,
  Star,
  Target,
  TrendingUp,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ProFeatureGuard } from "@/components/pro-feature-guard";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  difficultyOptions,
  partOptions,
  recentTests,
  skillOptions,
  type DifficultyOptionId,
  type PartOptionId,
  type SkillOptionId,
} from "@src/data/mock-test";

export function MockTestPage() {
  const [selectedParts, setSelectedParts] = useState<PartOptionId[]>([]);
  const [selectedSkill, setSelectedSkill] =
    useState<SkillOptionId>("listening");
  const [selectedDifficulty, setSelectedDifficulty] =
    useState<DifficultyOptionId>("mixed");
  const [questionCount, setQuestionCount] = useState<number>(20);
  const [testMode, setTestMode] = useState<"exam" | "smart">("exam");

  const togglePart = (partId: PartOptionId) => {
    setSelectedParts((prev) =>
      prev.includes(partId)
        ? prev.filter((p) => p !== partId)
        : [...prev, partId],
    );
  };

  const selectPreset = (preset: "listening" | "reading" | "full") => {
    if (preset === "listening") {
      setSelectedParts([1, 2, 3, 4]);
    } else if (preset === "reading") {
      setSelectedParts([5, 6, 7]);
    } else {
      setSelectedParts([1, 2, 3, 4, 5, 6, 7]);
    }
  };

  const estimatedTime = Math.round(questionCount * 1.5);
  const skillParts: Record<SkillOptionId, number[]> = {
    listening: [1, 2, 3, 4],
    reading: [5, 6, 7],
    grammar: [5],
    vocabulary: [5, 6],
  };
  const miniSkillUrl = `/mock-test/runner?type=mini&mode=mini&parts=${skillParts[selectedSkill].join(",")}&count=${questionCount}&difficulty=${selectedDifficulty}&test_mode=${testMode}`;
  const miniPartUrl = `/mock-test/runner?type=mini&mode=mini&parts=${selectedParts.join(",")}&count=${questionCount}&difficulty=${selectedDifficulty}&test_mode=${testMode}`;

  return (
    <ProFeatureGuard
      feature="mockTestUnlimited"
      title="Mock Test day du dang khoa cho Free"
      description="Free van co placement va practice. Mock Test, Mini Test va Weekly Check la quyen loi cua Pro."
    >
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Mock Test TOEIC
          </h1>
          <p className="mt-1 text-muted-foreground">
            Luyện thi với đề thi mô phỏng thực tế
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="gap-2" asChild>
            <Link to="/progress">
              <History className="h-4 w-4" />
              Lịch sử bài test
            </Link>
          </Button>
          <Button variant="secondary" className="gap-2" asChild>
            <Link to="/mock-test/runner?type=full">
              <Play className="h-4 w-4" />
              Tiếp tục bài đang làm
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="relative overflow-hidden border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
          <div className="absolute top-0 right-0 h-32 w-32 translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/10" />
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Badge className="border-0 bg-primary/10 text-primary">
                Đề thi đầy đủ
              </Badge>
              <Star className="h-5 w-5 fill-yellow-500 text-yellow-500" />
            </div>
            <CardTitle className="mt-3 text-xl">Full TOEIC Test</CardTitle>
            <CardDescription>
              Làm bài thi hoàn chỉnh như thi thật
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span>200 câu</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                <span>120 phút</span>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Headphones className="h-4 w-4 text-blue-600" />
              <span>Listening</span>
              <span className="text-muted-foreground">+</span>
              <BookOpen className="h-4 w-4 text-green-600" />
              <span>Reading</span>
            </div>
            <div className="flex items-center gap-2 pt-2">
              <Button
                variant={testMode === "exam" ? "default" : "outline"}
                size="sm"
                onClick={() => setTestMode("exam")}
                className="flex-1"
              >
                Exam Mode
              </Button>
              <Button
                variant={testMode === "smart" ? "default" : "outline"}
                size="sm"
                onClick={() => setTestMode("smart")}
                className="flex-1 gap-1"
              >
                <Sparkles className="h-3 w-3" />
                Smart Mode
              </Button>
            </div>
            <Button asChild className="w-full gap-2">
              <Link to="/mock-test/runner?type=full">
                <Play className="h-4 w-4" />
                Bắt đầu Full Test
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute top-0 right-0 h-24 w-24 translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-500/10" />
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Badge variant="secondary">Luyện tập nhanh</Badge>
              <Zap className="h-5 w-5 text-blue-500" />
            </div>
            <CardTitle className="mt-3 text-xl">Mini Test</CardTitle>
            <CardDescription>Tùy chỉnh số câu và dạng bài</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span>10-50 câu</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                <span>Linh hoạt</span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Luyện theo kỹ năng hoặc theo part TOEIC
            </p>
            <Button variant="outline" className="w-full gap-2" asChild>
              <a href="#mini-test-builder">
                <Target className="h-4 w-4" />
                Tạo Mini Test
              </a>
            </Button>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-2 border-yellow-200 bg-gradient-to-br from-yellow-50 to-transparent">
          <div className="absolute top-0 right-0 h-24 w-24 translate-x-1/2 -translate-y-1/2 rounded-full bg-yellow-500/10" />
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Badge className="border-yellow-200 bg-yellow-100 text-yellow-700">
                Đề xuất
              </Badge>
              <Calendar className="h-5 w-5 text-yellow-600" />
            </div>
            <CardTitle className="mt-3 text-xl">Weekly Check</CardTitle>
            <CardDescription>
              Bài kiểm tra hàng tuần được gợi ý
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span>50 câu</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                <span>45 phút</span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Được tạo dựa trên điểm yếu của bạn
            </p>
            <Button
              asChild
              className="w-full gap-2 bg-yellow-600 text-white hover:bg-yellow-700"
            >
              <Link to="/weekly-check/runner">
                <Play className="h-4 w-4" />
                Làm bài tuần này
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card id="mini-test-builder">
        <CardHeader>
          <CardTitle>Tạo Mini Test</CardTitle>
          <CardDescription>
            Tùy chỉnh bài test theo nhu cầu của bạn
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="skill" className="space-y-6">
            <TabsList className="grid w-full max-w-md grid-cols-2">
              <TabsTrigger value="skill">Theo kỹ năng</TabsTrigger>
              <TabsTrigger value="part">Theo part TOEIC</TabsTrigger>
            </TabsList>

            <TabsContent value="skill" className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-3">
                  <label className="text-sm font-medium">Kỹ năng</label>
                  <div className="grid grid-cols-2 gap-3">
                    {skillOptions.map((skill) => (
                      <button
                        key={skill.id}
                        onClick={() => setSelectedSkill(skill.id)}
                        className={`flex items-center gap-3 rounded-xl border-2 p-4 transition-all ${
                          selectedSkill === skill.id
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        <skill.icon
                          className={`h-5 w-5 ${
                            selectedSkill === skill.id
                              ? "text-primary"
                              : "text-muted-foreground"
                          }`}
                        />
                        <span
                          className={
                            selectedSkill === skill.id ? "font-medium" : ""
                          }
                        >
                          {skill.name}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <label className="text-sm font-medium">Độ khó</label>
                  <div className="grid grid-cols-2 gap-3">
                    {difficultyOptions.map((diff) => (
                      <button
                        key={diff.id}
                        onClick={() => setSelectedDifficulty(diff.id)}
                        className={`rounded-xl border-2 p-3 transition-all ${
                          selectedDifficulty === diff.id
                            ? `${diff.color} border-current`
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        {diff.name}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Số câu hỏi</label>
                  <span className="text-sm text-muted-foreground">
                    {questionCount} câu - ~{estimatedTime} phút
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  {[10, 20, 30, 40, 50].map((count) => (
                    <button
                      key={count}
                      onClick={() => setQuestionCount(count)}
                      className={`flex-1 rounded-lg border-2 py-2 transition-all ${
                        questionCount === count
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      {count}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-sm font-medium">Chế độ làm bài</label>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setTestMode("exam")}
                    className={`flex-1 rounded-xl border-2 p-4 transition-all ${
                      testMode === "exam"
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <FileText
                        className={`h-5 w-5 ${
                          testMode === "exam"
                            ? "text-primary"
                            : "text-muted-foreground"
                        }`}
                      />
                      <div className="text-left">
                        <p
                          className={`font-medium ${
                            testMode === "exam" ? "text-primary" : ""
                          }`}
                        >
                          Exam Mode
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Như thi thật, không hỗ trợ
                        </p>
                      </div>
                    </div>
                  </button>
                  <button
                    onClick={() => setTestMode("smart")}
                    className={`flex-1 rounded-xl border-2 p-4 transition-all ${
                      testMode === "smart"
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Sparkles
                        className={`h-5 w-5 ${
                          testMode === "smart"
                            ? "text-primary"
                            : "text-muted-foreground"
                        }`}
                      />
                      <div className="text-left">
                        <p
                          className={`font-medium ${
                            testMode === "smart" ? "text-primary" : ""
                          }`}
                        >
                          Smart Mode
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Có AI hỗ trợ giải thích
                        </p>
                      </div>
                    </div>
                  </button>
                </div>
              </div>

              <Button size="lg" className="w-full gap-2" asChild>
                <Link to={miniSkillUrl} className="flex items-center justify-center gap-2">
                  <span className="hidden">
                  <span>
                    <Play className="h-5 w-5" />
                    Bắt đầu Mini Test ({selectedParts.length} part)
                  </span>
                  </span>
                  <Play className="h-5 w-5" />
                Bắt đầu Mini Test
                </Link>
              </Button>
            </TabsContent>

            <TabsContent value="part" className="space-y-6">
              <div className="space-y-3">
                <label className="text-sm font-medium">Chọn nhanh</label>
                <div className="flex items-center gap-3">
                  <Button
                    variant="outline"
                    onClick={() => selectPreset("listening")}
                    className="gap-2"
                  >
                    <Headphones className="h-4 w-4" />
                    Listening
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => selectPreset("reading")}
                    className="gap-2"
                  >
                    <BookOpen className="h-4 w-4" />
                    Reading
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => selectPreset("full")}
                    className="gap-2"
                  >
                    <FileText className="h-4 w-4" />
                    Full Mini
                  </Button>
                  <Button variant="ghost" onClick={() => setSelectedParts([])}>
                    Bỏ chọn
                  </Button>
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-sm font-medium">Chọn part</label>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
                  {partOptions.map((part) => (
                    <button
                      key={part.id}
                      onClick={() => togglePart(part.id)}
                      className={`rounded-xl border-2 p-4 text-center transition-all ${
                        selectedParts.includes(part.id)
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      <div
                        className={`text-lg font-bold ${
                          selectedParts.includes(part.id) ? "text-primary" : ""
                        }`}
                      >
                        {part.name}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {part.desc}
                      </div>
                      <Badge
                        variant="secondary"
                        className={`mt-2 text-xs ${
                          part.type === "listening"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-green-100 text-green-700"
                        }`}
                      >
                        {part.type === "listening" ? "Listening" : "Reading"}
                      </Badge>
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-3">
                  <label className="text-sm font-medium">Độ khó</label>
                  <div className="grid grid-cols-2 gap-3">
                    {difficultyOptions.map((diff) => (
                      <button
                        key={diff.id}
                        onClick={() => setSelectedDifficulty(diff.id)}
                        className={`rounded-xl border-2 p-3 transition-all ${
                          selectedDifficulty === diff.id
                            ? `${diff.color} border-current`
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        {diff.name}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium">Số câu hỏi</label>
                    <span className="text-sm text-muted-foreground">
                      ~{estimatedTime} phút
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    {[10, 20, 30, 40, 50].map((count) => (
                      <button
                        key={count}
                        onClick={() => setQuestionCount(count)}
                        className={`flex-1 rounded-lg border-2 py-2 transition-all ${
                          questionCount === count
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        {count}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {selectedParts.length === 0 ? (
                <Button size="lg" className="w-full gap-2" disabled>
                  <Play className="h-5 w-5" />
                  Bắt đầu Mini Test ({selectedParts.length} part)
                </Button>
              ) : (
                <Button size="lg" className="w-full gap-2" asChild>
                  <Link to={miniPartUrl}>
                    <Play className="h-5 w-5" />
                    Bắt đầu Mini Test ({selectedParts.length} part)
                  </Link>
                </Button>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              <CardTitle>Gợi ý cho bạn</CardTitle>
            </div>
            <CardDescription>Dựa trên kết quả học tập của bạn</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-4 rounded-xl border border-primary/10 bg-primary/5 p-4">
              <div className="rounded-lg bg-primary/10 p-2">
                <TrendingUp className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <h4 className="font-medium">Luyện thêm Part 5 - Điền câu</h4>
                <p className="mt-1 text-sm text-muted-foreground">
                  Bạn đang có độ chính xác 65% ở phần này. Luyện thêm 20 câu để
                  cải thiện.
                </p>
                <Button size="sm" variant="link" className="mt-2 px-0" asChild>
                  <Link to="/practice/runner?mode=recommended&parts=5&difficulty=medium&count=20&source=mock-test">
                    Luyện ngay <ChevronRight className="ml-1 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
            <div className="flex items-start gap-4 rounded-xl border border-yellow-100 bg-yellow-50 p-4">
              <div className="rounded-lg bg-yellow-100 p-2">
                <Calendar className="h-5 w-5 text-yellow-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-medium">Lịch học tuần này</h4>
                <p className="mt-1 text-sm text-muted-foreground">
                  Còn 3 bài luyện tập chưa hoàn thành. Hoàn thành trước Chủ nhật
                  để duy trì streak.
                </p>
                <Button
                  size="sm"
                  variant="link"
                  className="mt-2 px-0 text-yellow-700"
                  asChild
                >
                  <Link to="/roadmap">
                    Xem lịch <ChevronRight className="ml-1 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Kết quả gần đây</CardTitle>
              <Button variant="ghost" size="sm">
                Xem tất cả
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {recentTests.map((test) => (
              <div
                key={test.id}
                className="flex cursor-pointer items-center justify-between rounded-xl border p-3 transition-colors hover:bg-muted/50"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`rounded-lg p-2 ${
                      test.type === "full"
                        ? "bg-primary/10"
                        : test.type === "weekly"
                          ? "bg-yellow-100"
                          : "bg-blue-100"
                    }`}
                  >
                    {test.type === "full" ? (
                      <FileText className="h-4 w-4 text-primary" />
                    ) : test.type === "weekly" ? (
                      <Calendar className="h-4 w-4 text-yellow-600" />
                    ) : (
                      <Zap className="h-4 w-4 text-blue-600" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium">{test.name}</p>
                    <p className="text-xs text-muted-foreground">{test.date}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-primary">{test.score}</p>
                  <p className="text-xs text-muted-foreground">điểm</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="border-orange-200 bg-orange-50/50">
        <CardContent className="flex items-center justify-between py-4">
          <div className="flex items-center gap-4">
            <div className="rounded-xl bg-orange-100 p-3">
              <Play className="h-6 w-6 text-orange-600" />
            </div>
            <div>
              <h3 className="font-semibold">Bạn có bài test chưa hoàn thành</h3>
              <p className="text-sm text-muted-foreground">
                Full Test #4 - Còn 45 phút - 120/200 câu đã làm
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Progress value={60} className="h-2 w-24" />
            <Button className="gap-2" asChild>
              <Link to="/mock-test/runner?type=full">
                <Play className="h-4 w-4" />
                Tiếp tục
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
    </ProFeatureGuard>
  );
}
