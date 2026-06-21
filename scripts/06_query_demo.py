"""Phase 1.7: demo hàm truy vấn ứng viên (category + mở cửa lúc T + mức giá)."""
import datetime

import _bootstrap  # noqa: F401

from wisetravel import db, query


def main():
    conn = db.connect()
    # Ví dụ: quán cà phê mở cửa 20:00 hôm nay, mức giá <= 2.
    t = datetime.datetime.now().replace(hour=20, minute=0, second=0, microsecond=0)
    df = query.query_pois(conn, categories=["cafe"], open_at=t, max_price=2, limit=10)
    conn.close()

    print(f"Quán cà phê mở cửa lúc {t:%H:%M %d/%m}, giá <= 2 (tối đa 10 KQ):\n")
    if df.empty:
        print("(không có kết quả)")
        return
    cols = [c for c in ("name", "price_level", "open_status", "opening_hours") if c in df.columns]
    print(df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
