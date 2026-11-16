#!/usr/bin/env python3
"""saban.py - công cụ dòng lệnh dựng sa bàn 3D bất động sản.

Phần đọc ảnh (vẽ ranh căn, viết HouseSpec) do Claude làm trong cuộc trò chuyện;
script này lo phần tính toán, kiểm tra, ghép dữ liệu và xuất trình xem.

Lệnh:
  init WD --name TÊN [--floor-height 3.3] [--podium 3] [--glass #15191c] [--north 0] [--note ...] [--mode review|auto]
  units WD BANG_HANG.xlsx|csv
  masterplan WD ANH [--mpp 0.36]
  tower WD --id ID --name TÊN --x PX --y PX --total SỐ_TẦNG [--rot ĐỘ]
  floor WD --tower ID --id FT --name TÊN --floors "12-22,24-33" --img ANH
  polys WD --tower ID --ft FT --json RANH.json [--approve]
  unittype WD --name LOẠI --spec spec.json [--photo ẢNH ...] [--approve]
  look WD --json dien_mao.json [--img ẢNH_PHỐI_CẢNH ...]
  build WD --out THƯ_MỤC [--single]
  log WD --step BƯỚC --item MỤC [--images ẢNH ...] [--out-chars N] [--note ...]
  report WD
  status WD
"""
import argparse, base64, csv, io, json, math, os, re, shutil, sys, time, unicodedata
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, '..', 'assets')
CATALOG = os.path.join(HERE, '..', '..', 'layout-can-ho', 'reference', 'catalog-sizes.json')


# ---------- tiện ích ----------
def norm(s):
    s = unicodedata.normalize('NFD', str('' if s is None else s))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').replace('đ', 'd').replace('Đ', 'D')
    return re.sub(r'[^a-z0-9]', '', s.lower())


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def pfile(wd):
    return os.path.join(wd, 'project.json')


def load(wd):
    if not os.path.exists(pfile(wd)):
        sys.exit('Chưa có dự án ở ' + wd + ' (chạy: saban.py init WD --name ...)')
    with open(pfile(wd), encoding='utf-8') as f:
        return json.load(f)


def save(wd, p):
    p['updatedAt'] = now()
    with open(pfile(wd), 'w', encoding='utf-8') as f:
        json.dump(p, f, ensure_ascii=False, indent=1)


def img_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


def copy_in(wd, src, prefix):
    os.makedirs(os.path.join(wd, 'files'), exist_ok=True)
    ext = os.path.splitext(src)[1].lower() or '.png'
    if ext == '.pdf':
        dst = os.path.join(wd, 'files', prefix + '.png')
        pdf_to_png(src, dst)
    else:
        dst = os.path.join(wd, 'files', prefix + ext)
        shutil.copyfile(src, dst)
    return os.path.relpath(dst, wd)


def pdf_to_png(pdf, png, dpi=200):
    import fitz
    doc = fitz.open(pdf)
    doc[0].get_pixmap(dpi=dpi).save(png)


