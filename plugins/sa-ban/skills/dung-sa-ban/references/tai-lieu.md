# Tài liệu đầu vào

| Mục | Bắt buộc | Định dạng | Ghi chú |
|---|---|---|---|
| Bảng hàng | Có | .xlsx / .csv | Cột nhận tự động (không phân biệt dấu, hoa thường): Tòa, Tầng, Mã căn, Loại, DT tim, DT TT, Hướng, Giá, Trạng thái, Layout, Vị trí. Cột **Vị trí** là số căn trên mặt bằng tầng (01, 02...) khi mã căn bán hàng khác số trên bản vẽ (ví dụ mã K5-1508 nằm ở vị trí 08). Bắt buộc có Mã căn và Tầng; cần DT tim để suy tỷ lệ mặt bằng. Giá ghi tỷ hoặc đồng đều được. Trạng thái: còn trống / giữ chỗ (đặt cọc, booking) / đã bán. |
| Tổng mặt bằng | Có | ảnh / PDF | Người dùng đánh dấu vị trí từng tòa (khoanh hoặc ghi tên). Có thước tỷ lệ hoặc một kích thước đã biết càng tốt. |
| Mặt bằng tầng | Có | **PDF xuất thẳng từ AutoCAD (giữ lớp) là tốt nhất**; hoặc ảnh độ phân giải cao | Một ảnh cho mỗi loại tầng, kèm khoảng tầng áp dụng (ví dụ 12-22, 24-33). Mã căn phải đọc được trên ảnh. |
| Số tầng, cao tầng | Nên có | số | Không có thì dùng 3,3 m và ghi là ước lượng. |
| Layout căn | Nên có | PDF vector từ CAD (tốt nhất) / ảnh có kích thước | Mỗi loại layout một bản. Ảnh không ghi kích thước thì cần biết tổng chiều rộng (mm). |
| Ảnh phối cảnh căn mẫu | Tùy chọn | ảnh | Hiện trong popup căn hộ. |
| Ảnh phối cảnh tổng thể | Nên có | ảnh ban ngày, rõ mặt đứng | Claude tự lấy màu kính, khung, tường, mái, khối đế. |
| Hướng bắc | Tùy chọn | hoa gió trên ảnh | Dùng cho mặt trời và hướng ban công. |

Mẹo giảm lượt đọc ảnh (tiết kiệm hạn mức):
- Ảnh mặt bằng tầng cắt sát khối nhà, bỏ bảng chú thích không liên quan, cạnh dài khoảng 1500–2500 px là đủ.
- Gộp các tầng giống nhau thành một loại tầng.
- Layout căn dạng PDF vector đi đường script `cadvec.py`, gần như không cần đọc ảnh.
