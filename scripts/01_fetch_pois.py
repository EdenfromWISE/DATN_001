"""Phase 1.1-1.2: Fetch POI từ Overpass -> chuẩn hóa -> dedup -> sample -> lưu SQLite."""
import _bootstrap  # noqa: F401  (thiết lập sys.path + thư mục)

import config
from wisetravel import db, normalize, overpass


def main():
    print(f"[1/5] Gọi Overpass cho bbox nội đô Hà Nội {config.HANOI_BBOX} ...")
    elements = overpass.fetch()
    print(f"      Nhận {len(elements)} element thô.")

    print("[2/5] Chuẩn hóa loại hình + heuristic giá/thời lượng ...")
    records = [r for r in (normalize.to_record(e) for e in elements) if r]
    print(f"      {len(records)} bản ghi hợp lệ (có tên + tọa độ + loại hình).")

    print("[3/5] Khử trùng lặp ...")
    records = normalize.dedupe(records)
    print(f"      Còn {len(records)} sau khi gộp trùng.")

    print(f"[4/5] Sample cân bằng về ~{config.TARGET_POI_COUNT} ...")
    records = normalize.balanced_sample(records)
    print(f"      Giữ {len(records)} địa điểm.")

    print("[5/5] Lưu vào SQLite ...")
    conn = db.connect()
    db.init_db(conn)
    conn.execute("DELETE FROM pois;")  # làm tươi toàn bộ mỗi lần chạy
    db.upsert_pois(conn, records)
    total = db.count(conn)
    by_cat = conn.execute(
        "SELECT category, COUNT(*) FROM pois GROUP BY category ORDER BY 2 DESC"
    ).fetchall()
    conn.close()

    print(f"\n✅ Đã lưu {total} địa điểm vào {db.DB_PATH}")
    for cat, n in by_cat:
        print(f"   - {config.CATEGORY_LABELS_VI.get(cat, cat):8s} {cat:10s}: {n}")


if __name__ == "__main__":
    main()
