"""Phase 1.4 + 1.6: sinh báo cáo chất lượng + bản đồ độ phủ folium."""
import _bootstrap  # noqa: F401

from wisetravel import coverage_map, db, quality


def main():
    conn = db.connect()
    if db.count(conn) == 0:
        print("DB rỗng — hãy chạy scripts/01_fetch_pois.py trước.")
        return

    report = quality.build_report(conn)
    report_path = _bootstrap.REPORTS / "quality_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"✅ Báo cáo chất lượng -> {report_path}")

    map_path = _bootstrap.REPORTS / "coverage_map.html"
    n = coverage_map.build_map(conn, map_path)
    print(f"✅ Bản đồ độ phủ ({n} điểm) -> {map_path}")
    conn.close()


if __name__ == "__main__":
    main()
