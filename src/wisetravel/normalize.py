"""Chuẩn hóa loại hình, heuristic giá/thời lượng, khử trùng lặp, sample cân bằng."""
import datetime
import random
import re
from collections import defaultdict

import config


def norm_name(name):
    """Chuẩn hóa tên để so trùng: thường hóa + gộp khoảng trắng."""
    return re.sub(r"\s+", " ", name.strip().lower())


def classify(tags):
    """Suy (category, subtype) từ tag OSM theo thứ tự ưu tiên trong config."""
    for cat, spec in config.CATEGORY_TAGS.items():
        for key, vals in spec.items():
            v = tags.get(key)
            if v is None:
                continue
            if vals == ["*"] or v in vals:
                return cat, f"{key}={v}"
    return None, None


def estimate_price(cat, tags):
    """Trả về (price_level, estimated) — estimated=True nếu chỉ đoán theo loại hình."""
    # Khách sạn có số sao -> suy mức giá từ dữ liệu thật.
    stars = tags.get("stars")
    if cat == "lodging" and stars and stars.strip()[:1].isdigit():
        s = int(stars.strip()[0])
        level = 3 if s >= 4 else (2 if s >= 3 else 1)
        return level, False
    # Fast food thường rẻ.
    if tags.get("amenity") == "fast_food":
        return 1, True
    # Mặc định theo loại hình.
    return config.DEFAULT_PRICE_LEVEL.get(cat, 2), True


def extract_address(tags):
    """Trích (district, address) từ các tag addr:* của OSM (có thể None)."""
    district = (tags.get("addr:district") or tags.get("addr:subdistrict")
                or tags.get("addr:suburb") or tags.get("addr:quarter"))
    num = tags.get("addr:housenumber")
    street = tags.get("addr:street")
    line = " ".join(p for p in (num, street) if p) or tags.get("addr:full")
    ward = tags.get("addr:ward") or tags.get("addr:quarter")
    address = ", ".join(p for p in (line, ward) if p) or None
    return district, address


def to_record(el):
    """Chuyển 1 element Overpass -> dict bản ghi POI, hoặc None nếu bỏ qua."""
    tags = el.get("tags", {})
    name = tags.get("name")
    if not name:
        return None  # bỏ địa điểm không tên để giữ chất lượng

    cat, subtype = classify(tags)
    if cat is None:
        return None

    if el.get("type") == "node":
        lat, lng = el.get("lat"), el.get("lon")
    else:  # way / relation -> dùng tâm
        c = el.get("center") or {}
        lat, lng = c.get("lat"), c.get("lon")
    if lat is None or lng is None:
        return None

    price, estimated = estimate_price(cat, tags)
    osm_hours = tags.get("opening_hours")
    district, address = extract_address(tags)
    return {
        "id": f"{el['type']}/{el['id']}",
        "name": name.strip(),
        "lat": float(lat),
        "lng": float(lng),
        "category": cat,
        "subtype": subtype,
        "district": district,
        "address": address,
        "opening_hours": osm_hours,
        "hours_source": "osm" if osm_hours else None,
        "price_level": price,
        "price_level_estimated": 1 if estimated else 0,
        "est_duration_min": config.EST_DURATION_MIN.get(cat),
        "source": "OpenStreetMap (Overpass)",
        "last_updated": datetime.date.today().isoformat(),
    }


def _richness(r):
    """Điểm "đầy đủ" để chọn bản ghi tốt hơn khi trùng."""
    score = 0
    if r.get("opening_hours"):
        score += 2
    if not r["price_level_estimated"]:
        score += 1
    return score


def dedupe(records):
    """Gộp bản ghi cùng tên chuẩn hóa trong cùng ô lưới ~100m, giữ bản đầy đủ hơn."""
    best = {}
    for r in records:
        key = (norm_name(r["name"]), round(r["lat"], 3), round(r["lng"], 3))
        if key not in best or _richness(r) > _richness(best[key]):
            best[key] = r
    return list(best.values())


def balanced_sample(records, target=None, seed=None):
    """Sample về ~target, cân bằng tỉ lệ theo category để báo cáo độ phủ đẹp."""
    target = target or config.TARGET_POI_COUNT
    seed = config.SAMPLE_SEED if seed is None else seed
    if len(records) <= target:
        return records

    rng = random.Random(seed)
    by_cat = defaultdict(list)
    for r in records:
        by_cat[r["category"]].append(r)

    total = len(records)
    out = []
    for cat, items in by_cat.items():
        k = max(1, round(target * len(items) / total))
        k = min(k, len(items))
        out.extend(rng.sample(items, k))

    rng.shuffle(out)
    return out[:target]
