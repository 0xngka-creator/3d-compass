# Diện mạo tòa nhà từ ảnh phối cảnh

Làm tự động, không hỏi trước. Người dùng sẽ yêu cầu chỉnh qua chat sau.

## Đọc ảnh
Mở ảnh phối cảnh tổng thể (ban ngày, rõ mặt đứng nhất). Nhiều ảnh thì chọn 1–2 ảnh nhìn gần tòa cần dựng; không mở thêm. Nếu cần lấy màu chính xác, cắt vùng mặt đứng bằng Pillow và lấy màu trung vị của vùng kính, khung, dải sàn thay vì đoán bằng mắt (ảnh render thường bị ám màu trời, nên chọn vùng kính không phản chiếu trời trực tiếp).

Xác định:
- Kiểu mặt đứng: **mặt kính** (vách kính liền, dải sàn mảnh) hay **tường + cửa sổ** (tường sơn/ốp, ô kính tách rời).
- Màu kính (phần tối của ô kính) và màu phản chiếu (phần sáng phía trên ô kính).
- Màu khung đứng/đố, màu dải sàn hoặc lan can, màu tường (nếu có), màu mái/tum.
- Module ô kính theo chiều ngang (m): đếm số ô trên một đoạn tòa có chiều dài suy ra được, hoặc ước 1,2–1,8 m cho vách kính, 3–4 m cho cửa sổ căn hộ.
- Khối đế: số tầng, vật liệu (đá/ốp sáng, kính cửa hàng), màu.

## Ghi file `WD/work/dien_mao.json`
```json
{
  "glass": "#1f2b31",        "glassReflect": "#6f8794",
  "mullion": "#d8dad6",      "slab": "#e9e7e1",
  "wall": null,              "roof": "#5d6366",
  "spandrel": 0.12,          "glassRatio": 0.94,
  "panes": 4,                "bay": 1.6,
  "podium": {"floors": 3, "wall": "#cbbfa8", "glass": "#24343b", "spandrel": 0.25, "glassRatio": 0.8, "panes": 2, "bay": 4},
  "notes": "Mặt kính xanh xám, dải sàn trắng; khối đế 3 tầng ốp đá be. Màu lấy từ ảnh phối cảnh 1."
}
```
- Màu dạng `#rrggbb`. `wall: null` nghĩa là mặt kính.
- `spandrel`: tỷ lệ chiều cao dải sàn/tường đặc trên một tầng (0,05–0,45). Mặt kính 0,08–0,15; tường + cửa sổ 0,3–0,45.
- `glassRatio`: tỷ lệ bề ngang phần kính trong mỗi ô (0,2–0,98).
- `panes`: số ô trong một mẫu lặp (1–8); `bay`: bề rộng một ô (m).
- `podium.floors: 0` nếu không có khối đế.

```bash
python3 scripts/saban.py look WD --json WD/work/dien_mao.json --img <ảnh phối cảnh đã dùng>
python3 scripts/saban.py log WD --step look --item "diện mạo" --images <ảnh đã mở> --out-chars <độ dài json>
```

## Chỉnh theo yêu cầu
Người dùng nói "kính tối hơn", "khối đế 4 tầng", "dải sàn màu ghi"...: sửa đúng trường liên quan trong `dien_mao.json`, chạy lại `look` rồi `build`. Không đọc lại ảnh phối cảnh trừ khi người dùng bảo xem lại.
