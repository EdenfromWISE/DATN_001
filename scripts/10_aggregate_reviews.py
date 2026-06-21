"""Phase 2.4: demo gộp cảm xúc theo địa điểm -> tỷ lệ pos/neg + biểu đồ cột."""
import _bootstrap  # noqa: F401

import config
from wisetravel import evaluation

# Ví dụ: một loạt review cho 1 quán (thay bằng dữ liệu thật khi demo).
DEMO_REVIEWS = [
    "Quán ngon, sẽ quay lại!",
    "Phục vụ chậm, đồ ăn nguội.",
    "Không gian đẹp, giá hợp lý.",
    "Dở tệ, không đáng tiền.",
    "Cũng bình thường thôi.",
    "Cà phê ngon, nhân viên dễ thương.",
]


def main():
    print(f"Gộp cảm xúc {len(DEMO_REVIEWS)} review (model mặc định)...\n")
    res = evaluation.aggregate_place_sentiment(DEMO_REVIEWS)
    print(f"Model: {res['model']} | tổng nhãn được: {res['total']}")
    for lab in config.SENTIMENT_LABELS:
        vi = config.SENTIMENT_LABELS_VI[lab]
        print(f"  {vi:10s} ({lab}): {res['counts'][lab]}  ({res['ratios'][lab]:.0%})")

    # Biểu đồ cột PNG.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [config.SENTIMENT_LABELS_VI[l] for l in config.SENTIMENT_LABELS]
    vals = [res["counts"][l] for l in config.SENTIMENT_LABELS]
    fig, ax = plt.subplots(figsize=(4.5, 3.2))
    ax.bar(labels, vals, color=["#d9534f", "#5cb85c", "#999999"])
    ax.set_title("Phân bố cảm xúc review (demo)")
    ax.set_ylabel("Số review")
    fig.tight_layout()
    out = _bootstrap.REPORTS / "place_sentiment_demo.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"\n✅ Biểu đồ -> {out}")


if __name__ == "__main__":
    main()
