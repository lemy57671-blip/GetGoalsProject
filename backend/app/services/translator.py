
import re
import json
import atexit
import logging
from collections import Counter
from difflib import SequenceMatcher
from typing import List, Optional, Tuple, Dict
from pathlib import Path

# Thư mục chứa model trong backend runtime
MODEL_ROOT = Path(__file__).resolve().parent.parent.parent / "runtime" / "models"
FINETUNED_DIR = MODEL_ROOT / "finetuned_model"
CT2_DIR = MODEL_ROOT / "ct2_model"
CACHE_FILE = MODEL_ROOT / "cache" / "cache.json"
MODEL_NAME = "Helsinki-NLP/opus-mt-en-vi"
FALLBACK_TRANSLATION = "Chưa có bản dịch phù hợp."

# Toi uu chat luong
MAX_LENGTH = 128
NUM_BEAMS = 4
REPETITION_PENALTY = 1.2

# Cache
SAVE_EVERY = 10       # Ghi file sau N ban dich moi
FUZZY_THRESHOLD = 0.85  # Nguong fuzzy matching

logger = logging.getLogger(__name__)


def is_bad_translation(input_text: str, translated_text: str) -> bool:
    translated_text = (translated_text or "").strip()
    if not translated_text:
        return True

    mojibake_markers = ("Ã", "á»", "áº", "Â", "â€", "â€™", "â€œ", "â€�", "�")
    if any(marker in translated_text for marker in mojibake_markers):
        return True

    input_len = max(len((input_text or "").strip()), 1)
    if len(translated_text) > max(160, input_len * 10):
        return True

    tokens = re.findall(r"\w+", translated_text.lower(), flags=re.UNICODE)
    if not tokens:
        return True

    repeated_run = 1
    previous = None
    for token in tokens:
        if token == previous:
            repeated_run += 1
            if repeated_run >= 4:
                return True
        else:
            repeated_run = 1
            previous = token

    if len(tokens) >= 6:
        counts = Counter(tokens)
        if counts.most_common(1)[0][1] / len(tokens) >= 0.6:
            return True

    return False


