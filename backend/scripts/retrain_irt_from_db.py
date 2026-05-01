from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
from sqlalchemy import create_engine, text


# =========================================================
# PATH CONFIG
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "app"
MODEL_DIR = APP_DIR / "ml_models"

RASCH_MODEL_PATH = MODEL_DIR / "rasch_model.json"
SCORE_MAPPER_PATH = MODEL_DIR / "score_mapper.json"
CALIBRATION_REPORT_PATH = MODEL_DIR / "calibration_report.csv"


# =========================================================
# RASCH / IRT LOGIC - BÁM SÁT CODE PyAI CŨ
# =========================================================

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def fit_rasch_jml(U, max_iter=200, lr=0.3, reg=0.01, seed=42):
    """
    Joint Maximum Likelihood cho Rasch.

    Bám sát logic cũ:

        P(u_ni = 1) = sigmoid(theta_n - b_i)

    U:
        rows = DiagnosticAttemptId
        cols = LegacyQuestionId
        values:
            1.0 = đúng
            0.0 = sai
            np.nan = missing / bỏ trống / không có dữ liệu
    """

    rng = np.random.default_rng(seed)
    N, I = U.shape

    theta = rng.normal(0, 0.5, size=N)
    b = rng.normal(0, 0.5, size=I)

    mask = ~np.isnan(U)
    U0 = np.where(mask, U, 0.0)

    denom_theta = np.sum(mask, axis=1) + 1e-6
    denom_b = np.sum(mask, axis=0) + 1e-6

    for _ in range(max_iter):
        D = theta[:, None] - b[None, :]
        P = sigmoid(D)

        E = (U0 - P) * mask

        g_theta = np.sum(E, axis=1) - reg * theta
        theta = theta + lr * (g_theta / denom_theta)

        g_b = -np.sum(E, axis=0) - reg * b
        b = b + lr * (g_b / denom_b)

        # Giống code cũ: chuẩn hóa lại scale
        b = b - np.mean(b)
        theta = theta - np.mean(theta)

    return theta, b


def estimate_theta_given_b(u_row, b, iters=50):
    """
    Estimate theta cho 1 attempt khi đã có item difficulty b.

    Bám sát code cũ:

        mask = ~np.isnan(u_row)
        u = u_row[mask]
        bb = b[mask]

        p = sigmoid(th - bb)
        g = np.sum(u - p)
        h = -np.sum(p * (1 - p)) - 1e-6
        step = g / h
        th = th - step

    Missing / blank = np.nan -> bỏ qua.
    """

    u_row = np.asarray(u_row, dtype=float)
    b = np.asarray(b, dtype=float)

    mask = ~np.isnan(u_row)
    u = u_row[mask]
    bb = b[mask]

    if len(u) == 0:
        return 0.0

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


def fit_linear_mapper(theta_arr, toeic_arr):
    """
    Train score_mapper:

        TrueToeic ≈ a * theta + c

    Bám sát logic calibration cũ.
    """

    x = np.asarray(theta_arr, dtype=float)
    y = np.asarray(toeic_arr, dtype=float)

    if len(x) == 0:
        return 180.0, 495.0

    x_mean = x.mean()
    y_mean = y.mean()

    denom = np.sum((x - x_mean) ** 2)

    if denom <= 1e-9:
        a = 180.0
        c = 495.0
    else:
        a = np.sum((x - x_mean) * (y - y_mean)) / denom
        c = y_mean - a * x_mean

    return float(a), float(c)


def evaluate_predictions(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    within_50 = float(np.mean(np.abs(y_true - y_pred) <= 50) * 100.0)
    within_75 = float(np.mean(np.abs(y_true - y_pred) <= 75) * 100.0)
    within_100 = float(np.mean(np.abs(y_true - y_pred) <= 100) * 100.0)

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "within_50_pct": round(within_50, 2),
        "within_75_pct": round(within_75, 2),
        "within_100_pct": round(within_100, 2),
    }


