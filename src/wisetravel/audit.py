"""Harness kiểm định độ chính xác (accuracy audit).

make_sample : xuất 50 địa điểm ngẫu nhiên ra CSV để người kiểm tay.
              Mỗi dòng có HAI link (theo tên + theo tọa độ) để đối chiếu vị trí.
score       : đọc CSV đã điền -> tính % chính xác tọa độ & giờ mở cửa.
"""
import random
import urllib.parse

import pandas as pd

import config

REAL_HOURS_SOURCES = ("osm", "google", "manual")

SAMPLE_COLS = [
    "id", "name", "category", "district", "address", "has_address",
    "lat", "lng", "opening_hours", "hours_source",
    "link_by_name",           # ghim theo tên + ĐỊA CHỈ + quận + "Hà Nội" (kèm place_id nếu có)
    "link_by_coord",          # ghim theo tọa độ lat,lng (xem business Google gắn tại điểm đó)
    "osm_link",               # đối tượng OSM gốc (ground-truth: xem đúng vật thể + vị trí nguồn)
    "coord_dung",             # ĐIỀN TAY: Y/N — tọa độ trỏ đúng địa điểm?
    "hours_dung",             # ĐIỀN TAY: Y/N — giờ mở cửa đúng? (để trống nếu không kiểm)
    "ghi_chu",                # ghi chú tùy ý
]


def _link_by_name(name, address, district, place_id):
    # Có ĐỊA CHỈ thì tìm theo địa chỉ (KHÔNG kèm tên) — Google trỏ đúng vị trí dễ hơn.
    # Không có địa chỉ mới fallback về tên + quận.
    if address:
        parts = [p for p in (address, district) if p] + ["Hà Nội"]
    else:
        parts = [p for p in (name, district) if p] + ["Hà Nội"]
    q = urllib.parse.quote(", ".join(parts))
    link = f"https://www.google.com/maps/search/?api=1&query={q}"
    if place_id:
        link += f"&query_place_id={urllib.parse.quote(place_id)}"
    return link


def _link_by_coord(lat, lng):
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"


def _osm_link(poi_id):
    # poi_id dạng "node/123" / "way/456" -> trang đối tượng trên openstreetmap.org.
    return f"https://www.openstreetmap.org/{poi_id}"


def make_sample(conn, out_path, n=50, seed=None):
    """Xuất mẫu kiểm định. Ưu tiên bản ghi có giờ NGUỒN THẬT để phép đo giờ có nghĩa.

    Bản ghi hours_source='heuristic' bị loại khỏi mẫu (giờ chỉ là mặc định theo loại hình).
    """
    seed = config.SAMPLE_SEED if seed is None else seed
    rows = [dict(r) for r in conn.execute("SELECT * FROM pois")]
    if not rows:
        raise RuntimeError("DB rỗng — chạy 01_fetch_pois.py trước.")

    real = [r for r in rows if r.get("hours_source") in REAL_HOURS_SOURCES]
    pool = real if len(real) >= n else rows  # đủ giờ thật thì lấy hẳn từ nhóm đó
    rng = random.Random(seed)
    sample = rng.sample(pool, min(n, len(pool)))

    out = []
    for r in sample:
        district = r.get("district") or ""
        address = r.get("address") or ""
        place_id = r.get("place_id") or ""
        out.append({
            "id": r["id"], "name": r["name"], "category": r["category"],
            "district": district, "address": address,
            "has_address": "Y" if address else "N",
            "lat": r["lat"], "lng": r["lng"],
            "opening_hours": r["opening_hours"] or "",
            "hours_source": r.get("hours_source") or "",
            "link_by_name": _link_by_name(
                r["name"], address or None, district or None, place_id or None),
            "link_by_coord": _link_by_coord(r["lat"], r["lng"]),
            "osm_link": _osm_link(r["id"]),
            "coord_dung": "", "hours_dung": "", "ghi_chu": "",
        })
    df = pd.DataFrame(out, columns=SAMPLE_COLS)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")  # utf-8-sig để Excel mở đúng tiếng Việt
    return len(df)


# Giá trị chấp nhận khi điền tay: hỗ trợ cả Y/N lẫn 1/0 (tương thích file cũ).
_YES = {"y", "yes", "1", "true", "đúng", "dung"}
_NO = {"n", "no", "0", "false", "sai"}


def _to_bin(series):
    if series is None:
        return pd.Series(dtype="float64")

    def conv(v):
        if pd.isna(v):
            return float("nan")
        s = str(v).strip().lower()
        if s in _YES:
            return 1.0
        if s in _NO:
            return 0.0
        return float("nan")

    return series.map(conv)


def score(csv_path):
    """Đọc CSV đã điền, trả về dict kết quả accuracy.

    Đọc cột mới (coord_dung/hours_dung, Y/N); vẫn tương thích cột cũ (coord_correct/hours_correct).
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    coord_col = df["coord_dung"] if "coord_dung" in df.columns else df.get("coord_correct")
    hours_col = df["hours_dung"] if "hours_dung" in df.columns else df.get("hours_correct")
    coord = _to_bin(coord_col)
    hours = _to_bin(hours_col)

    # Loại bản ghi heuristic khỏi phép đo độ chính xác giờ mở cửa.
    if "hours_source" in df.columns:
        real = df["hours_source"].isin(REAL_HOURS_SOURCES)
        hours = hours.where(real)
        heuristic_excluded = int((~real).sum())
    else:
        heuristic_excluded = 0

    coord_n = int(coord.notna().sum())
    hours_n = int(hours.notna().sum())
    result = {
        "rows_total": len(df),
        "coord_checked": coord_n,
        "coord_correct": int((coord == 1).sum()),
        "coord_accuracy": (coord == 1).sum() / coord_n if coord_n else None,
        "hours_checked": hours_n,
        "hours_correct": int((hours == 1).sum()),
        "hours_accuracy": (hours == 1).sum() / hours_n if hours_n else None,
        "hours_heuristic_excluded": heuristic_excluded,
    }
    return result


def format_score(result):
    def pct(x):
        return "n/a (chưa điền)" if x is None else f"{x:.1%}"
    return (
        "=== KẾT QUẢ ACCURACY AUDIT ===\n"
        f"Tổng dòng mẫu          : {result['rows_total']}\n"
        f"Tọa độ đã kiểm         : {result['coord_checked']} "
        f"(đúng {result['coord_correct']}) -> {pct(result['coord_accuracy'])}\n"
        f"Giờ mở cửa đã kiểm     : {result['hours_checked']} "
        f"(đúng {result['hours_correct']}) -> {pct(result['hours_accuracy'])}\n"
        f"  (đã loại {result.get('hours_heuristic_excluded', 0)} bản ghi heuristic khỏi phép đo)\n"
    )
