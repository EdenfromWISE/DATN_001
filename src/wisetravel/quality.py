"""Sinh báo cáo chất lượng dữ liệu địa điểm (markdown)."""
import datetime

import pandas as pd

import config


def _df(conn):
    rows = [dict(r) for r in conn.execute("SELECT * FROM pois")]
    return pd.DataFrame(rows)


def build_report(conn):
    df = _df(conn)
    total = len(df)
    lines = []
    lines.append("# Báo cáo chất lượng dữ liệu địa điểm — WiseTravel\n")
    lines.append(f"_Sinh tự động lúc {datetime.datetime.now():%Y-%m-%d %H:%M}_\n")
    lines.append(f"**Tổng số địa điểm:** {total}\n")

    if total == 0:
        lines.append("\n> Chưa có dữ liệu. Hãy chạy `scripts/01_fetch_pois.py` trước.\n")
        return "\n".join(lines)

    # 1) Số lượng theo loại hình
    lines.append("\n## 1. Số địa điểm theo loại hình\n")
    lines.append("| Loại hình | Mã | Số lượng | Tỷ lệ |")
    lines.append("|---|---|---:|---:|")
    by_cat = df["category"].value_counts()
    for cat, n in by_cat.items():
        vi = config.CATEGORY_LABELS_VI.get(cat, cat)
        lines.append(f"| {vi} | `{cat}` | {n} | {n / total:.1%} |")

    # 2) Độ đầy đủ của từng trường
    has_hours = df["opening_hours"].notna() & (df["opening_hours"].astype(str).str.len() > 0)
    if "hours_source" not in df.columns:
        df["hours_source"] = None
    real_hours = df["hours_source"].isin(["osm", "google", "manual"])
    lines.append("\n## 2. Tỷ lệ đầy đủ theo trường\n")
    lines.append("| Trường | Có dữ liệu | Tỷ lệ |")
    lines.append("|---|---:|---:|")
    completeness = {
        "name": df["name"].notna() & (df["name"].str.len() > 0),
        "lat/lng (tọa độ)": df["lat"].notna() & df["lng"].notna(),
        "opening_hours (mọi nguồn)": has_hours,
        "opening_hours (nguồn thật: osm/google/manual)": real_hours,
        "price_level (suy từ dữ liệu thật)": df["price_level_estimated"] == 0,
        "est_duration_min": df["est_duration_min"].notna(),
    }
    for field, mask in completeness.items():
        n = int(mask.sum())
        lines.append(f"| {field} | {n} | {n / total:.1%} |")
    lines.append(
        "\n> Ghi chú: `price_level` luôn có giá trị, nhưng đa số là **ước lượng heuristic** "
        "(cờ `price_level_estimated=1`). Cột trên đếm số bản ghi mức giá suy được từ dữ liệu thật "
        "(vd số sao khách sạn).\n"
    )

    # 2b) Phân bố giờ mở cửa theo nguồn
    lines.append("\n## 2b. Giờ mở cửa theo nguồn (`hours_source`)\n")
    lines.append("| hours_source | Số lượng | Tỷ lệ | Tính vào accuracy audit? |")
    lines.append("|---|---:|---:|:---:|")
    src_order = ["osm", "google", "manual", "heuristic"]
    counts = df["hours_source"].value_counts(dropna=False).to_dict()
    extra = [k for k in counts if isinstance(k, str) and k not in src_order]
    for src in src_order + extra:
        n = counts.get(src, 0)
        if n == 0:
            continue
        mark = "✔" if src in ("osm", "google", "manual") else "✗"
        lines.append(f"| {src} | {n} | {n / total:.1%} | {mark} |")
    n_null = int(df["hours_source"].isna().sum())
    if n_null:
        lines.append(f"| (trống) | {n_null} | {n_null / total:.1%} | ✗ |")
    lines.append(
        "\n> Accuracy audit **chỉ đo trên bản ghi nguồn thật** (`osm`/`google`/`manual`). "
        "Bản ghi `heuristic` là giá trị mặc định theo loại hình nên bị loại khỏi phép đo độ chính xác.\n"
    )

    # 2c) Trạng thái hoạt động (Google) — chỉ in nếu đã làm giàu Google
    if "business_status" in df.columns and df["business_status"].notna().any():
        lines.append("\n## 2c. Trạng thái hoạt động (`business_status`, nguồn Google)\n")
        lines.append("| business_status | Số lượng | Tỷ lệ |")
        lines.append("|---|---:|---:|")
        for st, n in df["business_status"].value_counts(dropna=False).items():
            label = st if isinstance(st, str) else "(chưa tra Google)"
            lines.append(f"| {label} | {n} | {n / total:.1%} |")
        lines.append(
            "\n> `CLOSED_PERMANENTLY` = quán đã đóng cửa (Google) → bị loại khỏi truy vấn & audit.\n")

    # 3) Giá mức giá phân bố
    lines.append("\n## 3. Phân bố mức giá (ước lượng)\n")
    lines.append("| price_level | Số lượng |")
    lines.append("|---:|---:|")
    for lvl, n in df["price_level"].value_counts().sort_index().items():
        lines.append(f"| {lvl} | {n} |")

    # 4) Nguồn
    lines.append("\n## 4. Nguồn dữ liệu\n")
    lines.append("| Nguồn | Số lượng |")
    lines.append("|---|---:|")
    for src, n in df["source"].value_counts().items():
        lines.append(f"| {src} | {n} |")

    return "\n".join(lines) + "\n"
