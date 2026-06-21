"""Phase 2.2: tính Cohen's Kappa từ 2 cột annotator của tập gold."""
import _bootstrap  # noqa: F401

import pandas as pd

from wisetravel import agreement

GOLD = _bootstrap.DATA / "gold" / "gold.csv"


def main():
    if not GOLD.exists():
        print(f"Chưa có {GOLD}. Tạo từ template:")
        print("   python scripts/07_make_gold_template.py  (rồi điền & lưu thành gold.csv)")
        return
    df = pd.read_csv(GOLD, encoding="utf-8-sig")
    stats = agreement.analyze(df)
    report = agreement.format_report(stats)
    print(report)
    out = _bootstrap.REPORTS / "kappa_result.md"
    out.write_text(report, encoding="utf-8")
    print(f"✅ Đã ghi {out}")


if __name__ == "__main__":
    main()