def parse_floors(s):
    out = []
    for part in re.split(r'[,;\s]+', str(s or '')):
        if not part:
            continue
        m = re.match(r'^(\d+)\s*-\s*(\d+)$', part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            out += list(range(min(a, b), max(a, b) + 1))
        elif part.isdigit():
            out.append(int(part))
    return sorted(set(out))


def poly_area(pts):
    a = 0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def find_tower(p, tid):
    for t in p['towers']:
        if t['id'] == tid:
            return t
    sys.exit('Không có tòa ' + tid)


def find_ft(t, fid):
    for f in t['floorTypes']:
        if f['id'] == fid:
            return f
    sys.exit('Tòa ' + t['id'] + ' không có loại tầng ' + fid)


# ---------- ước lượng token (để theo dõi mức dùng gói, KHÔNG phải hóa đơn) ----------
def est_image_tokens(path):
    try:
        w, h = img_size(path)
    except Exception:
        return 0
    s = min(1.0, 1568 / max(w, h))
    w, h = w * s, h * s
    if w * h > 1_150_000:
        k = math.sqrt(1_150_000 / (w * h))
        w, h = w * k, h * k
    return int(w * h / 750)


def append_log(wd, e):
    e = dict(ts=now(), **e)
    with open(os.path.join(wd, 'log.jsonl'), 'a', encoding='utf-8') as f:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')
    return e


# ---------- lệnh ----------
def cmd_init(a):
    os.makedirs(a.wd, exist_ok=True)
    if os.path.exists(pfile(a.wd)) and not a.force:
        sys.exit('Đã có dự án ở ' + a.wd + ' (thêm --force để tạo lại)')
    p = dict(name=a.name, createdAt=now(), mode=a.mode,
             config=dict(floorHeight=a.floor_height, podiumFloors=a.podium, glassColor=a.glass, northDeg=a.north),
             dataNote=a.note or '', masterplan=None, towers=[], units=[], unitTypes=[])
    save(a.wd, p)
    append_log(a.wd, dict(step='init', item=a.name, kind='script'))
    print('Đã tạo dự án "%s" ở %s (chế độ %s)' % (a.name, a.wd, a.mode))


COLS = dict(tower=['toa', 'block', 'tower', 'thap'], floor=['tang', 'floor', 'lau'],
            code=['macan', 'can', 'ma', 'unit', 'code', 'socan'], type=['loai', 'loaican', 'type', 'loaihinh'],
            area=['dttim', 'dientichtim', 'dttimtuong', 'gfa', 'dientich', 'dt'],
            netArea=['dttt', 'dtthongthuy', 'dientichthongthuy', 'nfa', 'thongthuy'],
            dir=['huong', 'huongbancong', 'direction', 'view'], price=['gia', 'giaban', 'price', 'tonggia'],
            status=['trangthai', 'status', 'tinhtrang'], layout=['layout', 'mabang', 'mau', 'mauthietke'])
STATUS = dict(avail=['controng', 'trong', 'conhang', 'available', 'mo', 'dangban', 'con'],
              hold=['giucho', 'datcoc', 'coc', 'hold', 'booking', 'reserved', 'dangiu', 'lock'],
              sold=['daban', 'ban', 'sold', 'dakyhd', 'hopdong'])


def read_rows(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.xlsx', '.xlsm', '.xls'):
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.worksheets[0]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        with open(path, encoding='utf-8-sig', newline='') as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            except csv.Error:
                dialect = csv.excel
            rows = list(csv.reader(f, dialect))
    # dòng tiêu đề = dòng đầu tiên nhận ra cột Mã căn
    for i, r in enumerate(rows[:20]):
        if any(norm(c) in COLS['code'] for c in r):
            return [str(c or '') for c in r], rows[i + 1:], i + 1
    sys.exit('Không tìm thấy dòng tiêu đề có cột "Mã căn"')


def num(v):
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r'[^\d.,-]', '', str(v))
    if s.count(',') and s.count('.'):
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    else:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def cmd_units(a):
    p = load(a.wd)
    head, rows, hline = read_rows(a.file)
    idx = {}
    for j, h in enumerate(head):
        nh = norm(h)
        for k, alias in COLS.items():
            if nh in alias and k not in idx:
                idx[k] = j
    units, skipped = [], []
    for i, r in enumerate(rows):
        g = lambda k: (r[idx[k]] if k in idx and idx[k] < len(r) else None)
        code, fl = g('code'), g('floor')
        if code in (None, '') or fl in (None, ''):
            if any(c not in (None, '') for c in r):
                skipped.append(hline + i + 1)
            continue
        st, status = norm(g('status')), 'avail'
        for s, alias in STATUS.items():
            if st in alias:
                status = s
        try:
            floor = int(num(fl))
        except (TypeError, ValueError):
            skipped.append(hline + i + 1)
            continue
        units.append(dict(tower=str(g('tower') or '').strip(), floor=floor, code=str(code).strip(),
                          type=str(g('type') or '').strip(), area=num(g('area')), netArea=num(g('netArea')),
                          dir=str(g('dir') or '').strip(), price=num(g('price')), status=status,
                          layout=str(g('layout') or g('type') or '').strip()))
    p['units'] = units
    p['unitsFile'] = copy_in(a.wd, a.file, 'bang_hang')
    names = sorted({u['layout'] for u in units if u['layout']})
    for n in names:
        if not any(norm(t['name']) == norm(n) for t in p['unitTypes']):
            p['unitTypes'].append(dict(name=n, status='empty'))
    save(a.wd, p)
    append_log(a.wd, dict(step='units', item=os.path.basename(a.file), kind='script', rows=len(units)))
    towers = sorted({u['tower'] for u in units})
    cnt = {s: sum(1 for u in units if u['status'] == s) for s in STATUS}
    print('Đọc %d căn, tòa: %s, loại layout: %s' % (len(units), ', '.join(towers) or '(không ghi tòa)', ', '.join(names)))
    print('Cột nhận ra: ' + ', '.join('%s=%s' % (k, head[j]) for k, j in idx.items()))
    missing = [k for k in ('area', 'price', 'status', 'dir') if k not in idx]
    if missing:
        print('Thiếu cột: ' + ', '.join(missing))
    print('Trạng thái: còn trống %(avail)d, giữ chỗ %(hold)d, đã bán %(sold)d' % cnt)
    if skipped:
        print('Bỏ qua %d dòng thiếu mã căn/tầng: %s' % (len(skipped), skipped[:20]))


def cmd_masterplan(a):
    p = load(a.wd)
    f = copy_in(a.wd, a.img, 'tong_mat_bang')
    w, h = img_size(os.path.join(a.wd, f))
    p['masterplan'] = dict(file=f, w=w, h=h, mPerPx=a.mpp)
    save(a.wd, p)
    print('Tổng mặt bằng %dx%d px, %.4f m/px (rộng %.0f m)' % (w, h, a.mpp, w * a.mpp))
    grid_image(os.path.join(a.wd, f), os.path.join(a.wd, 'work', 'grid_tong_mat_bang.png'), pixel_labels=True)
    print('Ảnh lưới để đọc toạ độ tòa: work/grid_tong_mat_bang.png (nhãn = pixel ảnh gốc)')


def cmd_tower(a):
    p = load(a.wd)
    t = next((t for t in p['towers'] if t['id'] == a.id), None)
    if not t:
        t = dict(id=a.id, floorTypes=[])
        p['towers'].append(t)
    t.update(name=a.name, x=a.x, y=a.y, rot=a.rot, total=a.total)
    save(a.wd, p)
    print('Tòa %s: tâm (%.1f, %.1f) px trên tổng mặt bằng, xoay %.1f°, %d tầng' % (a.name, a.x, a.y, a.rot, a.total))


def grid_image(src, dst, pixel_labels=False):
    """Ảnh thu nhỏ có lưới, để Claude đọc toạ độ. Nhãn là toạ độ 0–1000 hoặc pixel gốc."""
    from PIL import Image, ImageDraw
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im = Image.open(src).convert('RGB')
    W, H = im.size
    s = min(1.0, 1500 / max(W, H))
    im = im.resize((int(W * s), int(H * s)))
    w, h = im.size
    d = ImageDraw.Draw(im, 'RGBA')
    for k in range(0, 1001, 50):
        x, y = k / 1000 * w, k / 1000 * h
        strong = k % 100 == 0
        col = (255, 0, 90, 150 if strong else 60)
        d.line([(x, 0), (x, h)], fill=col, width=1)
        d.line([(0, y), (w, y)], fill=col, width=1)
        if strong:
            lx = str(round(k / 1000 * W)) if pixel_labels else str(k)
            ly = str(round(k / 1000 * H)) if pixel_labels else str(k)
            d.rectangle([x + 1, 1, x + 7 * len(lx) + 3, 12], fill=(255, 255, 255, 200))
            d.text((x + 2, 1), lx, fill=(200, 0, 70))
            d.rectangle([1, y + 1, 7 * len(ly) + 3, y + 12], fill=(255, 255, 255, 200))
            d.text((2, y + 1), ly, fill=(200, 0, 70))
    im.save(dst)


def floor_units(p, t, ft):
    floors = parse_floors(ft['floors'])
    rows = [u for u in p['units'] if (not u['tower'] or norm(u['tower']) == norm(t['name'])) and u['floor'] in floors]
    first = next((f for f in floors if any(u['floor'] == f for u in rows)), None)
    return [u for u in rows if u['floor'] == first], first


def cmd_floor(a):
    p = load(a.wd)
    t = find_tower(p, a.tower)
    ft = next((f for f in t['floorTypes'] if f['id'] == a.id), None)
    if not ft:
        ft = dict(id=a.id, units=[], status='empty')
        t['floorTypes'].append(ft)
    f = copy_in(a.wd, a.img, 'mat_bang_%s_%s' % (t['id'], a.id))
    w, h = img_size(os.path.join(a.wd, f))
    ft.update(name=a.name, floors=a.floors, file=f, w=w, h=h)
    save(a.wd, p)
    g = os.path.join('work', 'grid_%s_%s.png' % (t['id'], a.id))
    grid_image(os.path.join(a.wd, f), os.path.join(a.wd, g))
    ref, first = floor_units(p, t, ft)
    print('Mặt bằng %s / %s: %dx%d px, áp cho tầng %s' % (t['name'], a.name, w, h, a.floors))
    print('Ảnh lưới (toạ độ 0–1000): ' + g)
    if ref:
        print('Mã căn trên tầng %d theo bảng hàng (%d căn):' % (first, len(ref)))
        for u in ref:
            print('  %s  %s  %s m²  %s' % (u['code'], u['type'], u['area'], u['dir']))
    else:
        print('Bảng hàng không có căn nào ở các tầng này: đọc mã căn in trên ảnh.')


def cmd_polys(a):
    p = load(a.wd)
    t = find_tower(p, a.tower)
    ft = find_ft(t, a.ft)
    with open(a.json, encoding='utf-8') as f:
        j = json.load(f)
    W, H = ft['w'], ft['h']
    ft['units'] = [dict(code=str(u['code']), poly=[[round(q[0] / 1000 * W, 1), round(q[1] / 1000 * H, 1)] for q in u['poly']])
                   for u in j.get('units', []) if len(u.get('poly', [])) >= 3]
    ft['notes'] = j.get('notes', '')
    ref, first = floor_units(p, t, ft)
    codes = [u['code'] for u in ref]
    byc = {norm(u['code']): u for u in ref}
    aPx = aM = 0
    for u in ft['units']:
        r = byc.get(norm(u['code']))
        if r and r['area']:
            aPx += poly_area(u['poly'])
            aM += r['area']
    issues = []
    if aPx and aM:
        ft['mPerPx'] = round(math.sqrt(aM / aPx), 5)
        ft['scaleFrom'] = 'diện tích tim tường của %d căn' % len(ft['units'])
    else:
        issues.append('Không suy được tỷ lệ (bảng hàng thiếu diện tích hoặc mã căn không khớp)')
    missing = [c for c in codes if norm(c) not in {norm(u['code']) for u in ft['units']}]
    extra = [u['code'] for u in ft['units'] if codes and norm(u['code']) not in byc]
    dev = []
    if ft.get('mPerPx'):
        for u in ft['units']:
            r = byc.get(norm(u['code']))
            if r and r['area']:
                m2 = poly_area(u['poly']) * ft['mPerPx'] ** 2
                d = (m2 - r['area']) / r['area']
                if abs(d) > 0.15:
                    dev.append('%s: vẽ %.1f m² / bảng %.1f m² (%+.0f%%)' % (u['code'], m2, r['area'], d * 100))
    overlap = overlaps(ft['units'], W, H)
    ft['check'] = dict(unitsFound=len(ft['units']), unitsInTable=len(codes), missing=missing, extra=extra,
                       areaDeviation=dev, overlap=overlap)
    ok = not missing and not extra and not dev and not overlap and ft.get('mPerPx')
    ft['status'] = 'approved' if (a.approve or (p['mode'] == 'auto' and ok)) else 'review'
    save(a.wd, p)
    ov = os.path.join('work', 'overlay_%s_%s.png' % (t['id'], ft['id']))
    draw_overlay(os.path.join(a.wd, ft['file']), ft['units'], os.path.join(a.wd, ov), {norm(x.split(':')[0]) for x in dev})
    append_log(a.wd, dict(step='digitize-check', item='%s / %s' % (t['name'], ft['name']), kind='script', units=len(ft['units'])))
    print('Ranh căn %s / %s: %d căn (bảng hàng %d)' % (t['name'], ft['name'], len(ft['units']), len(codes)))
    if ft.get('mPerPx'):
        print('Tỷ lệ %.5f m/px → mặt bằng rộng %.1f m x %.1f m' % (ft['mPerPx'], W * ft['mPerPx'], H * ft['mPerPx']))
    for label, v in (('Thiếu', missing), ('Thừa', extra), ('Lệch diện tích >15%', dev), ('Chồng nhau', overlap), ('Khác', issues)):
        if v:
            print(label + ': ' + '; '.join(v))
    print('Ảnh đối chiếu: ' + ov)
    print('Trạng thái: ' + ('đã duyệt' if ft['status'] == 'approved' else 'chờ duyệt'))


def overlaps(units, W, H):
    import numpy as np, cv2
    s = min(1.0, 1200 / max(W, H))
    acc = np.zeros((int(H * s) + 1, int(W * s) + 1), np.uint8)
    masks = []
    for u in units:
        m = np.zeros_like(acc)
        cv2.fillPoly(m, [np.array([[x * s, y * s] for x, y in u['poly']], np.int32)], 1)
        masks.append(m)
        acc += m
    out = []
    for i, u in enumerate(units):
        inter = int(((acc > 1) & (masks[i] > 0)).sum())
        area = int(masks[i].sum()) or 1
        if inter / area > 0.03:
            out.append('%s (%.0f%%)' % (u['code'], inter / area * 100))
    return out


def draw_overlay(src, units, dst, bad):
    from PIL import Image, ImageDraw
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im = Image.open(src).convert('RGB')
    W, H = im.size
    s = min(1.0, 1500 / max(W, H))
    im = im.resize((int(W * s), int(H * s)))
    d = ImageDraw.Draw(im, 'RGBA')
    pal = [(31, 119, 180), (44, 160, 44), (148, 103, 189), (23, 190, 207), (255, 127, 14)]
    for i, u in enumerate(units):
        pts = [(x * s, y * s) for x, y in u['poly']]
        c = (214, 39, 40) if norm(u['code']) in bad else pal[i % len(pal)]
        d.polygon(pts, fill=c + (70,), outline=c + (255,))
        cx = sum(q[0] for q in pts) / len(pts)
        cy = sum(q[1] for q in pts) / len(pts)
        d.rectangle([cx - 4 * len(u['code']) - 2, cy - 7, cx + 4 * len(u['code']) + 2, cy + 7], fill=(255, 255, 255, 220))
        d.text((cx - 3 * len(u['code']), cy - 6), u['code'], fill=(0, 0, 0))
    im.save(dst)


def cmd_unittype(a):
    p = load(a.wd)
    ut = next((t for t in p['unitTypes'] if norm(t['name']) == norm(a.name)), None)
    if not ut:
        ut = dict(name=a.name)
        p['unitTypes'].append(ut)
    key = norm(a.name) or 'loai'
    if a.spec:
        os.makedirs(os.path.join(a.wd, 'specs'), exist_ok=True)
        dst = os.path.join('specs', key + '.json')
        shutil.copyfile(a.spec, os.path.join(a.wd, dst))
        ut['spec'] = dst
    if a.photo:
        ut['photos'] = [copy_in(a.wd, ph, 'phoi_canh_%s_%d' % (key, i + 1)) for i, ph in enumerate(a.photo)]
    if a.layout:
        ut['file'] = copy_in(a.wd, a.layout, 'layout_' + key)
    ut['status'] = 'approved' if (a.approve or p['mode'] == 'auto') and ut.get('spec') else ('review' if ut.get('spec') else 'empty')
    save(a.wd, p)
    print('Loại %s: spec %s, %d ảnh phối cảnh, trạng thái %s' % (a.name, ut.get('spec') or '-', len(ut.get('photos') or []), ut['status']))


def cmd_look(a):
    p = load(a.wd)
    with open(a.json, encoding='utf-8') as f:
        look = json.load(f)
    hexok = lambda v: isinstance(v, str) and re.match(r'^#[0-9a-fA-F]{6}$', v)
    bad = [k for k, v in list(look.items()) + [('podium.' + k, v) for k, v in (look.get('podium') or {}).items()]
           if k.split('.')[-1] in ('glass', 'glassReflect', 'mullion', 'slab', 'wall', 'roof') and v is not None and not hexok(v)]
    if bad:
        sys.exit('Màu phải dạng #rrggbb: ' + ', '.join(bad))
    p['config']['look'] = look
    if look.get('glass'):
        p['config']['glassColor'] = look['glass']
    if (look.get('podium') or {}).get('floors') is not None:
        p['config']['podiumFloors'] = look['podium']['floors']
    if a.img:
        p['lookFrom'] = [copy_in(a.wd, x, 'phoi_canh_tong_%d' % (i + 1)) for i, x in enumerate(a.img)]
    save(a.wd, p)
    print('Diện mạo: kính %s, khung %s, dải sàn %s, tường %s, mái %s; khối đế %s tầng (%s)' % (
        look.get('glass'), look.get('mullion'), look.get('slab'), look.get('wall') or 'không (mặt kính)', look.get('roof'),
        (look.get('podium') or {}).get('floors', p['config'].get('podiumFloors')), (look.get('podium') or {}).get('wall') or 'kính'))


def cmd_status(a):
    p = load(a.wd)
    print('Dự án: %s (chế độ %s)' % (p['name'], p['mode']))
    print('Bảng hàng: %d căn' % len(p['units']))
    print('Tổng mặt bằng: ' + ('có, %.3f m/px' % p['masterplan']['mPerPx'] if p['masterplan'] else 'chưa có'))
    for t in p['towers']:
        print('Tòa %s (%d tầng, tâm %.0f,%.0f):' % (t['name'], t['total'], t['x'], t['y']))
        for ft in t['floorTypes']:
            print('  %s [%s]: %d ranh căn, %s' % (ft['name'], ft['floors'], len(ft.get('units') or []), ft.get('status')))
    for ut in p['unitTypes']:
        n = sum(1 for u in p['units'] if norm(u['layout']) == norm(ut['name']))
        print('Layout %s (%d căn): %s' % (ut['name'], n, ut.get('status')))


def data_uri(path, max_side=2048, quality=82):
    from PIL import Image
    if path.endswith('.webp'):
        return 'data:image/webp;base64,' + base64.b64encode(open(path, 'rb').read()).decode()
    im = Image.open(path)
    has_alpha = im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info)
    s = min(1.0, max_side / max(im.size))
    if s < 1:
        im = im.resize((int(im.size[0] * s), int(im.size[1] * s)), Image.LANCZOS)
    buf = io.BytesIO()
    if has_alpha:
        im.convert('RGBA').save(buf, 'PNG', optimize=True)
        mime = 'image/png'
    else:
        im.convert('RGB').save(buf, 'JPEG', quality=quality, optimize=True)
        mime = 'image/jpeg'
    return 'data:%s;base64,%s' % (mime, base64.b64encode(buf.getvalue()).decode())


