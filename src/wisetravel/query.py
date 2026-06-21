"""Truy vấn ứng viên địa điểm: lọc theo category + mở cửa lúc T + mức giá."""
import pandas as pd

from wisetravel import oh


def load_df(conn):
    rows = [dict(r) for r in conn.execute("SELECT * FROM pois")]
    return pd.DataFrame(rows)


def query_pois(conn, categories=None, open_at=None, max_price=None,
               limit=None, include_unknown_hours=True):
    """Trả về DataFrame ứng viên.

    categories            : list category cần lấy (None = tất cả).
    open_at               : datetime; lọc địa điểm mở cửa lúc đó.
    max_price             : mức giá tối đa (1..3).
    include_unknown_hours : True -> giữ cả địa điểm không rõ giờ mở cửa.
    """
    df = load_df(conn)
    if df.empty:
        return df

    if categories:
        df = df[df["category"].isin(categories)]
    if max_price is not None:
        df = df[df["price_level"] <= max_price]

    if open_at is not None:
        status = df["opening_hours"].apply(lambda v: oh.is_open(v, open_at))
        df = df.assign(open_status=status.map(
            {True: "open", False: "closed", None: "unknown"}))
        keep = status == True  # noqa: E712 - so sánh phần tử Series
        if include_unknown_hours:
            keep = keep | status.isna()
        df = df[keep]

    df = df.reset_index(drop=True)
    if limit:
        df = df.head(limit)
    return df
