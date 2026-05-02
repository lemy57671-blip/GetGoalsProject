from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    NVARCHAR,
    UnicodeText,
)
from sqlalchemy.orm import declarative_base, relationship, synonym
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "Users"

    id = Column("Id", Integer, primary_key=True, index=True)
    name = Column("Name", NVARCHAR(200), nullable=False)
    email = Column("Email", NVARCHAR(255), nullable=False, unique=True, index=True)
    password_hash = Column("PasswordHash", NVARCHAR(500), nullable=True)
    avatar_url = Column("AvatarUrl", NVARCHAR(1000), nullable=False, default="")
    provider = Column("Provider", NVARCHAR(50), nullable=False, default="local")
    provider_id = Column("ProviderId", NVARCHAR(255), nullable=True)
    onboarding_completed = Column("OnboardingCompleted", Boolean, nullable=False, default=False)
    current_score = Column("CurrentScore", Integer, nullable=True)
    target_score = Column("TargetScore", Integer, nullable=True)
    exam_date = Column("ExamDate", Date, nullable=True)
    study_minutes_per_day = Column("StudyMinutesPerDay", Integer, nullable=True)
    weak_skills_json = Column("WeakSkillsJson", UnicodeText, nullable=False, default="[]")
    subscription_plan = Column("SubscriptionPlan", NVARCHAR(50), nullable=False, default="free")
    plan_expired_at = Column("PlanExpiredAt", DateTime, nullable=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())
    last_login_at_utc = Column("LastLoginAtUtc", DateTime, nullable=True)

    plan = synonym("subscription_plan")

    Id = synonym("id")
    Name = synonym("name")
    Email = synonym("email")
    PasswordHash = synonym("password_hash")
    AvatarUrl = synonym("avatar_url")
    Provider = synonym("provider")
    ProviderId = synonym("provider_id")
    OnboardingCompleted = synonym("onboarding_completed")
    CurrentScore = synonym("current_score")
    TargetScore = synonym("target_score")
    ExamDate = synonym("exam_date")
    StudyMinutesPerDay = synonym("study_minutes_per_day")
    WeakSkillsJson = synonym("weak_skills_json")
    SubscriptionPlan = synonym("subscription_plan")
    PlanExpiredAt = synonym("plan_expired_at")
    CreatedAtUtc = synonym("created_at_utc")
    LastLoginAtUtc = synonym("last_login_at_utc")


class Course(Base):
    __tablename__ = "Courses"

    id = Column("Id", Integer, primary_key=True)
    title = Column("Title", NVARCHAR(255), nullable=False)
    author = Column("Author", NVARCHAR(255), nullable=False, default="")
    rating = Column("Rating", Numeric(5, 2), nullable=False, default=0)


class Enrollment(Base):
    __tablename__ = "Enrollments"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    course_id = Column("CourseId", Integer, ForeignKey("Courses.Id"), nullable=False, index=True)
    progress_percent = Column("ProgressPercent", Integer, nullable=False, default=0)

    user = relationship("User")
    course = relationship("Course")


class ProgressLog(Base):
    __tablename__ = "ProgressLogs"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    course_id = Column("CourseId", Integer, ForeignKey("Courses.Id"), nullable=False, index=True)
    minutes_learned = Column("MinutesLearned", Integer, nullable=False, default=0)
    progress_delta = Column("ProgressDelta", Integer, nullable=False, default=0)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")
    course = relationship("Course")


