# WiseTravel — Demo kỹ thuật "bài toán dữ liệu"

Demo chứng minh nhóm giải quyết được **(1) pipeline dữ liệu địa điểm** và
**(2) pipeline + đánh giá dữ liệu cảm xúc**, kèm bằng chứng chất lượng định lượng.
Phạm vi: **12 quận nội thành Hà Nội**, ~500 địa điểm. Đây là **demo kỹ thuật**, không phải app hoàn chỉnh.

> Trạng thái: **Phase 1 (địa điểm) + Phase 2 (cảm xúc) đã xong**, có app Streamlit gói toàn bộ bằng chứng. Phase 3 (planner) tùy chọn.
>
> **Kết quả thật (chạy trên dữ liệu nhóm gán):** 500 POI · audit tọa độ **64%**, giờ mở cửa **48%** · Cohen's Kappa **0.611** (substantial) · ViSoBERT acc **86.4%** / macro-F1 **0.723** > PhoBERT acc 84.2% / F1 0.656.

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

# 2) Làm giàu từ Google Places (nếu có key): place_id + địa chỉ chuẩn + business_status + giờ
#    -> heuristic cho phần giờ còn thiếu. Tự phát hiện & loại quán đã đóng cửa.
$env:GOOGLE_PLACES_API_KEY = "AIza..."     # không có key -> tự bỏ qua Google, vẫn chạy heuristic
python scripts/02_enrich_hours.py
#   (tùy chọn) xóa hẳn quán đóng cửa vĩnh viễn khỏi DB:
#   python scripts/02_enrich_hours.py --drop-closed

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

### Google Places (tùy chọn nhưng khuyến nghị)
Bước 2 đọc key từ biến môi trường `GOOGLE_PLACES_API_KEY` (hoặc `GOOGLE_MAPS_API_KEY`).
Cần bật **Places API (New)** (`places.googleapis.com`) trong Google Cloud **và bật Billing**
(gắn thẻ, pay-as-you-go — bắt buộc kể cả khi dùng miễn phí). Code dùng endpoint mới
`v1/places:searchText` vì Google đã khóa Places API **legacy** với project tạo mới.
Mỗi POI chỉ tốn **1 request**; với hạn mức miễn phí hằng tháng theo SKU, 500 quán gần như
không tốn tiền. Khi có key, bước 2 sẽ:
- Lấy **địa chỉ chuẩn** (`address_google`) + **`place_id`** → link audit mở **đúng 100%** địa điểm.
- Lấy **`business_status`** → tự **loại quán đã đóng cửa** (`CLOSED_PERMANENTLY`) khỏi truy vấn & audit.
- Bổ sung **giờ mở cửa** cho POI mà OSM còn thiếu.
- Đánh dấu POI Google không tìm thấy (có thể OSM lỗi thời).

Không có key vẫn chạy được — chỉ thiếu các trường Google, phần giờ được điền bằng heuristic
(sửa bảng mặc định trong `config.HEURISTIC_OPENING_HOURS`).

> Lưu ý ToS: dùng **Places API chính thức**, KHÔNG cào (scrape) Google Maps. Theo điều khoản Google,
> chỉ `place_id` được lưu vô thời hạn; các trường khác nên coi là cache ngắn hạn (đủ cho demo học thuật).

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

## Chạy Phase 2 (pipeline + đánh giá cảm xúc)
Cần deps nặng (`torch`, `transformers`) — đã có trong `requirements.txt`. Lần đầu chạy
model sẽ tải vài trăm MB từ HuggingFace.

```powershell
# 7) Sinh template tập gold + guideline gán nhãn
python scripts/07_make_gold_template.py
#   -> data/gold/gold_template.csv   (XÓA 4 dòng ví dụ, điền 300–500 dòng thật)
#   -> reports/labeling_guideline.md  (định nghĩa nhãn + ca biên tiếng Việt)
#   Lưu file đã điền thành data/gold/gold.csv

# 7b) (tùy chọn) Kéo sẵn review từ HuggingFace / CSV Foody để khỏi copy tay
python scripts/07b_seed_reviews.py --csv foody.csv --text-col review --n 400
#   -> data/gold/gold_seed.csv  (cột text điền sẵn, nhãn để trống cho 2 người gán)
#   Khuyến nghị nguồn nhà hàng: Foody.vn reviews (Kaggle) -> dùng --csv.
#   Dataset HF dạng script (UIT-VSFC/ViSFD) KHÔNG load được với datasets>=3 -> tải CSV rồi --csv.

# 8) Cohen's Kappa giữa annotator1 & annotator2
python scripts/08_compute_kappa.py        # -> reports/kappa_result.md

# 9) Chạy & so sánh model trên tập gold
python scripts/09_eval_models.py
#   -> reports/model_comparison.md + reports/confusion_*.png

# 10) Demo gộp cảm xúc theo địa điểm (tỷ lệ pos/neg + biểu đồ)
python scripts/10_aggregate_reviews.py    # -> reports/place_sentiment_demo.png
```

> **Nhãn chốt (`label`) lấy theo `annotator2`.** Trong dự án này annotator1 là vòng rà soát nhanh,
> annotator2 là người gán chính → gold truth tham chiếu annotator2 (script tự dựng khi tạo `gold.csv`).

