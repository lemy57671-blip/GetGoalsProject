import os
import re
import json
import atexit
from difflib import SequenceMatcher
from typing import List, Optional, Tuple, Dict
from pathlib import Path

# Thư mục chứa model trong backend runtime
BASE_DIR = Path(__file__).resolve().parent.parent.parent / "runtime" / "models" / "translate"
FINETUNED_DIR = BASE_DIR / "finetuned_model"
CT2_DIR = BASE_DIR / "ct2_model"
CACHE_FILE = BASE_DIR / "cache" / "cache.json"
MODEL_NAME = "Helsinki-NLP/opus-mt-en-vi"

# Toi uu chat luong
MAX_LENGTH = 128
NUM_BEAMS = 4
REPETITION_PENALTY = 1.2

# Cache
SAVE_EVERY = 10       # Ghi file sau N ban dich moi
FUZZY_THRESHOLD = 0.85  # Nguong fuzzy matching

class Translator:
    """
    English -> Vietnamese Translator Service.
    """

    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._new = 0
        self._model = None
        self._tokenizer = None
        self._translator = None
        self._model_type = "hf"

        # Đảm bảo thư mục cache tồn tại
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        self._load_cache()
        self._load_model()
        atexit.register(self._save_cache)

        print(f"[Translator Service] Ready | Cache: {len(self._cache)} entries")

    def _load_cache(self):
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as e:
                print(f"[Translator Service] Error loading cache: {e}")
                self._cache = {}

    def _save_cache(self):
        if self._new > 0:
            try:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f, ensure_ascii=False, indent=2)
                self._new = 0
            except Exception as e:
                print(f"[Translator Service] Error saving cache: {e}")

    def _auto_save(self):
        if self._new >= SAVE_EVERY:
            self._save_cache()

    def _load_model(self):
        try:
            # Ưu tiên load CTranslate2 nếu có
            if CT2_DIR.exists():
                import ctranslate2
                from transformers import MarianTokenizer
                self._model_type = "ct2"
                print(f"[Translator Service] Loading CT2 model: {CT2_DIR}")
                # Ưu tiên tokenizer từ finetuned, sau đó đến model name
                tokenizer_path = str(FINETUNED_DIR) if FINETUNED_DIR.exists() else MODEL_NAME
                self._tokenizer = MarianTokenizer.from_pretrained(tokenizer_path)
                self._translator = ctranslate2.Translator(str(CT2_DIR), device="cpu", compute_type="int8")
            else:
                from transformers import MarianMTModel, MarianTokenizer
                self._model_type = "hf"
                path = str(FINETUNED_DIR) if FINETUNED_DIR.exists() else MODEL_NAME
                print(f"[Translator Service] Loading HuggingFace model: {path}")
                self._tokenizer = MarianTokenizer.from_pretrained(path)
                self._model = MarianMTModel.from_pretrained(path)
                self._model.to("cpu")
                self._model.eval()
        except Exception as e:
            print(f"[Translator Service] Critical error loading model: {e}")
            raise e

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r'\s+', ' ', text.strip())

    def _fuzzy(self, text: str) -> Optional[Tuple[str, str, float]]:
        best = None
        best_r = 0.0
        for k, v in self._cache.items():
            r = SequenceMatcher(None, text, k).ratio()
            if r > best_r:
                best_r = r
                best = (k, v, r)
        return best if best and best[2] >= FUZZY_THRESHOLD else None

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return ""

        key = self.normalize(text)

        # 1. Exact cache
        if key in self._cache:
            return self._cache[key]

        # 2. Fuzzy
        f = self._fuzzy(key)
        if f:
            self._cache[key] = f[1]
            self._new += 1
            self._auto_save()
            return f[1]

        # 3. Model
        if self._model_type == "ct2":
            source = self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(key, padding=False))
            results = self._translator.translate_batch(
                [source], 
                max_decoding_length=MAX_LENGTH, 
                beam_size=NUM_BEAMS, 
                repetition_penalty=REPETITION_PENALTY
            )
            target = results[0].hypotheses[0]
            result = self._tokenizer.decode(self._tokenizer.convert_tokens_to_ids(target), skip_special_tokens=True)
        else:
            import torch
            inp = self._tokenizer(key, return_tensors="pt", padding=True,
                                  truncation=True, max_length=MAX_LENGTH)
            with torch.no_grad():
                out = self._model.generate(**inp, max_length=MAX_LENGTH, num_beams=NUM_BEAMS)
            result = self._tokenizer.decode(out[0], skip_special_tokens=True)

        self._cache[key] = result
        self._new += 1
        self._auto_save()
        return result

    def translate_batch(self, texts: List[str]) -> List[str]:
        # Tương tự như translate nhưng xử lý nhiều câu cùng lúc để tối ưu CT2
        if not texts:
            return []
        # (Để đơn giản ta có thể gọi translate từng câu hoặc copy logic batch từ file cũ nếu cần)
        return [self.translate(t) for t in texts]
