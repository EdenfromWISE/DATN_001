"""Đánh giá model cảm xúc trên tập gold: accuracy, macro-F1, ma trận nhầm lẫn, bảng so sánh."""
import pandas as pd

import config
from wisetravel import sentiment


def evaluate(y_true, y_pred):
    """Trả về dict {accuracy, macro_f1, confusion(DataFrame), per_class(DataFrame)}."""
    from sklearn.metrics import (accuracy_score, confusion_matrix,
                                  f1_score, precision_recall_fscore_support)

    labels = config.SENTIMENT_LABELS
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=[f"thật:{l}" for l in labels],
                         columns=[f"dự đoán:{l}" for l in labels])

    p, r, f, s = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0)
    per_class = pd.DataFrame(
        {"precision": p, "recall": r, "f1": f, "support": s}, index=labels)

    return {"accuracy": acc, "macro_f1": macro_f1,
            "confusion": cm_df, "per_class": per_class}


def run_models(texts, y_true, specs=None):
    """Chạy nhiều model trên cùng tập gold. Trả về list kết quả + bảng so sánh."""
    specs = specs or config.SENTIMENT_MODELS
    rows, details = [], {}
    for spec in specs:
        model = sentiment.SentimentModel(spec)
        y_pred = model.predict(texts)
        # Bỏ cặp mà model không phân loại được (hiếm) để metric không lỗi.
        pairs = [(t, p) for t, p in zip(y_true, y_pred) if p is not None]
        yt, yp = (list(z) for z in zip(*pairs)) if pairs else ([], [])
        res = evaluate(yt, yp)
        rows.append({"model": spec["name"], "hf_id": spec["hf_id"],
                     "accuracy": res["accuracy"], "macro_f1": res["macro_f1"],
                     "n_eval": len(yt)})
        details[spec["name"]] = res
    comparison = pd.DataFrame(rows).sort_values("macro_f1", ascending=False)
    return comparison, details


def save_confusion_png(cm_df, title, out_path):
    """Lưu ma trận nhầm lẫn ra PNG bằng matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(cm_df.values, cmap="Blues")
    ax.set_xticks(range(len(cm_df.columns)))
    ax.set_yticks(range(len(cm_df.index)))
    ax.set_xticklabels(cm_df.columns, rotation=45, ha="right")
    ax.set_yticklabels(cm_df.index)
    for i in range(cm_df.shape[0]):
        for j in range(cm_df.shape[1]):
            ax.text(j, i, cm_df.values[i, j], ha="center", va="center")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def format_comparison(comparison, details):
    """Sinh markdown: bảng so sánh + per-class + ma trận nhầm lẫn từng model."""
    lines = ["# So sánh model cảm xúc trên tập gold\n"]
    lines.append("## Bảng so sánh\n")
    lines.append("| Model | HF id | Accuracy | Macro-F1 | Số mẫu |")
    lines.append("|---|---|---:|---:|---:|")
    for _, r in comparison.iterrows():
        lines.append(f"| {r['model']} | `{r['hf_id']}` | {r['accuracy']:.1%} | "
                     f"{r['macro_f1']:.3f} | {r['n_eval']} |")
    best = comparison.iloc[0]["model"] if len(comparison) else "—"
    lines.append(f"\n**Model tốt nhất theo macro-F1: {best}.**\n")

    for name, res in details.items():
        lines.append(f"\n## {name}\n")
        lines.append("**Per-class:**\n")
        lines.append(res["per_class"].round(3).to_markdown())
        lines.append("\n\n**Ma trận nhầm lẫn:**\n")
        lines.append(res["confusion"].to_markdown())
        lines.append("")
    return "\n".join(lines) + "\n"


def aggregate_place_sentiment(texts, model_spec=None):
    """Gộp cảm xúc cho 1 địa điểm: list review -> tỷ lệ pos/neg/neu."""
    spec = model_spec or config.SENTIMENT_MODELS[0]
    model = sentiment.SentimentModel(spec)
    preds = [p for p in model.predict(texts) if p]
    total = len(preds)
    counts = {l: preds.count(l) for l in config.SENTIMENT_LABELS}
    ratios = {l: (counts[l] / total if total else 0.0) for l in counts}
    return {"total": total, "counts": counts, "ratios": ratios, "model": spec["name"]}
