#!/usr/bin/env python3
"""cad.py - đọc mặt bằng tầng từ PDF vector xuất từ AutoCAD (giữ lớp/layer).

Lệnh:
  info PDF                               liệt kê trang (tên bản vẽ, khoảng tầng, diện tích sàn) và các lớp
  layers PDF --page N --out ẢNH.png      bảng ảnh nhỏ: mỗi lớp một ô, để xác định vai trò lớp
  extract PDF --map lop.json --page N --out THƯ_MỤC [--scale 100] [--codes ma.json]
                                         tách tường, phòng, căn hộ, cửa, nội thất; xuất ảnh mặt bằng nền trong suốt
  preview THƯ_MỤC                        vẽ ảnh đánh số căn/phòng để Claude kiểm tra và gán mã căn

lop.json: {"wall":[..], "door":[..], "window":[..], "glass":[..], "furniture":[..], "furniture_tall":[..],
           "outline":[..], "hide":[..]}  (tên lớp; "hide" là các lớp không vẽ lên ảnh mặt bằng, ví dụ khung tên)
"""
import argparse, json, math, os, re, sys, unicodedata
import warnings
warnings.filterwarnings('ignore')
try:
    import pymupdf as fitz
except ImportError:
    import fitz
import numpy as np
import cv2

CM_PER_PX = 2.0  # độ phân giải phân tích: 2 cm/px


def norm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').replace('đ', 'd').replace('Đ', 'D')
    return re.sub(r'[^a-z0-9]', '', s.lower())


def floors_from_title(t):
    """'MẶT BẰNG TẦNG 5-12A' -> '5-13'; '14 VÀ 16' -> '14,16'. 12A được hiểu là tầng 13."""
    u = t.upper()
    if 'HẦM' in u or 'HAM' in norm(u) and 'tangham' in norm(u):
        return None
    m = re.search(r'TẦNG\s+([0-9A]+(?:\s*(?:-|VÀ|,)\s*[0-9A]+)*)', u)
    if not m:
        return None
    fix = lambda x: str(int(x[:-1]) + 1) if x.endswith('A') else x
    s = m.group(1)
    s = re.sub(r'([0-9]+A)', lambda mm: fix(mm.group(1)), s)
    return re.sub(r'\s*VÀ\s*', ',', s).replace(' ', '')


GUESS = [('outline', ['ranhgioi', 'outline', 'bound', 'ranh']), ('glass', ['glaz', 'kinh', 'vachkinh']),
         ('window', ['window', 'cuaso', 'ktcua', 'win']), ('door', ['door', 'cuadi', 'sectdoor']),
         ('furniture_tall', ['sectfurn']), ('furniture', ['furn', 'noithat', 'thietbi', 'tbvs', 'equip']),
         ('wall', ['sectwall', 'wall', 'tuong', 'sectconc', 'cot', 'column', 'conc']),
         ('hide', ['xref', 'khungten', 'title', 'anno', 'dim', 'text', 'grid', 'truc', 'hatch', 'hidden', 'temp', 'pccc', 'symbol'])]


def guess_role(name):
    n = norm(name)
    for role, keys in GUESS:
        if any(k in n for k in keys):
            return role
    return None