# =========================================================
# DATABASE
# =========================================================

def load_dotenv_if_exists():
    """
    Load .env đơn giản để script có thể đọc SQLSERVER_CONNECTION_STRING.
    Không cần cài python-dotenv.
    """

    env_path = BACKEND_DIR / ".env"

    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            os.environ.setdefault(key, value)


def get_engine():
    """
    Dùng SQLSERVER_CONNECTION_STRING trong .env.

    Hỗ trợ 2 dạng:

    1. SQLAlchemy URL:
       mssql+pyodbc:///?odbc_connect=...

    2. ODBC raw string:
       DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...;...
    """

    load_dotenv_if_exists()

    conn = os.getenv("SQLSERVER_CONNECTION_STRING")

    if not conn:
        raise RuntimeError(
            "Thiếu SQLSERVER_CONNECTION_STRING trong .env hoặc environment."
        )

    if conn.startswith("mssql+"):
        return create_engine(conn, pool_pre_ping=True)

    sqlalchemy_url = "mssql+pyodbc:///?odbc_connect=" + quote_plus(conn)
    return create_engine(sqlalchemy_url, pool_pre_ping=True)


def fetch_training_rows(engine):
    """
    Lấy toàn bộ data để train Rasch b.

    Không lọc CorrectCount.
    Không lọc AnsweredCount.
    Không lọc thời gian.
    Không lọc TrueToeic.

    Chỉ cần:
    - Có DiagnosticAttemptAnswers
    - Join được DiagnosticAttempts
    - Join được ToeicQuestions để lấy LegacyQuestionId
    """

    sql = text(
        """
        SELECT
            da.Id AS DiagnosticAttemptId,
            da.UserId,
            q.LegacyQuestionId AS ItemId,
            daa.SelectedAnswerIndex,
            daa.IsCorrect,
            da.CorrectCount,
            da.AnsweredCount,
            da.TotalQuestions,
            da.TrueToeic,
            da.SubmittedAtUtc
        FROM dbo.DiagnosticAttemptAnswers daa
        JOIN dbo.DiagnosticAttempts da
            ON da.Id = daa.DiagnosticAttemptId
        JOIN dbo.ToeicQuestions q
            ON q.Id = daa.QuestionId
        WHERE
            q.LegacyQuestionId IS NOT NULL
        ORDER BY
            da.Id ASC,
            q.LegacyQuestionId ASC
        """
    )

    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def fetch_calibration_rows(engine, attempt_ids: list[int]):
    """
    Lấy data để train score_mapper.

    Bám sát logic cũ:
    - Chỉ cần attempt có Theta
    - Và có TrueToeic
    - Không thêm filter nhiễu
    """

    if not attempt_ids:
        return []

    attempt_ids_csv = ",".join(str(x) for x in attempt_ids)

    sql = text(
        """
        SELECT
            da.Id AS DiagnosticAttemptId,
            da.UserId,
            da.Theta,
            da.TrueToeic,
            da.EstimatedScore,
            da.CorrectCount,
            da.AnsweredCount,
            da.TotalQuestions,
            da.SubmittedAtUtc
        FROM dbo.DiagnosticAttempts da
        WHERE
            da.Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(:attempt_ids_csv, ',')
            )
            AND da.Theta IS NOT NULL
            AND da.TrueToeic IS NOT NULL
        ORDER BY
            da.Id ASC
        """
    )

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "attempt_ids_csv": attempt_ids_csv,
            },
        ).mappings().all()


def update_attempt_thetas(engine, theta_by_attempt_id: dict[int, float]):
    """
    Update lại DiagnosticAttempts.Theta sau khi train Rasch b mới.
    """

    if not theta_by_attempt_id:
        return

    sql = text(
        """
        UPDATE dbo.DiagnosticAttempts
        SET Theta = :theta
        WHERE Id = :attempt_id
        """
    )

    payload = [
        {
            "attempt_id": int(attempt_id),
            "theta": float(theta),
        }
        for attempt_id, theta in theta_by_attempt_id.items()
    ]

    with engine.begin() as conn:
        conn.execute(sql, payload)


