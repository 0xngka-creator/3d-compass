#!/bin/sh
# Chạy thử phần script với dữ liệu mẫu (ranh căn đã vẽ sẵn).
# Dùng: sh examples/lumiere/chay-thu.sh <ảnh mặt bằng tầng L1> [thư mục làm việc]
# Ảnh mặt bằng thuộc chủ đầu tư nên không kèm trong repo.
set -e
IMG=${1:?Cần đường dẫn ảnh mặt bằng tầng L1}
H=$(cd "$(dirname "$0")" && pwd); S="$H/../../plugins/sa-ban/skills/dung-sa-ban/scripts/saban.py"; W=${2:-/tmp/saban-lumiere}
python3 "$S" init "$W" --name "Lumière (mẫu)" --mode auto --note "Trạng thái và giá căn là dữ liệu giả để thử nghiệm" --force
python3 "$S" units "$W" "$H/lumiere_bang_can_mau.csv"
python3 "$S" tower "$W" --id l1 --name L1 --x 0 --y 0 --total 36
python3 "$S" floor "$W" --tower l1 --id dh --name "Tầng điển hình" --floors "12-22,24-33" --img "$IMG"
python3 "$S" polys "$W" --tower l1 --ft dh --json "$H/ranh_l1_dh.json" --approve
python3 "$S" build "$W" --out "$W/dist-single" --single
echo "Mở $W/dist-single/index.html"
