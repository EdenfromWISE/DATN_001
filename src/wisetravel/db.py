"""Lớp lưu trữ SQLite cho POI."""
import pathlib
import sqlite3

DB_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "wisetravel.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pois (
    id                     TEXT PRIMARY KEY,   -- "node/123", "way/456" từ OSM
    name                   TEXT NOT NULL,
    lat                    REAL NOT NULL,
    lng                    REAL NOT NULL,
    category               TEXT NOT NULL,      -- food | cafe | lodging | attraction
    subtype                TEXT,               -- tag OSM gốc, vd "amenity=restaurant"
    district               TEXT,               -- quận/phường từ tag addr:* (nếu có)
    address                TEXT,               -- địa chỉ ghép từ addr:* OSM (nếu có)
    address_google         TEXT,               -- formatted_address từ Google (nếu đã làm giàu)
    opening_hours          TEXT,               -- chuỗi opening_hours OSM (có thể NULL)
    hours_source           TEXT,               -- osm | google | heuristic | manual
    place_id               TEXT,               -- Google Place ID (nếu đã làm giàu)
    business_status        TEXT,               -- OPERATIONAL|CLOSED_TEMPORARILY|CLOSED_PERMANENTLY (Google)
    price_level            INTEGER,            -- 1..3
    price_level_estimated  INTEGER NOT NULL DEFAULT 1,  -- 1=ước lượng, 0=suy từ dữ liệu
    est_duration_min       INTEGER,            -- thời lượng tham quan ước lượng (phút)
    source                 TEXT NOT NULL,
    last_updated           TEXT NOT NULL       -- ISO date
);
"""

INSERT_SQL = """
INSERT INTO pois (id, name, lat, lng, category, subtype, district, address,
                  opening_hours, hours_source, price_level, price_level_estimated,
                  est_duration_min, source, last_updated)
VALUES (:id, :name, :lat, :lng, :category, :subtype, :district, :address,
        :opening_hours, :hours_source, :price_level, :price_level_estimated,
        :est_duration_min, :source, :last_updated)
ON CONFLICT(id) DO UPDATE SET
    name=excluded.name, lat=excluded.lat, lng=excluded.lng,
    category=excluded.category, subtype=excluded.subtype,
    district=excluded.district, address=excluded.address,
    opening_hours=excluded.opening_hours, hours_source=excluded.hours_source,
    price_level=excluded.price_level,
    price_level_estimated=excluded.price_level_estimated,
    est_duration_min=excluded.est_duration_min,
    source=excluded.source, last_updated=excluded.last_updated;
"""


def connect(db_path=DB_PATH):
    db_path = pathlib.Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    # Migration: thêm cột mới cho DB cũ chưa có (CREATE IF NOT EXISTS không tự thêm cột).
    cols = {row[1] for row in conn.execute("PRAGMA table_info(pois)")}
    for col in ("hours_source", "district", "address", "address_google",
                "place_id", "business_status"):
        if col not in cols:
            conn.execute(f"ALTER TABLE pois ADD COLUMN {col} TEXT")
    conn.commit()


def upsert_pois(conn, records):
    conn.executemany(INSERT_SQL, records)
    conn.commit()
    return len(records)


def count(conn):
    return conn.execute("SELECT COUNT(*) FROM pois").fetchone()[0]
