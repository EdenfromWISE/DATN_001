"""Suy luận cảm xúc tiếng Việt bằng model có sẵn trên HuggingFace.

- Chuẩn hóa nhãn về 3 lớp canonical: NEG / POS / NEU.
- Tự đọc id2label thật từ model.config (không cứng hóa thứ tự nhãn).
- Tách từ (word segmentation) tùy model: PhoBERT cần, ViSoBERT không.
  Tách từ bằng pyvi (nhẹ); nếu chưa cài mà model yêu cầu segment -> báo lỗi rõ ràng.
"""
import functools

import config

CANONICAL = set(config.SENTIMENT_LABELS)

# Quy mọi cách viết nhãn (model trả về / người gán tay) về canonical NEG/POS/NEU.
_ALIASES = {
    "neg": "NEG", "negative": "NEG", "tiêu cực": "NEG", "tieu cuc": "NEG",
    "tiêucực": "NEG", "0": "NEG", "label_0": "NEG",
    "pos": "POS", "positive": "POS", "tích cực": "POS", "tich cuc": "POS",
    "tíchcực": "POS", "1": "POS", "label_1": "POS",
    "neu": "NEU", "neutral": "NEU", "trung tính": "NEU", "trung tinh": "NEU",
    "trung lập": "NEU", "trung lap": "NEU", "2": "NEU", "label_2": "NEU",
}


def normalize_label(raw):
    """Chuyển một nhãn bất kỳ về NEG/POS/NEU, hoặc None nếu không nhận diện được."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s in CANONICAL:
        return s
    return _ALIASES.get(s.lower())


def segment(text):
    """Tách từ tiếng Việt bằng pyvi (vd 'mô hình' -> 'mô_hình')."""
    try:
        from pyvi import ViTokenizer
    except ImportError as err:  # pragma: no cover
        raise ImportError(
            "Model này cần tách từ nhưng chưa cài 'pyvi'. Chạy: pip install pyvi"
        ) from err
    return ViTokenizer.tokenize(text)


class SentimentModel:
    """Bọc 1 model phân loại cảm xúc; predict() trả nhãn canonical."""

    def __init__(self, spec):
        self.name = spec["name"]
        self.hf_id = spec["hf_id"]
        self.need_segment = bool(spec.get("segment"))
        self._tok = None
        self._model = None
        self._id2canon = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        import torch  # noqa: F401  (đảm bảo có backend)
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        # PhoBERT khuyến nghị use_fast=False; để chung cho an toàn.
        self._tok = AutoTokenizer.from_pretrained(self.hf_id, use_fast=False)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.hf_id)
        self._model.eval()
        # Đọc id2label THẬT từ model rồi quy về canonical.
        id2label = self._model.config.id2label
        self._id2canon = {}
        for idx, lab in id2label.items():
            canon = normalize_label(lab) or normalize_label(idx)
            self._id2canon[int(idx)] = canon

    def predict(self, texts, batch_size=16):
        """Nhận list[str] -> list nhãn canonical (NEG/POS/NEU)."""
        import torch

        self._ensure_loaded()
        prepared = [segment(t) if self.need_segment else t for t in texts]
        out = []
        for i in range(0, len(prepared), batch_size):
            chunk = prepared[i:i + batch_size]
            enc = self._tok(chunk, padding=True, truncation=True,
                            max_length=256, return_tensors="pt")
            with torch.no_grad():
                logits = self._model(**enc).logits
            for row in logits.argmax(dim=-1).tolist():
                out.append(self._id2canon.get(int(row)))
        return out


@functools.lru_cache(maxsize=8)
def get_model(hf_id):
    """Cache model theo hf_id để không nạp lại."""
    spec = next((m for m in config.SENTIMENT_MODELS if m["hf_id"] == hf_id), None)
    if spec is None:
        spec = {"name": hf_id, "hf_id": hf_id, "segment": False}
    return SentimentModel(spec)