def footprint(wd, t, ft):
    """Ranh khối nhà = các căn + hành lang/lõi kẹp giữa (đóng hình thái học), và ảnh mặt bằng đã bỏ nền ngoài khối."""
    import numpy as np, cv2
    from PIL import Image
    W, H, mpp = ft['w'], ft['h'], ft['mPerPx']
    s = min(1.0, 1600 / max(W, H))
    m = np.zeros((int(H * s) + 1, int(W * s) + 1), np.uint8)
    for u in ft['units']:
        cv2.fillPoly(m, [np.array([[x * s, y * s] for x, y in u['poly']], np.int32)], 255)
    px = lambda meters: max(1, int(round(meters / mpp * s)))
    k = px(9)  # bắc cầu hành lang/lõi rộng tới ~9 m
    pad = k + 2
    m2 = cv2.copyMakeBorder(m, pad, pad, pad, pad, cv2.BORDER_CONSTANT, 0)
    m2 = cv2.morphologyEx(m2, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))[pad:-pad, pad:-pad]
    cs, _ = cv2.findContours(m2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    fill = np.zeros_like(m)
    cv2.drawContours(fill, cs, -1, 255, -1)
    # đa giác lõi (lùi 0,4 m để không đè mặt đứng căn); chỉ lấy khối lớn nhất
    def poly_of(mask, eps_m):
        c2, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not c2:
            return None
        c = max(c2, key=cv2.contourArea)
        c = cv2.approxPolyDP(c, max(1, eps_m / mpp * s), True)
        return [[round(float(q[0][0]) / s, 1), round(float(q[0][1]) / s, 1)] for q in c] if len(c) >= 3 else None
    fp = poly_of(fill, 0.25)
    core = poly_of(cv2.erode(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (px(0.8), px(0.8)))), 0.25)
    # ảnh mặt bằng: ngoài khối (nới 0,8 m) trong suốt
    alpha = cv2.dilate(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (px(1.6), px(1.6))))
    im = Image.open(os.path.join(wd, ft['file'])).convert('RGBA')
    a_img = Image.fromarray(alpha).resize(im.size, Image.BILINEAR)
    im.putalpha(a_img)
    bb = a_img.getbbox()
    out = os.path.join('work', 'plan_%s_%s.webp' % (t['id'], ft['id']))
    sc = min(1.0, 2048 / max(im.size))
    if sc < 1:
        im = im.resize((int(im.size[0] * sc), int(im.size[1] * sc)), Image.LANCZOS)
    im.save(os.path.join(wd, out), 'WEBP', quality=88)
    return fp, core, out, bb


