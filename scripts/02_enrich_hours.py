"""Phase 1 (nâng cấp): làm giàu giờ mở cửa.

Thứ tự: (a) Google Places cho POI thiếu giờ (nếu có API key) -> hours_source='google';
        (b) Heuristic theo category cho phần vẫn thiếu        -> hours_source='heuristic'.

Chạy SAU 01_fetch_pois.py. Google đọc key từ biến môi trường:
    PowerShell:  $env:GOOGLE_PLACES_API_KEY = "AIza..."
Không có key -> bỏ qua bước Google, vẫn chạy heuristic.
"""
import time

import _bootstrap  # noqa: F401

import config
from wisetravel import db, google_places


def main():
    conn = db.connect()
    db.init_db(conn)
    if db.count(conn) == 0:
        print("DB rỗng — hãy chạy scripts/01_fetch_pois.py trước.")
        return

    # (a) Google Places: nhắm các bản ghi chưa có giờ "thật" (NULL hoặc đang là heuristic).
    key = google_places.get_api_key()
    if key:
        targets = conn.execute(
            "SELECT id, name, lat, lng FROM pois "
            "WHERE opening_hours IS NULL OR opening_hours='' OR hours_source='heuristic'"
        ).fetchall()
        print(f"[Google] {len(targets)} POI cần làm giàu. Đang gọi Places API ...")
        session = google_places.requests.Session()
        filled = 0   # số POI được bổ sung GIỜ mở cửa
        matched = 0  # số POI khớp được place_id
        try:
            for i, row in enumerate(targets, 1):
                try:
                    res = google_places.lookup(
                        row["name"], row["lat"], row["lng"], key, session=session)
                except google_places.GoogleApiError as err:
                    print(f"  [stop] Lỗi cấu hình Google: {err}")
                    break
                except Exception as err:  # noqa: BLE001 - lỗi mạng lẻ tẻ -> bỏ qua POI đó
                    print(f"  [warn] {row['name']}: {err!r}")
                    continue
                if res:
                    if res.get("place_id"):
                        conn.execute("UPDATE pois SET place_id=? WHERE id=?",
                                     (res["place_id"], row["id"]))
                        matched += 1
                    if res.get("opening_hours"):
                        conn.execute(
                            "UPDATE pois SET opening_hours=?, hours_source='google' WHERE id=?",
                            (res["opening_hours"], row["id"]))
                        filled += 1
                if i % 50 == 0:
                    conn.commit()
                    print(f"  ... {i}/{len(targets)} (giờ {filled}, place_id {matched})")
                time.sleep(0.05)  # nhẹ tay với quota
        finally:
            conn.commit()
        print(f"[Google] Khớp place_id: {matched}; bổ sung giờ: {filled} POI.")
    else:
        print("[Google] Không thấy GOOGLE_PLACES_API_KEY -> bỏ qua bước Google.")

    # (b) Heuristic fallback cho phần vẫn thiếu.
    still = conn.execute(
        "SELECT id, category FROM pois WHERE opening_hours IS NULL OR opening_hours=''"
    ).fetchall()
    heur = 0
    for row in still:
        default = config.HEURISTIC_OPENING_HOURS.get(row["category"])
        if default:
            conn.execute(
                "UPDATE pois SET opening_hours=?, hours_source='heuristic' WHERE id=?",
                (default, row["id"]))
            heur += 1
    conn.commit()
    print(f"[Heuristic] Điền giờ mặc định cho {heur} POI.")

    # Tổng kết phân bố nguồn giờ.
    print("\nPhân bố hours_source:")
    rows = conn.execute(
        "SELECT COALESCE(hours_source,'(trống)') s, COUNT(*) n "
        "FROM pois GROUP BY s ORDER BY n DESC"
    ).fetchall()
    for s, n in rows:
        print(f"   {s:12s}: {n}")
    conn.close()


if __name__ == "__main__":
    main()
