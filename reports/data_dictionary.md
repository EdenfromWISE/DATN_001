# Data Dictionary — Bảng `pois` (WiseTravel)

Mô tả từng trường trong bảng địa điểm (SQLite `data/wisetravel.db`).

| Trường | Kiểu | Bắt buộc | Mô tả | Nguồn / cách sinh |
|---|---|:---:|---|---|
| `id` | TEXT (PK) | ✔ | Định danh duy nhất, dạng `node/123`, `way/456`, `relation/789`. | Ghép `type/id` của element OSM. |
| `name` | TEXT | ✔ | Tên địa điểm. | Tag `name` của OSM. Bản ghi không có tên bị loại. |
| `lat` | REAL | ✔ | Vĩ độ (WGS84). | Node: tọa độ node. Way/Relation: tâm hình học (`out center`). |
| `lng` | REAL | ✔ | Kinh độ (WGS84). | Như trên. |
| `category` | TEXT | ✔ | Loại hình WiseTravel: `food`, `cafe`, `lodging`, `attraction`. | Suy từ tag OSM theo bảng ánh xạ trong `config.CATEGORY_TAGS`. |
| `subtype` | TEXT |  | Tag OSM gốc, vd `amenity=restaurant`, `tourism=hotel`. | Lưu lại để truy vết. |
| `district` | TEXT |  | Quận/phường nếu OSM có tag địa chỉ. | `addr:district` / `addr:suburb` / `addr:quarter`. Thường thưa trong OSM. |
| `address` | TEXT |  | Địa chỉ ghép từ OSM (số nhà + đường, phường). | Các tag `addr:*` của OSM (nếu có). |
| `address_google` | TEXT |  | Địa chỉ chuẩn của Google (`formatted_address`). | Lấy khi làm giàu Google Places. Ưu tiên dùng cho link audit. |
| `place_id` | TEXT |  | Google Place ID — dựng link kiểm chứng mở đúng 100% địa điểm. | Lấy khi làm giàu Google Places. NULL nếu chưa làm giàu. |
| `business_status` | TEXT |  | Trạng thái hoạt động: `OPERATIONAL` / `CLOSED_TEMPORARILY` / `CLOSED_PERMANENTLY`. | Google Places. Quán `CLOSED_PERMANENTLY` bị loại khỏi truy vấn & audit. |
| `opening_hours` | TEXT |  | Chuỗi giờ mở cửa theo chuẩn OSM, vd `Mo-Su 08:00-22:00`. | Tag `opening_hours`; hoặc làm giàu từ Google; hoặc heuristic. |
| `hours_source` | TEXT |  | Nguồn của `opening_hours`: `osm`, `google`, `heuristic`, `manual`. | OSM gốc → `osm`; làm giàu Google → `google`; điền mặc định theo loại hình → `heuristic`; sửa tay → `manual`. |
| `price_level` | INTEGER |  | Mức giá 1 (rẻ) – 3 (cao). **Luôn có giá trị.** | Suy từ số sao khách sạn nếu có; còn lại = mặc định theo loại hình. |
| `price_level_estimated` | INTEGER | ✔ | Cờ minh bạch: `1` = mức giá là **ước lượng heuristic**; `0` = suy từ dữ liệu thật (vd số sao). | `normalize.estimate_price`. |
| `est_duration_min` | INTEGER |  | Thời lượng tham quan ước lượng (phút). `lodging`=0 (điểm qua đêm). | Bảng heuristic `config.EST_DURATION_MIN`. |
| `source` | TEXT | ✔ | Nguồn dữ liệu, vd `OpenStreetMap (Overpass)`. | Cố định theo pipeline. |
| `last_updated` | TEXT | ✔ | Ngày cập nhật bản ghi (ISO `YYYY-MM-DD`). | Ngày chạy pipeline. |

## Ghi chú về tính minh bạch dữ liệu
- **`price_level` và `est_duration_min` là ước lượng**, không phải dữ liệu đo thật. Cờ `price_level_estimated` cho biết bản ghi nào được suy từ dữ liệu thật.
- **`opening_hours`** được làm giàu theo thứ tự ưu tiên OSM → Google → heuristic; cờ `hours_source` cho biết nguồn. Accuracy audit **chỉ đo trên** `osm`/`google`/`manual` (loại `heuristic`). Độ phủ và độ chính xác được định lượng trong *Báo cáo chất lượng* và *Accuracy Audit*.
- **File audit** (`data/audit/audit_sample.csv`) có 3 link đối chiếu: `link_by_coord` (căn cứ chính — ghim tọa độ), `link_by_name` (ghim tên + địa chỉ; chính xác khi `has_address=Y`), `osm_link` (đối tượng OSM gốc). Quy tắc chấm `coord_dung` xem README.
- Khử trùng lặp: gộp bản ghi cùng tên (chuẩn hóa) trong ô lưới ~100 m, giữ bản đầy đủ hơn.
