"""Phase 2.3: chạy các model ứng viên trên tập gold -> accuracy/macro-F1/ma trận + bảng so sánh.

Lần đầu chạy sẽ TẢI model từ HuggingFace (vài trăm MB) -> cần mạng + đã cài torch/transformers.
"""
import _bootstrap  # noqa: F401

import pandas as pd

import config
from wisetravel import evaluation, sentiment

GOLD = _bootstrap.DATA / "gold" / "gold.csv"


def main():
    if not GOLD.exists():
        print(f"Chưa có {GOLD} — tạo & điền tập gold trước (xem 07_make_gold_template.py).")
        return
    df = pd.read_csv(GOLD, encoding="utf-8-sig")

    # Nhãn chốt: ưu tiên cột 'label'; nếu trống thì lấy annotator1.
    gold_label = df["label"].where(df["label"].notna(), df.get("annotator1"))
    y_true = gold_label.map(sentiment.normalize_label)
    mask = y_true.notna() & df["text"].notna()
    texts = df.loc[mask, "text"].astype(str).tolist()
    y_true = y_true[mask].tolist()
    print(f"Đánh giá trên {len(texts)} mẫu có nhãn hợp lệ, {len(config.SENTIMENT_MODELS)} model.\n")

    comparison, details = evaluation.run_models(texts, y_true)
    report = evaluation.format_comparison(comparison, details)
    out = _bootstrap.REPORTS / "model_comparison.md"
    out.write_text(report, encoding="utf-8")

    # Lưu ma trận nhầm lẫn PNG cho từng model.
    for name, res in details.items():
        png = _bootstrap.REPORTS / f"confusion_{name.split()[0].lower()}.png"
        evaluation.save_confusion_png(res["confusion"], f"Confusion — {name}", png)

    print(comparison.to_string(index=False))
    print(f"\n✅ Bảng so sánh -> {out}")
    print("✅ Ma trận nhầm lẫn PNG -> reports/confusion_*.png")


if __name__ == "__main__":
    main()
