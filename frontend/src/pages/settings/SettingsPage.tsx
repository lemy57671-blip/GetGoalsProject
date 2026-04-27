"use client";

import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useTheme } from "next-themes";
import {
  AlertTriangle,
  Bell,
  BookOpen,
  Calendar,
  Camera,
  CheckCircle2,
  Clock,
  CreditCard,
  Crown,
  LogOut,
  Palette,
  RefreshCcw,
  Shield,
  Target,
  Trash2,
  User,
} from "lucide-react";

import {
  AlertDialogAction,
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { learningSkillTags, subscriptionFeatures } from "@src/data/settings";
import { useAuthSession } from "@src/hooks/useAuthSession";
import { authService } from "@src/services/authService";
import { roadmapService } from "@src/services/roadmapService";
import {
  settingsService,
  type DangerousActionResult,
  type ExperiencePreferences,
  type LanguageCode,
  type NotificationPreferences,
  type ThemeMode,
} from "@src/services/settingsService";
import {
  subscriptionService,
  type CurrentSubscription,
} from "@src/services/subscriptionService";

const defaultExperience: ExperiencePreferences = {
  themeMode: "system",
  language: "vi",
  notificationSoundEnabled: true,
  autoPlayAudio: true,
  autoAiExplanation: true,
};

const defaultNotifications: NotificationPreferences = {
  dailyReminderEnabled: true,
  weeklyCheckReminderEnabled: true,
  emailNotificationsEnabled: false,
  reminderTimeLocal: "20:00",
  timezone: "Asia/Bangkok",
};

function toInputDate(value?: string | null) {
  return value ? value.slice(0, 10) : "";
}

function parseOptionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildInitials(name?: string, email?: string) {
  const source = (name || email || "GG").trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length <= 1) return source.slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function statusText(error: string | null, loading: boolean, label: string) {
  if (loading) return `Dang tai ${label} tu FastAPI...`;
  return error;
}

function StatusMessage({
  type,
  children,
}: {
  type: "success" | "error" | "info";
  children: string | null;
}) {
  if (!children) return null;

  const className =
    type === "success"
      ? "border-green-200 bg-green-50 text-green-700"
      : type === "error"
        ? "border-destructive/20 bg-destructive/5 text-destructive"
        : "border-blue-200 bg-blue-50 text-blue-700";

  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${className}`}>
      {children}
    </div>
  );
}

function ActionSummary({ result }: { result: DangerousActionResult | null }) {
  if (!result) return null;

  const deleted = Object.entries(result.summary.deleted || {});
  const updated = Object.entries(result.summary.updated || {});
  const skipped = result.summary.skipped || [];

  return (
    <Card className="border-green-200 bg-green-50">
      <CardContent className="space-y-3 p-4 text-sm text-green-800">
        <div className="flex items-center gap-2 font-semibold">
          <CheckCircle2 className="h-4 w-4" />
          {result.message}
        </div>
        {deleted.length > 0 && (
          <div>
            <div className="font-medium">Deleted</div>
            <div className="mt-1 flex flex-wrap gap-2">
              {deleted.map(([key, value]) => (
                <Badge key={key} variant="outline" className="bg-white">
                  {key}: {value}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {updated.length > 0 && (
          <div>
            <div className="font-medium">Updated</div>
            <div className="mt-1 flex flex-wrap gap-2">
              {updated.map(([key, value]) => (
                <Badge key={key} variant="outline" className="bg-white">
                  {key}: {value}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {skipped.length > 0 && (
          <div className="text-yellow-700">
            Skipped: {skipped.join(", ")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function SettingsPage() {
  const navigate = useNavigate();
  const { setTheme } = useTheme();
  const {
    user,
    isLoading: isSessionLoading,
    logout,
    planLabel,
    refreshSession,
  } = useAuthSession();

  const [name, setName] = useState("");
  const [currentScore, setCurrentScore] = useState("550");
  const [targetScore, setTargetScore] = useState("750");
  const [examDate, setExamDate] = useState("");
  const [studyMinutesPerDay, setStudyMinutesPerDay] = useState("30");
  const [weakSkills, setWeakSkills] = useState<string[]>([]);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordFormOpen, setPasswordFormOpen] = useState(false);
  const [experience, setExperience] = useState<ExperiencePreferences>(defaultExperience);
  const [notifications, setNotifications] =
    useState<NotificationPreferences>(defaultNotifications);
  const [subscription, setSubscription] = useState<CurrentSubscription | null>(null);
  const [accountMessage, setAccountMessage] = useState<string | null>(null);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [learningMessage, setLearningMessage] = useState<string | null>(null);
  const [learningError, setLearningError] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [experienceError, setExperienceError] = useState<string | null>(null);
  const [notificationsError, setNotificationsError] = useState<string | null>(null);
  const [subscriptionError, setSubscriptionError] = useState<string | null>(null);
  const [privacyError, setPrivacyError] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<DangerousActionResult | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingLearning, setIsSavingLearning] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isRegeneratingRoadmap, setIsRegeneratingRoadmap] = useState(false);
  const [isLoadingExperience, setIsLoadingExperience] = useState(false);
  const [isSavingExperience, setIsSavingExperience] = useState(false);
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(false);
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);
  const [dangerAction, setDangerAction] = useState<
    "reset-progress" | "delete-history" | "delete-account" | null
  >(null);

  useEffect(() => {
    if (!user) return;

    setName(user.name || "");
    setCurrentScore(String(user.currentScore ?? 550));
    setTargetScore(String(user.targetScore ?? 750));
    setExamDate(toInputDate(user.examDate));
    setStudyMinutesPerDay(String(user.studyMinutesPerDay ?? 30));
    setWeakSkills(user.weakSkills || []);
  }, [user]);

  useEffect(() => {
    if (isSessionLoading || !user) return;

    let cancelled = false;

    async function loadSettings() {
      setIsLoadingExperience(true);
      setIsLoadingNotifications(true);
      setExperienceError(null);
      setNotificationsError(null);

      try {
        const [nextExperience, nextNotifications, currentSubscription] =
          await Promise.all([
            settingsService.getPreferences(),
            settingsService.getNotifications(),
            subscriptionService.getCurrent().catch((error) => {
              setSubscriptionError(
                error instanceof Error
                  ? error.message
                  : "Could not load subscription.",
              );
              return null;
            }),
          ]);

        if (cancelled) return;
        setExperience(nextExperience);
        setTheme(nextExperience.themeMode);
        setNotifications(nextNotifications);
        setSubscription(currentSubscription);
      } catch (error) {
        if (!cancelled) {
          const message =
            error instanceof Error ? error.message : "Could not load settings.";
          setExperienceError(message);
          setNotificationsError(message);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingExperience(false);
          setIsLoadingNotifications(false);
        }
      }
    }

    void loadSettings();

    return () => {
      cancelled = true;
    };
  }, [isSessionLoading, setTheme, user]);

  const displayEmail = user?.email || "";
  const currentPlan = subscription?.plan || user?.plan || "free";
  const isPro = currentPlan.toLowerCase() === "pro";
  const currentPlanLabel = isPro ? "Pro Plan" : planLabel || "Free Plan";
  const planExpiryText = subscription?.planExpiredAt
    ? new Date(subscription.planExpiredAt).toLocaleDateString("vi-VN")
    : null;
  const isLocalAccount = (user?.provider || "local").toLowerCase() === "local";
  const avatarFallback = useMemo(
    () => buildInitials(user?.name, user?.email),
    [user?.email, user?.name],
  );
  const reminderTimeDisabled =
    !notifications.dailyReminderEnabled &&
    !notifications.weeklyCheckReminderEnabled;

  const toggleWeakSkill = (value: string) => {
    setWeakSkills((prev) =>
      prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value],
    );
  };

  const updateExperienceDraft = <K extends keyof ExperiencePreferences>(
    key: K,
    value: ExperiencePreferences[K],
  ) => {
    setExperience((prev) => ({ ...prev, [key]: value }));
  };

  const updateNotificationsDraft = <K extends keyof NotificationPreferences>(
    key: K,
    value: NotificationPreferences[K],
  ) => {
    setNotifications((prev) => ({ ...prev, [key]: value }));
  };

  const handleSaveProfile = async () => {
    setAccountMessage(null);
    setAccountError(null);
    setIsSavingProfile(true);

    try {
      const updated = await authService.updateProfile({ name });
      setName(updated.name || "");
      await refreshSession();
      setAccountMessage("Profile saved.");
      toast.success("Da luu profile.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save profile.";
      setAccountError(message);
      toast.error(message);
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleSaveLearning = async () => {
    setLearningMessage(null);
    setLearningError(null);
    setIsSavingLearning(true);

    try {
      const updated = await authService.updateLearningSettings({
        currentScore: parseOptionalNumber(currentScore),
        targetScore: parseOptionalNumber(targetScore),
        examDate: examDate || null,
        studyMinutesPerDay: parseOptionalNumber(studyMinutesPerDay),
        weakSkills,
      });
      setCurrentScore(String(updated.currentScore ?? 550));
      setTargetScore(String(updated.targetScore ?? 750));
      setExamDate(toInputDate(updated.examDate));
      setStudyMinutesPerDay(String(updated.studyMinutesPerDay ?? 30));
      setWeakSkills(updated.weakSkills || []);
      await refreshSession();
      setLearningMessage("Learning settings saved.");
      toast.success("Da luu muc tieu hoc tap.");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not save learning settings.";
      setLearningError(message);
      toast.error(message);
    } finally {
      setIsSavingLearning(false);
    }
  };

  const handleChangePassword = async () => {
    setPasswordMessage(null);
    setPasswordError(null);

    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }

    setIsChangingPassword(true);
    try {
      await authService.changePassword({ currentPassword, newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordFormOpen(false);
      setPasswordMessage("Password changed successfully.");
      toast.success("Da doi mat khau.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not change password.";
      setPasswordError(message);
      toast.error(message);
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleSaveExperience = async () => {
    const previous = experience;
    setIsSavingExperience(true);
    setExperienceError(null);

    try {
      const saved = await settingsService.updatePreferences(experience);
      setExperience(saved);
      setTheme(saved.themeMode);
      toast.success("Da luu tuy chon trai nghiem.");
    } catch (error) {
      setExperience(previous);
      const message =
        error instanceof Error ? error.message : "Could not save preferences.";
      setExperienceError(message);
      toast.error(message);
    } finally {
      setIsSavingExperience(false);
    }
  };

  const handleSaveNotifications = async () => {
    setIsSavingNotifications(true);
    setNotificationsError(null);

    try {
      const saved = await settingsService.updateNotifications(notifications);
      setNotifications(saved);
      toast.success("Da luu tuy chon nhac hoc cho tai khoan cua ban.");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not save notifications.";
      setNotificationsError(message);
      toast.error(message);
    } finally {
      setIsSavingNotifications(false);
    }
  };

  const handleRegenerateRoadmap = async () => {
    setIsRegeneratingRoadmap(true);

    try {
      await roadmapService.generateCurrent();
      toast.success("Da tao lai roadmap.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not regenerate roadmap.");
    } finally {
      setIsRegeneratingRoadmap(false);
    }
  };

  const runDangerAction = async (
    action: "reset-progress" | "delete-history" | "delete-account",
  ) => {
    setDangerAction(action);
    setPrivacyError(null);
    setActionResult(null);

    try {
      const result =
        action === "reset-progress"
          ? await settingsService.resetProgress()
          : action === "delete-history"
            ? await settingsService.deleteHistory()
            : await settingsService.deleteAccount(deleteConfirm);

      setActionResult(result);
      toast.success(result.message);

      if (action === "delete-account") {
        logout();
        navigate("/login");
        return;
      }

      await refreshSession();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Dangerous action failed.";
      setPrivacyError(message);
      toast.error(message);
    } finally {
      setDangerAction(null);
      if (action === "delete-account") setDeleteConfirm("");
    }
  };

  if (isSessionLoading) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Loading settings from FastAPI...
        </CardContent>
      </Card>
    );
  }

  if (!user) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Settings require sign in</CardTitle>
          <CardDescription>
            The settings page is backed by your authenticated FastAPI account.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to="/login">Go to login</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Cai dat</h1>
        <p className="mt-1 text-muted-foreground">
          Quan ly tai khoan va tuy chinh trai nghiem hoc tap tu backend state.
        </p>
      </div>

      <Tabs defaultValue="account" className="space-y-6">
        <TabsList className="grid w-full max-w-3xl grid-cols-6">
          <TabsTrigger value="account" className="gap-2">
            <User className="h-4 w-4" />
            <span className="hidden sm:inline">Tai khoan</span>
          </TabsTrigger>
          <TabsTrigger value="learning" className="gap-2">
            <BookOpen className="h-4 w-4" />
            <span className="hidden sm:inline">Hoc tap</span>
          </TabsTrigger>
          <TabsTrigger value="experience" className="gap-2">
            <Palette className="h-4 w-4" />
            <span className="hidden sm:inline">Trai nghiem</span>
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-2">
            <Bell className="h-4 w-4" />
            <span className="hidden sm:inline">Thong bao</span>
          </TabsTrigger>
          <TabsTrigger value="subscription" className="gap-2">
            <CreditCard className="h-4 w-4" />
            <span className="hidden sm:inline">Goi</span>
          </TabsTrigger>
          <TabsTrigger value="privacy" className="gap-2">
            <Shield className="h-4 w-4" />
            <span className="hidden sm:inline">Rieng tu</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="account" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Thong tin ca nhan</CardTitle>
              <CardDescription>
                Profile doc va ghi qua JWT user hien tai.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <StatusMessage type="success">{accountMessage}</StatusMessage>
              <StatusMessage type="error">{accountError}</StatusMessage>

              <div className="flex items-center gap-6">
                <Avatar className="h-20 w-20">
                  <AvatarImage src={user.avatarUrl || undefined} />
                  <AvatarFallback className="bg-primary/10 text-2xl text-primary">
                    {avatarFallback}
                  </AvatarFallback>
                </Avatar>
                <div className="space-y-2">
                  <Button variant="outline" className="gap-2" disabled>
                    <Camera className="h-4 w-4" />
                    Thay doi anh
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Avatar upload can file upload contract rieng nen chua bat trong scope nay.
                  </p>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Ho va ten</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" value={displayEmail} disabled />
                  <p className="text-xs text-muted-foreground">
                    Email la dinh danh dang nhap nen khong sua tai day.
                  </p>
                </div>
              </div>

              <div className="rounded-xl border p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <Label>Mat khau</Label>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {isLocalAccount
                        ? "Doi mat khau bang endpoint /api/auth/change-password."
                        : "Tai khoan Google khong doi mat khau trong app nay."}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => setPasswordFormOpen((value) => !value)}
                    disabled={!isLocalAccount}
                  >
                    {passwordFormOpen ? "Dong" : "Doi mat khau"}
                  </Button>
                </div>

                <StatusMessage type="success">{passwordMessage}</StatusMessage>
                <StatusMessage type="error">{passwordError}</StatusMessage>

                {passwordFormOpen && (
                  <div className="mt-4 grid gap-4 md:grid-cols-3">
                    <div className="space-y-2">
                      <Label htmlFor="current-password">Mat khau hien tai</Label>
                      <Input
                        id="current-password"
                        type="password"
                        value={currentPassword}
                        onChange={(event) => setCurrentPassword(event.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="new-password">Mat khau moi</Label>
                      <Input
                        id="new-password"
                        type="password"
                        value={newPassword}
                        onChange={(event) => setNewPassword(event.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="confirm-password">Nhap lai mat khau moi</Label>
                      <Input
                        id="confirm-password"
                        type="password"
                        value={confirmPassword}
                        onChange={(event) => setConfirmPassword(event.target.value)}
                      />
                    </div>
                    <div className="md:col-span-3">
                      <Button
                        onClick={() => void handleChangePassword()}
                        disabled={
                          isChangingPassword ||
                          !currentPassword ||
                          !newPassword ||
                          !confirmPassword
                        }
                      >
                        {isChangingPassword ? "Dang doi..." : "Luu mat khau moi"}
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between border-t pt-4">
                <Button
                  onClick={() => void handleSaveProfile()}
                  disabled={isSavingProfile}
                >
                  {isSavingProfile ? "Dang luu..." : "Luu profile"}
                </Button>
                <Button
                  variant="outline"
                  className="gap-2 text-destructive hover:text-destructive"
                  onClick={() => {
                    logout();
                    navigate("/login");
                  }}
                >
                  <LogOut className="h-4 w-4" />
                  Dang xuat
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="learning" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Muc tieu hoc tap</CardTitle>
              <CardDescription>
                Cac gia tri nay luu vao Users va duoc roadmap/practice doc lai.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <StatusMessage type="success">{learningMessage}</StatusMessage>
              <StatusMessage type="error">{learningError}</StatusMessage>

              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Diem hien tai
                  </Label>
                  <Select value={currentScore} onValueChange={setCurrentScore}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="250">250 diem</SelectItem>
                      <SelectItem value="350">350 diem</SelectItem>
                      <SelectItem value="450">450 diem</SelectItem>
                      <SelectItem value="550">550 diem</SelectItem>
                      <SelectItem value="650">650 diem</SelectItem>
                      <SelectItem value="750">750 diem</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Diem TOEIC muc tieu
                  </Label>
                  <Select value={targetScore} onValueChange={setTargetScore}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="550">550 diem</SelectItem>
                      <SelectItem value="650">650 diem</SelectItem>
                      <SelectItem value="750">750 diem</SelectItem>
                      <SelectItem value="850">850 diem</SelectItem>
                      <SelectItem value="900">900+ diem</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Ngay thi du kien
                  </Label>
                  <Input
                    type="date"
                    value={examDate}
                    onChange={(event) => setExamDate(event.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Thoi luong hoc moi ngay
                  </Label>
                  <Select
                    value={studyMinutesPerDay}
                    onValueChange={setStudyMinutesPerDay}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="15">15 phut/ngay</SelectItem>
                      <SelectItem value="30">30 phut/ngay</SelectItem>
                      <SelectItem value="45">45 phut/ngay</SelectItem>
                      <SelectItem value="60">60 phut/ngay</SelectItem>
                      <SelectItem value="90">90 phut/ngay</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Ky nang can cai thien</Label>
                <div className="flex flex-wrap gap-2">
                  {learningSkillTags.map((tag) => {
                    const active = weakSkills.includes(tag.value);
                    return (
                      <Button
                        key={tag.value}
                        type="button"
                        variant={active ? "default" : "outline"}
                        size="sm"
                        onClick={() => toggleWeakSkill(tag.value)}
                      >
                        {tag.label}
                      </Button>
                    );
                  })}
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
                <Button
                  onClick={() => void handleSaveLearning()}
                  disabled={isSavingLearning}
                >
                  {isSavingLearning ? "Dang luu..." : "Luu muc tieu"}
                </Button>
                <div className="flex flex-wrap gap-3">
                  <Button variant="outline" size="sm" asChild>
                    <Link to="/placement-test">Lam lai bai chan doan</Link>
                  </Button>
                  <Button
                    variant="outline"
                    className="gap-2"
                    onClick={() => void handleRegenerateRoadmap()}
                    disabled={isRegeneratingRoadmap}
                  >
                    <RefreshCcw className="h-4 w-4" />
                    {isRegeneratingRoadmap ? "Dang tao..." : "Tao lai roadmap"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="experience" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Trai nghiem</CardTitle>
              <CardDescription>
                Cac tuy chon nay doc/ghi qua /api/settings/preferences.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <StatusMessage type="info">
                {statusText(experienceError, isLoadingExperience, "preferences")}
              </StatusMessage>

              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label>Che do giao dien</Label>
                  <p className="text-sm text-muted-foreground">
                    Theme duoc ap dung tren trinh duyet hien tai sau khi luu.
                  </p>
                </div>
                <Select
                  value={experience.themeMode}
                  onValueChange={(value: ThemeMode) =>
                    updateExperienceDraft("themeMode", value)
                  }
                  disabled={isLoadingExperience}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="system">Theo he thong</SelectItem>
                    <SelectItem value="light">Sang</SelectItem>
                    <SelectItem value="dark">Toi</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label>Ngon ngu</Label>
                  <p className="text-sm text-muted-foreground">
                    Luu lua chon ngon ngu cho tai khoan.
                  </p>
                </div>
                <Select
                  value={experience.language}
                  onValueChange={(value: LanguageCode) =>
                    updateExperienceDraft("language", value)
                  }
                  disabled={isLoadingExperience}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="vi">Tieng Viet</SelectItem>
                    <SelectItem value="en">English</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label>Am thanh thong bao</Label>
                  <p className="text-sm text-muted-foreground">
                    Bat/tat am thanh thong bao trong app.
                  </p>
                </div>
                <Switch
                  checked={experience.notificationSoundEnabled}
                  onCheckedChange={(checked) =>
                    updateExperienceDraft("notificationSoundEnabled", checked)
                  }
                  disabled={isLoadingExperience}
                />
              </div>

              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label>Tu dong phat audio</Label>
                  <p className="text-sm text-muted-foreground">
                    Preference nay duoc luu de cac bai Listening su dung.
                  </p>
                </div>
                <Switch
                  checked={experience.autoPlayAudio}
                  onCheckedChange={(checked) =>
                    updateExperienceDraft("autoPlayAudio", checked)
                  }
                  disabled={isLoadingExperience}
                />
              </div>

              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label>AI giai thich tu dong</Label>
                  <p className="text-sm text-muted-foreground">
                    Luu preference hien thi giai thich AI sau cau sai.
                  </p>
                </div>
                <Switch
                  checked={experience.autoAiExplanation}
                  onCheckedChange={(checked) =>
                    updateExperienceDraft("autoAiExplanation", checked)
                  }
                  disabled={isLoadingExperience}
                />
              </div>

              <div className="border-t pt-4">
                <Button
                  onClick={() => void handleSaveExperience()}
                  disabled={isSavingExperience || isLoadingExperience}
                >
                  {isSavingExperience ? "Dang luu..." : "Luu trai nghiem"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Thong bao</CardTitle>
              <CardDescription>
                Backend luu preference that; scheduler se doc cac gia tri nay khi duoc bat.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <StatusMessage type="info">
                {statusText(notificationsError, isLoadingNotifications, "notifications")}
              </StatusMessage>

              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label>Nhac hoc hang ngay</Label>
                  <p className="text-sm text-muted-foreground">
                    Luu trang thai daily reminder cho tai khoan.
                  </p>
                </div>
                <Switch
                  checked={notifications.dailyReminderEnabled}
                  onCheckedChange={(checked) =>
                    updateNotificationsDraft("dailyReminderEnabled", checked)
                  }
                  disabled={isLoadingNotifications}
                />
              </div>

              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label>Nhac weekly check</Label>
                  <p className="text-sm text-muted-foreground">
                    Luu trang thai weekly check reminder.
                  </p>
                </div>
                <Switch
                  checked={notifications.weeklyCheckReminderEnabled}
                  onCheckedChange={(checked) =>
                    updateNotificationsDraft("weeklyCheckReminderEnabled", checked)
                  }
                  disabled={isLoadingNotifications}
                />
              </div>

              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label>Thong bao qua email</Label>
                  <p className="text-sm text-muted-foreground">
                    Luu preference email notification, khong gia lap gui email.
                  </p>
                </div>
                <Switch
                  checked={notifications.emailNotificationsEnabled}
                  onCheckedChange={(checked) =>
                    updateNotificationsDraft("emailNotificationsEnabled", checked)
                  }
                  disabled={isLoadingNotifications}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Gio nhac nho</Label>
                  <Input
                    type="time"
                    value={notifications.reminderTimeLocal}
                    onChange={(event) =>
                      updateNotificationsDraft("reminderTimeLocal", event.target.value)
                    }
                    disabled={isLoadingNotifications || reminderTimeDisabled}
                  />
                  {reminderTimeDisabled && (
                    <p className="text-xs text-muted-foreground">
                      Bat daily hoac weekly reminder de sua gio nhac.
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label>Timezone</Label>
                  <Input
                    value={notifications.timezone}
                    onChange={(event) =>
                      updateNotificationsDraft("timezone", event.target.value)
                    }
                    disabled={isLoadingNotifications}
                  />
                </div>
              </div>

              <div className="border-t pt-4">
                <Button
                  onClick={() => void handleSaveNotifications()}
                  disabled={isSavingNotifications || isLoadingNotifications}
                >
                  {isSavingNotifications ? "Dang luu..." : "Luu thong bao"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="subscription" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Crown className="h-5 w-5 text-yellow-500" />
                Goi dich vu hien tai
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between rounded-xl border bg-muted/50 p-4">
                <div className="flex items-center gap-4">
                  <div className="rounded-xl bg-primary/10 p-3">
                    <CreditCard className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{currentPlanLabel}</h3>
                      <Badge variant={isPro ? undefined : "secondary"}>
                        Dang su dung
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {isPro
                        ? planExpiryText
                          ? `Pro con hieu luc den ${planExpiryText}`
                          : "Tai khoan dang mo khoa Pro"
                        : "Goi mien phi co ban"}
                    </p>
                    <StatusMessage type="error">{subscriptionError}</StatusMessage>
                  </div>
                </div>
                {!isPro && (
                  <Button className="gap-2" asChild>
                    <Link to="/pricing">
                      <Crown className="h-4 w-4" />
                      Nang cap Pro
                    </Link>
                  </Button>
                )}
              </div>

              <div className="space-y-2">
                <h4 className="font-medium">Tinh nang dang co:</h4>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {(isPro
                    ? [
                        "AI Tutor unlimited",
                        "Mock test va weekly check",
                        "Advanced roadmap/progress",
                      ]
                    : subscriptionFeatures
                  ).map((feature) => (
                    <li key={feature} className="flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="privacy" className="space-y-6">
          <StatusMessage type="error">{privacyError}</StatusMessage>
          <ActionSummary result={actionResult} />

          <Card>
            <CardHeader>
              <CardTitle>Du lieu hoc tap</CardTitle>
              <CardDescription>
                Cac hanh dong nay chi tac dong du lieu cua current JWT user.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between gap-4 rounded-xl border p-4">
                <div className="space-y-1">
                  <Label>Reset tien do hoc tap</Label>
                  <p className="text-sm text-muted-foreground">
                    Xoa progress, review queue, roadmap, stats va attempt history cua ban.
                    Khong xoa TOEIC question bank/media/static files.
                  </p>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="outline">Reset tien do</Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Reset tien do hoc tap?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Hanh dong nay xoa attempts, answers, review queue, progress logs,
                        skill stats va roadmap cua tai khoan hien tai. Noi dung TOEIC goc
                        va media se khong bi dung toi.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Huy</AlertDialogCancel>
                      <AlertDialogAction asChild>
                        <Button
                          variant="destructive"
                          onClick={() => void runDangerAction("reset-progress")}
                          disabled={dangerAction === "reset-progress"}
                        >
                          {dangerAction === "reset-progress" ? "Dang reset..." : "Xac nhan reset"}
                        </Button>
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>

              <div className="flex items-center justify-between gap-4 rounded-xl border p-4">
                <div className="space-y-1">
                  <Label>Xoa lich su lam bai</Label>
                  <p className="text-sm text-muted-foreground">
                    Xoa practice/mock attempts, answers, review queue va stats cache lien quan.
                  </p>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="outline">Xoa lich su</Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Xoa lich su lam bai?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Hanh dong nay chi xoa lich su attempts cua tai khoan hien tai
                        va cac cache phu thuoc. Account va TOEIC content giu nguyen.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Huy</AlertDialogCancel>
                      <AlertDialogAction asChild>
                        <Button
                          variant="destructive"
                          onClick={() => void runDangerAction("delete-history")}
                          disabled={dangerAction === "delete-history"}
                        >
                          {dangerAction === "delete-history" ? "Dang xoa..." : "Xac nhan xoa"}
                        </Button>
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </CardContent>
          </Card>

          <Card className="border-destructive/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                Vung nguy hiem
              </CardTitle>
              <CardDescription>
                Delete account duoc thuc hien bang soft-delete de khong lam crash FK.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between gap-4 rounded-xl border border-destructive/20 bg-destructive/5 p-4">
                <div className="space-y-1">
                  <Label className="text-destructive">Xoa tai khoan</Label>
                  <p className="text-sm text-muted-foreground">
                    Tai khoan se bi deactivate, token cu bi chan, email/password duoc vo hieu hoa.
                  </p>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="destructive" className="gap-2">
                      <Trash2 className="h-4 w-4" />
                      Xoa tai khoan
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Xoa tai khoan?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Nhap DELETE de xac nhan. Sau khi thanh cong, app se logout va
                        chuyen ve trang dang nhap.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <div className="space-y-2">
                      <Label htmlFor="delete-confirm">Nhap DELETE</Label>
                      <Input
                        id="delete-confirm"
                        value={deleteConfirm}
                        onChange={(event) => setDeleteConfirm(event.target.value)}
                        placeholder="DELETE"
                      />
                    </div>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Huy</AlertDialogCancel>
                      <AlertDialogAction asChild>
                        <Button
                          variant="destructive"
                          onClick={() => void runDangerAction("delete-account")}
                          disabled={
                            dangerAction === "delete-account" ||
                            deleteConfirm !== "DELETE"
                          }
                        >
                          {dangerAction === "delete-account" ? "Dang xoa..." : "Xoa tai khoan"}
                        </Button>
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
