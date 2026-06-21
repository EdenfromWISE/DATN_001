"""Fetch POI từ Overpass API (OpenStreetMap)."""
import time

import requests

import config


def build_query(bbox):
    """Sinh Overpass QL lấy mọi loại hình trong bbox.

    bbox = (south, west, north, east).
    """
    s, w, n, e = bbox
    b = f"{s},{w},{n},{e}"
    selectors = []
    for spec in config.CATEGORY_TAGS.values():
        for key, vals in spec.items():
            if vals == ["*"]:
                selectors.append(f'  nwr["{key}"]({b});')
            else:
                rx = "|".join(vals)
                selectors.append(f'  nwr["{key}"~"^({rx})$"]({b});')
    body = "\n".join(selectors)
    return f"[out:json][timeout:180];\n(\n{body}\n);\nout center tags;"


def fetch(bbox=None, urls=None, max_retries=3):
    """Trả về list element thô từ Overpass (node/way/relation)."""
    bbox = bbox or config.HANOI_BBOX
    urls = urls or config.OVERPASS_FALLBACKS
    query = build_query(bbox)
    last_err = None
    for url in urls:
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    url, data={"data": query}, timeout=300,
                    headers={"User-Agent": "WiseTravel-demo/1.0 (academic project)"},
                )
                resp.raise_for_status()
                return resp.json().get("elements", [])
            except (requests.RequestException, ValueError) as err:
                last_err = err
                wait = 5 * (attempt + 1)
                print(f"  [warn] {url} thất bại ({err!r}), thử lại sau {wait}s...")
                time.sleep(wait)
        print(f"  [warn] Bỏ qua endpoint {url}, chuyển endpoint khác.")
    raise RuntimeError(f"Không gọi được Overpass sau khi thử mọi endpoint: {last_err!r}")
