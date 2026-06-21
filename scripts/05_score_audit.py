"""Phase 1.5b: đọc CSV audit đã điền -> tính % chính xác."""
import _bootstrap  # noqa: F401

from wisetravel import audit


def main():
    csv = _bootstrap.AUDIT / "audit_sample.csv"
    if not csv.exists():
        print("Chưa có audit_sample.csv — chạy 04_make_audit_sample.py trước.")
        return
    result = audit.score(csv)
    print(audit.format_score(result))

    out = _bootstrap.REPORTS / "audit_result.md"
    lines = [
        "# Kết quả Accuracy Audit\n",
        f"- Tổng dòng mẫu: **{result['rows_total']}**",
        f"- Tọa độ: kiểm {result['coord_checked']}, đúng {result['coord_correct']} "
        f"→ **{_pct(result['coord_accuracy'])}**",
        f"- Giờ mở cửa: kiểm {result['hours_checked']}, đúng {result['hours_correct']} "
        f"→ **{_pct(result['hours_accuracy'])}**",
        f"- (Đã loại {result.get('hours_heuristic_excluded', 0)} bản ghi `heuristic` "
        "khỏi phép đo giờ mở cửa.)",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Đã ghi {out}")


def _pct(x):
    return "n/a" if x is None else f"{x:.1%}"


if __name__ == "__main__":
    main()
