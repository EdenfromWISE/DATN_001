"""Sinh toàn bộ biểu đồ PNG cho báo cáo demo -> reports/figures/.

Đọc dữ liệu THẬT từ: SQLite (POI), data audit đã điền, gold.csv, model_comparison.md.
Chạy:  python scripts/make_report_figures.py
"""
import re

import _bootstrap  # noqa: F401

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config
from wisetravel import audit, db

FIG = _bootstrap.REPORTS / "figures"
FIG.mkdir(parents=True, exist_ok=True)
DATA = _bootstrap.DATA

# Bảng màu nhất quán cho cả báo cáo.
C_BLUE, C_GREEN, C_RED, C_AMBER, C_GREY = "#5b8def", "#5cb85c", "#d9534f", "#f0ad4e", "#adb5bd"
plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.25,
                     "axes.axisbelow": True, "figure.dpi": 130})


def _save(fig, name):
    fig.tight_layout()
    out = FIG / name
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {out.relative_to(_bootstrap.ROOT)}")


def _barlabels(ax, bars, fmt="{:.0f}"):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                fmt.format(b.get_height()), ha="center", va="bottom", fontsize=10)


def fig_category(pois):
    order = ["food", "cafe", "lodging", "attraction"]
    vals = [int((pois["category"] == c).sum()) for c in order]
    labels = [config.CATEGORY_LABELS_VI[c] for c in order]
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars = ax.bar(labels, vals, color=[C_RED, C_AMBER, "#5bc0de", C_GREEN])
    _barlabels(ax, bars)
    ax.set_title(f"Phân bố {len(pois)} địa điểm theo loại hình")
    ax.set_ylabel("Số địa điểm")
    _save(fig, "fig_category.png")


def fig_hours_source(pois):
    hs = pois["hours_source"].fillna("(trống)")
    real = int(hs.isin(["osm", "google", "manual"]).sum())
    heur = int((hs == "heuristic").sum())
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    bars = ax.bar(["Nguồn thật\n(osm/google/manual)", "Heuristic\n(đoán theo loại)"],
                  [real, heur], color=[C_GREEN, C_GREY])
    _barlabels(ax, bars)
    ax.set_title("Giờ mở cửa theo nguồn dữ liệu")
    ax.set_ylabel("Số địa điểm")
    ax.text(0.5, 0.92, f"Chỉ {real}/{len(pois)} ({real/len(pois):.0%}) là nguồn thật "
            "→ chỉ phần này được đo audit",
            transform=ax.transAxes, ha="center", fontsize=9, color="#555")
    _save(fig, "fig_hours_source.png")


def fig_audit():
    csv = DATA / "audit_sample.csv"
    if not csv.exists():
        csv = DATA / "audit" / "audit_sample.csv"
    if not csv.exists():
        print("  (bỏ qua audit: chưa có file)")
        return
    r = audit.score(csv)
    cats = ["Tọa độ", "Giờ mở cửa"]
    acc = [r["coord_accuracy"] or 0, r["hours_accuracy"] or 0]
    n = [f"{r['coord_correct']}/{r['coord_checked']}",
         f"{r['hours_correct']}/{r['hours_checked']}"]
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    bars = ax.bar(cats, [a * 100 for a in acc], color=[C_BLUE, C_AMBER])
    for b, a, lab in zip(bars, acc, n):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                f"{a:.1%}\n({lab})", ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% đúng (đối chiếu Google Maps)")
    ax.set_title(f"Accuracy Audit — kiểm tay {r['rows_total']} địa điểm ngẫu nhiên")
    _save(fig, "fig_audit.png")


def fig_label_dist():
    path = DATA / "gold" / "gold.csv"
    if not path.exists():
        path = DATA / "gold" / "gold_template.csv"
    if not path.exists():
        print("  (bỏ qua nhãn: chưa có gold)")
        return
    df = pd.read_csv(path, encoding="utf-8-sig")
    lab = df["label"].astype(str).str.upper()
    order = config.SENTIMENT_LABELS
    vals = [int((lab == l).sum()) for l in order]
    names = [config.SENTIMENT_LABELS_VI[l] for l in order]
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    bars = ax.bar(names, vals, color=[C_RED, C_GREEN, C_GREY])
    _barlabels(ax, bars)
    ax.set_title(f"Phân bố {int(lab.isin(order).sum())} nhãn chốt (gold = annotator2)")
    ax.set_ylabel("Số review")
    ax.text(0.5, 0.9, "Dữ liệu lệch mạnh về POS → NEU ít mẫu, model khó học",
            transform=ax.transAxes, ha="center", fontsize=9, color="#555")
    _save(fig, "fig_label_dist.png")


