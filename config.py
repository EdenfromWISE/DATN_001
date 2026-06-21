"""Cấu hình tập trung cho pipeline WiseTravel (Phase 1)."""

# --- Overpass ---
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Endpoint dự phòng nếu cái chính quá tải:
OVERPASS_FALLBACKS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

# Bounding box lõi nội đô Hà Nội (12 quận nội thành): (south, west, north, east)
# Bao phủ Hoàn Kiếm, Ba Đình, Đống Đa, Hai Bà Trưng, Tây Hồ, Cầu Giấy,
# Thanh Xuân, Hoàng Mai, Long Biên, Hà Đông, Bắc/Nam Từ Liêm.
HANOI_BBOX = (20.950, 105.760, 21.110, 105.900)

# --- Taxonomy: gom tag OSM về 4 nhóm loại hình của WiseTravel ---
# Thứ tự khai báo = thứ tự ưu tiên khi 1 địa điểm khớp nhiều tag.
CATEGORY_TAGS = {
    "food":       {"amenity": ["restaurant", "fast_food", "food_court"]},
    "cafe":       {"amenity": ["cafe"]},
    "lodging":    {"tourism": ["hotel", "hostel", "guest_house", "motel"]},
    "attraction": {
        "tourism": ["attraction", "museum", "artwork", "viewpoint", "gallery"],
        "historic": ["*"],  # mọi giá trị historic=*
    },
}

CATEGORY_LABELS_VI = {
    "food": "Ăn uống",
    "cafe": "Cà phê",
    "lodging": "Lưu trú",
    "attraction": "Tham quan",
}

# --- Số lượng mục tiêu lưu vào DB (sample cân bằng nếu fetch ra nhiều hơn) ---
TARGET_POI_COUNT = 500
SAMPLE_SEED = 42

# --- Heuristic thời lượng tham quan (phút) theo loại hình ---
# lodging = 0: là điểm lưu trú/qua đêm, không tính như 1 điểm dừng tham quan.
EST_DURATION_MIN = {"food": 75, "cafe": 45, "lodging": 0, "attraction": 90}

# --- Heuristic mức giá mặc định (1=rẻ, 2=trung bình, 3=cao) khi thiếu dữ liệu ---
DEFAULT_PRICE_LEVEL = {"food": 2, "cafe": 1, "lodging": 2, "attraction": 1}

# --- Heuristic giờ mở cửa mặc định theo loại hình ---
# Dùng cho POI vẫn thiếu opening_hours sau khi đã thử OSM + Google.
# Bản ghi điền theo bảng này sẽ mang hours_source='heuristic' và bị LOẠI khỏi accuracy audit.
# Định dạng: chuỗi opening_hours kiểu OSM. CHỈNH TỰ DO ở đây.
HEURISTIC_OPENING_HOURS = {
    "food": "Mo-Su 10:00-22:00",
    "cafe": "Mo-Su 07:00-22:00",
    "lodging": "24/7",
    "attraction": "Mo-Su 08:00-17:00",
}
