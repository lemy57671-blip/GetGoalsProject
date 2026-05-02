from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    message: str | None = None
    reply: str | None = None


class QualityGuard:
    max_message_length = 4000
    direct_data_patterns = (
        r"\bselect\s+.+\s+from\b",
        r"\binsert\s+into\b",
        r"\bupdate\s+\w+\s+set\b",
        r"\bdelete\s+from\b",
        r"\bdrop\s+table\b",
        r"\brun\s+sql\b",
        r"\bexecute\s+sql\b",
        r"\bdump\s+(the\s+)?database\b",
        r"\ball\s+users\b",
        r"\bsystem\s+prompt\b",
    )

    def check_user_message(self, message: str | None) -> GuardResult:
        cleaned = (message or "").strip()
        if not cleaned:
            return GuardResult(allowed=False, reply="Please enter a message first.")
        if len(cleaned) > self.max_message_length:
            cleaned = cleaned[: self.max_message_length]

        lowered = cleaned.lower()
        if any(re.search(pattern, lowered, flags=re.IGNORECASE | re.DOTALL) for pattern in self.direct_data_patterns):
            return GuardResult(
                allowed=False,
                reply=(
                    "Mình không thể chạy SQL, trích xuất dữ liệu thô, hoặc tiết lộ system prompt. "
                    "Bạn có thể hỏi mình phân tích TOEIC, lỗi sai, câu hỏi, hoặc kế hoạch học dựa trên ngữ cảnh học tập đã được backend lọc an toàn."
                ),
            )
        return GuardResult(allowed=True, message=cleaned)

    def clean_reply(self, reply: str | None) -> str:
        cleaned = (reply or "").strip()
        if not cleaned:
            return "Mình chưa tạo được phản hồi. Bạn thử hỏi lại ngắn hơn nhé."
        cleaned = re.sub(r"```sql[\s\S]*?```", "[SQL removed]", cleaned, flags=re.IGNORECASE)
        return cleaned