def _parse_model_comparison():
    """Đọc accuracy & macro-F1 từ reports/model_comparison.md (bảng markdown)."""
    md = _bootstrap.REPORTS / "model_comparison.md"
    if not md.exists():
        return None
    rows = []
    for line in md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*`[^`]+`\s*\|\s*([\d.]+)%\s*\|\s*([\d.]+)\s*\|",
                     line)
        if m:
            rows.append((m.group(1), float(m.group(2)), float(m.group(3))))
    return rows or None


def fig_model_compare():
    rows = _parse_model_comparison()
    if not rows:
        print("  (bỏ qua so sánh model: chưa có model_comparison.md)")
        return
    names = [r[0] for r in rows]
    acc = [r[1] for r in rows]
    f1 = [r[2] * 100 for r in rows]
    x = range(len(names))
    w = 0.36
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    b1 = ax.bar([i - w/2 for i in x], acc, w, label="Accuracy (%)", color=C_BLUE)
    b2 = ax.bar([i + w/2 for i in x], f1, w, label="Macro-F1 (×100)", color=C_GREEN)
    _barlabels(ax, b1, "{:.1f}")
    _barlabels(ax, b2, "{:.1f}")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Điểm (%)")
    ax.set_title("So sánh model cảm xúc trên tập gold")
    ax.legend()
    _save(fig, "fig_model_compare.png")


def fig_pipeline():
    """Sơ đồ quy trình 2 nhánh dữ liệu + app."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off"); ax.grid(False)

    def box(x, y, w, h, text, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                    linewidth=1.2, edgecolor="#33415c", facecolor=color))
        ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=9.5)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=14, linewidth=1.3, color="#33415c"))

    # Nhánh ĐỊA ĐIỂM (trên)
    ax.text(0.1, 4.55, "NHÁNH 1 — DỮ LIỆU ĐỊA ĐIỂM", fontsize=9, weight="bold", color="#c0392b")
    b = [("OSM / Overpass\n(500 POI)", 0.1), ("Chuẩn hóa\n+ khử trùng", 2.5),
         ("SQLite", 4.9), ("Accuracy Audit\n(kiểm 50 điểm)", 6.9)]
    for text, x in b:
        box(x, 3.5, 2.0, 0.85, text, "#fdece9")
    for i in range(len(b) - 1):
        arrow(b[i][1] + 2.0, 3.92, b[i+1][1], 3.92)

    # Nhánh CẢM XÚC (dưới)
    ax.text(0.1, 2.4, "NHÁNH 2 — DỮ LIỆU CẢM XÚC", fontsize=9, weight="bold", color="#1e824c")
    c = [("493 review\n2 người gán", 0.1), ("Cohen's Kappa\n(0.611)", 2.5),
         ("So sánh model\nViSoBERT/PhoBERT", 4.9), ("Chọn model\ntốt nhất", 7.3)]
    for text, x in c:
        box(x, 1.35, 2.0, 0.85, text, "#e9f7ef")
    for i in range(len(c) - 1):
        arrow(c[i][1] + 2.0, 1.77, c[i+1][1], 1.77)

    # Gộp về APP
    box(3.6, 0.05, 2.8, 0.8, "APP STREAMLIT (3 tab)\ngói toàn bộ bằng chứng", "#eaf1fd")
    arrow(7.9, 3.5, 5.6, 0.85)   # audit -> app
    arrow(8.3, 1.35, 5.4, 0.85)  # model -> app
    _save(fig, "fig_pipeline.png")


def copy_confusion():
    """Gom ma trận nhầm lẫn (do script 09 sinh) vào figures/ để báo cáo tự chứa."""
    import shutil
    for name in ("confusion_visobert.png", "confusion_phobert.png"):
        src = _bootstrap.REPORTS / name
        if src.exists():
            shutil.copy2(src, FIG / name)
            print(f"  -> reports/figures/{name} (copy)")


def main():
    print("Sinh biểu đồ báo cáo -> reports/figures/")
    fig_pipeline()
    conn = db.connect()
    pois = pd.DataFrame([dict(r) for r in conn.execute("SELECT * FROM pois")])
    conn.close()
    fig_category(pois)
    fig_hours_source(pois)
    fig_audit()
    fig_label_dist()
    fig_model_compare()
    copy_confusion()
    print("Xong.")


if __name__ == "__main__":
    main()