def update_attempt_estimated_scores(engine, score_by_attempt_id: dict[int, int]):
    """
    Sau khi train score_mapper mới, update lại EstimatedScore cho các attempt đã có theta.
    """

    if not score_by_attempt_id:
        return

    sql = text(
        """
        UPDATE dbo.DiagnosticAttempts
        SET EstimatedScore = :estimated_score
        WHERE Id = :attempt_id
        """
    )

    payload = [
        {
            "attempt_id": int(attempt_id),
            "estimated_score": int(score),
        }
        for attempt_id, score in score_by_attempt_id.items()
    ]

    with engine.begin() as conn:
        conn.execute(sql, payload)


# =========================================================
# MATRIX BUILDING
# =========================================================

def is_blank_answer(selected_answer_index) -> bool:
    """
    Bám sát missing logic cũ:
    nếu không có selected answer thì xem là missing -> np.nan.
    """

    if selected_answer_index is None:
        return True

    try:
        return int(selected_answer_index) < 0
    except Exception:
        return True


def build_response_matrix(rows):
    """
    Build ma trận U từ database.

    rows:
        DiagnosticAttemptId
        ItemId = LegacyQuestionId
        SelectedAnswerIndex
        IsCorrect

    Output:
        U
        attempt_ids
        item_ids
    """

    attempt_ids = sorted({int(row["DiagnosticAttemptId"]) for row in rows})
    item_ids = sorted({int(row["ItemId"]) for row in rows})

    attempt_index = {attempt_id: idx for idx, attempt_id in enumerate(attempt_ids)}
    item_index = {item_id: idx for idx, item_id in enumerate(item_ids)}

    U = np.full((len(attempt_ids), len(item_ids)), np.nan, dtype=float)

    for row in rows:
        attempt_id = int(row["DiagnosticAttemptId"])
        item_id = int(row["ItemId"])

        n = attempt_index[attempt_id]
        i = item_index[item_id]

        if is_blank_answer(row["SelectedAnswerIndex"]):
            U[n, i] = np.nan
        else:
            U[n, i] = 1.0 if bool(row["IsCorrect"]) else 0.0

    return U, attempt_ids, item_ids


# =========================================================
# SAVE FILES
# =========================================================

def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_calibration_report(rows: list[dict]):
    CALIBRATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        return

    fieldnames = [
        "DiagnosticAttemptId",
        "UserId",
        "theta",
        "true_toeic",
        "pred_score",
        "abs_error",
    ]

    with CALIBRATION_REPORT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# =========================================================
# MAIN PIPELINE
# =========================================================