def cmd_build(a):
    t0 = time.time()
    p = load(a.wd)
    out = a.out
    os.makedirs(out, exist_ok=True)
    warn = []
    if a.single:
        url = lambda f: data_uri(os.path.join(a.wd, f)) if f else None
    else:
        os.makedirs(os.path.join(out, 'files'), exist_ok=True)

        def url(f):
            if not f:
                return None
            shutil.copyfile(os.path.join(a.wd, f), os.path.join(out, 'files', os.path.basename(f)))
            return 'files/' + os.path.basename(f)
    auto = p['mode'] == 'auto'
    towers = []
    for t in p['towers']:
        fts = []
        for ft in t['floorTypes']:
            if ft.get('units') and ft.get('mPerPx') and (ft.get('status') == 'approved' or auto):
                fp, core, plan_img, _ = footprint(a.wd, t, ft)
                fts.append(dict(id=ft['id'], name=ft['name'], floors=parse_floors(ft['floors']), img=url(plan_img),
                                w=ft['w'], h=ft['h'], mPerPx=ft['mPerPx'], units=ft['units'], footprint=fp, core=core))
            else:
                warn.append('%s / %s: chưa duyệt hoặc thiếu ranh căn/tỷ lệ, bỏ qua' % (t['name'], ft.get('name')))
        towers.append(dict(id=t['id'], name=t['name'], x=t['x'], y=t['y'], rot=t.get('rot', 0), total=t['total'], floorTypes=fts))
    unit_types = {}
    for ut in p['unitTypes']:
        if ut.get('spec') and (ut.get('status') == 'approved' or auto):
            with open(os.path.join(a.wd, ut['spec']), encoding='utf-8') as f:
                spec = json.load(f)
            unit_types[norm(ut['name'])] = dict(name=ut['name'], spec=spec, photos=[url(x) for x in ut.get('photos') or []])
        elif ut.get('status') != 'empty':
            warn.append('Layout %s: chưa duyệt, bỏ qua' % ut['name'])
    catalog = {}
    if os.path.exists(CATALOG):
        with open(CATALOG, encoding='utf-8') as f:
            catalog = json.load(f)
    mp = p.get('masterplan')
    scene = dict(id=norm(p['name'])[:24], name=p['name'], generatedAt=now(), config=p['config'], dataNote=p.get('dataNote', ''),
                 masterplan=dict(img=url(mp['file']), w=mp['w'], h=mp['h'], mPerPx=mp['mPerPx']) if mp else None,
                 towers=towers, units=p['units'], unitTypes=unit_types, catalog=catalog)
    with open(os.path.join(ASSETS, 'viewer.html'), encoding='utf-8') as f:
        html = f.read()
    three = open(os.path.join(ASSETS, 'three.min.js'), encoding='utf-8').read()
    orbit = open(os.path.join(ASSETS, 'OrbitControls.js'), encoding='utf-8').read()
    if a.single:
        inject = '<script>%s</script>\n<script>%s</script>\n<script>window.SCENE=%s;</script>' % (
            three, orbit, json.dumps(scene, ensure_ascii=False).replace('</', '<\\/'))
    else:
        shutil.copyfile(os.path.join(ASSETS, 'three.min.js'), os.path.join(out, 'three.min.js'))
        shutil.copyfile(os.path.join(ASSETS, 'OrbitControls.js'), os.path.join(out, 'OrbitControls.js'))
        with open(os.path.join(out, 'scene.json'), 'w', encoding='utf-8') as f:
            json.dump(scene, f, ensure_ascii=False)
        inject = '<script src="three.min.js"></script>\n<script src="OrbitControls.js"></script>'
    html = html.replace('<!--SABAN_LIBS-->', inject)
    with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    size = os.path.getsize(os.path.join(out, 'index.html'))
    append_log(a.wd, dict(step='build', item='single' if a.single else 'folder', kind='script',
                          duration_ms=int((time.time() - t0) * 1000)))
    print('Đã xuất %s/index.html (%.1f MB)%s' % (out, size / 1e6, '' if a.single else ' kèm scene.json, files/'))
    print('%d tòa, %d loại tầng, %d căn, %d loại layout 3D' % (len(towers), sum(len(t['floorTypes']) for t in towers), len(p['units']), len(unit_types)))
    for w_ in warn:
        print('Cảnh báo: ' + w_)


