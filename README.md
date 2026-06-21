# WiseTravel — Demo kỹ thuật "bài toán dữ liệu"

Demo chứng minh nhóm giải quyết được **(1) pipeline dữ liệu địa điểm** và
**(2) pipeline + đánh giá dữ liệu cảm xúc**, kèm bằng chứng chất lượng định lượng.
Phạm vi: **12 quận nội thành Hà Nội**, ~500 địa điểm. Đây là **demo kỹ thuật**, không phải app hoàn chỉnh.

> Trạng thái: **Phase 1 (pipeline địa điểm) đã xong.** Phase 2 (cảm xúc) & Phase 3 (planner) bổ sung sau.

## Yêu cầu
- Python 3.10+ (đã test 3.12), có Internet để gọi Overpass (miễn phí, không cần API key).

## Cài đặt
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r requirements.txt
```

## Chạy Phase 1 (theo thứ tự)
```powershell
# 1) Fetch POI từ OpenStreetMap -> chuẩn hóa -> dedup -> sample ~500 -> SQLite
python scripts/01_fetch_pois.py

# 2) Làm giàu giờ mở cửa: Google Places (nếu có key) -> heuristic cho phần còn thiếu
#    (tùy chọn) khai báo key trước khi chạy:
$env:GOOGLE_PLACES_API_KEY = "AIza..."     # không có key -> tự bỏ qua Google, vẫn chạy heuristic
python scripts/02_enrich_hours.py

# 3) Sinh báo cáo chất lượng + bản đồ độ phủ (folium HTML)
python scripts/03_build_reports.py
#   -> reports/quality_report.md   (có bảng phân bố giờ theo hours_source)
#   -> reports/coverage_map.html   (mở bằng trình duyệt)

# 4) Xuất 50 địa điểm để kiểm tay (chỉ lấy bản ghi giờ nguồn thật)
python scripts/04_make_audit_sample.py
#   -> data/audit/audit_sample.csv
#   Mở bằng Excel, điền cột coord_dung (Y/N) — xem "Quy tắc chấm audit" bên dưới

# 5) Tính % chính xác (tự loại bản ghi heuristic khỏi phép đo giờ)
python scripts/05_score_audit.py
#   -> reports/audit_result.md

