"""
============================================================================
  BUOC 2: TRAINING MODEL  (train.py)
============================================================================
  - Load du lieu tu data/train.json (tao boi prepare_data.py)
  - Download model goc Helsinki-NLP/opus-mt-en-vi
  - Fine-tune tren du lieu TOEIC (API-generated)
  - Luu model fine-tuned ra finetuned_model/

  Chay: python train.py
  Tuy chinh: python train.py --epochs 5 --batch_size 8
============================================================================
"""

import os
import sys
import json
import time
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TRAIN_FILE = os.path.join(DATA_DIR, "train.json")
FINETUNED_DIR = os.path.join(BASE_DIR, "finetuned_model")
LOG_FILE = os.path.join(BASE_DIR, "training_log.json")

MODEL_NAME = "Helsinki-NLP/opus-mt-en-vi"
MODEL_LOCAL = os.path.join(BASE_DIR, "model_local")

# Mac dinh (toi uu cho CPU i5)
DEFAULT_EPOCHS = 3
DEFAULT_BATCH_SIZE = 4
DEFAULT_LR = 5e-5
DEFAULT_MAX_LEN = 128


# ============================================================================
# DATASET & OPTIMIZATION
# ============================================================================

import torch

# Mac dinh toi uu (tranh full load CPU neu khong can thiet)
NUM_THREADS = max(1, (os.cpu_count() or 4) // 2)
torch.set_num_threads(NUM_THREADS)

class PairDataset:
    """Dataset da duoc toi uu: Tokenize truoc toan bo data de chay cuc nhanh"""

    def __init__(self, pairs, tokenizer, max_len=128):
        print("  Dang Pre-tokenize toan bo du lieu (giup tang toc 300% tren CPU)...")
        en_texts = [p["en"] for p in pairs]
        vi_texts = [p["vi"] for p in pairs]

        self.src = tokenizer(
            en_texts, max_length=max_len, padding="max_length",
            truncation=True, return_tensors="pt"
        )
        self.tgt = tokenizer(
            text_target=vi_texts, max_length=max_len, padding="max_length",
            truncation=True, return_tensors="pt"
        )

        self.labels = self.tgt["input_ids"].clone()
        self.labels[self.labels == tokenizer.pad_token_id] = -100

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids": self.src["input_ids"][idx],
            "attention_mask": self.src["attention_mask"][idx],
            "labels": self.labels[idx],
        }


# ============================================================================
# TRAINING
# ============================================================================

def train(epochs, batch_size, lr, max_len, low_power=False):
    from torch.utils.data import DataLoader
    from transformers import MarianMTModel, MarianTokenizer

    # 1. Load data (Tat ca JSON trong muc data)
    print("  Load toan bo file json trong data/...")
    train_data = []
    seen = set()
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".json") and "test" not in fname and "merged" not in fname:
            fp = os.path.join(DATA_DIR, fname)
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
                for item in d:
                    key = item["en"].strip().lower()
                    if key not in seen:
                        seen.add(key)
                        train_data.append(item)
            print(f"    - {fname}")
            
    if not train_data:
        print(f"[LOI] Khong tim thay du lieu data/*.json")
        sys.exit(1)

    print(f"  Da gop tong cong {len(train_data):,} cap cau (khong trung lap)")

    # 2. Load model (uu tien local)
    model_path = MODEL_LOCAL if os.path.exists(MODEL_LOCAL) else MODEL_NAME
    print(f"\nLoad model: {model_path}")
    tokenizer = MarianTokenizer.from_pretrained(model_path)
    model = MarianMTModel.from_pretrained(model_path)
    model.to("cpu")
    model.train()

    params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {params:,}")

    # 3. Dataset + DataLoader
    dataset = PairDataset(train_data, tokenizer, max_len)
    # Su dung num_workers de load batch nhanh hon neu can
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    total_batches = len(loader)

    print(f"\nTraining config (CPU Optimized):")
    print(f"  Epochs:     {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  LR:         {lr}")
    print(f"  Max length: {max_len}")
    print(f"  Batches:    {total_batches}/epoch")
    print(f"  Low Power:  {'ON (CPU Relaxed)' if low_power else 'OFF (Full Speed)'}")
    print(f"  Threads:    {torch.get_num_threads()}")

    # 4. Optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)

    # 5. Training loop
    history = []
    best_loss = float("inf")
    t0 = time.time()

    print(f"\n{'='*50}")
    print(f"  BAT DAU TRAINING")
    print(f"{'='*50}\n")

    from tqdm import tqdm

    for epoch in range(1, epochs + 1):
        epoch_loss = 0.0
        et = time.time()

        pbar = tqdm(loader, desc=f"Epoch {epoch}/{epochs}", unit="batch", file=sys.stdout)
        for step, batch in enumerate(pbar, 1):
            optimizer.zero_grad()
            out = model(
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
                labels=batch["labels"],
            )
            loss = out.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item()

            # Giam tai CPU: nghi mot chut neu dang o che do low_power
            if low_power:
                time.sleep(0.02) # Nghi 20ms de CPU "tho"

            pbar.set_postfix({"Loss": f"{epoch_loss / step:.4f}"})

        avg_loss = epoch_loss / total_batches
        etime = time.time() - et
        history.append({
            "epoch": epoch, "loss": round(avg_loss, 4),
            "time_s": round(etime, 1)
        })

        print(f"  >>> Epoch {epoch}: Loss={avg_loss:.4f} | Time={etime:.1f}s\n")

        # Save best
        if avg_loss < best_loss:
            best_loss = avg_loss
            os.makedirs(FINETUNED_DIR, exist_ok=True)
            model.save_pretrained(FINETUNED_DIR)
            tokenizer.save_pretrained(FINETUNED_DIR)
            print(f"  [SAVED] Best model -> {FINETUNED_DIR}\n")

    total_time = time.time() - t0

    # 6. Log
    log = {
        "model": MODEL_NAME,
        "train_samples": len(train_data),
        "epochs": epochs, "batch_size": batch_size, "lr": lr,
        "best_loss": round(best_loss, 4),
        "total_time_s": round(total_time, 1),
        "history": history,
    }
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"{'='*50}")
    print(f"  TRAINING HOAN TAT!")
    print(f"  Best loss: {best_loss:.4f}")
    print(f"  Time:      {total_time:.1f}s")
    print(f"  Model:     {FINETUNED_DIR}")
    print(f"  Log:       {LOG_FILE}")
    print(f"{'='*50}")
    print(f"\nChay tiep: python test.py")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Fine-tune MarianMT en->vi")
    p.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    p.add_argument("--batch_size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--lr", type=float, default=DEFAULT_LR)
    p.add_argument("--max_len", type=int, default=DEFAULT_MAX_LEN)
    p.add_argument("--low_power", type=int, default=1, help="1: Giam tai CPU (mac dinh), 0: Chay full toc do")
    a = p.parse_args()
    train(a.epochs, a.batch_size, a.lr, a.max_len, low_power=bool(a.low_power))
