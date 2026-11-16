---
name: dung-sa-ban
description: Dựng sa bàn 3D bán hàng cho dự án chung cư từ bảng hàng, tổng mặt bằng, mặt bằng tầng, layout căn và ảnh phối cảnh; xoay được, lọc căn theo trạng thái/giá/hướng, xem căn hộ 3D. Dùng khi người dùng nói "dựng sa bàn", "tạo sa bàn 3D", "làm sa bàn cho dự án", "số hóa mặt bằng tầng", "cập nhật bảng hàng sa bàn", "xuất sa bàn lên Netlify".
---

# Dựng sa bàn 3D bất động sản

Claude tự đọc ảnh trong cuộc trò chuyện (không gọi API ngoài); `scripts/saban.py` lo tính toán, kiểm tra, ghép và xuất trình xem. Mọi lệnh chạy từ thư mục skill này: `python3 scripts/saban.py <lệnh> <WD> ...`, với `WD` là thư mục làm việc của dự án (ví dụ `./du-an/<slug>`). Chạy `python3 scripts/saban.py -h` để xem đủ tham số.

Cài thư viện nếu thiếu: `pip install -r requirements.txt` (thêm `--break-system-packages` nếu pip yêu cầu).

## 0. Nhận tài liệu
Đối chiếu tài liệu người dùng gửi với `references/tai-lieu.md`. Bắt buộc: bảng hàng, tổng mặt bằng (đã đánh dấu vị trí tòa), mặt bằng tầng. Thiếu thì hỏi một lần, gom mọi thứ còn thiếu vào cùng câu hỏi. Hỏi luôn chế độ nếu người dùng chưa nói: `review` (duyệt từng bước, mặc định) hay `auto` (tự duyệt khi kiểm tra không lỗi).

Lập danh sách việc (TaskCreate nếu có) theo các bước dưới đây.

## 1. Khởi tạo và bảng hàng
```bash
python3 scripts/saban.py init WD --name "<Tên dự án>" --mode review --floor-height 3.3 --note "<ghi chú dữ liệu>"
python3 scripts/saban.py units WD <bang_hang.xlsx|csv>
```
Nếu bảng hàng là dữ liệu mẫu/giả, đặt `--note "Trạng thái và giá căn là dữ liệu giả để thử nghiệm"`; ghi chú này hiện cố định trên sa bàn. Báo người dùng các cột không nhận ra và các dòng bị bỏ qua.

## 2. Tổng mặt bằng và vị trí tòa
```bash
python3 scripts/saban.py masterplan WD <tong_mat_bang> --mpp <m/px>
```
Mở `WD/work/grid_tong_mat_bang.png` (nhãn lưới là pixel ảnh gốc), đọc tâm từng tòa và góc xoay so với trục ngang, rồi:
```bash
python3 scripts/saban.py tower WD --id l1 --name L1 --x <px> --y <px> --rot <độ> --total <số tầng>
```
`--mpp`: nếu không có thước tỷ lệ, ước từ một kích thước đã biết (chiều dài tòa, làn đường 3,5 m) và nói rõ là ước lượng.

## 3. Số hóa mặt bằng tầng (Claude đọc ảnh)
Làm theo `references/so-hoa.md`. Tóm tắt: `floor` tạo ảnh lưới và in danh sách mã căn → Claude vẽ ranh căn ra file JSON toạ độ 0–1000 → `polys` kiểm tra (thiếu/thừa mã, lệch diện tích >15%, chồng nhau) và vẽ ảnh đối chiếu → sửa tối đa 2 vòng. Ở chế độ `review`, gửi ảnh đối chiếu cho người dùng duyệt rồi chạy lại `polys ... --approve`.

## 4. Layout căn hộ 3D (tùy chọn)
Với mỗi loại layout có bản vẽ, dùng skill `layout-can-ho` để ra `spec.json`, rồi:
```bash
python3 scripts/saban.py unittype WD --name 2BR --spec <spec.json> --layout <ảnh layout> --photo <ảnh phối cảnh ...>
```
Loại chưa có layout vẫn hiện trên sa bàn, chỉ không mở được mô hình căn.

## 5. Ghi nhật ký mức dùng
Sau mỗi lượt Claude đọc ảnh hoặc viết dữ liệu (bước 2, 3, 4), ghi một dòng:
```bash
python3 scripts/saban.py log WD --step digitize --item "L1 / Tầng điển hình" --images <các ảnh đã xem> --out-chars <số ký tự JSON đã viết>
```
Đây là ước lượng token để theo dõi hạn mức gói, không phải hóa đơn; ảnh tính theo công thức kích thước ảnh. `report WD [--csv WD/log.csv]` in bảng tổng hợp theo bước.

## 6. Xuất sa bàn
```bash
python3 scripts/saban.py status WD
python3 scripts/saban.py build WD --out WD/dist-single --single   # một file HTML, ảnh nhúng sẵn
python3 scripts/saban.py build WD --out WD/dist                   # thư mục cho Netlify / máy chủ
```
Chọn cách giao theo `references/xuat-ban.md`. Trước khi giao, mở thử trình xem (ảnh chụp bằng trình duyệt không giao diện nếu có Chrome) và xem cảnh báo của `build`.

## Nguyên tắc
- Không bịa số liệu: chiều cao tầng, số tầng, tỷ lệ chưa có nguồn thì ghi là ước lượng trong báo cáo cuối.
- Ảnh và bảng hàng thuộc chủ đầu tư; không đưa lên đâu ngoài nơi người dùng chọn.
- Khi người dùng gửi bảng hàng mới cho dự án đã dựng: chỉ chạy lại `units` rồi `build`.
- Kết thúc bằng: sa bàn đã giao, các mục còn chờ duyệt hoặc ước lượng, và bảng `report`.
