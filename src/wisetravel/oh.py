"""Parser opening_hours OSM (thực dụng, đủ dùng cho demo).

is_open(oh, dt) -> True / False / None(không rõ hoặc không parse được).
Hỗ trợ: 24/7, danh sách/khoảng ngày (Mo-Fr, Sa,Su), nhiều khung giờ, qua nửa đêm.
Bỏ qua: PH (ngày lễ), quy tắc "off", chú thích trong ngoặc.
"""
import re

DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
DAY_IDX = {d: i for i, d in enumerate(DAYS)}
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")


def _parse_days(spec):
    """spec kiểu 'Mo-Fr' hoặc 'Sa,Su' -> tập chỉ số ngày (Mon=0..Sun=6)."""
    result = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = a.strip()[:2], b.strip()[:2]
            if a in DAY_IDX and b in DAY_IDX:
                i, j = DAY_IDX[a], DAY_IDX[b]
                if i <= j:
                    result.update(range(i, j + 1))
                else:  # vòng qua cuối tuần, vd Sa-Mo
                    result.update(list(range(i, 7)) + list(range(0, j + 1)))
        else:
            p = part[:2]
            if p in DAY_IDX:
                result.add(DAY_IDX[p])
    return result


def is_open(oh, dt):
    if not oh:
        return None
    s = oh.strip()
    if s.replace(" ", "") in ("24/7", "Mo-Su00:00-24:00", "00:00-24:00"):
        return True

    wd = dt.weekday()          # Mon=0
    minutes = dt.hour * 60 + dt.minute
    parsed_any = False

    for rule in s.split(";"):
        rule = re.sub(r"\([^)]*\)", "", rule).strip()  # bỏ chú thích trong ngoặc
        if not rule:
            continue
        low = rule.lower()
        if "ph" in low or "off" in low or "closed" in low:
            continue
        if "24/7" in rule:
            return True

        m = TIME_RE.search(rule)
        if not m:
            continue

        dayspec = rule[: m.start()].strip()
        if dayspec:
            days = _parse_days(dayspec)
            if not days:        # không nhận diện được -> coi như mọi ngày
                days = set(range(7))
        else:
            days = set(range(7))

        parsed_any = True
        if wd not in days:
            continue

        for h1, m1, h2, m2 in TIME_RE.findall(rule):
            start = int(h1) * 60 + int(m1)
            end = int(h2) * 60 + int(m2)
            if end == 0:
                end = 24 * 60
            if start <= end:
                if start <= minutes < end:
                    return True
            else:               # khung qua nửa đêm, vd 18:00-02:00
                if minutes >= start or minutes < end:
                    return True

    return False if parsed_any else None