class Translator:
    """
    English -> Vietnamese Translator Service.
    """

    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._cache_index: Dict[str, str] = {}
        self._new = 0
        self._model = None
        self._tokenizer = None
        self._translator = None
        self._model_type = "hf"
        self._model_loaded = False
        self._model_error: Optional[Exception] = None

        # Đảm bảo thư mục cache tồn tại
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        logger.info("[Translator Service] Cache path: %s", CACHE_FILE)
        self._load_cache()
        atexit.register(self._save_cache)

        logger.info("[Translator Service] Ready | Cache: %s entries", len(self._cache))

    def _load_cache(self):
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8-sig") as f:
                    self._cache = json.load(f)
            except Exception as e:
                logger.exception("[Translator Service] Error loading cache: %s", e)
                self._cache = {}
        self._rebuild_cache_index()

    def _rebuild_cache_index(self):
        self._cache_index = {}
        for cache_key in self._cache:
            normalized_key = self.normalize(cache_key)
            if normalized_key:
                self._cache_index.setdefault(normalized_key, cache_key)

    def _save_cache(self):
        if self._new > 0:
            try:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f, ensure_ascii=False, indent=2)
                self._new = 0
            except Exception as e:
                logger.exception("[Translator Service] Error saving cache: %s", e)

    def _auto_save(self):
        if self._new >= SAVE_EVERY:
            self._save_cache()

    def _ensure_model_loaded(self):
        if self._model_loaded:
            return
        if self._model_error is not None:
            raise RuntimeError(f"Translation model unavailable: {self._model_error}") from self._model_error

        try:
            self._load_model()
            self._model_loaded = True
        except Exception as e:
            self._model_error = e
            raise

    def _load_model(self):
        try:
            # Ưu tiên load CTranslate2 nếu có
            if CT2_DIR.exists():
                try:
                    import ctranslate2
                    from transformers import MarianTokenizer
                    self._model_type = "ct2"
                    logger.info("[Translator Service] Loading CT2 model: %s", CT2_DIR)
                    # Ưu tiên tokenizer từ finetuned, sau đó đến model name
                    tokenizer_path = str(FINETUNED_DIR) if FINETUNED_DIR.exists() else MODEL_NAME
                    self._tokenizer = MarianTokenizer.from_pretrained(tokenizer_path)
                    self._translator = ctranslate2.Translator(str(CT2_DIR), device="cpu", compute_type="int8")
                    return
                except ImportError as e:
                    logger.warning(
                        "[Translator Service] CT2 model exists but ctranslate2 is unavailable; falling back to HuggingFace: %s",
                        e,
                    )

            from transformers import MarianMTModel, MarianTokenizer
            self._model_type = "hf"
            path = str(FINETUNED_DIR) if FINETUNED_DIR.exists() else MODEL_NAME
            logger.info("[Translator Service] Loading HuggingFace model: %s", path)
            self._tokenizer = MarianTokenizer.from_pretrained(path)
            self._model = MarianMTModel.from_pretrained(path)
            self._model.to("cpu")
            self._model.eval()
        except Exception as e:
            logger.exception("[Translator Service] Critical error loading model: %s", e)
            raise e

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r'\s+', ' ', (text or "").strip().lower())

    def _cache_hit(self, key: str) -> Optional[Tuple[str, str]]:
        if key in self._cache:
            return key, self._cache[key]

        stored_key = self._cache_index.get(key)
        if stored_key is not None:
            return stored_key, self._cache[stored_key]

        return None

    def _fuzzy(self, text: str) -> Optional[Tuple[str, str, float]]:
        best = None
        best_r = 0.0
        for k, v in self._cache.items():
            r = SequenceMatcher(None, text, k).ratio()
            if r > best_r:
                best_r = r
                best = (k, v, r)
        return best if best and best[2] >= FUZZY_THRESHOLD else None

    def _translate_with_model(self, key: str) -> str:
        self._ensure_model_loaded()
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
                out = self._model.generate(**inp, max_length=MAX_LENGTH, num_beams=NUM_BEAMS, repetition_penalty=REPETITION_PENALTY)
            result = self._tokenizer.decode(out[0], skip_special_tokens=True)

        return result

    def translate_with_source(self, text: str) -> Dict[str, str]:
        original_text = text or ""
        key = self.normalize(original_text)
        logger.info("[Translator Service] Normalized key: %r", key)

        if not key:
            return {
                "text": original_text,
                "translated_text": "",
                "source": "cache",
            }

        cached = self._cache_hit(key)
        if cached:
            logger.info("[Translator Service] Cache hit: %r", key)
            return {
                "text": original_text,
                "translated_text": cached[1],
                "source": "cache",
            }

        logger.info("[Translator Service] Cache miss: %r", key)
        logger.info("[Translator Service] Model fallback: %r", key)
        try:
            result = self._translate_with_model(key).strip()
        except Exception as e:
            logger.warning("[Translator Service] Model fallback failed for %r: %s", key, e)
            return {
                "text": original_text,
                "translated_text": FALLBACK_TRANSLATION,
                "source": "model",
            }

        if is_bad_translation(key, result):
            logger.warning("[Translator Service] Bad translation rejected for %r: %r", key, result)
            return {
                "text": original_text,
                "translated_text": FALLBACK_TRANSLATION,
                "source": "model",
            }

        if key not in self._cache and key not in self._cache_index:
            self._cache[key] = result
            self._cache_index[key] = key
            self._new += 1
            self._auto_save()

        return {
            "text": original_text,
            "translated_text": result,
            "source": "model",
        }

    def translate(self, text: str) -> str:
        return self.translate_with_source(text)["translated_text"]

    def translate_batch(self, texts: List[str]) -> List[str]:
        # Tương tự như translate nhưng xử lý nhiều câu cùng lúc để tối ưu CT2
        if not texts:
            return []
        # (Để đơn giản ta có thể gọi translate từng câu hoặc copy logic batch từ file cũ nếu cần)
        return [self.translate(t) for t in texts]
