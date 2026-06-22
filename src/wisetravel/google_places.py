"""Làm giàu dữ liệu từ Google Places API (New) — tùy chọn, chỉ chạy khi có API key.

Dùng **Places API (New)** (`places.googleapis.com/v1`) vì Google đã khóa Places API
legacy với các project tạo mới. Một lần gọi `places:searchText` trả về luôn
place_id + địa chỉ + business_status + giờ mở cửa (field mask), nên mỗi POI chỉ tốn
1 request (rẻ & nhanh hơn legacy 2 request).

Đọc key từ biến môi trường GOOGLE_PLACES_API_KEY (hoặc GOOGLE_MAPS_API_KEY).
Cần bật **"Places API (New)"** trong Google Cloud (service `places.googleapis.com`).
"""
import os

import requests

SEARCHTEXT_URL = "https://places.googleapis.com/v1/places:searchText"

# Field mask: chỉ xin đúng các trường cần -> rẻ hơn (tính tiền theo SKU theo field).
FIELD_MASK = ",".join([
    "places.id",
    "places.formattedAddress",
    "places.businessStatus",
    "places.regularOpeningHours.periods",
])

# Google: 0=Chủ nhật .. 6=Thứ bảy  ->  ký hiệu ngày OSM
GOOGLE_DAY_TO_OSM = {0: "Su", 1: "Mo", 2: "Tu", 3: "We", 4: "Th", 5: "Fr", 6: "Sa"}


class GoogleApiError(RuntimeError):
    """Lỗi cấu hình/khóa Google (PERMISSION_DENIED, API chưa bật, billing, ...)."""


def get_api_key():
    return os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")


def _fmt(part):
    """{'hour':9,'minute':0} -> '09:00'."""
    return f"{int(part.get('hour', 0)):02d}:{int(part.get('minute', 0)):02d}"


def periods_to_osm(periods):
    """Chuyển danh sách periods (Places API New) -> chuỗi opening_hours kiểu OSM (hoặc None).

    Mỗi period: {'open': {'day','hour','minute'}, 'close': {'day','hour','minute'}}.
    Mở 24/24: đúng 1 period, open Chủ nhật 00:00, không có 'close'.
    """
    if not periods:
        return None
    if len(periods) == 1 and "close" not in periods[0]:
        o = periods[0].get("open", {})
        if int(o.get("hour", 0)) == 0 and int(o.get("minute", 0)) == 0:
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
        rng = "00:00-24:00" if c is None else f"{_fmt(o)}-{_fmt(c)}"
        rules.append(f"{day} {rng}")
    return "; ".join(rules) if rules else None


def _raise_for_error(resp):
    """API New báo lỗi qua HTTP status + body {'error': {...}}. Ném GoogleApiError nếu lỗi cấu hình."""
    if resp.status_code == 200:
        return
    try:
        err = resp.json().get("error", {})
    except ValueError:
        err = {}
    status = err.get("status") or resp.status_code
    msg = err.get("message", "")
    raise GoogleApiError(f"Google trả status={status} {msg}".strip())


def parse_response(data):
    """Tách (place_id, address, business_status, opening_hours) từ kết quả searchText.

    Trả về None nếu không có địa điểm nào (Google không tìm thấy).
    """
    places = data.get("places") or []
    if not places:
        return None
    top = places[0]
    oh = top.get("regularOpeningHours") or {}
    return {
        "place_id": top.get("id"),
        "address": top.get("formattedAddress"),
        "business_status": top.get("businessStatus"),
        "opening_hours": periods_to_osm(oh.get("periods")),
    }


def lookup(name, lat, lng, api_key, session=None):
    """Tra cứu 1 địa điểm trên Google Places (New).

    Trả về dict {place_id, address, business_status, opening_hours} (giá trị có thể None),
    hoặc None nếu Google không tìm thấy địa điểm nào.
    """
    sess = session or requests.Session()
    resp = sess.post(
        SEARCHTEXT_URL,
        timeout=30,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        json={
            "textQuery": name,
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": 150.0,  # ưu tiên kết quả gần tọa độ OSM
                }
            },
            "maxResultCount": 1,
            "languageCode": "vi",
        },
    )
    _raise_for_error(resp)
    return parse_response(resp.json())
