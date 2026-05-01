from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE_DIR / "ml_models"

RASCH_MODEL_PATH = MODEL_DIR / "rasch_model.json"
SCORE_MAPPER_PATH = MODEL_DIR / "score_mapper.json"


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def estimate_theta_given_b(u_row: list[float], b: list[float], iters: int = 50) -> float:
    """
    Bám sát code cũ:

        p = sigmoid(th - bb)
        g = np.sum(u - p)
        h = -np.sum(p * (1 - p)) - 1e-6
        step = g / h
        th = th - step
    """

    if not u_row or not b:
        return 0.0

    u = np.asarray(u_row, dtype=float)
    bb = np.asarray(b, dtype=float)

    if len(u) != len(bb):
        min_len = min(len(u), len(bb))
        u = u[:min_len]
        bb = bb[:min_len]

    th = 0.0

    for _ in range(iters):
        p = sigmoid(th - bb)
        g = np.sum(u - p)
        h = -np.sum(p * (1.0 - p)) - 1e-6
        step = g / h
        th = th - step

        if abs(step) < 1e-4:
            break

    return float(th)


def theta_to_score(theta: float, mapper: dict | None) -> int:
    """
    Bám sát score_mapper cũ:
        score = c + a * theta
        score = clip(score, clip_min, clip_max)
    """

    if not mapper:
        score = 495.0 + 180.0 * float(theta)
        score = np.clip(score, 0, 990)
        return int(round(float(score)))

    a = float(mapper.get("a", 180.0))
    c = float(mapper.get("c", 495.0))
    clip_min = float(mapper.get("clip_min", 0))
    clip_max = float(mapper.get("clip_max", 990))

    score = c + a * float(theta)
    score = np.clip(score, clip_min, clip_max)

    return int(round(float(score)))


def level_from_score(score: int) -> tuple[str, str, str]:
    if score <= 450:
        return "starter", "Starter", "250-450"

    if score <= 600:
        return "elementary", "Elementary", "450-600"

    if score <= 750:
        return "intermediate", "Intermediate", "600-750"

    if score <= 850:
        return "upper_intermediate", "Upper Intermediate", "750-850"

    return "advanced", "Advanced", "850-990"


def score_diagnostic_with_rasch(answered_items: Iterable[dict]) -> dict:
    """
    answered_items chỉ nên chứa các câu đã có kết quả đúng/sai.

    Input:
        [
            {"item_id": 1, "is_correct": True},
            {"item_id": 2, "is_correct": False}
        ]

    item_id map với ToeicQuestions.LegacyQuestionId.
    Câu không có trong answered_items sẽ bị bỏ qua, giống logic xử lý missing của code cũ.
    """

    rasch_model = load_json(RASCH_MODEL_PATH)
    score_mapper = load_json(SCORE_MAPPER_PATH)

    items = list(answered_items)

    total_answered = len(items)
    correct_count = sum(1 for item in items if bool(item.get("is_correct")))

    fallback_score = int(round((correct_count / total_answered) * 990)) if total_answered else 0

    if not rasch_model or "item_ids" not in rasch_model or "b" not in rasch_model:
        level_code, level_name, level_range = level_from_score(fallback_score)

        return {
            "theta": None,
            "estimated_score": fallback_score,
            "level_code": level_code,
            "level_name": level_name,
            "level_range": level_range,
            "model_used": "rule_accuracy",
        }

    model_item_ids = [int(x) for x in rasch_model["item_ids"]]
    model_b = [float(x) for x in rasch_model["b"]]

    answer_by_item_id = {
        int(item["item_id"]): 1.0 if bool(item.get("is_correct")) else 0.0
        for item in items
        if item.get("item_id") is not None
    }

    u_row: list[float] = []
    b_row: list[float] = []

    for item_id, difficulty in zip(model_item_ids, model_b):
        if item_id not in answer_by_item_id:
            continue

        u_row.append(answer_by_item_id[item_id])
        b_row.append(difficulty)

    theta = estimate_theta_given_b(u_row, b_row)
    estimated_score = theta_to_score(theta, score_mapper)
    level_code, level_name, level_range = level_from_score(estimated_score)

    return {
        "theta": theta,
        "estimated_score": estimated_score,
        "level_code": level_code,
        "level_name": level_name,
        "level_range": level_range,
        "model_used": "rasch",
    }