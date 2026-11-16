# Số hóa mặt bằng tầng

## Chuẩn bị
```bash
python3 scripts/saban.py floor WD --tower l1 --id dh --name "Tầng điển hình" --floors "12-22,24-33" --img <ảnh hoặc PDF>
```
- Mỗi "loại tầng" là một mặt bằng áp cho một khoảng tầng. Tầng có bố trí khác (tầng đế, penthouse) là loại tầng riêng.
- Lệnh in mã căn của tầng đầu tiên trong khoảng, theo bảng hàng, kèm loại và diện tích. Danh sách này là đáp án: mỗi mã phải có đúng một đa giác.
- Ảnh lưới `WD/work/grid_<tòa>_<loại tầng>.png`: vạch đậm mỗi 100, vạch mảnh mỗi 50, toạ độ 0–1000 theo chiều rộng và chiều cao ảnh (x sang phải, y xuống dưới).

## Vẽ ranh căn
Mở ảnh lưới bằng Read. Nếu ảnh nhiều chi tiết, cắt phóng to từng vùng bằng Pillow (giữ quy đổi về 0–1000) thay vì đoán.

Viết `WD/work/ranh_<tòa>_<loại tầng>.json`:
```json
{"units":[{"code":"CH-01","poly":[[x,y],[x,y],...]}],"notes":"điểm chưa chắc"}
```
Quy tắc:
- Đa giác đi theo mép ngoài tường bao của căn, kể cả lô gia/ban công thuộc căn; bỏ hành lang, lõi thang, hộp kỹ thuật.
- 4–12 đỉnh, theo chiều kim đồng hồ; căn bo cong thì dùng 8–12 đỉnh dọc đường cong.
- Hai căn kề nhau dùng chung cạnh (cùng toạ độ), không chồng, không hở.
- Đọc mã căn in trên ảnh (bảng chú thích, nhãn trong căn) để gán mã; nhãn chú thích có đường dẫn thì theo đường dẫn tới căn.
- Mã nào không xác định được vị trí: bỏ ra và ghi vào `notes`, không đoán bừa.

## Kiểm tra
```bash
python3 scripts/saban.py polys WD --tower l1 --ft dh --json WD/work/ranh_l1_dh.json
```
Kết quả:
- Tỷ lệ m/px suy từ tổng diện tích tim tường trong bảng hàng chia tổng diện tích đa giác. Kiểm tra lại cảm quan: tòa chung cư thường rộng 20–90 m.
- `Thiếu`/`Thừa`: mã căn lệch so với bảng hàng.
- `Lệch diện tích >15%`: đa giác quá to/nhỏ so với diện tích tim tường; thường do lấn sang căn bên, tính cả hành lang, hoặc gán nhầm mã giữa hai căn cạnh nhau.
- `Chồng nhau`: hai căn chồng lên nhau quá 3%.
- Ảnh `WD/work/overlay_*.png`: mở để xem, căn lỗi tô đỏ.

Sửa và chạy lại, tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng, gửi ảnh đối chiếu cho người dùng và nêu từng căn còn lỗi.

## Duyệt
- `review`: gửi ảnh đối chiếu (SendUserFile) và hỏi người dùng duyệt; duyệt xong chạy lại `polys ... --approve`.
- `auto`: `polys` tự duyệt khi không có lỗi nào.

## Ghi nhật ký
Sau khi xong một loại tầng: `log WD --step digitize --item "<tòa> / <loại tầng>" --images <ảnh lưới, ảnh cắt, ảnh đối chiếu đã mở> --out-chars <độ dài file JSON>`.
