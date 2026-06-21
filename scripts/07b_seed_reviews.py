"""Phase 2.1 (tùy chọn): kéo review tiếng Việt từ HuggingFace -> điền sẵn cột text vào tập gold.

Mục đích: bạn KHÔNG phải copy tay từng review. Script lấy TEXT THÔ (bỏ nhãn cũ),
sample ngẫu nhiên N dòng, ghi ra data/gold/gold_seed.csv với:
    - text     : điền sẵn
    - label / annotator1 / annotator2 : ĐỂ TRỐNG cho 2 người tự gán
Sau đó đổi tên thành gold.csv khi đã gán xong.

KHUYẾN NGHỊ (đúng chủ đề nhà hàng): tải CSV Foody từ Kaggle rồi dùng --csv:
    python scripts/07b_seed_reviews.py --csv path/to/foody.csv --text-col review --n 400

Hoặc dataset HF dạng parquet (load 1 dòng):
    python scripts/07b_seed_reviews.py --dataset minhtoan/vietnamese-comment-sentiment --text-col Content --n 400

LƯU Ý: nhiều bộ UIT kinh điển (UIT-VSFC, UIT-ViSFD) đóng gói bằng "loading script" mà
bản `datasets` mới (>=3) đã bỏ hỗ trợ -> sẽ lỗi "Dataset scripts are no longer supported".
Với chúng, tải file CSV/JSON thủ công rồi dùng --csv.
"""
import argparse
import random

import _bootstrap  # noqa: F401

import pandas as pd

GOLD_DIR = _bootstrap.DATA / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)
GOLD_COLS = ["id", "text", "label", "annotator1", "annotator2", "source"]

# Tên cột text thường gặp ở các dataset review tiếng Việt.
TEXT_COL_CANDIDATES = ["text", "sentence", "review", "comment", "content", "Review"]


def _pick_text_col(columns, override):
    if override:
        if override not in columns:
            raise SystemExit(f"Không thấy cột '{override}'. Có: {list(columns)}")
        return override
    for c in TEXT_COL_CANDIDATES:
        if c in columns:
            return c
    raise SystemExit(f"Không đoán được cột text. Hãy chỉ --text-col. Có: {list(columns)}")


def load_texts(args):
    if args.csv:
        df = pd.read_csv(args.csv)
        col = _pick_text_col(df.columns, args.text_col)
        return df[col].dropna().astype(str).tolist(), f"csv:{args.csv}"
    from datasets import load_dataset

    ds = load_dataset(args.dataset, split=args.split)
    col = _pick_text_col(ds.column_names, args.text_col)
    return [str(t) for t in ds[col] if t], f"hf:{args.dataset}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", help="HF dataset id, vd minhtoan/vietnamese-comment-sentiment")
    ap.add_argument("--csv", help="Đường dẫn CSV cục bộ (vd Foody từ Kaggle)")
    ap.add_argument("--split", default="train")
    ap.add_argument("--text-col", help="Tên cột chứa review (tự đoán nếu bỏ trống)")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if not args.dataset and not args.csv:
        raise SystemExit("Cần --dataset <hf_id> hoặc --csv <path>.")

    texts, source = load_texts(args)
    # Khử trùng + lọc review quá ngắn (nhiễu).
    seen, clean = set(), []
    for t in texts:
        s = " ".join(t.split())
        if len(s) >= 10 and s.lower() not in seen:
            seen.add(s.lower())
            clean.append(s)
    rng = random.Random(args.seed)
    rng.shuffle(clean)
    sample = clean[:args.n]

    rows = [{"id": i + 1, "text": t, "label": "", "annotator1": "",
             "annotator2": "", "source": source} for i, t in enumerate(sample)]
    out = GOLD_DIR / "gold_seed.csv"
    pd.DataFrame(rows, columns=GOLD_COLS).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"✅ Đã ghi {len(rows)} review (chưa gán nhãn) -> {out}")
    print("👉 Mở file, để 2 người gán cột annotator1 & annotator2 (xem guideline),")
    print("   điền cột label = nhãn chốt, rồi đổi tên thành data/gold/gold.csv.")


if __name__ == "__main__":
    main()
