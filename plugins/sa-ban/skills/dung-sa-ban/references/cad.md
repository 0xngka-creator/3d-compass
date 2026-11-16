# Đường CAD: mặt bằng tầng là PDF vector xuất từ AutoCAD

Dùng đường này khi PDF còn lớp (layer). Kiểm tra bằng `info`: có danh sách lớp và mỗi trang có hàng nghìn nét. PDF scan hoặc ảnh thì quay về `so-hoa.md`.

## 1. Xem file
```bash
python3 scripts/cad.py info <file.pdf> --json WD/work/cad_info.json
```
In ra: các trang mặt bằng (tên bản vẽ, khoảng tầng tự suy từ tên, ví dụ "5-12A" → 5-13 vì 12A là tầng 13; diện tích sàn) và danh sách lớp kèm vai trò đoán theo tên.

## 2. Xác định vai trò lớp (Claude, một lần mỗi dự án)
```bash
python3 scripts/cad.py layers <file.pdf> --page <trang mặt bằng điển hình> --out WD/work/lop.png
```
Mở `lop.png` (mỗi lớp một ô). Viết `WD/work/lop.json`:
```json
{"wall": [...], "partition": [...], "door": [...], "window": [...], "glass": [...], "railing": [...],
 "furniture": [...], "furniture_tall": [...], "outline": [...], "hide": [...]}
```
- `wall`: tường chính, cột, vách bê tông (nét kép hoặc tô đặc). `partition`: vách ngăn nhẹ giữa các phòng (thường màu đỏ, tên lớp kiểu TEMP/VACH). Đây là cách tách căn: vùng bao bởi `wall` là căn, vùng bao bởi cả `partition` là phòng.
- `door`: ký hiệu cửa đi (cánh + cung mở). `window`: cửa sổ trên mặt ngoài. `glass`: vách kính, cửa kính ra lô gia. `railing`: lan can, mép sàn ban công.
- `furniture`: nội thất thấp; `furniture_tall`: tủ bếp, thiết bị vệ sinh, tủ cao.
- `outline`: ranh khối nhà nếu có. `hide`: các lớp không vẽ lên ảnh mặt bằng (khung tên, kích thước, trục, ghi chú, PCCC).
- Lớp không chắc: để ngoài mọi nhóm; vẫn hiện trên ảnh mặt bằng nhưng không dùng để tính.

Tỷ lệ: mặc định 1:100. Kiểm tra bằng kích thước tổng trên mặt đứng/mặt cắt (cùng file) so với bề rộng khối nhà `extract` báo ra; lệch thì đặt `--scale`.

## 3. Tách từng trang mặt bằng
```bash
python3 scripts/cad.py extract <file.pdf> --map WD/work/lop.json --page <N> --out WD/work/cad_p<N>
```
Ra `floor.json` (căn, phòng, tường, cửa, nội thất theo mét), `plan.webp` (ảnh mặt bằng vẽ từ chính các lớp, nền trong suốt) và `preview.png` (căn tô màu, mã căn, số phòng màu đỏ).

Mở `preview.png` và kiểm tra:
- Mỗi căn một màu, không có hai căn chung màu (thường do cửa thông căn hoặc vách ngăn căn nằm ở lớp `partition`), không có căn nào lẫn sảnh/lõi.
- Danh sách "Phòng chưa thuộc căn nào" chỉ nên là hộp kỹ thuật, thang, khe nhỏ.

Sai thì viết `WD/work/nhom_p<N>.json` = danh sách căn, mỗi căn là danh sách số phòng (đọc trên preview), rồi chạy lại với `--groups`. Trang có cùng bản vẽ (cùng số phòng, ví dụ tầng 4 và tầng 5-12A) dùng lại được file nhóm.

Mã căn: bản vẽ kiến trúc thường không ghi mã. `extract` đánh số tạm 01, 02... từ góc trên trái theo chiều kim đồng hồ. Khi có mặt bằng bán hàng ghi mã hoặc quy ước đánh số, viết `ma.json` dạng `{"01": "A-05", ...}` và chạy lại với `--codes`. Chưa có thì ghi rõ trong ghi chú sa bàn là mã tạm.

Tầng giật cấp (diện tích sàn ghi trên bản vẽ nhỏ hơn hẳn ranh khối nhà): script tự thu ranh khối theo phần có căn và lõi.

## 4. Nạp vào sa bàn
```bash
python3 scripts/saban.py cadfloor WD --tower k12 --id t5 --name "Tầng 5-12A" --floors 5-13 --dir WD/work/cad_p12
```
Trang không có căn (tầng thương mại, tầng kỹ thuật) vẫn nạp để dựng đúng hình khối. Mô hình 3D căn hộ dựng thẳng từ tường, cửa, kính, nội thất của bản vẽ; không cần skill `layout-can-ho` cho các căn này.

## 5. Ghi nhật ký
`log WD --step cad --item "<tòa> lớp + N trang" --images <lop.png và các preview đã mở>`.