def cmd_info(a):
    d = fitz.open(a.pdf)
    layers = [v['name'] for v in (d.get_ocgs() or {}).values()]
    pages = []
    for i, p in enumerate(d):
        txt = p.get_text()
        titles = re.findall(r'MẶT BẰNG[^\n|]*', txt)
        title = max(titles, key=len).strip() if titles else ''
        area = re.search(r'DIỆN TÍCH SÀN:\s*([\d.,]+)', txt)
        dr = p.get_drawings()
        pages.append(dict(page=i, title=title, floors=floors_from_title(title) if title else None,
                          area=float(area.group(1).replace(',', '')) if area else None, drawings=len(dr)))
    out = dict(pdf=os.path.basename(a.pdf), creator=d.metadata.get('creator'), size_pt=list(d[0].rect)[2:],
               layers=[dict(name=l, guess=guess_role(l)) for l in layers], pages=pages)
    if a.json:
        json.dump(out, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('PDF: %s, %d trang, tạo bởi %s' % (out['pdf'], len(pages), out['creator']))
    for pg in pages:
        if pg['title'] or pg['drawings'] > 500:
            print('  trang %2d: %-32s tầng %-10s DT sàn %-7s %d nét' % (pg['page'], pg['title'][:32], pg['floors'] or '-', pg['area'] or '-', pg['drawings']))
    print('Lớp (đoán vai trò):')
    for l in out['layers']:
        print('  %-45s %s' % (l['name'], l['guess'] or '?'))


def paths(p, layers=None):
    for x in p.get_drawings():
        if layers is not None and x.get('layer') not in layers:
            continue
        yield x


def item_pts(it):
    k = it[0]
    if k == 'l':
        return [it[1], it[2]]
    if k == 're':
        r = it[1]
        return [r.tl, r.tr, r.br, r.bl, r.tl]
    if k == 'qu':
        q = it[1]
        return [q.ul, q.ur, q.lr, q.ll, q.ul]
    if k == 'c':
        a, b, c, e = it[1], it[2], it[3], it[4]
        out = []
        for t in np.linspace(0, 1, 9):
            mt = 1 - t
            out.append(fitz.Point(mt ** 3 * a.x + 3 * mt * mt * t * b.x + 3 * mt * t * t * c.x + t ** 3 * e.x,
                                  mt ** 3 * a.y + 3 * mt * mt * t * b.y + 3 * mt * t * t * c.y + t ** 3 * e.y))
        return out
    return []


def cmd_layers(a):
    from PIL import Image, ImageDraw
    d = fitz.open(a.pdf)
    p = d[a.page]
    by = {}
    for x in p.get_drawings():
        by.setdefault(x.get('layer') or '?', []).append(x)
    names = sorted([k for k, v in by.items() if len(v) >= 3], key=lambda k: -len(by[k]))[:24]
    # khung chung = bao của mọi nét trừ lớp khung tên
    xs, ys = [], []
    for k in names:
        if guess_role(k) == 'hide' and 'xref' in norm(k):
            continue
        for x in by[k]:
            r = x['rect']
            xs += [r.x0, r.x1]
            ys += [r.y0, r.y1]
    x0, x1, y0, y1 = np.percentile(xs, 1), np.percentile(xs, 99), np.percentile(ys, 1), np.percentile(ys, 99)
    tw, th = 420, int(420 * (y1 - y0) / max(1, x1 - x0)) + 22
    cols = 4
    sheet = Image.new('RGB', (tw * cols, th * ((len(names) + cols - 1) // cols)), 'white')
    for i, k in enumerate(names):
        tile = Image.new('RGB', (tw, th), 'white')
        g = ImageDraw.Draw(tile)
        sx = (tw - 10) / (x1 - x0)
        for x in by[k]:
            for it in x['items']:
                pts = [((q.x - x0) * sx + 5, (q.y - y0) * sx + 20) for q in item_pts(it)]
                if len(pts) > 1:
                    g.line(pts, fill=(0, 0, 0), width=1)
        g.rectangle([0, 0, tw - 1, 17], fill=(235, 235, 235))
        g.text((4, 3), '%d. %s (%d)' % (i + 1, k[:48], len(by[k])), fill=(180, 0, 60))
        g.rectangle([0, 0, tw - 1, th - 1], outline=(150, 150, 150))
        sheet.paste(tile, ((i % cols) * tw, (i // cols) * th))
    sheet.save(a.out)
    print('Đã vẽ %d lớp vào %s' % (len(names), a.out))


def raster(shape, items, R, ox, oy, width=1, fill_closed=False):
    m = np.zeros(shape, np.uint8)
    for x in items:
        for it in x['items']:
            pts = np.array([[(q.x - ox) * R, (q.y - oy) * R] for q in item_pts(it)], np.int32)
            if len(pts) > 1:
                cv2.polylines(m, [pts], False, 255, width)
        if fill_closed and x.get('fill') is not None:
            for it in x['items']:
                pts = np.array([[(q.x - ox) * R, (q.y - oy) * R] for q in item_pts(it)], np.int32)
                if len(pts) > 2:
                    cv2.fillPoly(m, [pts], 255)
    return m


def contours_to_polys(mask, eps, min_area):
    cs, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    if hier is None:
        return out
    hier = hier[0]
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or cv2.contourArea(c) < min_area:
            continue
        outer = cv2.approxPolyDP(c, eps, True)[:, 0, :].tolist()
        holes = []
        j = hier[i][2]
        while j != -1:
            if cv2.contourArea(cs[j]) >= min_area * 0.5:
                holes.append(cv2.approxPolyDP(cs[j], eps, True)[:, 0, :].tolist())
            j = hier[j][0]
        if len(outer) >= 3:
            out.append(dict(o=outer, h=holes))
    return out


ROOM_SKIP = ['thang', 'ktdien', 'ktctn', 'kt', 'brac', 'sanhtang', 'hanhlang', 'loithang', 'hk', 'ta', 'tg', 'pccc', 'nuoc', 'gen']


def cmd_extract(a):
    from PIL import Image
    lm = json.load(open(a.map, encoding='utf-8'))
    L = lambda role: set(lm.get(role) or [])
    d = fitz.open(a.pdf)
    p = d[a.page]
    m_per_pt = 25.4 / 72 * a.scale / 1000
    R = m_per_pt * 100 / CM_PER_PX  # px trên pt
    allw = list(paths(p, L('wall') | L('outline')))
    if not allw:
        sys.exit('Không có nét nào thuộc lớp tường/ranh khối nhà trên trang %d' % a.page)
    outl = list(paths(p, L('outline')))
    src = outl or allw
    xs = [v for x in src for v in (x['rect'].x0, x['rect'].x1)]
    ys = [v for x in src for v in (x['rect'].y0, x['rect'].y1)]
    pad = 1.5 / m_per_pt
    ox, oy, ex, ey = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    W, H = int((ex - ox) * R) + 1, int((ey - oy) * R) + 1
    mpp = m_per_pt / R
    px = lambda meters: max(1, int(round(meters / mpp)))
    os.makedirs(a.out, exist_ok=True)
    # --- ảnh mặt bằng từ chính bản vẽ (nền trong suốt), tắt lớp khung tên ---
    ocg = {v['name']: k for k, v in (d.get_ocgs() or {}).items()}
    hide = [ocg[n] for n in L('hide') if n in ocg]
    if hide:
        d.set_layer(-1, off=hide)
    clip = fitz.Rect(ox, oy, ex, ey)
    zoom = min(R * 1.25, 4096 / max(clip.width, clip.height))
    pix = p.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=True)
    img = Image.frombytes('RGBA', (pix.width, pix.height), pix.samples)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(os.path.join(a.out, 'plan.webp'), 'WEBP', quality=90)
    # --- tường ---
    wl = raster((H, W), list(paths(p, L('wall'))), R, ox, oy, 1, True)
    walls = cv2.morphologyEx(wl, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.26), px(.26))))
    # --- ranh khối nhà ---
    if outl:
        ol = raster((H, W), outl, R, ox, oy, 2)
        cs, _ = cv2.findContours(cv2.dilate(ol, np.ones((3, 3), np.uint8)), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        foot = np.zeros_like(wl)
        cv2.drawContours(foot, [max(cs, key=cv2.contourArea)], -1, 255, -1)
    else:
        k = px(9)
        cl = cv2.morphologyEx(walls, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        cs, _ = cv2.findContours(cl, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        foot = np.zeros_like(wl)
        cv2.drawContours(foot, [max(cs, key=cv2.contourArea)], -1, 255, -1)
    # --- cửa đi: gom nét thành từng cửa, lấp vùng quét cánh để chặn lối đi ---
    door_items = list(paths(p, L('door')))
    dm = raster((H, W), door_items, R, ox, oy, 1)
    dmc = cv2.morphologyEx(dm, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.3), px(.3))))
    n_d, dlab, dstat, _ = cv2.connectedComponentsWithStats(dmc)
    doors = []
    dfill = np.zeros_like(wl)
    for i in range(1, n_d):
        x, y, w, h, ar = dstat[i]
        if max(w, h) * mpp < .45 or max(w, h) * mpp > 4.5:
            continue
        cv2.rectangle(dfill, (x, y), (x + w, y + h), 255, -1)
        doors.append([int(x), int(y), int(w), int(h), i])
    win = raster((H, W), list(paths(p, L('window'))), R, ox, oy, 2)
    gla = raster((H, W), list(paths(p, L('glass'))), R, ox, oy, 2, True)
    # lấp ô cửa đi trong tường (khe <= 1,5 m dọc theo phương tường) để tách phòng; vách mở rộng hơn vẫn thông
    k = px(1.5)
    wclose = cv2.morphologyEx(walls, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1))) | \
        cv2.morphologyEx(walls, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, k)))
    rail = raster((H, W), list(paths(p, L('railing'))), R, ox, oy, 2)
    part = raster((H, W), list(paths(p, L('partition'))), R, ox, oy, 2, True)
    pclose = cv2.morphologyEx(part | walls, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1))) | \
        cv2.morphologyEx(part | walls, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, k)))
    border = cv2.dilate(foot, np.ones((3, 3), np.uint8)) - cv2.erode(foot, np.ones((3, 3), np.uint8))
    base = dfill | rail | cv2.dilate(win, np.ones((3, 3), np.uint8)) | cv2.dilate(gla, np.ones((3, 3), np.uint8)) | border

    def regions(bar):
        fr = ((foot > 0) & (bar == 0)).astype(np.uint8) * 255
        fr = cv2.morphologyEx(fr, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        return cv2.connectedComponentsWithStats(fr, connectivity=4)
    # vùng A: chỉ tường chính (gom căn); vùng B: thêm vách ngăn nhẹ (phòng)
    nA, labA, statA, _ = regions(base | wclose)
    barrier = base | wclose | pclose
    free = ((foot > 0) & (barrier == 0)).astype(np.uint8) * 255
    free = cv2.morphologyEx(free, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    if os.environ.get('CAD_DEBUG'):
        dbg = np.dstack([wclose | pclose, dfill, cv2.dilate(win, np.ones((3, 3), np.uint8)) | gla]); cv2.imwrite(os.path.join(a.out, 'debug_barrier.png'), 255 - dbg)
    n_r, rlab, rstat, rcent = cv2.connectedComponentsWithStats(free, connectivity=4)
    # --- nhãn phòng từ chữ ---
    words = p.get_text('words')
    lines = {}
    for w in words:
        lines.setdefault((w[5], w[6]), []).append(w)
    labels = []
    for ws in lines.values():
        t = ' '.join(w[4] for w in ws).strip()
        cx = (min(w[0] for w in ws) + max(w[2] for w in ws)) / 2
        cy = (min(w[1] for w in ws) + max(w[3] for w in ws)) / 2
        X, Y = int((cx - ox) * R), int((cy - oy) * R)
        if 0 <= X < W and 0 <= Y < H and foot[Y, X] and len(t) <= 24:
            labels.append(dict(text=t, x=X, y=Y))
    min_room = (0.6 / mpp) ** 2
    if os.environ.get('CAD_DEBUG'):
        rng = np.random.RandomState(3); colr = rng.randint(60, 255, (n_r, 3)).astype(np.uint8); colr[0] = 255
        vis = colr[rlab]; vis[barrier > 0] = 0; cv2.imwrite(os.path.join(a.out, 'debug_rooms.png'), vis)
    rooms = {}
    for i in range(1, n_r):
        if rstat[i][4] < min_room:
            continue
        rooms[i] = dict(id=i, area=round(rstat[i][4] * mpp * mpp, 2), name='', cx=float(rcent[i][0]), cy=float(rcent[i][1]))
    for lb in labels:
        X, Y = lb['x'], lb['y']
        rid = int(rlab[Y, X])
        if rid not in rooms:  # chữ nằm đè lên nét: tìm phòng gần nhất trong 0,6 m
            win_ = rlab[max(0, Y - px(.6)):Y + px(.6), max(0, X - px(.6)):X + px(.6)]
            ids, cnt = np.unique(win_[win_ > 0], return_counts=True)
            ids = [int(r) for r in ids[np.argsort(-cnt)] if int(r) in rooms]
            rid = ids[0] if ids else 0
        if rid in rooms:
            rooms[rid]['name'] = (rooms[rid]['name'] + ' / ' if rooms[rid]['name'] else '') + lb['text']
            rooms[rid]['lx'], rooms[rid]['ly'] = X, Y
    # --- đồ thị phòng nối qua cửa ---
    adj = {r: set() for r in rooms}
    for (x, y, w, h, _lab) in doors:
        g = px(.32)
        sub = rlab[max(0, y - g):y + h + g, max(0, x - g):x + w + g]
        ids = set(int(v) for v in np.unique(sub) if int(v) in rooms)
        for u in ids:
            adj[u] |= ids - {u}
    # phòng thông nhau không qua cửa (vách mở): chạm nhau qua khe < 0,3 m không có tường
    def is_common(r):
        n = norm(r['name'])
        return (not n and r['area'] > 25) or any(n.startswith(k) for k in ROOM_SKIP) or 'sanhtang' in n or 'hanhlang' in n
    common = {r for r in rooms if is_common(rooms[r])}
    groups = json.load(open(a.groups, encoding='utf-8')) if a.groups else None
    # phòng B thuộc vùng A nào (theo đa số điểm ảnh)
    inA = {}
    for r in rooms:
        ids, cnt = np.unique(labA[rlab == r], return_counts=True)
        ok = [(c, int(i)) for i, c in zip(ids, cnt) if i > 0]
        inA[r] = max(ok)[1] if ok else 0
    if groups:  # Claude/người dùng chỉ định: [[id phòng, ...], ...]
        units = [[r for r in g if r in rooms] for g in groups]
    else:
        areaA = {}
        for r in rooms:
            areaA.setdefault(inA[r], []).append(r)
        def a_common(i):
            rs = areaA.get(i, [])
            return i == 0 or any(r in common for r in rs)
        seeds = [i for i, rs in areaA.items() if not a_common(i) and sum(rooms[r]['area'] for r in rs) >= 14
                 and any(re.search(r'khach|ngu|bep', norm(rooms[r]['name'])) for r in rs)]
        owner = {i: i for i in seeds}
        rest = [i for i in areaA if i not in owner and not a_common(i)]
        kern = cv2.getStructuringElement(cv2.MORPH_RECT, (px(.5), px(.5)))
        for _ in range(4):
            lab_own = np.zeros(labA.shape, np.int32)
            for i, o in owner.items():
                lab_own[labA == i] = o
            left = []
            for i in rest:
                x, y, w, h, _a = statA[i]
                g = px(.6)
                y0, y1, x0, x1 = max(0, y - g), y + h + g, max(0, x - g), x + w + g
                ring = cv2.dilate((labA[y0:y1, x0:x1] == i).astype(np.uint8), kern) > 0
                ids, cnt = np.unique(lab_own[y0:y1, x0:x1][ring], return_counts=True)
                best = [(c, int(j)) for j, c in zip(ids, cnt) if j > 0]
                if best:
                    owner[i] = max(best)[1]
                else:
                    left.append(i)
            rest = left
        units = [[r for r in rooms if owner.get(inA[r]) == sd and r not in common] for sd in seeds]
        units = [u for u in units if u]
    # --- đa giác căn: hợp các phòng + tường kề (nới 0,25 m), cắt theo ranh khối nhà ---
    cxb, cyb = W / 2, H / 2
    U = []
    for comp in units:
        mk = np.isin(rlab, comp).astype(np.uint8) * 255
        mk = cv2.dilate(mk, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.5), px(.5))))
        mk = cv2.morphologyEx(mk, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.6), px(.6))))
        mk &= foot
        cs, _ = cv2.findContours(mk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        poly = cv2.approxPolyDP(c, px(.12), True)[:, 0, :].tolist()
        M = cv2.moments(c)
        U.append(dict(rooms=comp, poly=poly, cx=M['m10'] / M['m00'], cy=M['m01'] / M['m00'], mask=mk,
                      area=round(cv2.contourArea(c) * mpp * mpp, 1)))
    # đánh số tạm: bắt đầu từ góc trên trái, theo chiều kim đồng hồ quanh tâm khối nhà
    U.sort(key=lambda u: (math.atan2(u['cy'] - cyb, u['cx'] - cxb) + math.pi * 1.25) % (2 * math.pi))
    codes = json.load(open(a.codes, encoding='utf-8')) if a.codes else {}
    # --- hình học 3D từng căn ---
    walls3d = walls | cv2.morphologyEx(part, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.15), px(.15))))

    # cánh cửa: hình chữ nhật mảnh dài 0,55–1,3 m trong lớp cửa đi (vẽ ở tư thế mở)
    leaves = []
    dm2 = cv2.morphologyEx(dm, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.08), px(.08))))
    for c_ in cv2.findContours(dm2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        (cx_, cy_), (rw_, rh_), an_ = cv2.minAreaRect(c_)
        Lp, Tp = max(rw_, rh_), min(rw_, rh_)
        if not (.55 <= Lp * mpp <= 1.3 and Tp * mpp <= .13):
            continue
        t_ = math.radians(an_ if rw_ >= rh_ else an_ + 90)
        ax_ = np.array([math.cos(t_), math.sin(t_)]) * Lp / 2
        leaves.append((np.array([cx_, cy_]) - ax_, np.array([cx_, cy_]) + ax_))
    def leaf_geom(e1, e2):
        """Bản lề là đầu cánh mà từ đó, theo phương vuông góc với cánh, có một khoảng trống dài bằng cánh (ô cửa)
        kết thúc ở bậu tường đối diện. Cánh khi đóng nằm trên khoảng trống đó."""
        wm = walls3d > 0
        def wall_at(q, r_m=.1):
            r_ = px(r_m)
            xa, xb, ya, yb = max(0, int(q[0]) - r_), min(W, int(q[0]) + r_ + 1), max(0, int(q[1]) - r_), min(H, int(q[1]) + r_ + 1)
            return xa < xb and ya < yb and bool(wm[ya:yb, xa:xb].any())
        Lp = np.linalg.norm(e2 - e1)
        found = []
        for hinge, tip in ((e1, e2), (e2, e1)):
            ax = (tip - hinge) / Lp
            perp = np.array([-ax[1], ax[0]])
            for s_ in (1, -1):
                gap = not any(wall_at(hinge + perp * s_ * Lp * t, .04) for t in (.35, .55, .75))
                jamb = wall_at(hinge + perp * s_ * Lp * 1.05, .14) and wall_at(hinge - perp * s_ * px(.12), .1)
                if gap and jamb:
                    found.append((hinge, tip, hinge + perp * s_ * Lp))
        if len(found) != 1:
            return None
        hinge, tip, closed = found[0]
        return dict(h=[round(float(v), 1) for v in hinge], c=[round(float(v), 1) for v in closed], o=[round(float(v), 1) for v in tip])
    door_list = []
    for e1, e2 in leaves:
        g_ = leaf_geom(e1, e2)
        if g_:
            mid = (np.array(g_['h']) + np.array(g_['c'])) / 2
            door_list.append(([int(mid[0]), int(mid[1]), 0, 0], g_))
    wall_polys_all = contours_to_polys(walls & cv2.dilate(foot, np.ones((5, 5), np.uint8)), 1.0, px(.08) ** 2)
    fur = raster((H, W), list(paths(p, L('furniture'))), R, ox, oy, 1)
    fur_t = raster((H, W), list(paths(p, L('furniture_tall'))), R, ox, oy, 1)
    win_segs = segs(list(paths(p, L('window'))), R, ox, oy, mpp)
    gla_segs = segs(list(paths(p, L('glass'))), R, ox, oy, mpp)
    out_units = []
    for i, u in enumerate(U):
        num = '%02d' % (i + 1)
        code = codes.get(num, num)
        mk = u['mask']
        inner = np.isin(rlab, u['rooms']).astype(np.uint8) * 255
        wpoly = contours_to_polys(walls3d & mk, 1.0, px(.08) ** 2)
        def pole(r):  # điểm giữa thoáng nhất của phòng (đặt camera)
            x, y, w, h, _a = rstat[r]
            dt = cv2.distanceTransform((rlab[y:y + h, x:x + w] == r).astype(np.uint8), cv2.DIST_L2, 3)
            iy, ix = np.unravel_index(int(np.argmax(dt)), dt.shape)
            return int(x + ix), int(y + iy)
        poles = {r: pole(r) for r in u['rooms']}
        furn = []
        for layer_mask, h in ((fur, .45), (fur_t, .9)):
            # nét nét đứt được xuất thành từng đoạn rời: nối lại bằng phép đóng 0,3 m, rồi lấp kín vùng bên trong
            fm = cv2.morphologyEx(layer_mask & inner, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.3), px(.3))))
            cs, _ = cv2.findContours(fm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cs:
                ar = cv2.contourArea(c) * mpp * mpp
                if ar < .12:
                    continue
                bx, by, bw, bh = cv2.boundingRect(c)
                hh = h
                if h < .5 and ar > 2.6 and min(bw, bh) * mpp > 1.3:
                    hh = .5   # giường
                (rcx, rcy), (rw, rh), ang = cv2.minAreaRect(c)
                if rw < rh:
                    rw, rh, ang = rh, rw, ang + 90
                M_ = cv2.moments(c)
                fx, fy = int(M_['m10'] / M_['m00']), int(M_['m01'] / M_['m00'])
                rid = int(rlab[min(H - 1, fy), min(W - 1, fx)])
                if rid not in poles:  # tâm khối rơi ra ngoài phòng: lấy phòng chứa nhiều điểm nhất của khối
                    cm = np.zeros(rlab.shape, np.uint8)
                    cv2.drawContours(cm, [c], -1, 1, -1)
                    ids, cnt = np.unique(rlab[cm > 0], return_counts=True)
                    ok = [(n_, int(i_)) for i_, n_ in zip(ids, cnt) if int(i_) in poles]
                    rid = max(ok)[1] if ok else 0
                furn.append(dict(h=hh, p=cv2.approxPolyDP(c, 1.5, True)[:, 0, :].tolist(),
                                 r=[round(rcx, 1), round(rcy, 1), round(rw * mpp, 2), round(rh * mpp, 2), round(ang, 1)],
                                 fill=round(cv2.contourArea(c) / max(1, rw * rh), 2),
                                 room=rooms[rid]['name'] if rid in rooms else '', rp=list(poles[rid]) if rid in poles else None))
        inside = lambda s: mk[min(H - 1, max(0, int((s[1] + s[3]) / 2))), min(W - 1, max(0, int((s[0] + s[2]) / 2)))] > 0
        rms = []
        for r in u['rooms']:
            vx, vy = poles[r]
            rm = cv2.dilate((rlab == r).astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.24), px(.24))))
            rcs, _ = cv2.findContours(rm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            rpoly = cv2.approxPolyDP(max(rcs, key=cv2.contourArea), 1.5, True)[:, 0, :].tolist() if rcs else []
            best_a, best_d = 0.0, -1
            for ang_ in np.linspace(0, 2 * math.pi, 24, endpoint=False):  # hướng nhìn thoáng nhất từ điểm đặt camera
                d_ = 0
                while d_ < px(15):
                    xx, yy = int(vx + math.cos(ang_) * d_), int(vy + math.sin(ang_) * d_)
                    if not (0 <= xx < W and 0 <= yy < H) or (rlab[yy, xx] != r and barrier[yy, xx]):
                        break
                    d_ += 2
                if d_ > best_d:
                    best_a, best_d = ang_, d_
            rms.append(dict(id=r, name=rooms[r]['name'], x=round(rooms[r].get('lx', rooms[r]['cx'])), y=round(rooms[r].get('ly', rooms[r]['cy'])),
                            vx=vx, vy=vy, va=round(best_a, 3), area=rooms[r]['area'], poly=rpoly))
        out_units.append(dict(code=code, num=num, poly=u['poly'], area=u['area'], rooms=rms,
                              vec=dict(walls=wpoly, win=[s for s in win_segs if inside(s)], glass=[s for s in gla_segs if inside(s)], furn=furn,
                                       doors=[g_ for d_, g_ in door_list if g_ and mk[min(H - 1, d_[1] + d_[3] // 2), min(W - 1, d_[0] + d_[2] // 2)] > 0])))
    # ranh khối nhà vẽ chung cho nhiều tầng: nếu lớn hơn hẳn diện tích sàn ghi trên bản vẽ (tầng giật cấp, sân thượng),
    # thu lại theo phần có căn + khu chung + lõi
    m_area = re.search(r'DIỆN TÍCH SÀN:\s*([\d.,]+)', p.get_text())
    floor_area = float(m_area.group(1).replace(',', '')) if m_area else None
    if floor_area and cv2.countNonZero(foot) * mpp * mpp > floor_area * 1.2:
        occ = np.zeros_like(foot)
        for u in U:
            occ |= u['mask']
        for r in rooms:
            if (r in common and rooms[r]['name']) or (r not in common and rooms[r]['area'] < 15 and not any(r in u_ for u_ in units)):
                occ[rlab == r] = 255
        k6 = cv2.getStructuringElement(cv2.MORPH_RECT, (px(6), px(6)))
        occ = cv2.morphologyEx(occ, cv2.MORPH_CLOSE, k6) & foot
        cs, _ = cv2.findContours(occ, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        foot = np.zeros_like(foot)
        cv2.drawContours(foot, [max(cs, key=cv2.contourArea)], -1, 255, -1)
        foot = cv2.dilate(foot, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.3), px(.3))))
        print('Ranh khối nhà thu theo diện tích sàn %.0f m² (đo được %.0f m²)' % (floor_area, cv2.countNonZero(foot) * mpp * mpp))
    fp = cv2.approxPolyDP(max(cv2.findContours(foot, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0], key=cv2.contourArea), px(.1), True)[:, 0, :].tolist()
    core = cv2.erode(foot, cv2.getStructuringElement(cv2.MORPH_RECT, (px(.8), px(.8))))
    core_p = cv2.approxPolyDP(max(cv2.findContours(core, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0], key=cv2.contourArea), px(.1), True)[:, 0, :].tolist()
    title = re.findall(r'MẶT BẰNG[^\n|]*', p.get_text())
    res = dict(source=os.path.basename(a.pdf), page=a.page, title=title[0].strip() if title else '', floors=floors_from_title(title[0]) if title else None,
               w=W, h=H, mPerPx=mpp, scale=a.scale, footprint=fp, core=core_p, units=out_units,
               common=[dict(name=rooms[r]['name'], area=rooms[r]['area']) for r in common], walls=wall_polys_all, doors_raw=doors,
               loose=[dict(id=r, name=rooms[r]['name'], area=rooms[r]['area'], x=round(rooms[r]['cx']), y=round(rooms[r]['cy']))
                      for r in rooms if r not in common and not any(r in u for u in units)])
    json.dump(res, open(os.path.join(a.out, 'floor.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('Trang %d "%s": %.1f x %.1f m, %d phòng, %d cửa, %d căn' % (a.page, res['title'], W * mpp, H * mpp, len(rooms), len(doors), len(out_units)))
    for u in out_units:
        print('  %s (mã %s): %.1f m², phòng %s' % (u['num'], u['code'], u['area'], ', '.join('%d:%s' % (r['id'], r['name'] or '?') for r in u['rooms'])))
    if res['loose']:
        print('Phòng chưa thuộc căn nào: ' + ', '.join('%d:%s %.0fm²' % (r['id'], r['name'] or '?', r['area']) for r in res['loose']))
    print('Khu chung: ' + ', '.join('%s %.0fm²' % (c['name'] or '(không tên)', c['area']) for c in res['common']))
    draw_preview(a.out)


def segs(items, R, ox, oy, mpp):
    out = []
    for x in items:
        for it in x['items']:
            pts = item_pts(it)
            for q1, q2 in zip(pts, pts[1:]):
                s = [(q1.x - ox) * R, (q1.y - oy) * R, (q2.x - ox) * R, (q2.y - oy) * R]
                if math.hypot(s[2] - s[0], s[3] - s[1]) * mpp > .3:
                    out.append([round(v, 1) for v in s])
    # gộp nét kép (2 nét song song của một ô kính) bằng cách bỏ nét gần trùng
    keep = []
    for s in sorted(out, key=lambda s: -math.hypot(s[2] - s[0], s[3] - s[1])):
        mx, my = (s[0] + s[2]) / 2, (s[1] + s[3]) / 2
        if not any(abs((k[0] + k[2]) / 2 - mx) < .25 / mpp and abs((k[1] + k[3]) / 2 - my) < .25 / mpp for k in keep):
            keep.append(s)
    return keep


def draw_preview(outdir):
    from PIL import Image, ImageDraw
    f = json.load(open(os.path.join(outdir, 'floor.json'), encoding='utf-8'))
    im = Image.new('RGBA', (f['w'], f['h']), (255, 255, 255, 255))
    pl = Image.open(os.path.join(outdir, 'plan.webp'))
    im.alpha_composite(pl)
    s = min(1.0, 1600 / max(im.size))
    im = im.resize((int(im.size[0] * s), int(im.size[1] * s))).convert('RGB')
    g = ImageDraw.Draw(im, 'RGBA')
    pal = [(31, 119, 180), (44, 160, 44), (148, 103, 189), (214, 39, 40), (255, 127, 14), (23, 190, 207), (140, 86, 75), (227, 119, 194)]
    for i, u in enumerate(f['units']):
        c = pal[i % len(pal)]
        g.polygon([(x * s, y * s) for x, y in u['poly']], fill=c + (60,), outline=c + (255,))
        xs = [q[0] for q in u['poly']]
        ys = [q[1] for q in u['poly']]
        cx, cy = sum(xs) / len(xs) * s, sum(ys) / len(ys) * s
        t = '%s  %.0fm2' % (u['code'], u['area'])
        g.rectangle([cx - 4 * len(t), cy - 9, cx + 4 * len(t), cy + 9], fill=(255, 255, 255, 230), outline=c + (255,))
        g.text((cx - 3 * len(t), cy - 6), t, fill=(0, 0, 0))
    for u in f['units']:
        for r in u['rooms']:
            t = str(r['id'])
            g.text((r['x'] * s - 3 * len(t), r['y'] * s + 8), t, fill=(200, 0, 60))
    for r in f.get('loose', []):
        t = str(r['id'])
        g.text((r['x'] * s - 3 * len(t), r['y'] * s), t, fill=(120, 120, 120))
    im.save(os.path.join(outdir, 'preview.png'))
    print('Ảnh kiểm tra: ' + os.path.join(outdir, 'preview.png'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('info'); s.add_argument('pdf'); s.add_argument('--json'); s.set_defaults(f=cmd_info)
    s = sp.add_parser('layers'); s.add_argument('pdf'); s.add_argument('--page', type=int, required=True); s.add_argument('--out', required=True); s.set_defaults(f=cmd_layers)
    s = sp.add_parser('extract'); s.add_argument('pdf'); s.add_argument('--map', required=True); s.add_argument('--page', type=int, required=True)
    s.add_argument('--out', required=True); s.add_argument('--scale', type=float, default=100); s.add_argument('--codes'); s.add_argument('--groups'); s.set_defaults(f=cmd_extract)
    s = sp.add_parser('preview'); s.add_argument('dir'); s.set_defaults(f=lambda a: draw_preview(a.dir))
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