## Chạy app demo (Streamlit)
Gói toàn bộ bằng chứng thành 1 giao diện 3 tab — dùng để trình bày trước hội đồng.
```powershell
streamlit run app.py
```
- **Tab 1 — Dữ liệu địa điểm & Chất lượng:** tổng quan 500 POI, phân bố loại hình, giờ mở cửa theo
  nguồn, **accuracy audit** (tọa độ/giờ), bản đồ độ phủ, tra cứu địa điểm.
- **Tab 2 — Gán nhãn & So sánh model:** phân bố nhãn, **Cohen's Kappa**, bảng so sánh ViSoBERT vs
  PhoBERT + ma trận nhầm lẫn.
- **Tab 3 — Demo cảm xúc:** gõ nhiều review → model chấm nhãn từng câu + tỷ lệ pos/neg/neu.

> App đọc **trực tiếp** từ `data/wisetravel.db` + `data/audit_sample.csv` + `data/gold/gold.csv`
> và các file trong `reports/`. Chạy đủ scripts 01→10 trước để mọi tab có dữ liệu.

### 📋 Quy trình gán nhãn cho cả nhóm (bàn giao teammate)
Phần này dành cho **2 người gán nhãn** (annotator1 + annotator2) để tạo tập gold chất lượng.

**B1 — Lấy review thật vào file (chọn 1 trong 2):**
- **Cách A (khuyến nghị, đúng chủ đề ăn uống):** tải CSV review **Foody.vn** từ Kaggle
  (tìm "Foody Vietnamese reviews" / "Vietnamese restaurant reviews"), đặt vào thư mục dự án,
  rồi điền sẵn cột text:
  ```powershell
  python scripts/07b_seed_reviews.py --csv foody.csv --text-col review --n 400
  #   -> data/gold/gold_seed.csv  (cột text đã có, nhãn để TRỐNG)
  ```
  > Lưu ý: các bộ HF dạng "loading script" (UIT-VSFC, UIT-ViSFD, SEACrowd) **không** tải được
  > với `datasets>=3` ("Dataset scripts are no longer supported") → phải tải CSV rồi dùng `--csv`.
- **Cách B (tự thu thập):** chép tay 300–500 review thật từ Foody/Google Maps về các quán
  ở Hà Nội vào `data/gold/gold_template.csv` (cột `text`).

**B2 — Hai người gán nhãn ĐỘC LẬP** (đọc kỹ `reports/labeling_guideline.md`):
- `annotator1` và `annotator2` mỗi người điền cột của mình, **không bàn trước** (để Kappa khách quan).
- Nhãn: `POS` / `NEG` / `NEU` (hoặc tiếng Việt — script tự chuẩn hóa). Mỗi dòng một nhãn.
- Cột `label` = nhãn **chốt** (đồng thuận; lệch thì thống nhất hoặc nhờ người thứ 3).

**B3 — Lưu thành `data/gold/gold.csv`** rồi chạy `08` → `09` → `10` như trên.

**Model ứng viên** (khai báo trong `config.SENTIMENT_MODELS`):
- `5CD-AI/Vietnamese-Sentiment-visobert` — text mạng xã hội, **không cần tách từ**.
- `wonrax/phobert-base-vietnamese-sentiment` — **bắt buộc tách từ** (pyvi, vd `mô_hình`).

Cả hai dùng nhãn `{0:NEG, 1:POS, 2:NEU}`; code tự đọc `id2label` thật từ model và quy về
3 nhãn chuẩn NEG/POS/NEU. Tập gold dùng nhãn tiếng Việt hay POS/NEG/NEU đều được (tự chuẩn hóa).

---

## KỊCH BẢN TRÌNH BÀY 5 PHÚT CHO GIẢNG VIÊN

Mở sẵn app: `streamlit run app.py`. Cả buổi bám theo 3 tab.

1. **Đặt vấn đề** (30s) — "Đồ án giải một *bài toán dữ liệu*: thu thập địa điểm + đánh giá cảm xúc,
   và **tự đo được chất lượng** dữ liệu chứ không tin suông."
2. **Tab 1 — Dữ liệu thật** (60s) — "500 POI thật lấy từ OpenStreetMap qua Overpass (miễn phí),
   chuẩn hóa về 4 loại hình, lưu SQLite. Bản đồ cho thấy phủ khắp nội đô. Giờ mở cửa **minh bạch theo
   nguồn**: 17% từ OSM thật, còn lại heuristic — nhóm không tô hồng."
3. **Tab 1 — Accuracy audit** (60s) — "Nhóm tự kiểm tay **50 điểm ngẫu nhiên** đối chiếu Google Maps:
   tọa độ đúng **64%**, giờ mở cửa **48%**. Đây là bằng chứng định lượng — và cũng là *phát hiện* về
   giới hạn của dữ liệu mở."
4. **Tab 2 — Chất lượng nhãn** (45s) — "2 người gán nhãn 493 review; **Cohen's Kappa = 0.611**
   (substantial) → tập gold đáng tin."
5. **Tab 2 — Chọn model** (45s) — "So sánh **ViSoBERT vs PhoBERT** trên tập gold: ViSoBERT thắng
   (acc **86.4%**, macro-F1 **0.723**). Ma trận nhầm lẫn cho thấy cả hai đều yếu ở **NEU** — vì NEU chỉ
   40/493 mẫu, dữ liệu lệch. Đây là hạn chế nhóm hiểu rõ, không giấu."
6. **Tab 3 — Demo trực tiếp** (60s) — gõ vài review Hà Nội thật → model trả nhãn từng câu + tỷ lệ
   pos/neg/neu cho địa điểm. "Đây là cách kết quả được dùng trong app du lịch thật."
