from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.irt_scoring import RASCH_MODEL_PATH, load_json  # noqa: E402
from app.services.weighted_score import compute_weight_score  # noqa: E402


def main() -> None:
    model = load_json(RASCH_MODEL_PATH) or {}
    pairs = sorted(
        (int(item_id), float(difficulty))
        for item_id, difficulty in zip(model.get("item_ids", []), model.get("b", []))
    )
    pairs_by_difficulty = sorted(pairs, key=lambda item: item[1])

    easy_ids = [item_id for item_id, _ in pairs_by_difficulty[:10]]
    hard_ids = [item_id for item_id, _ in pairs_by_difficulty[-10:]]

    easy_correct_attempt = [
        {"item_id": item_id, "is_correct": True, "selected_answer_index": 0}
        for item_id in easy_ids
    ] + [
        {"item_id": item_id, "is_correct": False, "selected_answer_index": 1}
        for item_id in hard_ids
    ]
    hard_correct_attempt = [
        {"item_id": item_id, "is_correct": False, "selected_answer_index": 1}
        for item_id in easy_ids
    ] + [
        {"item_id": item_id, "is_correct": True, "selected_answer_index": 0}
        for item_id in hard_ids
    ]

    easy_result = compute_weight_score(easy_correct_attempt)
    hard_result = compute_weight_score(hard_correct_attempt)

    assert hard_result.weight_score > easy_result.weight_score, (
        hard_result,
        easy_result,
    )

    easy_all_correct = compute_weight_score(
        [
            {"item_id": item_id, "is_correct": True, "selected_answer_index": 0}
            for item_id in easy_ids
        ]
    )
    hard_all_correct = compute_weight_score(
        [
            {"item_id": item_id, "is_correct": True, "selected_answer_index": 0}
            for item_id in hard_ids
        ]
    )
    assert hard_all_correct.weight_score > easy_all_correct.weight_score, (
        hard_all_correct,
        easy_all_correct,
    )

    fallback_result = compute_weight_score(
        [
            {"item_id": 999001, "is_correct": True, "selected_answer_index": 0},
            {"item_id": 999002, "is_correct": False, "selected_answer_index": 1},
        ]
    )
    assert fallback_result.weighted_correct == 1.0
    assert fallback_result.weighted_total == 2.0
    assert fallback_result.weight_score_ratio == 0.5

    print("weight_score verification passed")
    print(
        {
            "easy_score": easy_result.weight_score,
            "hard_score": hard_result.weight_score,
            "easy_all_correct_score": easy_all_correct.weight_score,
            "hard_all_correct_score": hard_all_correct.weight_score,
            "fallback_ratio": fallback_result.weight_score_ratio,
        }
    )


if __name__ == "__main__":
    main()
