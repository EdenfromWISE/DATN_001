"""Làm giàu giờ mở cửa từ Google Places API (tùy chọn — chỉ chạy khi có API key).

Đọc key từ biến môi trường GOOGLE_PLACES_API_KEY (hoặc GOOGLE_MAPS_API_KEY).
Luồng: Text Search (name + tọa độ) -> lấy place_id -> Place Details (opening_hours)
-> chuyển periods của Google sang chuỗi opening_hours kiểu OSM để parser oh.py dùng được.
"""
import os

import requests

TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

# Google: 0=Chủ nhật .. 6=Thứ bảy  ->  ký hiệu ngày OSM
GOOGLE_DAY_TO_OSM = {0: "Su", 1: "Mo", 2: "Tu", 3: "We", 4: "Th", 5: "Fr", 6: "Sa"}


class GoogleApiError(RuntimeError):
    """Lỗi cấu hình/khóa Google (REQUEST_DENIED, OVER_QUERY_LIMIT, ...)."""


def get_api_key():
    return os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")


def _fmt_time(hhmm):
    """'0900' -> '09:00'."""
    hhmm = (hhmm or "").zfill(4)
    return f"{hhmm[:2]}:{hhmm[2:]}"


def periods_to_osm(periods):
    """Chuyển danh sách periods của Google -> chuỗi opening_hours kiểu OSM (hoặc None)."""
    if not periods:
        return None
    # Mở 24/7: đúng 1 period, open ngày 0 lúc 0000, không có close.
    if len(periods) == 1 and "close" not in periods[0]:
        if periods[0].get("open", {}).get("time") in ("0000", "", None):
            return "24/7"
    rules = []
    for p in periods:
        o = p.get("open")
        if not o:
            continue
        day = GOOGLE_DAY_TO_OSM.get(o.get("day"))
        if not day:
            continue
        c = p.get("close")
        if c is None:
            rng = "00:00-24:00"
        else:
            rng = f"{_fmt_time(o.get('time'))}-{_fmt_time(c.get('time'))}"
        rules.append(f"{day} {rng}")
    return "; ".join(rules) if rules else None


def _check_status(payload):
    status = payload.get("status")
    if status in ("OK", "ZERO_RESULTS"):
        return status
    msg = payload.get("error_message", "")
    raise GoogleApiError(f"Google trả status={status} {msg}".strip())


def parse_textsearch(ts_json):
    """Tách (place_id, address, business_status) từ kết quả Text Search.

    Trả về None nếu không có kết quả (ZERO_RESULTS / rỗng).
    business_status: OPERATIONAL | CLOSED_TEMPORARILY | CLOSED_PERMANENTLY | None.
    """
    if _check_status(ts_json) == "ZERO_RESULTS":
        return None
    results = ts_json.get("results") or []
    if not results:
        return None
    top = results[0]
    return {
        "place_id": top.get("place_id"),
        "address": top.get("formatted_address"),
        "business_status": top.get("business_status"),
    }


def lookup(name, lat, lng, api_key, session=None):
    """Tra cứu 1 địa điểm trên Google Places.

    Trả về dict {place_id, opening_hours, address, business_status} (có thể None),
    hoặc None nếu không tìm thấy địa điểm nào trên Google.
    """
    sess = session or requests.Session()

    ts = sess.get(TEXTSEARCH_URL, timeout=30, params={
        "query": name,
        "location": f"{lat},{lng}",
        "radius": 150,           # ưu tiên kết quả gần tọa độ OSM
        "key": api_key,
    })
    ts.raise_for_status()
    base = parse_textsearch(ts.json())
    if base is None:
        return None
    result = {**base, "opening_hours": None}

    place_id = base.get("place_id")
    if not place_id:
        return result

    det = sess.get(DETAILS_URL, timeout=30, params={
        "place_id": place_id,
        "fields": "opening_hours",
        "key": api_key,
    })
    det.raise_for_status()
    det_json = det.json()
    _check_status(det_json)
    oh = (det_json.get("result") or {}).get("opening_hours") or {}
    result["opening_hours"] = periods_to_osm(oh.get("periods"))
    return result
