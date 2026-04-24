from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status_code: int, content: dict):
        super().__init__(content.get("message") or f"API error {status_code}")
        self.status_code = status_code
        self.content = content


def unauthorized_error() -> ApiError:
    return ApiError(401, {"message": "Unauthorized"})


def pro_required_error() -> ApiError:
    return ApiError(403, {"message": "Pro plan required", "code": "PRO_REQUIRED"})
