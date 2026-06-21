"""Phase 2.1: sinh template tập gold (CSV) + guideline gán nhãn (markdown)."""
import _bootstrap  # noqa: F401

import pandas as pd

GOLD_DIR = _bootstrap.DATA / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)

GOLD_COLS = ["id", "text", "label", "annotator1", "annotator2", "source"]

# Vài dòng ví dụ để bạn thấy định dạng (xóa đi rồi điền dữ liệu thật của bạn).
EXAMPLES = [
    ("1", "Quán ngon, nhân viên thân thiện, sẽ quay lại!", "POS", "POS", "POS", "vd"),
    ("2", "Đồ ăn dở, đợi rất lâu mà phục vụ thái độ.", "NEG", "NEG", "NEG", "vd"),
    ("3", "Quán bình thường, không có gì đặc biệt.", "NEU", "NEU", "NEU", "vd"),
    ("4", "Giá hơi cao nhưng không gian đẹp, đồ uống ổn.", "POS", "POS", "NEU", "vd"),
]

GUIDELINE = """# Guideline gán nhãn cảm xúc — WiseTravel

Mục tiêu: gán mỗi review tiếng Việt vào **một** trong ba nhãn cảm xúc.

## 3 nhãn
| Nhãn | Mã | Định nghĩa |
|---|---|---|
| **Tích cực** | `POS` | Người viết hài lòng / khen / có ý định quay lại. |
| **Tiêu cực** | `NEG` | Người viết không hài lòng / chê / cảnh báo người khác. |
| **Trung tính** | `NEU` | Mô tả khách quan, không rõ khen chê, hoặc cảm xúc lẫn lộn cân bằng. |

> Có thể ghi nhãn bằng tiếng Việt ("tích cực"/"tiêu cực"/"trung tính") hoặc mã POS/NEG/NEU —
> script tự chuẩn hóa. Mỗi dòng **chỉ một nhãn**.

## Quy tắc chung
1. **Gán theo tổng thể** trải nghiệm, không bắt theo từng từ.
2. **Mỉa mai/châm biếm** tính theo ý thật: "Ngon dữ luôn, ăn xong nằm viện" → `NEG`.
3. **Khen chê lẫn lộn**: nếu nghiêng hẳn một phía → theo phía đó; nếu cân bằng → `NEU`.
4. **Chỉ hỏi/thông tin** ("Quán mở tới mấy giờ?") → `NEU`.
5. **Emoji/teencode** vẫn tính: "vãi 😍" → `POS`, "vcl dở 🤮" → `NEG`.
6. Không suy diễn ngoài nội dung review.

## Ca biên tiếng Việt (tham khảo)
| Review | Nhãn | Vì sao |
|---|---|---|
| "Cũng được, ăn tạm." | `NEU` | Chấp nhận, không khen rõ. |
| "Đắt nhưng đáng tiền." | `POS` | Kết luận tích cực. |
| "Ngon mà phục vụ chậm kinh khủng." | `NEG` | Trải nghiệm tổng thể nghiêng tiêu cực (nhấn mạnh "kinh khủng"). |
| "Bình thường như bao quán khác." | `NEU` | Trung tính. |
| "Không gian ok, đồ ăn dở." | `NEU` | Khen chê cân bằng, không rõ thắng phía nào. |
| "Nhất định không bao giờ quay lại." | `NEG` | Ý định tiêu cực rõ. |

## Quy trình hai người (để tính Cohen's Kappa)
- `annotator1` và `annotator2` gán **độc lập**, không bàn trước.
- Cột `label` = nhãn chốt (đồng thuận; nếu lệch thì thống nhất lại hoặc người thứ 3 quyết).
- Khuyến nghị **300–500 dòng**, cân đối cả ba nhãn nếu có thể.
"""


def main():
    df = pd.DataFrame(EXAMPLES, columns=GOLD_COLS)
    csv = GOLD_DIR / "gold_template.csv"
    df.to_csv(csv, index=False, encoding="utf-8-sig")

    guide = _bootstrap.REPORTS / "labeling_guideline.md"
    guide.write_text(GUIDELINE, encoding="utf-8")

    print(f"✅ Template gold  -> {csv}")
    print(f"✅ Guideline      -> {guide}")
    print("\n👉 Việc của bạn:")
    print("   1. Mở gold_template.csv, XÓA 4 dòng ví dụ, điền dữ liệu thật (300–500 dòng).")
    print("   2. annotator1 & annotator2 gán độc lập; cột label = nhãn chốt.")
    print("   3. Lưu thành data/gold/gold.csv rồi chạy:")
    print("      python scripts/08_compute_kappa.py")
    print("      python scripts/09_eval_models.py")


if __name__ == "__main__":
    main()
