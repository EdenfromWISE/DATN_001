"""Phase 1.5a: xuất 50 địa điểm ngẫu nhiên ra CSV để kiểm tay."""
import _bootstrap  # noqa: F401

from wisetravel import audit, db


def main():
    conn = db.connect()
    out = _bootstrap.AUDIT / "audit_sample.csv"
    try:
        n = audit.make_sample(conn, out, n=50)
    except PermissionError:
        # File đang mở (thường do Excel) -> ghi ra file dự phòng, không làm hỏng file đang xem.
        fallback = _bootstrap.AUDIT / "audit_sample_NEW.csv"
        n = audit.make_sample(conn, fallback, n=50)
        conn.close()
        print(f"⚠️  '{out.name}' đang bị khóa (Excel đang mở?). Đã ghi tạm -> {fallback}")
        print("   Hãy ĐÓNG Excel, xóa file cũ rồi đổi tên file _NEW thành audit_sample.csv,")
        print("   hoặc chạy lại script này.")
        return
    conn.close()
    print(f"✅ Đã xuất {n} dòng -> {out}")
    print("\n👉 Cách kiểm mỗi dòng (xem chi tiết 'Quy tắc chấm' trong README):")
    print("   B1. Mở 'link_by_coord' → Google ghim đúng tọa độ. ZOOM TO, xem Google gắn")
    print("       cửa hàng/địa điểm TÊN GÌ ngay tại ghim đó.")
    print("   B2. So tên đó với cột 'name'. Trùng (hoặc cùng một nơi) → coord_dung = Y; nếu")
    print("       chỗ ghim là nơi khác hẳn / đồng trống → N.")
    print("   B3. Tham chiếu thêm: 'link_by_name' (chính xác hơn khi has_address=Y) và")
    print("       'osm_link' (xem đúng đối tượng OSM gốc).")
    print("   - hours_dung: (tùy chọn) Y/N nếu muốn kiểm giờ mở cửa; để trống nếu không kiểm.")
    print("   (Mẫu chỉ gồm bản ghi giờ nguồn thật osm/google/manual — bỏ heuristic.)")
    print("   Lưu lại rồi chạy: python scripts/05_score_audit.py")


if __name__ == "__main__":
    main()