def cmd_log(a):
    imgs = [dict(file=os.path.basename(x), tokens=est_image_tokens(x)) for x in (a.images or [])]
    e = append_log(a.wd, dict(step=a.step, item=a.item, kind='claude', images=imgs,
                              est_input_tokens=sum(i['tokens'] for i in imgs) + int(a.in_chars / 3.5),
                              est_output_tokens=int(a.out_chars / 3.5), note=a.note or ''))
    print('Ghi nhật ký: %s / %s, ước lượng %d token vào, %d token ra' % (a.step, a.item, e['est_input_tokens'], e['est_output_tokens']))


def cmd_report(a):
    path = os.path.join(a.wd, 'log.jsonl')
    rows = [json.loads(l) for l in open(path, encoding='utf-8')] if os.path.exists(path) else []
    agg = {}
    for r in rows:
        k = r['step']
        g = agg.setdefault(k, dict(n=0, ai=0, tin=0, tout=0))
        g['n'] += 1
        if r.get('kind') == 'claude':
            g['ai'] += 1
            g['tin'] += r.get('est_input_tokens', 0)
            g['tout'] += r.get('est_output_tokens', 0)
    print('%-18s %5s %7s %12s %12s' % ('Bước', 'Lượt', 'Claude', 'Token vào~', 'Token ra~'))
    for k, g in agg.items():
        print('%-18s %5d %7d %12d %12d' % (k, g['n'], g['ai'], g['tin'], g['tout']))
    ti = sum(g['tin'] for g in agg.values())
    to = sum(g['tout'] for g in agg.values())
    print('Tổng ước lượng: %d token vào, %d token ra (chưa tính phần hội thoại và đọc tài liệu skill)' % (ti, to))
    if a.csv:
        with open(a.csv, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['ts', 'step', 'item', 'kind', 'est_input_tokens', 'est_output_tokens', 'note'])
            for r in rows:
                w.writerow([r.get('ts'), r.get('step'), r.get('item'), r.get('kind'), r.get('est_input_tokens', ''), r.get('est_output_tokens', ''), r.get('note', '')])
        print('Đã ghi ' + a.csv)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('init'); s.add_argument('wd'); s.add_argument('--name', required=True)
    s.add_argument('--floor-height', type=float, default=3.3); s.add_argument('--podium', type=int, default=3)
    s.add_argument('--glass', default='#15191c'); s.add_argument('--north', type=float, default=0)
    s.add_argument('--note', default=''); s.add_argument('--mode', choices=['review', 'auto'], default='review')
    s.add_argument('--force', action='store_true'); s.set_defaults(f=cmd_init)
    s = sp.add_parser('units'); s.add_argument('wd'); s.add_argument('file'); s.set_defaults(f=cmd_units)
    s = sp.add_parser('masterplan'); s.add_argument('wd'); s.add_argument('img'); s.add_argument('--mpp', type=float, default=0.36); s.set_defaults(f=cmd_masterplan)
    s = sp.add_parser('tower'); s.add_argument('wd'); s.add_argument('--id', required=True); s.add_argument('--name', required=True)
    s.add_argument('--x', type=float, required=True); s.add_argument('--y', type=float, required=True)
    s.add_argument('--rot', type=float, default=0); s.add_argument('--total', type=int, required=True); s.set_defaults(f=cmd_tower)
    s = sp.add_parser('floor'); s.add_argument('wd'); s.add_argument('--tower', required=True); s.add_argument('--id', required=True)
    s.add_argument('--name', required=True); s.add_argument('--floors', required=True); s.add_argument('--img', required=True); s.set_defaults(f=cmd_floor)
    s = sp.add_parser('polys'); s.add_argument('wd'); s.add_argument('--tower', required=True); s.add_argument('--ft', required=True)
    s.add_argument('--json', required=True); s.add_argument('--approve', action='store_true'); s.set_defaults(f=cmd_polys)
    s = sp.add_parser('unittype'); s.add_argument('wd'); s.add_argument('--name', required=True); s.add_argument('--spec')
    s.add_argument('--photo', nargs='*'); s.add_argument('--layout'); s.add_argument('--approve', action='store_true'); s.set_defaults(f=cmd_unittype)
    s = sp.add_parser('build'); s.add_argument('wd'); s.add_argument('--out', required=True); s.add_argument('--single', action='store_true'); s.set_defaults(f=cmd_build)
    s = sp.add_parser('log'); s.add_argument('wd'); s.add_argument('--step', required=True); s.add_argument('--item', required=True)
    s.add_argument('--images', nargs='*'); s.add_argument('--in-chars', type=int, default=0); s.add_argument('--out-chars', type=int, default=0)
    s.add_argument('--note'); s.set_defaults(f=cmd_log)
    s = sp.add_parser('report'); s.add_argument('wd'); s.add_argument('--csv'); s.set_defaults(f=cmd_report)
    s = sp.add_parser('look'); s.add_argument('wd'); s.add_argument('--json', required=True); s.add_argument('--img', nargs='*'); s.set_defaults(f=cmd_look)
    s = sp.add_parser('status'); s.add_argument('wd'); s.set_defaults(f=cmd_status)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