def retrain():
    engine = get_engine()

    print("Đang lấy dữ liệu từ database...")
    rows = fetch_training_rows(engine)

    if not rows:
        print("Không có dữ liệu DiagnosticAttemptAnswers hợp lệ để train.")
        sys.exit(1)

    U, attempt_ids, item_ids = build_response_matrix(rows)

    observed = int(np.sum(~np.isnan(U)))

    if observed == 0:
        print("Ma trận U không có response nào hợp lệ.")
        sys.exit(1)

    print("Build response matrix xong:")
    print(f"- Attempts: {len(attempt_ids)}")
    print(f"- Items: {len(item_ids)}")
    print(f"- Observed responses: {observed}")

    print("Đang train Rasch model...")
    theta_jml, b = fit_rasch_jml(
        U,
        max_iter=200,
        lr=0.3,
        reg=0.01,
        seed=42,
    )

    rasch_model = {
        "item_ids": [int(x) for x in item_ids],
        "b": [float(x) for x in b],
        "trained_on_attempts": len(attempt_ids),
        "observed_responses": observed,
        "missing_answer_policy": "np.nan_skip_like_old_pyai",
        "algorithm": "rasch_jml",
        "formula": "P(correct)=sigmoid(theta-b)",
        "max_iter": 200,
        "lr": 0.3,
        "reg": 0.01,
        "seed": 42,
    }

    save_json(RASCH_MODEL_PATH, rasch_model)
    print(f"Đã lưu rasch_model.json: {RASCH_MODEL_PATH}")

    print("Đang estimate theta theo b mới và update database...")

    theta_by_attempt_id: dict[int, float] = {}

    for row_idx, attempt_id in enumerate(attempt_ids):
        theta = estimate_theta_given_b(U[row_idx, :], b)
        theta_by_attempt_id[int(attempt_id)] = float(theta)

    update_attempt_thetas(engine, theta_by_attempt_id)

    print(f"Đã update Theta cho {len(theta_by_attempt_id)} attempts.")

    print("Đang lấy calibration data có TrueToeic...")
    calibration_rows = fetch_calibration_rows(engine, attempt_ids)

    if not calibration_rows:
        print("Chưa có attempt nào có TrueToeic nên chưa train score_mapper.")
        print("Giữ nguyên score_mapper.json hiện tại nếu đã có.")
        return

    theta_list = []
    toeic_list = []

    for row in calibration_rows:
        theta_list.append(float(row["Theta"]))
        toeic_list.append(float(row["TrueToeic"]))

    print(f"Calibration rows: {len(theta_list)}")
    print("Đang train score_mapper...")

    a, c = fit_linear_mapper(theta_list, toeic_list)

    pred_scores = [
        float(np.clip(a * theta + c, 0, 990))
        for theta in theta_list
    ]

    metrics = evaluate_predictions(toeic_list, pred_scores)

    score_mapper = {
        "type": "linear",
        "a": round(float(a), 6),
        "c": round(float(c), 6),
        "clip_min": 0,
        "clip_max": 990,
        "trained_on_users": len(theta_list),
        "metrics": metrics,
        "algorithm": "linear_regression",
        "formula": "score = a * theta + c",
        "filters": {
            "require_theta": True,
            "require_true_toeic": True,
            "extra_noise_filters": False,
        },
    }

    save_json(SCORE_MAPPER_PATH, score_mapper)

    report_rows = []

    score_by_attempt_id: dict[int, int] = {}

    for row, pred_score in zip(calibration_rows, pred_scores):
        attempt_id = int(row["DiagnosticAttemptId"])
        true_toeic = float(row["TrueToeic"])
        pred_score_clipped = int(round(float(pred_score)))

        score_by_attempt_id[attempt_id] = pred_score_clipped

        report_rows.append(
            {
                "DiagnosticAttemptId": attempt_id,
                "UserId": int(row["UserId"]),
                "theta": round(float(row["Theta"]), 6),
                "true_toeic": round(true_toeic, 2),
                "pred_score": round(float(pred_score), 2),
                "abs_error": round(abs(true_toeic - float(pred_score)), 2),
            }
        )

    save_calibration_report(report_rows)

    # Chỉ update EstimatedScore cho các attempt dùng train mapper.
    # Nếu muốn update toàn bộ attempts có theta, mình sẽ gửi thêm bản mở rộng.
    update_attempt_estimated_scores(engine, score_by_attempt_id)

    print("Train score_mapper hoàn tất.")
    print(f"- Đã lưu score_mapper.json: {SCORE_MAPPER_PATH}")
    print(f"- Đã lưu calibration report: {CALIBRATION_REPORT_PATH}")
    print(f"- Đã update EstimatedScore cho {len(score_by_attempt_id)} calibration attempts.")
    print("Metrics:")
    for key, value in metrics.items():
        print(f"  - {key}: {value}")


if __name__ == "__main__":
    retrain()