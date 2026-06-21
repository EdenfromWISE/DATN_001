"""Phase 1 (nâng cấp): làm giàu dữ liệu từ Google Places + heuristic.

(a) Google Places cho MỌI POI (nếu có API key):
      - place_id, địa chỉ chuẩn (address_google), business_status
      - opening_hours nếu OSM còn thiếu -> hours_source='google'
(b) Heuristic giờ mở cửa cho phần vẫn thiếu -> hours_source='heuristic'.

business_status giúp tự phát hiện quán đã đóng (CLOSED_PERMANENTLY) để loại khỏi demo/audit.

Chạy SAU 01_fetch_pois.py. Google đọc key từ biến môi trường:
    PowerShell:  $env:GOOGLE_PLACES_API_KEY = "AIza..."
Không có key -> bỏ qua bước Google, vẫn chạy heuristic.
"""
import time

import _bootstrap  # noqa: F401

import config
from wisetravel import db, google_places


def _enrich_google(conn, key):
    # Gọi Google cho TẤT CẢ POI để lấy place_id + địa chỉ + business_status.
    targets = conn.execute("SELECT id, name, lat, lng, opening_hours FROM pois").fetchall()
    print(f"[Google] Làm giàu {len(targets)} POI (place_id + địa chỉ + trạng thái + giờ)...")
    session = google_places.requests.Session()
    matched = hours = closed = notfound = 0
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
            if not res:
                notfound += 1  # ZERO_RESULTS -> có thể OSM lỗi thời
                continue
            if res.get("place_id"):
                conn.execute("UPDATE pois SET place_id=? WHERE id=?",
                             (res["place_id"], row["id"]))
                matched += 1
            if res.get("address"):
                conn.execute("UPDATE pois SET address_google=? WHERE id=?",
                             (res["address"], row["id"]))
            if res.get("business_status"):
                conn.execute("UPDATE pois SET business_status=? WHERE id=?",
                             (res["business_status"], row["id"]))
                if res["business_status"] == "CLOSED_PERMANENTLY":
                    closed += 1
            # Chỉ bổ sung giờ nếu OSM chưa có (không đè dữ liệu OSM thật).
            if not row["opening_hours"] and res.get("opening_hours"):
                conn.execute(
                    "UPDATE pois SET opening_hours=?, hours_source='google' WHERE id=?",
                    (res["opening_hours"], row["id"]))
                hours += 1
            if i % 50 == 0:
                conn.commit()
                print(f"  ... {i}/{len(targets)} "
                      f"(place_id {matched}, giờ {hours}, đóng cửa {closed})")
            time.sleep(0.05)  # nhẹ tay với quota
    finally:
        conn.commit()
    print(f"[Google] place_id {matched} · bổ sung giờ {hours} · "
          f"đóng cửa vĩnh viễn {closed} · không thấy trên Google {notfound}")


def main():
    conn = db.connect()
    db.init_db(conn)
    if db.count(conn) == 0:
        print("DB rỗng — hãy chạy scripts/01_fetch_pois.py trước.")
        return

    key = google_places.get_api_key()
    if key:
        _enrich_google(conn, key)
    else:
        print("[Google] Không thấy GOOGLE_PLACES_API_KEY -> bỏ qua bước Google.")

    # Heuristic fallback cho phần vẫn thiếu giờ.
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

    print("\nPhân bố hours_source:")
    for s, n in conn.execute(
        "SELECT COALESCE(hours_source,'(trống)') s, COUNT(*) n "
        "FROM pois GROUP BY s ORDER BY n DESC"
    ).fetchall():
        print(f"   {s:12s}: {n}")

    closed_total = conn.execute(
        "SELECT COUNT(*) FROM pois WHERE business_status='CLOSED_PERMANENTLY'"
    ).fetchone()[0]
    if closed_total:
        print(f"\n⚠️  {closed_total} quán Google báo đã ĐÓNG CỬA VĨNH VIỄN.")
        print("   Truy vấn (query.py) mặc định đã loại các quán này.")
        print("   Muốn xóa hẳn khỏi DB, chạy: python scripts/02_enrich_hours.py --drop-closed")
    conn.close()


def drop_closed():
    conn = db.connect()
    n = conn.execute(
        "DELETE FROM pois WHERE business_status='CLOSED_PERMANENTLY'").rowcount
    conn.commit()
    conn.close()
    print(f"🗑️  Đã xóa {n} quán đóng cửa vĩnh viễn khỏi DB.")


if __name__ == "__main__":
    import sys
    if "--drop-closed" in sys.argv:
        drop_closed()
    else:
        main()
