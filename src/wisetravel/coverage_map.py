"""Vẽ bản đồ độ phủ POI bằng folium (xuất HTML)."""
import folium
from folium.plugins import MarkerCluster

import config

CATEGORY_COLORS = {
    "food": "red",
    "cafe": "orange",
    "lodging": "blue",
    "attraction": "green",
}
HANOI_CENTER = (21.0285, 105.8542)  # Hồ Hoàn Kiếm


def build_map(conn, out_path):
    rows = [dict(r) for r in conn.execute("SELECT * FROM pois")]
    fmap = folium.Map(location=HANOI_CENTER, zoom_start=13, tiles="cartodbpositron")

    # Mỗi loại hình một cụm marker bật/tắt được.
    clusters = {}
    for cat in config.CATEGORY_TAGS:
        label = config.CATEGORY_LABELS_VI.get(cat, cat)
        fg = folium.FeatureGroup(name=f"{label} ({cat})")
        clusters[cat] = MarkerCluster().add_to(fg)
        fg.add_to(fmap)

    for r in rows:
        cat = r["category"]
        color = CATEGORY_COLORS.get(cat, "gray")
        price = "₫" * (r["price_level"] or 1)
        hsrc = r["hours_source"] if "hours_source" in r.keys() else None
        popup = folium.Popup(
            f"<b>{r['name']}</b><br>{cat} · {price}<br>"
            f"Giờ: {r['opening_hours'] or '—'} <i>({hsrc or 'n/a'})</i><br>"
            f"Thời lượng ~{r['est_duration_min']}'",
            max_width=260,
        )
        folium.CircleMarker(
            location=(r["lat"], r["lng"]),
            radius=4, color=color, fill=True, fill_opacity=0.8,
            popup=popup,
        ).add_to(clusters.get(cat, fmap))

    folium.LayerControl(collapsed=False).add_to(fmap)
    fmap.save(str(out_path))
    return len(rows)
