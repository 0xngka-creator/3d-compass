# Giao sa bàn

Chọn theo công cụ có trong phiên và điều người dùng muốn:

1. **Trang xem trên Claude (mặc định ở claude.ai / Claude Desktop):** nếu phiên có công cụ Artifact, publish `WD/dist-single/index.html` thành artifact (tiêu đề "Sa bàn <tên dự án>"). Bản một file có ảnh nhúng, cỡ 1–5 MB. Người dùng chia sẻ link từ giao diện.
2. **Netlify / máy chủ riêng:** nén `WD/dist` thành zip và gửi (SendUserFile). Người dùng kéo thư mục vào Netlify Drop hoặc chép lên máy chủ. Bản này tách `scene.json` nên cập nhật bảng hàng chỉ cần thay file đó.
3. **Claude Code / có thư mục trên máy người dùng:** ghi thẳng `dist` vào thư mục người dùng chỉ định.

Kiểm tra trước khi giao:
- Mở trình xem bằng trình duyệt không giao diện nếu có Chrome (`--use-gl=swiftshader`), chụp ảnh, xác nhận không còn chữ "Đang tải" và không có lỗi console.
- Nếu `build` cảnh báo loại tầng/layout bị bỏ qua, nói rõ trong báo cáo.
- Bảng hàng giả: ghi chú dữ liệu giả phải hiện trên sa bàn (đặt bằng `init --note`).

Thao tác trên sa bàn (ghi vào báo cáo giao cho người dùng):
- Kéo chuột trái: xoay quanh tòa nhà dưới con trỏ (con trỏ ở mặt đất thì xoay quanh giữa màn hình). Kéo chuột phải hoặc giữ Shift: dịch. Cuộn: tiến/lùi về phía con trỏ. Điện thoại: 1 ngón xoay, 2 ngón chụm và dịch.
- Popup căn hộ (căn đi đường CAD), chế độ đi bộ: nút "Đi bộ" đặt người ở tiền sảnh căn (hoặc phòng đầu tiên). Kéo để nhìn quanh. Bấm vào sàn hoặc bấm tên phòng: người tự tìm đường qua cửa, quay về hướng đi rồi bước tới, đầu nhún theo bước chân, tới nơi thì quay về hướng nhìn thoáng nhất của phòng. Máy tính: bấm vào cảnh để khóa chuột, rê chuột để quay người và ngước/cúi, bấm chuột để đi tới chỗ tâm ngắm, lăn chuột để tiến/lùi, Esc để thả chuột (không khóa được chuột thì kéo để quay người). Phím vẫn dùng được: ↑/W tiến, ↓/S lùi, ←/→ quay, A/D bước ngang, Shift đi nhanh. Điện thoại có cần điều khiển ở góc trái. Tường, kính và đồ nội thất chặn đường; đi chéo vào tường thì trượt dọc tường. Nhìn ra cửa sổ thấy tổng mặt bằng và các tòa xung quanh đúng vị trí.
- Nội thất trong popup dựng bằng code (bộ của floorplan-3d, MIT), đặt theo khối nội thất trên bản vẽ, chỉ để hình dung tỷ lệ; sàn và tường để màu trung tính vì không biết vật liệu thật của căn mẫu.
- Toàn cảnh căn mặc định tường cắt thấp có viền sẫm; nút "Tường cao/Tường thấp" để đổi. Nút phòng ghi diện tích phòng đo trên bản vẽ; bảng Thông tin căn có danh sách diện tích phòng.
- Cửa đi một cánh dựng từ ký hiệu cửa trên bản vẽ, mặc định mở như bản vẽ; bấm vào cánh để đóng/mở, khi đi bộ tới cửa đang đóng thì cửa tự mở. Cửa trượt, cửa hai cánh và cửa có ký hiệu lạ chưa dựng.

Điều khiển từ ngoài (avatar dẫn tour): trang có `window.saBan` với `getState`, `goFloor(tầng)`, `setTime('day'|'night')`, `showUnit(tầng, mã)` (gọi `goFloor` trước), `closeUnit()`; nhận cả `postMessage({saBan:'<tên>', args:[...]})` khi nhúng trong iframe.
