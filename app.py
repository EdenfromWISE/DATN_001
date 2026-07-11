"""WiseTravel — App demo kỹ thuật (Streamlit).

Đóng gói toàn bộ bằng chứng "bài toán dữ liệu" thành 3 tab:
  1) Dữ liệu địa điểm  : thu thập OSM + đo chất lượng + accuracy audit
  2) Gán nhãn & Model  : Cohen's Kappa + so sánh model cảm xúc
  3) Demo cảm xúc      : nhập review -> ViSoBERT chấm & gộp theo địa điểm

Chạy:  streamlit run app.py
"""
import pathlib
import sys

# --- Đưa gốc dự án + src/ vào path (giống scripts/_bootstrap.py) ---
ROOT = pathlib.Path(__file__).resolve().parent
for _p in (ROOT, ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pandas as pd
import streamlit as st

import config
from wisetravel import audit, db

DATA = ROOT / "data"
REPORTS = ROOT / "reports"
# File audit đã điền tay: ưu tiên bản committed ở gốc data/, fallback data/audit/.
AUDIT_CSV = DATA / "audit_sample.csv"
if not AUDIT_CSV.exists():
    AUDIT_CSV = DATA / "audit" / "audit_sample.csv"
GOLD_CSV = DATA / "gold" / "gold.csv"
GOLD_TEMPLATE = DATA / "gold" / "gold_template.csv"

st.set_page_config(page_title="WiseTravel — Demo dữ liệu", page_icon="🧭", layout="wide")

CAT_COLORS = {"food": "#d9534f", "cafe": "#f0ad4e", "lodging": "#5bc0de", "attraction": "#5cb85c"}
SENT_COLORS = {"NEG": "#d9534f", "POS": "#5cb85c", "NEU": "#999999"}


# ---------------------------------------------------------------- helpers
@st.cache_data(show_spinner=False)
def load_pois():
    """Đọc toàn bộ POI từ SQLite. None nếu chưa có DB."""
    if not db.DB_PATH.exists():
        return None
    conn = db.connect()
    df = pd.DataFrame([dict(r) for r in conn.execute("SELECT * FROM pois")])
    conn.close()
    return df


@st.cache_data(show_spinner=False)
def load_gold():
    path = GOLD_CSV if GOLD_CSV.exists() else GOLD_TEMPLATE
    if not path.exists():
        return None, None
    return pd.read_csv(path, encoding="utf-8-sig"), path.name


@st.cache_data(show_spinner=False)
def score_audit():
    if not AUDIT_CSV.exists():
        return None
    return audit.score(AUDIT_CSV)


@st.cache_resource(show_spinner=True)
def get_sentiment_model(hf_id):
    """Nạp model 1 lần, cache suốt phiên (nặng: tải vài trăm MB lần đầu)."""
    from wisetravel import sentiment
    return sentiment.get_model(hf_id)


def pct(x):
    return "n/a" if x is None else f"{x:.1%}"


# ================================================================ HEADER
st.title("🧭 WiseTravel — Demo giải quyết bài toán dữ liệu")
st.caption(
    "Đồ án tốt nghiệp · Demo kỹ thuật (không phải app hoàn chỉnh). "
    "Quy trình: **thu thập → đo chất lượng → gán nhãn → chọn model → ứng dụng**."
)

tab1, tab2, tab3 = st.tabs([
    "📍 Dữ liệu địa điểm & Chất lượng",
    "🏷️ Gán nhãn & So sánh model",
    "💬 Demo phân tích cảm xúc",
])

# ================================================================ TAB 1
with tab1:
    pois = load_pois()
    if pois is None:
        st.warning(
            "Chưa có `data/wisetravel.db`. Chạy pipeline để tạo:\n\n"
            "```\npython scripts/01_fetch_pois.py\npython scripts/03_build_reports.py\n```"
        )
    else:
        st.subheader("1. Tổng quan dữ liệu thu thập")
        c = st.columns(5)
        c[0].metric("Tổng địa điểm", len(pois))
        for i, cat in enumerate(["food", "cafe", "lodging", "attraction"]):
            n = int((pois["category"] == cat).sum())
            c[i + 1].metric(config.CATEGORY_LABELS_VI[cat], n)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Phân bố theo loại hình**")
            counts = pois["category"].value_counts()
            counts.index = [config.CATEGORY_LABELS_VI.get(i, i) for i in counts.index]
            st.bar_chart(counts, color="#5b8def", horizontal=True)
        with col_b:
            st.markdown("**Giờ mở cửa theo nguồn** (`hours_source`)")
            if "hours_source" in pois.columns:
                hs = pois["hours_source"].fillna("(trống)").value_counts()
                st.bar_chart(hs, color="#f0ad4e", horizontal=True)
                real = int(pois["hours_source"].isin(["osm", "google", "manual"]).sum())
                st.caption(
                    f"Nguồn **thật** (osm/google/manual): {real}/{len(pois)} "
                    f"({real/len(pois):.1%}) — chỉ phần này được tính vào accuracy audit. "
                    f"Còn lại là heuristic theo loại hình (minh bạch, không tô hồng)."
                )

        st.divider()
        st.subheader("2. Accuracy Audit — tự kiểm chứng chất lượng")
        res = score_audit()
        if res is None:
            st.info("Chưa có file audit đã điền tay. Xem `scripts/04` + `scripts/05`.")
        else:
            m = st.columns(3)
            m[0].metric("Mẫu kiểm", res["rows_total"])
            m[1].metric("Tọa độ đúng",
                        pct(res["coord_accuracy"]),
                        f"{res['coord_correct']}/{res['coord_checked']}")
            m[2].metric("Giờ mở cửa đúng",
                        pct(res["hours_accuracy"]),
                        f"{res['hours_correct']}/{res['hours_checked']}")
            st.caption(
                "Con số này đo trên **mẫu ngẫu nhiên 50 địa điểm, người thật đối chiếu Google Maps**. "
                "Điểm mấu chốt của đồ án: có công cụ *đo được* chất lượng dữ liệu, không chỉ thu thập rồi tin."
            )

        st.divider()
        st.subheader("3. Bản đồ phủ địa điểm")
        map_df = pois[["lat", "lng"]].rename(columns={"lng": "lon"}).dropna()
        st.map(map_df, size=20, color="#d9534f66")

        st.divider()
        st.subheader("4. Tra cứu địa điểm")
        f = st.columns(3)
        cats = f[0].multiselect(
            "Loại hình",
            options=list(config.CATEGORY_LABELS_VI),
            format_func=lambda x: config.CATEGORY_LABELS_VI[x],
            default=list(config.CATEGORY_LABELS_VI),
        )
        max_price = f[1].slider("Mức giá tối đa", 1, 3, 3)
        kw = f[2].text_input("Tìm theo tên", "")
        view = pois[pois["category"].isin(cats) & (pois["price_level"] <= max_price)]
        if kw.strip():
            view = view[view["name"].str.contains(kw.strip(), case=False, na=False)]
        show_cols = [c for c in ["name", "category", "district", "address",
                                 "opening_hours", "hours_source", "price_level"]
                     if c in view.columns]
        st.caption(f"{len(view)} địa điểm khớp bộ lọc.")
        st.dataframe(view[show_cols], width="stretch", height=320)

# ================================================================ TAB 2
with tab2:
    gold, gold_name = load_gold()
    if gold is None:
        st.warning("Chưa có tập gold. Xem `scripts/07_make_gold_template.py`.")
    else:
        labeled = gold[gold["label"].notna()] if "label" in gold.columns else gold
        st.subheader("1. Tập gold đã gán nhãn")
        st.caption(f"Nguồn: `{gold_name}` · Nhãn chốt (`label`) = **annotator2**.")
        c = st.columns(4)
        c[0].metric("Số review", len(labeled))
        for i, lab in enumerate(config.SENTIMENT_LABELS):
            n = int((labeled["label"].astype(str).str.upper() == lab).sum())
            c[i + 1].metric(config.SENTIMENT_LABELS_VI[lab], n)

        colL, colR = st.columns([1, 1])
        with colL:
            st.markdown("**Phân bố nhãn chốt**")
            dist = labeled["label"].astype(str).str.upper().value_counts()
            st.bar_chart(dist, color="#5b8def", horizontal=True)
            st.caption("⚠️ Dữ liệu lệch mạnh về POS — lý do NEU khó với mọi model (ít mẫu học).")
        with colR:
            st.markdown("**Độ đồng thuận 2 người gán (Cohen's Kappa)**")
            try:
                from wisetravel import agreement
                stats = agreement.analyze(gold)
                k = stats.get("kappa")
                st.metric("Cohen's Kappa", f"{k:.3f}" if k is not None else "n/a")
                st.caption(
                    f"{stats.get('n_valid_pairs','?')} cặp hợp lệ · đồng ý "
                    f"{pct(stats.get('percent_agree'))}. "
                    "Thang Landis–Koch: 0.6–0.8 = *substantial* (tốt)."
                )
            except Exception as e:  # noqa: BLE001
                st.info(f"Không tính được Kappa trực tiếp: {e}")

        st.divider()
        st.subheader("2. So sánh model cảm xúc (trên tập gold)")
        mc = REPORTS / "model_comparison.md"
        if mc.exists():
            st.markdown(mc.read_text(encoding="utf-8"))
        else:
            st.info(
                "Chưa có `reports/model_comparison.md`. Chạy:\n\n"
                "```\npython scripts/09_eval_models.py\n```"
            )
        pngs = [("confusion_visobert.png", "ViSoBERT"),
                ("confusion_phobert.png", "PhoBERT")]
        imgs = [(REPORTS / f, t) for f, t in pngs if (REPORTS / f).exists()]
        if imgs:
            cols = st.columns(len(imgs))
            for col, (p, t) in zip(cols, imgs):
                col.image(str(p), caption=f"Ma trận nhầm lẫn — {t}")

# ================================================================ TAB 3
with tab3:
    st.subheader("Phân tích cảm xúc review theo địa điểm")
    st.caption(
        "Nhập nhiều review (mỗi dòng một review) rồi bấm phân tích. "
        "Model mặc định **ViSoBERT** (thắng ở macro-F1)."
    )
    default_reviews = (
        "Quán ngon, nhân viên dễ thương, sẽ quay lại!\n"
        "Phục vụ chậm kinh khủng, đồ ăn nguội ngắt.\n"
        "Không gian đẹp, giá hợp lý.\n"
        "Dở tệ, không đáng tiền.\n"
        "Cũng bình thường thôi, không có gì đặc biệt.\n"
        "Cà phê thơm, view đẹp, sống ảo cực chill 😍"
    )
    model_label = st.selectbox(
        "Model",
        options=[m["hf_id"] for m in config.SENTIMENT_MODELS],
        format_func=lambda h: next(m["name"] for m in config.SENTIMENT_MODELS if m["hf_id"] == h),
    )
    txt = st.text_area("Danh sách review", value=default_reviews, height=180)

    if st.button("🔍 Phân tích cảm xúc", type="primary"):
        reviews = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        if not reviews:
            st.warning("Hãy nhập ít nhất một review.")
        else:
            with st.spinner("Đang nạp model & suy luận…"):
                model = get_sentiment_model(model_label)
                preds = model.predict(reviews)
            rows = [{"Review": r, "Cảm xúc": config.SENTIMENT_LABELS_VI.get(p, "?"),
                     "Nhãn": p} for r, p in zip(reviews, preds)]
            res_df = pd.DataFrame(rows)

            valid = [p for p in preds if p]
            counts = {l: valid.count(l) for l in config.SENTIMENT_LABELS}
            total = len(valid) or 1
            st.markdown(f"**Tổng hợp cảm xúc** ({model.name} · {len(valid)} review)")
            mc = st.columns(3)
            for i, lab in enumerate(config.SENTIMENT_LABELS):
                mc[i].metric(config.SENTIMENT_LABELS_VI[lab],
                             counts[lab], f"{counts[lab]/total:.0%}")
            st.bar_chart(pd.Series(counts).rename(index=config.SENTIMENT_LABELS_VI),
                         color="#5b8def", horizontal=True)

            def _style(row):
                c = SENT_COLORS.get(row["Nhãn"], "#ffffff")
                return [f"background-color: {c}22"] * len(row)
            st.dataframe(res_df[["Review", "Cảm xúc"]].style.apply(_style, axis=1),
                         width="stretch", hide_index=True)
