"""Thêm thư mục gốc dự án và src/ vào sys.path để import được config + wisetravel."""
import pathlib
import sys

# Ép stdout/stderr sang UTF-8 để in được tiếng Việt trên console Windows (cp1252).
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "src"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

REPORTS = ROOT / "reports"
DATA = ROOT / "data"
AUDIT = DATA / "audit"
for d in (REPORTS, DATA, AUDIT):
    d.mkdir(parents=True, exist_ok=True)
