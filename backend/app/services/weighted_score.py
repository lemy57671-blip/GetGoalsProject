from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import exp
from typing import Any, Iterable

import numpy as np

from app.services.irt_scoring import RASCH_MODEL_PATH, load_json


DEFAULT_ALPHA = 0.35
DEFAULT_SCORE_MIN = 0
DEFAULT_SCORE_MAX = 990
WEIGHT_MIN = 0.7
WEIGHT_MAX = 1.3


@dataclass(frozen=True)
class WeightedScoreResult:
    weight_score: int
    weighted_correct: float
    weighted_total: float
    weight_score_ratio: float


def compute_weighted_score(u_row: np.ndarray, b_row: np.ndarray) -> int:
    result = _compute_weighted_score_result(u_row, b_row)
    return result.weight_score


def compute_weight_score(
    answered_items: Iterable[Any],
    *,
    alpha: float = DEFAULT_ALPHA,
    score_min: int = DEFAULT_SCORE_MIN,
    score_max: int = DEFAULT_SCORE_MAX,
) -> WeightedScoreResult:
    """
    Difficulty-weighted score used by diagnostic hybrid scoring.

    Items with lower Rasch b are easier and receive lower weight; items with
    higher b are harder and receive higher weight. The score can also be
    returned independently for analysis/debugging.
    """

    _ = alpha

    u_values: list[float] = []
    b_values: list[float] = []
    for item in answered_items:
        if not _is_answered(item):
            continue

        u_values.append(
            1.0 if _as_bool(_get_value(item, "is_correct", "isCorrect", "correct")) else 0.0
        )
        b_values.append(_resolve_difficulty_for_weighting(item))

    return _compute_weighted_score_result(
        np.asarray(u_values, dtype=float),
        np.asarray(b_values, dtype=float),
        score_min=score_min,
        score_max=score_max,
    )


def _compute_weighted_score_result(
    u_row: np.ndarray,
    b_row: np.ndarray,
    *,
    score_min: int = DEFAULT_SCORE_MIN,
    score_max: int = DEFAULT_SCORE_MAX,
) -> WeightedScoreResult:
    if len(u_row) == 0 or len(b_row) == 0:
        return WeightedScoreResult(
            weight_score=0,
            weighted_correct=0.0,
            weighted_total=0.0,
            weight_score_ratio=0.0,
        )

    min_len = min(len(u_row), len(b_row))
    u_row = np.asarray(u_row[:min_len], dtype=float)
    b_row = np.asarray(b_row[:min_len], dtype=float)

    mask = (~np.isnan(u_row)) & (~np.isnan(b_row))
    u = u_row[mask]
    difficulties = b_row[mask]

    if len(u) == 0:
        return WeightedScoreResult(
            weight_score=0,
            weighted_correct=0.0,
            weighted_total=0.0,
            weight_score_ratio=0.0,
        )

    min_b = float(np.min(difficulties))
    max_b = float(np.max(difficulties))

    if max_b == min_b:
        weights = np.ones_like(difficulties, dtype=float)
    else:
        normalized = (difficulties - min_b) / (max_b - min_b)
        weights = WEIGHT_MIN + normalized * (WEIGHT_MAX - WEIGHT_MIN)

    weighted_correct = float(np.sum(weights * u))
    weighted_total = float(np.sum(weights))
    ratio = 0.0 if weighted_total <= 0 else max(0.0, min(weighted_correct / weighted_total, 1.0))
    raw_score = int(round(ratio * float(score_max)))
    score = int(np.clip(raw_score, score_min, score_max))

    return WeightedScoreResult(
        weight_score=score,
        weighted_correct=round(weighted_correct, 4),
        weighted_total=round(weighted_total, 4),
        weight_score_ratio=round(ratio, 6),
    )


