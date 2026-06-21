"""Độ đồng thuận gán nhãn giữa 2 annotator: Cohen's Kappa + thống kê kèm theo."""
import pandas as pd

from wisetravel import sentiment


def _interpret(k):
    """Diễn giải Kappa theo thang Landis & Koch (1977)."""
    if k is None:
        return "n/a"
    if k < 0:
        return "tệ hơn ngẫu nhiên"
    if k < 0.20:
        return "rất thấp (slight)"
    if k < 0.40:
        return "thấp (fair)"
    if k < 0.60:
        return "trung bình (moderate)"
    if k < 0.80:
        return "tốt (substantial)"
    return "rất tốt (almost perfect)"


def cohen_kappa(a1, a2):
    """Cohen's Kappa cho 2 chuỗi nhãn (đã loại cặp thiếu). Trả về float hoặc None."""
    from sklearn.metrics import cohen_kappa_score

    pairs = [(x, y) for x, y in zip(a1, a2)
             if x is not None and y is not None]
    if not pairs:
        return None
    xs, ys = zip(*pairs)
    if len(set(xs)) == 1 and len(set(ys)) == 1 and xs[0] == ys[0]:
        return 1.0  # mọi nhãn trùng & cùng 1 lớp -> Kappa định nghĩa = 1
    return float(cohen_kappa_score(xs, ys))


def analyze(df, col1="annotator1", col2="annotator2"):
    """Tính Kappa + % đồng ý + số cặp hợp lệ từ DataFrame tập gold."""
    a1 = df[col1].map(sentiment.normalize_label)
    a2 = df[col2].map(sentiment.normalize_label)
    pairs = [(x, y) for x, y in zip(a1, a2) if x and y]
    n = len(pairs)
    agree = sum(1 for x, y in pairs if x == y)
    k = cohen_kappa(list(a1), list(a2))
    return {
        "n_rows": len(df),
        "n_valid_pairs": n,
        "n_agree": agree,
        "percent_agree": agree / n if n else None,
        "kappa": k,
        "interpretation": _interpret(k),
    }


def format_report(stats):
    def pct(x):
        return "n/a" if x is None else f"{x:.1%}"

    def num(x):
        return "n/a" if x is None else f"{x:.3f}"

    return (
        "# Cohen's Kappa — Độ đồng thuận gán nhãn\n\n"
        f"- Tổng dòng: **{stats['n_rows']}**\n"
        f"- Cặp hợp lệ (cả 2 annotator có nhãn): **{stats['n_valid_pairs']}**\n"
        f"- Số cặp đồng ý: **{stats['n_agree']}** "
        f"(observed agreement **{pct(stats['percent_agree'])}**)\n"
        f"- **Cohen's Kappa = {num(stats['kappa'])}** → {stats['interpretation']}\n\n"
        "> Thang Landis & Koch: <0.2 rất thấp · 0.2–0.4 thấp · 0.4–0.6 trung bình · "
        "0.6–0.8 tốt · >0.8 rất tốt.\n"
    )