class PaymentOrder(Base):
    __tablename__ = "PaymentOrders"

    id = Column("Id", Integer, primary_key=True)
    order_code = Column("OrderCode", NVARCHAR(100), nullable=False, unique=True, index=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    plan_code = Column("PlanCode", NVARCHAR(50), nullable=False)
    amount = Column("Amount", Numeric(18, 2), nullable=False)
    status = Column("Status", NVARCHAR(50), nullable=False, default="pending")
    payos_order_code = Column("PayOsOrderCode", BigInteger, nullable=True, index=True)
    checkout_url = Column("CheckoutUrl", NVARCHAR(1000), nullable=True)
    qr_code = Column("QrCode", UnicodeText, nullable=True)
    payos_payment_link_id = Column("PayOsPaymentLinkId", NVARCHAR(255), nullable=True)
    paid_by_webhook_signature = Column("PaidByWebhookSignature", NVARCHAR(500), nullable=True)
    transfer_content = Column("TransferContent", NVARCHAR(255), nullable=True)
    created_at = Column("CreatedAt", DateTime, nullable=False, server_default=func.sysutcdatetime())
    expired_at = Column("ExpiredAt", DateTime, nullable=False)
    paid_at = Column("PaidAt", DateTime, nullable=True)

    user = relationship("User")


class ChatConversation(Base):
    __tablename__ = "ChatConversations"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    title = Column("Title", NVARCHAR(255), nullable=False, default="")
    created_at = Column("CreatedAt", DateTime, nullable=False, server_default=func.sysutcdatetime())
    updated_at = Column("UpdatedAt", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "ChatMessages"

    id = Column("Id", Integer, primary_key=True)
    conversation_id = Column("ConversationId", Integer, ForeignKey("ChatConversations.Id"), nullable=False, index=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    role = Column("Role", NVARCHAR(20), nullable=False)
    content = Column("Content", UnicodeText, nullable=False, default="")
    intent = Column("Intent", NVARCHAR(100), nullable=True)
    created_at = Column("CreatedAt", DateTime, nullable=False, server_default=func.sysutcdatetime())

    conversation = relationship("ChatConversation", back_populates="messages")
    user = relationship("User")


class PracticeAttempt(Base):
    __tablename__ = "PracticeAttempts"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    title = Column("Title", NVARCHAR(255), nullable=False)
    subtitle = Column("Subtitle", NVARCHAR(255), nullable=True)
    mode = Column("Mode", NVARCHAR(50), nullable=False)
    parts = Column("Parts", NVARCHAR(100), nullable=True)
    difficulty = Column("Difficulty", NVARCHAR(50), nullable=True)
    total_questions = Column("TotalQuestions", Integer, nullable=False, default=0)
    answered_count = Column("AnsweredCount", Integer, nullable=False, default=0)
    correct_count = Column("CorrectCount", Integer, nullable=False, default=0)
    accuracy_pct = Column("AccuracyPct", Numeric(7, 2), nullable=False, default=0)
    score = Column("Score", Integer, nullable=True)
    time_spent_seconds = Column("TimeSpentSeconds", Integer, nullable=False, default=0)
    started_at_utc = Column("StartedAtUtc", DateTime, nullable=True)
    submitted_at_utc = Column("SubmittedAtUtc", DateTime, nullable=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")
    answers = relationship(
        "PracticeAttemptAnswer",
        back_populates="practice_attempt",
        cascade="all, delete-orphan",
    )


class PracticeAttemptAnswer(Base):
    __tablename__ = "PracticeAttemptAnswers"

    id = Column("Id", Integer, primary_key=True)
    practice_attempt_id = Column("PracticeAttemptId", Integer, ForeignKey("PracticeAttempts.Id"), nullable=False, index=True)
    question_id = Column("QuestionId", Integer, nullable=False, index=True)
    question_number = Column("QuestionNumber", Integer, nullable=True)
    part = Column("Part", Integer, nullable=True)
    skill = Column("Skill", NVARCHAR(100), nullable=True)
    selected_answer_index = Column("SelectedAnswerIndex", Integer, nullable=True)
    correct_answer_index = Column("CorrectAnswerIndex", Integer, nullable=True)
    is_correct = Column("IsCorrect", Boolean, nullable=False, default=False)
    is_flagged = Column("IsFlagged", Boolean, nullable=False, default=False)
    explanation = Column("Explanation", UnicodeText, nullable=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    practice_attempt = relationship("PracticeAttempt", back_populates="answers")


class MockTestAttempt(Base):
    __tablename__ = "MockTestAttempts"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    title = Column("Title", NVARCHAR(255), nullable=False)
    total_questions = Column("TotalQuestions", Integer, nullable=False, default=0)
    answered_count = Column("AnsweredCount", Integer, nullable=False, default=0)
    correct_count = Column("CorrectCount", Integer, nullable=False, default=0)
    listening_score = Column("ListeningScore", Integer, nullable=True)
    reading_score = Column("ReadingScore", Integer, nullable=True)
    total_score = Column("TotalScore", Integer, nullable=True)
    accuracy_pct = Column("AccuracyPct", Numeric(7, 2), nullable=False, default=0)
    time_spent_seconds = Column("TimeSpentSeconds", Integer, nullable=False, default=0)
    status = Column("Status", NVARCHAR(50), nullable=True)
    started_at_utc = Column("StartedAtUtc", DateTime, nullable=True)
    submitted_at_utc = Column("SubmittedAtUtc", DateTime, nullable=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")
    answers = relationship(
        "MockTestAttemptAnswer",
        back_populates="mock_test_attempt",
        cascade="all, delete-orphan",
    )


class MockTestAttemptAnswer(Base):
    __tablename__ = "MockTestAttemptAnswers"

    id = Column("Id", Integer, primary_key=True)
    mock_test_attempt_id = Column("MockTestAttemptId", Integer, ForeignKey("MockTestAttempts.Id"), nullable=False, index=True)
    question_id = Column("QuestionId", Integer, nullable=False, index=True)
    question_number = Column("QuestionNumber", Integer, nullable=True)
    part = Column("Part", Integer, nullable=True)
    skill = Column("Skill", NVARCHAR(100), nullable=True)
    selected_answer_index = Column("SelectedAnswerIndex", Integer, nullable=True)
    correct_answer_index = Column("CorrectAnswerIndex", Integer, nullable=True)
    is_correct = Column("IsCorrect", Boolean, nullable=False, default=False)
    is_flagged = Column("IsFlagged", Boolean, nullable=False, default=False)
    explanation = Column("Explanation", UnicodeText, nullable=True)

    mock_test_attempt = relationship("MockTestAttempt", back_populates="answers")


class ReviewQueueItem(Base):
    __tablename__ = "ReviewQueue"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    question_id = Column("QuestionId", Integer, nullable=False, index=True)
    part = Column("Part", Integer, nullable=True)
    skill = Column("Skill", NVARCHAR(100), nullable=True)
    status = Column("Status", NVARCHAR(50), nullable=False, default="pending")
    source_attempt_type = Column("SourceAttemptType", NVARCHAR(50), nullable=True)
    source_attempt_id = Column("SourceAttemptId", Integer, nullable=True)
    note = Column("Note", UnicodeText, nullable=True)
    added_at_utc = Column("AddedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())
    reviewed_at_utc = Column("ReviewedAtUtc", DateTime, nullable=True)

    user = relationship("User")


class UserQuestionNote(Base):
    __tablename__ = "UserQuestionNotes"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    question_id = Column("QuestionId", Integer, nullable=False, index=True)
    attempt_id = Column("AttemptId", Integer, nullable=True)
    note_text = Column("NoteText", UnicodeText, nullable=False)
    created_at = Column("CreatedAt", DateTime, nullable=False, server_default=func.sysutcdatetime())
    updated_at = Column("UpdatedAt", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")


class UserQuestionHighlight(Base):
    __tablename__ = "UserQuestionHighlights"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    question_id = Column("QuestionId", Integer, nullable=False, index=True)
    attempt_id = Column("AttemptId", Integer, nullable=True)
    target_type = Column("TargetType", NVARCHAR(50), nullable=False)
    target_key = Column("TargetKey", NVARCHAR(20), nullable=True)
    selected_text = Column("SelectedText", UnicodeText, nullable=False)
    start_offset = Column("StartOffset", Integer, nullable=True)
    end_offset = Column("EndOffset", Integer, nullable=True)
    color = Column("Color", NVARCHAR(30), nullable=False, default="yellow")
    note_text = Column("NoteText", UnicodeText, nullable=True)
    created_at = Column("CreatedAt", DateTime, nullable=False, server_default=func.sysutcdatetime())
    updated_at = Column("UpdatedAt", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")


class UserQuestionBookmark(Base):
    __tablename__ = "UserQuestionBookmarks"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    question_id = Column("QuestionId", Integer, nullable=False, index=True)
    attempt_id = Column("AttemptId", Integer, nullable=True)
    created_at = Column("CreatedAt", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")


class UserSkillProfile(Base):
    __tablename__ = "UserSkillProfiles"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    skill_code = Column("SkillCode", NVARCHAR(100), nullable=False, index=True)
    skill_name = Column("SkillName", NVARCHAR(255), nullable=True)
    accuracy_pct = Column("AccuracyPct", Numeric(7, 2), nullable=False, default=0)
    correct_count = Column("CorrectCount", Integer, nullable=False, default=0)
    attempt_count = Column("AttemptCount", Integer, nullable=False, default=0)
    last_practiced_at_utc = Column("LastPracticedAtUtc", DateTime, nullable=True)
    updated_at_utc = Column("UpdatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")


class UserPartStat(Base):
    __tablename__ = "UserPartStats"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    part = Column("Part", Integer, nullable=False, index=True)
    accuracy_pct = Column("AccuracyPct", Numeric(7, 2), nullable=False, default=0)
    correct_count = Column("CorrectCount", Integer, nullable=False, default=0)
    attempt_count = Column("AttemptCount", Integer, nullable=False, default=0)
    average_time_seconds = Column("AverageTimeSeconds", Integer, nullable=False, default=0)
    updated_at_utc = Column("UpdatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")


class UserSkillAnalytics(Base):
    __tablename__ = "UserSkillAnalytics"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, unique=True, index=True)
    weakest_skill = Column("WeakestSkill", NVARCHAR(100), nullable=True)
    weakest_skill_label = Column("WeakestSkillLabel", NVARCHAR(255), nullable=True)
    weakest_part = Column("WeakestPart", Integer, nullable=True)
    top_weak_subskills_json = Column("TopWeakSubskillsJson", UnicodeText, nullable=True)
    skill_breakdown_json = Column("SkillBreakdownJson", UnicodeText, nullable=True)
    subskill_breakdown_json = Column("SubskillBreakdownJson", UnicodeText, nullable=True)
    part_breakdown_json = Column("PartBreakdownJson", UnicodeText, nullable=True)
    based_on_attempt_id = Column("BasedOnAttemptId", Integer, nullable=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())
    updated_at_utc = Column("UpdatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")


class UserRoadmap(Base):
    __tablename__ = "UserRoadmaps"

    id = Column("Id", Integer, primary_key=True)
    user_id = Column("UserId", Integer, ForeignKey("Users.Id"), nullable=False, index=True)
    title = Column("Title", NVARCHAR(255), nullable=False)
    source_type = Column("SourceType", NVARCHAR(100), nullable=False)
    based_on_attempt_id = Column("BasedOnAttemptId", Integer, nullable=True)
    weakest_skill = Column("WeakestSkill", NVARCHAR(100), nullable=True)
    weakest_skill_label = Column("WeakestSkillLabel", NVARCHAR(255), nullable=True)
    weakest_part = Column("WeakestPart", Integer, nullable=True)
    total_weeks = Column("TotalWeeks", Integer, nullable=False, default=8)
    is_active = Column("IsActive", Boolean, nullable=False, default=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())
    updated_at_utc = Column("UpdatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    user = relationship("User")
    weeks = relationship(
        "UserRoadmapWeek",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="UserRoadmapWeek.week_number",
    )


class UserRoadmapWeek(Base):
    __tablename__ = "UserRoadmapWeeks"

    id = Column("Id", Integer, primary_key=True)
    roadmap_id = Column("RoadmapId", Integer, ForeignKey("UserRoadmaps.Id"), nullable=False, index=True)
    week_number = Column("WeekNumber", Integer, nullable=False)
    title = Column("Title", NVARCHAR(255), nullable=False)
    description = Column("Description", UnicodeText, nullable=True)
    focus_skill = Column("FocusSkill", NVARCHAR(100), nullable=True)
    focus_part = Column("FocusPart", Integer, nullable=True)
    subskills_json = Column("SubskillsJson", UnicodeText, nullable=True)
    recommended_question_count = Column("RecommendedQuestionCount", Integer, nullable=False, default=0)
    estimated_minutes = Column("EstimatedMinutes", Integer, nullable=False, default=0)
    status = Column("Status", NVARCHAR(50), nullable=False, default="not_started")
    sort_order = Column("SortOrder", Integer, nullable=False, default=0)
    started_at_utc = Column("StartedAtUtc", DateTime, nullable=True)
    completed_at_utc = Column("CompletedAtUtc", DateTime, nullable=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())
    updated_at_utc = Column("UpdatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    roadmap = relationship("UserRoadmap", back_populates="weeks")
    items = relationship(
        "UserRoadmapWeekItem",
        back_populates="roadmap_week",
        cascade="all, delete-orphan",
        order_by="UserRoadmapWeekItem.sort_order",
    )


class UserRoadmapWeekItem(Base):
    __tablename__ = "UserRoadmapWeekItems"

    id = Column("Id", Integer, primary_key=True)
    roadmap_week_id = Column("RoadmapWeekId", Integer, ForeignKey("UserRoadmapWeeks.Id"), nullable=False, index=True)
    item_type = Column("ItemType", NVARCHAR(50), nullable=False)
    set_key = Column("SetKey", NVARCHAR(100), nullable=True)
    title = Column("Title", NVARCHAR(255), nullable=False)
    description = Column("Description", UnicodeText, nullable=True)
    focus_skill = Column("FocusSkill", NVARCHAR(100), nullable=True)
    focus_part = Column("FocusPart", Integer, nullable=True)
    subskills_json = Column("SubskillsJson", UnicodeText, nullable=True)
    question_count = Column("QuestionCount", Integer, nullable=False, default=0)
    difficulty = Column("Difficulty", NVARCHAR(50), nullable=True)
    tags_json = Column("TagsJson", UnicodeText, nullable=True)
    metadata_json = Column("MetadataJson", UnicodeText, nullable=True)
    sort_order = Column("SortOrder", Integer, nullable=False, default=0)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())
    updated_at_utc = Column("UpdatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    roadmap_week = relationship("UserRoadmapWeek", back_populates="items")


class ToeicSet(Base):
    __tablename__ = "ToeicSets"

    id = Column("Id", Integer, primary_key=True)
    code = Column("Code", NVARCHAR(100), nullable=False, index=True)
    title = Column("Title", NVARCHAR(255), nullable=False)
    type = Column("Type", NVARCHAR(50), nullable=False, index=True)
    test_number = Column("TestNumber", Integer, nullable=True, index=True)
    part = Column("Part", Integer, nullable=True)
    is_active = Column("IsActive", Boolean, nullable=False, default=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    passages = relationship("ToeicPassage", back_populates="set")
    questions = relationship("ToeicQuestion", back_populates="set")


class ToeicPassage(Base):
    __tablename__ = "ToeicPassages"

    id = Column("Id", Integer, primary_key=True)
    set_id = Column("SetId", Integer, ForeignKey("ToeicSets.Id"), nullable=False, index=True)
    group_code = Column("GroupCode", NVARCHAR(100), nullable=True, index=True)
    part = Column("Part", Integer, nullable=False)
    title = Column("Title", NVARCHAR(255), nullable=True)
    passage_text = Column("PassageText", UnicodeText, nullable=True)
    audio_path = Column("AudioPath", NVARCHAR(1000), nullable=True)
    image_path = Column("ImagePath", NVARCHAR(1000), nullable=True)
    sort_order = Column("SortOrder", Integer, nullable=False, default=0)

    set = relationship("ToeicSet", back_populates="passages")
    questions = relationship("ToeicQuestion", back_populates="passage")
    assets = relationship(
        "ToeicQuestionAsset",
        back_populates="passage",
        foreign_keys="ToeicQuestionAsset.passage_id",
    )


class ToeicQuestion(Base):
    __tablename__ = "ToeicQuestions"

    id = Column("Id", Integer, primary_key=True)
    set_id = Column("SetId", Integer, ForeignKey("ToeicSets.Id"), nullable=False, index=True)
    passage_id = Column("PassageId", Integer, ForeignKey("ToeicPassages.Id"), nullable=True, index=True)
    legacy_question_id = Column("LegacyQuestionId", Integer, nullable=True)
    test_number = Column("TestNumber", Integer, nullable=True, index=True)
    question_number = Column("QuestionNumber", Integer, nullable=False, index=True)
    part = Column("Part", Integer, nullable=False, index=True)
    skill_code = Column("SkillCode", NVARCHAR(100), nullable=True)
    subskill_code = Column("SubskillCode", NVARCHAR(100), nullable=True)
    topic = Column("Topic", NVARCHAR(255), nullable=True)
    difficulty = Column("Difficulty", NVARCHAR(50), nullable=True)
    question_text = Column("QuestionText", UnicodeText, nullable=False)
    explanation = Column("Explanation", UnicodeText, nullable=True)
    correct_option_key = Column("CorrectOptionKey", NVARCHAR(10), nullable=True)
    transcript = Column("Transcript", UnicodeText, nullable=True)
    sort_order = Column("SortOrder", Integer, nullable=False, default=0)
    is_active = Column("IsActive", Boolean, nullable=False, default=True)
    section = Column("Section", NVARCHAR(50), nullable=True)
    part_label = Column("PartLabel", NVARCHAR(100), nullable=True)
    question_type = Column("QuestionType", NVARCHAR(100), nullable=True)
    group_code = Column("GroupCode", NVARCHAR(100), nullable=True)
    ability_band = Column("AbilityBand", NVARCHAR(100), nullable=True)
    min_score = Column("MinScore", Integer, nullable=True)
    max_score = Column("MaxScore", Integer, nullable=True)
    audio_url = Column("AudioUrl", NVARCHAR(1000), nullable=True)

    set = relationship("ToeicSet", back_populates="questions")
    passage = relationship("ToeicPassage", back_populates="questions")
    options = relationship(
        "ToeicQuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="ToeicQuestionOption.sort_order",
    )
    assets = relationship(
        "ToeicQuestionAsset",
        back_populates="question",
        foreign_keys="ToeicQuestionAsset.question_id",
        order_by="ToeicQuestionAsset.sort_order",
    )


class ToeicQuestionOption(Base):
    __tablename__ = "ToeicQuestionOptions"

    id = Column("Id", Integer, primary_key=True)
    question_id = Column("QuestionId", Integer, ForeignKey("ToeicQuestions.Id"), nullable=False, index=True)
    option_key = Column("OptionKey", NVARCHAR(10), nullable=False)
    option_text = Column("OptionText", UnicodeText, nullable=False)
    sort_order = Column("SortOrder", Integer, nullable=False, default=0)

    question = relationship("ToeicQuestion", back_populates="options")


class ToeicQuestionAsset(Base):
    __tablename__ = "ToeicQuestionAssets"

    id = Column("Id", Integer, primary_key=True)
    question_id = Column("QuestionId", Integer, ForeignKey("ToeicQuestions.Id"), nullable=True, index=True)
    passage_id = Column("PassageId", Integer, ForeignKey("ToeicPassages.Id"), nullable=True, index=True)
    asset_type = Column("AssetType", NVARCHAR(50), nullable=False)
    relative_path = Column("RelativePath", NVARCHAR(1000), nullable=True)
    sort_order = Column("SortOrder", Integer, nullable=False, default=0)

    question = relationship("ToeicQuestion", back_populates="assets", foreign_keys=[question_id])
    passage = relationship("ToeicPassage", back_populates="assets", foreign_keys=[passage_id])


class FlashcardTopic(Base):
    __tablename__ = "FlashcardTopics"

    id = Column("Id", Integer, primary_key=True)
    code = Column("Code", NVARCHAR(100), nullable=False, index=True)
    title = Column("Title", NVARCHAR(255), nullable=False)
    description = Column("Description", UnicodeText, nullable=True)
    icon = Column("Icon", NVARCHAR(50), nullable=True)
    color = Column("Color", NVARCHAR(50), nullable=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    cards = relationship("Flashcard", back_populates="topic", cascade="all, delete-orphan")


class Flashcard(Base):
    __tablename__ = "Flashcards"

    id = Column("Id", Integer, primary_key=True)
    topic_id = Column("TopicId", Integer, ForeignKey("FlashcardTopics.Id"), nullable=False, index=True)
    word = Column("Word", NVARCHAR(255), nullable=False)
    pos = Column("Pos", NVARCHAR(50), nullable=True)
    phonetic = Column("Phonetic", NVARCHAR(255), nullable=True)
    meaning = Column("Meaning", UnicodeText, nullable=False)
    example = Column("Example", UnicodeText, nullable=True)
    created_at_utc = Column("CreatedAtUtc", DateTime, nullable=False, server_default=func.sysutcdatetime())

    topic = relationship("FlashcardTopic", back_populates="cards")