def compute_weight_score_fields(
    answered_items: Iterable[Any],
    *,
    alpha: float = DEFAULT_ALPHA,
    score_min: int = DEFAULT_SCORE_MIN,
    score_max: int = DEFAULT_SCORE_MAX,
) -> dict[str, int | float]:
    result = compute_weight_score(
        answered_items,
        alpha=alpha,
        score_min=score_min,
        score_max=score_max,
    )
    return {
        "weight_score": result.weight_score,
        "weighted_score": result.weight_score,
        "weighted_correct": result.weighted_correct,
        "weighted_total": result.weighted_total,
        "weight_score_ratio": result.weight_score_ratio,
    }


def _resolve_difficulty_for_weighting(item: Any) -> float:
    difficulty = _resolve_numeric_difficulty(item)
    if difficulty is None:
        difficulty = _difficulty_label_to_normalized(
            _get_value(item, "difficulty", "Difficulty", "item_difficulty", "itemDifficulty")
        )
        if difficulty is None:
            return float("nan")
        return float(difficulty)

    return float(difficulty)


def _resolve_numeric_difficulty(item: Any) -> float | None:
    direct = _coerce_float(_get_value(item, "b", "difficulty_b", "difficultyB", "item_b", "itemB"))
    if direct is not None:
        return direct

    explicit_difficulty = _coerce_float(_get_value(item, "difficulty", "Difficulty", "item_difficulty", "itemDifficulty"))
    if explicit_difficulty is not None:
        return explicit_difficulty

    item_id = _coerce_int(_get_value(item, "item_id", "itemId", "legacy_id", "legacyId"))
    if item_id is None:
        item_id = _coerce_int(_get_value(item, "question_id", "questionId"))

    if item_id is None:
        return None

    return _rasch_difficulty_by_item_id().get(item_id)


def _normalize_numeric_difficulty(difficulty: float) -> float:
    min_b, max_b = _rasch_difficulty_bounds()
    if min_b is None or max_b is None or max_b <= min_b:
        return 1.0 / (1.0 + exp(-float(difficulty)))

    normalized = (float(difficulty) - min_b) / (max_b - min_b)
    return max(0.0, min(normalized, 1.0))


def _difficulty_label_to_normalized(value: Any) -> float | None:
    label = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not label or label in {"mixed", "unknown", "none", "null"}:
        return None

    label_map = {
        "easy": 0.0,
        "starter": 0.0,
        "beginner": 0.0,
        "low": 0.0,
        "medium": 0.5,
        "intermediate": 0.5,
        "normal": 0.5,
        "hard": 1.0,
        "advanced": 1.0,
        "high": 1.0,
    }
    return label_map.get(label)


def _is_answered(item: Any) -> bool:
    sentinel = object()
    selected = _get_value(
        item,
        "selected_answer_index",
        "selectedAnswerIndex",
        "selected",
        "answer",
        default=sentinel,
    )
    if selected is sentinel:
        return True
    return selected is not None and selected != ""


@lru_cache(maxsize=1)
def _rasch_difficulty_by_item_id() -> dict[int, float]:
    model = load_json(RASCH_MODEL_PATH) or {}
    item_ids = model.get("item_ids") or []
    difficulties = model.get("b") or []
    result: dict[int, float] = {}

    for item_id, difficulty in zip(item_ids, difficulties):
        parsed_id = _coerce_int(item_id)
        parsed_difficulty = _coerce_float(difficulty)
        if parsed_id is None or parsed_difficulty is None:
            continue
        result[parsed_id] = parsed_difficulty

    return result


@lru_cache(maxsize=1)
def _rasch_difficulty_bounds() -> tuple[float | None, float | None]:
    values = list(_rasch_difficulty_by_item_id().values())
    if not values:
        return None, None
    return min(values), max(values)


def _get_value(item: Any, *keys: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        for key in keys:
            if key in item:
                return item[key]
        return default

    for key in keys:
        if hasattr(item, key):
            return getattr(item, key)

    return default


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "correct", "right"}
