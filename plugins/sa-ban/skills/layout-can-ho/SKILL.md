---
name: layout-can-ho
description: Dựng mô hình căn hộ (tường, cửa, cửa sổ, phòng, nội thất chính) dạng HouseSpec JSON từ layout 2D căn hộ, là PDF vector/DXF xuất từ CAD hoặc ảnh có ghi kích thước. Dùng khi dựng sa bàn cần mô hình 3D căn hộ, hoặc khi người dùng nói "dựng layout căn", "dựng 3D căn hộ từ mặt bằng", "số hóa layout căn hộ".
---

# Layout căn hộ → HouseSpec

Bản rút gọn của house-plan-designer (MIT, xem `NOTICE.md`). Đầu ra duy nhất: `spec.json` theo `reference/spec-lite.md`; skill `dung-sa-ban` nạp file này bằng `saban.py unittype`. Mọi lệnh chạy từ thư mục skill này; `<wd>` là thư mục làm việc riêng cho loại căn (ví dụ `WD/work/layout_2br`).

Thư viện Python: dùng `requirements.txt` của skill `dung-sa-ban`.

## Bước 1. Nhận diện (chọn một đường)
| Đầu vào | Lệnh | Đọc thêm |
|---|---|---|
| PDF vector / DXF từ CAD | `python3 scripts/cadvec.py <file> --out <wd>/cad` (không nhận ra tường thì `cadpair.py`) | `reference/route-cad.md` |
| Ảnh có kích thước | `python3 scripts/rectify.py` rồi `python3 scripts/analyze.py <ảnh> --total-width <mm> --out <wd>/ana` | `reference/route-image.md` |

Kết quả là `draft.json`. Đọc nó rồi bổ sung, không viết lại tường. Ảnh không có kích thước nào: hỏi người dùng tổng chiều rộng căn (mm); nếu không có, ước từ diện tích thông thủy trong bảng hàng và ghi là ước lượng.

Tài liệu `route-*.md` viết bằng tiếng Trung (giữ nguyên từ bản gốc); chỉ đọc phần cần cho bước đang làm.

## Bước 2. Hoàn thiện spec (viết bằng script Python, không gõ JSON tay)
- Đặt tên phòng tiếng Việt (Phòng khách, Bếp, Phòng ngủ 1, WC, Lô gia...), đổi `hole` thành cửa theo công năng phòng, ghi cao bậu cửa sổ nếu biết.
- Ghi chuỗi kích thước vào `dims` / `expectDims`; phòng có ghi diện tích thì điền `area`.
- Nội thất: chỉ món chính của từng phòng (giường, tủ, sofa, bàn ăn, bếp, thiết bị vệ sinh), kích thước lấy từ `reference/catalog-sizes.json`.
- KHÔNG ghi `autoElec`, `elec`, `ceil`, `lighting`, `free*`, `style`, `look`.
- Thông số không có trên bản vẽ (cao tầng, cao bậu): ước lượng và đánh dấu `heightFrom: "estimated"`.
- Mẫu script: `reference/example-gen-cad.py`, `reference/example-gen-precise.py`; mẫu spec: `reference/example-spec.json`.

## Bước 3. Kiểm tra (tối đa hai vòng)
```bash
python3 scripts/build.py <wd>/spec.json -o <wd>/check.html
# nếu có Chrome/Chromium và Node: (cd scripts && npm install) một lần, rồi
node scripts/check.mjs <wd>/check.html <wd>/check
```
Đọc `report.json`: đầu tường hở, tường bị nuốt, cửa bị mất, `dimIssues`, diện tích phòng. Chỉ mở `plan2d.png` / `view3d.png` khi report có lỗi không tự giải thích được. Không có Chrome: so `draft.json` với `<wd>/ana/analysis.png` bằng mắt một lần và ghi rõ trong báo cáo là chưa chạy kiểm tra tự động.
Đầu vào là ảnh: chạy thêm `python3 scripts/coverage.py` một lần để tìm tường sót.

## Bước 4. Nạp vào sa bàn và ghi nhật ký
Quay lại skill `dung-sa-ban`: `saban.py unittype ...` rồi `saban.py log WD --step layout --item <loại> --images <ảnh đã mở> --out-chars <độ dài script sinh spec>`.
