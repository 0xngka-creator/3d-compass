# Giao sa bàn

Chọn theo công cụ có trong phiên và điều người dùng muốn:

1. **Trang xem trên Claude (mặc định ở claude.ai / Claude Desktop):** nếu phiên có công cụ Artifact, publish `WD/dist-single/index.html` thành artifact (tiêu đề "Sa bàn <tên dự án>"). Bản một file có ảnh nhúng, cỡ 1–5 MB. Người dùng chia sẻ link từ giao diện.
2. **Netlify / máy chủ riêng:** nén `WD/dist` thành zip và gửi (SendUserFile). Người dùng kéo thư mục vào Netlify Drop hoặc chép lên máy chủ. Bản này tách `scene.json` nên cập nhật bảng hàng chỉ cần thay file đó.
3. **Claude Code / có thư mục trên máy người dùng:** ghi thẳng `dist` vào thư mục người dùng chỉ định.

Kiểm tra trước khi giao:
- Mở trình xem bằng trình duyệt không giao diện nếu có Chrome (`--use-gl=swiftshader`), chụp ảnh, xác nhận không còn chữ "Đang tải" và không có lỗi console.
- Nếu `build` cảnh báo loại tầng/layout bị bỏ qua, nói rõ trong báo cáo.
- Bảng hàng giả: ghi chú dữ liệu giả phải hiện trên sa bàn (đặt bằng `init --note`).

Điều khiển từ ngoài (avatar dẫn tour): trang có `window.saBan` với `getState`, `goFloor(tầng)`, `setTime('day'|'night')`, `showUnit(tầng, mã)` (gọi `goFloor` trước), `closeUnit()`; nhận cả `postMessage({saBan:'<tên>', args:[...]})` khi nhúng trong iframe.