# 6) Demo hàm truy vấn ứng viên (category + mở cửa lúc T + mức giá)
python scripts/06_query_demo.py
```

### Quy tắc chấm accuracy audit (cột `coord_dung`)
Mỗi dòng có ba link để đối chiếu:
- **`link_by_coord`** — ghim theo `lat,lng` lưu trong DB. **Đây là căn cứ chính.**
- **`link_by_name`** — nếu có địa chỉ: ghim theo `địa chỉ + quận + "Hà Nội"` (bỏ tên cho dễ tìm);
  nếu không: theo `tên + quận`. Kèm `query_place_id` nếu có. Chính xác khi `has_address=Y`;
  với địa điểm tên chung chung & không có địa chỉ, Google có thể trả nhiều kết quả → **đừng dựa
  vào link này để kết luận**.
- **`osm_link`** — trang đối tượng OSM gốc, xem đúng vật thể nguồn và vị trí của nó.

**Cách chấm (ưu tiên `link_by_coord`, không phụ thuộc tên trùng):**
1. Mở `link_by_coord`, **zoom to** đến khi thấy Google gắn nhãn cửa hàng tại đúng điểm ghim.
2. So nhãn đó với cột `name`:
   - `coord_dung = Y` nếu **đúng địa điểm đó** (hoặc rõ ràng cùng một nơi) nằm tại ghim.
   - `coord_dung = N` nếu ghim rơi vào **nơi khác hẳn** (sai đường/sai tòa nhà) hoặc chỗ trống.
3. Dùng `link_by_name` + `osm_link` để xác nhận thêm khi phân vân.
- `hours_dung` *(tùy chọn)* = `Y/N` nếu muốn kiểm cả giờ mở cửa; để trống nếu bỏ qua.

> Vì sao đổi cách: kiểm "ghim-theo-tên vs ghim-theo-tọa-độ có trùng không" chỉ chuẩn khi tên đủ
> đặc thù. Nhiều quán ở OSM tên chung chung và thiếu địa chỉ, tìm theo tên ra cả loạt kết quả.
> Lấy **vị trí tọa độ làm gốc** rồi xem Google gắn gì tại đó cho kết quả tin cậy hơn nhiều.

Script `05_score_audit.py` chấp nhận `Y/N` (và `1/0` cho file cũ), tự **loại bản ghi `heuristic`**
khỏi phép đo giờ mở cửa, rồi xuất `reports/audit_result.md`.

### Google Places (tùy chọn)
Bước 2 đọc key từ biến môi trường `GOOGLE_PLACES_API_KEY` (hoặc `GOOGLE_MAPS_API_KEY`).
Cần bật **Places API** trong Google Cloud. Không có key vẫn chạy được — chỉ thiếu nguồn `google`,
phần còn lại được điền bằng heuristic (sửa bảng mặc định trong `config.HEURISTIC_OPENING_HOURS`).

## Cấu trúc thư mục
```
DATN/
├── config.py                 # bbox HN, ánh xạ loại hình, hằng số heuristic
├── requirements.txt
├── data/
│   ├── wisetravel.db         # SQLite (sinh ra khi chạy)
│   └── audit/audit_sample.csv
├── reports/
│   ├── data_dictionary.md    # mô tả từng trường dữ liệu
│   ├── quality_report.md     # thống kê độ phủ/đầy đủ (sinh tự động)
│   ├── coverage_map.html     # bản đồ độ phủ
│   └── audit_result.md       # kết quả accuracy audit
├── src/wisetravel/           # logic pipeline (đóng gói tái dùng)
│   ├── overpass.py  normalize.py  oh.py  db.py  google_places.py
│   ├── quality.py   audit.py      coverage_map.py  query.py
└── scripts/                  # các bước chạy theo thứ tự 01..06
```

## Mô hình dữ liệu
Xem [`reports/data_dictionary.md`](reports/data_dictionary.md). Lưu ý minh bạch:
`price_level` và `est_duration_min` là **ước lượng heuristic**; cờ `price_level_estimated`
đánh dấu bản ghi nào suy từ dữ liệu thật.

---

## KỊCH BẢN TRÌNH BÀY 5 PHÚT CHO GIẢNG VIÊN
*(phần Phase 2/3 sẽ bổ sung vào kịch bản khi hoàn thành)*

1. **Pipeline** (45s) — chạy `01_fetch_pois.py`: "Lấy POI thật từ OpenStreetMap qua Overpass,
   chuẩn hóa về 4 loại hình, khử trùng lặp, lưu SQLite. Đây là dữ liệu thật, không bịa."
2. **Thống kê độ phủ** (45s) — mở `reports/quality_report.md` + `coverage_map.html`:
   "Bao nhiêu địa điểm mỗi loại, % trường nào đầy đủ. Bản đồ cho thấy phủ khắp nội đô."
3. **Accuracy audit** (60s) — mở `audit_sample.csv` đã điền + `audit_result.md`:
   "Nhóm tự kiểm tay 50 điểm ngẫu nhiên so với Google Maps → độ chính xác tọa độ X%, giờ mở cửa Y%.
   Đây là bằng chứng định lượng, không nói suông."
4. *(Phase 2)* **Cohen's Kappa** — độ đồng thuận gán nhãn cảm xúc giữa 2 người.
5. *(Phase 2)* **Bảng so sánh model** — accuracy / macro-F1 / ma trận nhầm lẫn của 2–3 model.
6. **Demo trực tiếp** (90s) — `06_query_demo.py`: "Tìm quán cà phê mở cửa 20h, giá vừa phải."
   *(Phase 2)* gõ một review tiếng Việt → model trả nhãn cảm xúc.
