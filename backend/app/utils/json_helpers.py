from __future__ import annotations

import json
from typing import TypeVar


T = TypeVar("T")


def deserialize_list(raw: str | None) -> list[T]:
    if not raw or not raw.strip():
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return value
    except json.JSONDecodeError:
        pass
    return []


def parse_string_list(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return []
    values = deserialize_list(raw)
    if values:
        return [str(item).strip() for item in values if str(item).strip()]
    return [
        part.strip()
        for part in raw.replace("\r", "\n").replace(";", ",").replace("|", ",").split(",")
        if part.strip()
    ]
