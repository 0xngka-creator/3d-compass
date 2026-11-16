# sa-ban — plugin dựng sa bàn 3D bất động sản cho Claude

Dựng sa bàn 3D bán hàng chung cư từ tài liệu thường có của dự án: bảng hàng, tổng mặt bằng, mặt bằng tầng, layout căn và ảnh phối cảnh. Sa bàn xoay được, tô màu căn theo trạng thái, lọc theo tầng/giá/diện tích/hướng, bấm căn để xem mô hình 3D và bảng thông tin.

Phần đọc ảnh (vẽ ranh căn trên mặt bằng tầng, dựng layout căn) do Claude làm ngay trong cuộc trò chuyện, nên tính vào hạn mức gói Claude của bạn, không cần API key. Phần tính toán, kiểm tra và xuất trang xem chạy bằng script Python.

## Cài đặt
- **Claude Code:** `/plugin marketplace add 0xngka-creator/3d-compass` rồi `/plugin install sa-ban@sa-ban-tools`.
- **Claude (web / desktop):** tải file `sa-ban.plugin` ở mục Releases và cài từ phần Plugins, hoặc tải từng thư mục trong `plugins/sa-ban/skills/` lên làm skill.

## Dùng
Gửi tài liệu dự án và nói "dựng sa bàn cho dự án X". Danh sách tài liệu cần có: `plugins/sa-ban/skills/dung-sa-ban/references/tai-lieu.md`.

Hai chế độ: `review` (Claude gửi ảnh đối chiếu ranh căn để bạn duyệt) và `auto` (tự duyệt khi kiểm tra không lỗi).

Đầu ra: một trang HTML tự chứa (đăng thành artifact trên Claude) hoặc thư mục `dist/` để kéo vào Netlify. Bảng hàng thay đổi thì gửi file mới, Claude chạy lại hai lệnh `units` và `build`.

## Theo dõi mức dùng
`saban.py report WD` in bảng ước lượng token theo bước (số ảnh đã đọc, độ dài dữ liệu đã viết). Đây là ước lượng để so giữa các dự án, không phải số liệu hạn mức chính thức.

## Chạy thử không cần Claude
`sh examples/lumiere/chay-thu.sh <ảnh mặt bằng tầng L1>` dựng sa bàn mẫu từ ranh căn vẽ sẵn. Bảng hàng mẫu là dữ liệu giả; ảnh mặt bằng thuộc chủ đầu tư nên không kèm trong repo.

## Cấu trúc
```
.claude-plugin/marketplace.json
plugins/sa-ban/
  .claude-plugin/plugin.json
  skills/dung-sa-ban/   quy trình chính, scripts/saban.py, trình xem Three.js r128
  skills/layout-can-ho/ layout căn → HouseSpec (rút gọn từ house-plan-designer, MIT)
examples/lumiere/       dữ liệu mẫu
```

## Giấy phép
MIT. `layout-can-ho` dựa trên [ZWD11/house-plan-designer](https://github.com/ZWD11/house-plan-designer) (MIT). Three.js (MIT). Repo không chứa ảnh của chủ đầu tư.
