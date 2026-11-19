"""Procedural PROTOTYPE illustration layers for the piano storybook (stand-ins for generated hand-painted art).

Outputs (src/assets/illustrations/):
  background.jpg   opaque olive garden (leaves, tiny flowers, vines, warm light)
  midground.png    RGBA foliage + dusty-pink blossoms framing the free areas (sits BEHIND the performer)
  foreground.png   RGBA corner tulips + soft out-of-focus leaves (sits IN FRONT of the performer, kept off the hands/keys)
  paper.png        grayscale paper/fibre texture for a soft-light overlay

Layers are 1200x2134 (10% margin each side) so parallax and the camera push-in never reveal an edge.
Frame coordinates (1080x1920) map to layer coordinates by +(PAD_X, PAD_Y).
Painterly feel comes from: two-tone leaf shading, darkened edges, rough polygon edges, low-frequency colour wash,
a wobble displacement and a brushy grain. It is still procedural; real generated art should replace these (see README).
Usage: python scripts/make_illustrations.py
"""
import os, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

W, H = 1080, 1920
PAD_X, PAD_Y = 60, 107
CW, CH = W + 2 * PAD_X, H + 2 * PAD_Y
SS = 2
OUT = 'src/assets/illustrations'
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- helpers
def smooth_noise(h, w, scale, rng):
    n = rng.normal(size=(max(2, h // scale + 2), max(2, w // scale + 2))).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
    n = cv2.GaussianBlur(n, (0, 0), scale * 0.35)
    return n / (np.abs(n).max() + 1e-6)


def fbm(h, w, rng, scales=(300, 110, 40), weights=(1.0, 0.6, 0.3)):
    out = np.zeros((h, w), np.float32)
    for s, wt in zip(scales, weights):
        out += wt * smooth_noise(h, w, s, rng)
    return out / sum(weights)


def jitter(c, rng, amt=7):
    return tuple(int(np.clip(v + rng.normal(0, amt), 0, 255)) for v in c)


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


class Canvas:
    """RGB painted with alpha-blended shapes + a separate coverage alpha (for transparent layers)."""

    def __init__(self, base_rgb=None):
        self.w, self.h = CW * SS, CH * SS
        self.rgb = Image.new('RGB', (self.w, self.h), (0, 0, 0)) if base_rgb is None else Image.fromarray(base_rgb)
        self.alpha = Image.new('L', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.rgb, 'RGBA')
        self.da = ImageDraw.Draw(self.alpha)

    def P(self, pts):
        return [(float(x + PAD_X) * SS, float(y + PAD_Y) * SS) for x, y in pts]

    def poly(self, pts, color, a=255, cover=True):
        p = self.P(pts)
        self.d.polygon(p, fill=(*color, a))
        if cover:
            self.da.polygon(p, fill=255)

    def line(self, pts, color, width, a=255, cover=True):
        p = self.P(pts)
        self.d.line(p, fill=(*color, a), width=max(1, int(width * SS)), joint='curve')
        if cover:
            self.da.line(p, fill=255, width=max(1, int(width * SS)), joint='curve')

    def circle(self, x, y, r, color, a=255, cover=True):
        p = self.P([(x - r, y - r), (x + r, y + r)])
        self.d.ellipse(p, fill=(*color, a))
        if cover:
            self.da.ellipse(p, fill=255)


def rot(pts, ang, ox, oy):
    c, s = math.cos(ang), math.sin(ang)
    R = np.array([[c, -s], [s, c]])
    return (np.asarray(pts) @ R.T) + [ox, oy]


def leaf(cv, x, y, length, width, ang, base, rng, alpha=255, bend=0.15, vein=True, light=None):
    """Painted leaf: base polygon, lighter half, darkened edge, midrib."""
    n = 16
    t = np.linspace(0, 1, n)
    mx = t * length
    my = bend * length * (t ** 2 - t) * rng.choice([-1, 1])
    w = width * np.sin(np.pi * t ** 0.8) ** 0.85
    left = np.stack([mx, my - w / 2], 1)
    right = np.stack([mx, my + w / 2], 1)
    jit = rng.normal(0, width * 0.025, (2 * n, 2))
    pts = rot(np.vstack([left, right[::-1]]) + jit, ang, x, y)
    mid = rot(np.stack([mx, my], 1), ang, x, y)
    cv.poly(pts, base, alpha)
    hi = light or mix(base, (225, 205, 140), 0.12)
    half = np.vstack([rot(left + jit[:n], ang, x, y), mid[::-1]])
    cv.poly(half, hi, int(alpha * 0.5), cover=False)
    dark = mix(base, (14, 18, 10), 0.35)
    cv.line(list(map(tuple, pts)) + [tuple(pts[0])], dark, 1.0, int(alpha * 0.28), cover=False)
    if vein:
        cv.line(list(map(tuple, mid)), mix(base, (240, 225, 170), 0.35), 1.1, int(alpha * 0.5), cover=False)


PINKS = [(192, 122, 120), (206, 142, 136), (216, 164, 150), (176, 106, 108)]
CREAM = (224, 206, 168)


def blossom(cv, x, y, r, rng, alpha=255, pink=None, rot0=None):
    pink = pink or PINKS[rng.integers(len(PINKS))]
    r0 = rng.uniform(0, 6.28) if rot0 is None else rot0
    for k in range(5):
        a = r0 + k * 2 * math.pi / 5
        px, py = x + math.cos(a) * r * 0.52, y + math.sin(a) * r * 0.52
        tt = np.linspace(0, 2 * math.pi, 22)
        ell = np.stack([np.cos(tt) * r * 0.5, np.sin(tt) * r * 0.42], 1) + rng.normal(0, r * 0.012, (22, 2))
        pts = rot(ell, a, px, py)
        cv.poly(pts, jitter(pink, rng, 5), alpha)
        cv.poly(rot(ell * 0.62, a, px - math.cos(a) * r * 0.05, py - math.sin(a) * r * 0.05), mix(pink, (245, 215, 205), 0.4), int(alpha * 0.5), cover=False)
        cv.line(list(map(tuple, pts)) + [tuple(pts[0])], mix(pink, (80, 30, 45), 0.35), 0.9, int(alpha * 0.4), cover=False)
    cv.circle(x, y, r * 0.18, CREAM, alpha)
    cv.circle(x, y, r * 0.08, (190, 140, 80), alpha, cover=False)
    for k in range(6):
        a = r0 + k * 1.05
        cv.circle(x + math.cos(a) * r * 0.26, y + math.sin(a) * r * 0.26, max(0.8, r * 0.035), (150, 100, 60), int(alpha * 0.8), cover=False)


def branch(cv, pts, width0, width1, color, rng):
    """Tapered woody branch through control points (Catmull-Rom-ish via splines)."""
    pts = np.asarray(pts, float)
    t = np.linspace(0, 1, len(pts))
    tt = np.linspace(0, 1, 90)
    xs = np.interp(tt, t, pts[:, 0]); ys = np.interp(tt, t, pts[:, 1])
    xs = ndi.gaussian_filter1d(xs, 6, mode='nearest'); ys = ndi.gaussian_filter1d(ys, 6, mode='nearest')
    for i in range(len(tt) - 1):
        w = width0 + (width1 - width0) * tt[i]
        cv.line([(xs[i], ys[i]), (xs[i + 1], ys[i + 1])], jitter(color, rng, 3), w, 255)
        cv.line([(xs[i] - w * 0.18, ys[i] - w * 0.18), (xs[i + 1] - w * 0.18, ys[i + 1] - w * 0.18)], mix(color, (150, 120, 80), 0.3), max(1, w * 0.3), 120, cover=False)
    return xs, ys


def tulip(cv, x, y, h, rng, alpha=255, scale=1.0):
    """Stylised painted tulip (stem base at x,y; bloom above), dusty pink, with long blade leaves."""
    stem_top = (x + rng.normal(0, h * 0.05), y - h)
    green = (84, 106, 56)
    cv.line([(x, y), ((x + stem_top[0]) / 2 + rng.normal(0, 8), y - h * 0.5), stem_top], green, 7 * scale, alpha)
    cv.line([(x - 2, y), ((x + stem_top[0]) / 2 - 2, y - h * 0.5), (stem_top[0] - 2, stem_top[1])], mix(green, (170, 190, 110), 0.3), 2 * scale, 110, cover=False)
    for sgn in (-1, 1):
        L = h * rng.uniform(0.7, 0.95)
        leaf(cv, x, y + 6, L, 34 * scale, -math.pi / 2 + sgn * rng.uniform(0.28, 0.5), jitter((74, 98, 54), rng, 5), rng, alpha, bend=0.35, vein=False)
    bx, by = stem_top
    pink = PINKS[rng.integers(len(PINKS))]
    r = h * 0.17
    # back petal, two front petals, centre petal highlight
    def petal(dx, ang, color, sc=1.0):
        tt = np.linspace(0, 2 * math.pi, 28)
        shape = np.stack([np.cos(tt) * r * 0.62 * sc, np.sin(tt) * r * 1.0 * sc], 1)
        shape[:, 1] += np.where(shape[:, 1] < 0, shape[:, 1] * 0.35, 0)
        pts = rot(shape + rng.normal(0, r * 0.012, shape.shape), ang, bx + dx, by - r * 0.7)
        cv.poly(pts, color, alpha)
        cv.poly(pts[: len(pts) // 2 + 2], mix(color, (245, 210, 205), 0.28), int(alpha * 0.45), cover=False)
        cv.line(list(map(tuple, pts)) + [tuple(pts[0])], mix(color, (90, 36, 52), 0.4), 1.4, int(alpha * 0.5), cover=False)
    petal(0, 0, mix(pink, (120, 60, 80), 0.25), 0.95)
    petal(-r * 0.38, -0.2, jitter(pink, rng, 5))
    petal(r * 0.38, 0.2, jitter(pink, rng, 5))
    petal(0, 0, mix(pink, (236, 190, 186), 0.3), 0.7)


def finish(cv, wobble=2.2, grain=0.10, seed=0, blur=0.0):
    """Common painterly finish: displacement wobble + brushy grain. Returns (rgb float 0..255, alpha float 0..1) at CWxCH."""
    rng = np.random.default_rng(seed)
    rgb = np.asarray(cv.rgb.resize((CW, CH), Image.LANCZOS)).astype(np.float32)
    al = np.asarray(cv.alpha.resize((CW, CH), Image.LANCZOS)).astype(np.float32) / 255.0
    if blur > 0:
        al = cv2.GaussianBlur(al, (0, 0), blur)
        rgb = cv2.GaussianBlur(rgb, (0, 0), blur)
    dx = fbm(CH, CW, rng, (140, 50), (1, 0.6)) * wobble
    dy = fbm(CH, CW, rng, (140, 50), (1, 0.6)) * wobble
    gx, gy = np.meshgrid(np.arange(CW, dtype=np.float32), np.arange(CH, dtype=np.float32))
    mapx, mapy = gx + dx, gy + dy
    rgb = cv2.remap(rgb, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    al = cv2.remap(al, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # brushy grain: anisotropic noise along a diagonal + fine speckle
    g1 = cv2.GaussianBlur(rng.normal(size=(CH, CW)).astype(np.float32), (0, 0), 1.0)
    g2 = cv2.GaussianBlur(rng.normal(size=(CH, CW)).astype(np.float32), (0, 0), sigmaX=9.0, sigmaY=1.4)
    g2 = ndi.rotate(g2, 24, reshape=False, mode='reflect')
    g = (0.6 * g1 / g1.std() + 0.5 * g2 / g2.std())
    rgb = np.clip(rgb * (1 + grain * g[..., None] * 0.9) + g[..., None] * 3.0, 0, 255)
    return rgb, al


# ---------------------------------------------------------------- layers
def make_background():
    rng = np.random.default_rng(11)
    y = np.linspace(0, 1, CH, dtype=np.float32)[:, None, None]
    top, mid, bot = np.array([24, 31, 20], np.float32), np.array([46, 58, 32], np.float32), np.array([32, 39, 24], np.float32)
    base = np.where(y < 0.45, top + (mid - top) * (y / 0.45), mid + (bot - mid) * ((y - 0.45) / 0.55))
    base = np.broadcast_to(base, (CH, CW, 3)).copy()
    base += fbm(CH, CW, rng, (520, 190, 60), (1.0, 0.8, 0.4))[..., None] * np.array([15, 19, 9], np.float32)
    # warm ambient light, upper right
    gx, gy = np.meshgrid(np.arange(CW, dtype=np.float32), np.arange(CH, dtype=np.float32))
    d = np.sqrt(((gx - 0.82 * CW) / (0.8 * CW)) ** 2 + ((gy - 0.10 * CH) / (0.5 * CH)) ** 2)
    glow = np.clip(1 - d, 0, 1) ** 1.6
    base += glow[..., None] * np.array([160, 108, 50], np.float32) * 0.52
    cv_ = Canvas(cv2.resize(np.clip(base, 0, 255).astype(np.uint8), (CW * SS, CH * SS), interpolation=cv2.INTER_CUBIC))
    cx_light, cy_light = 0.82 * CW - PAD_X, 0.10 * CH - PAD_Y

    def near_light(x, y):
        return math.exp(-(((x - cx_light) / 520) ** 2 + ((y - cy_light) / 520) ** 2))

    dark = [(24, 28, 15), (32, 38, 19), (42, 48, 24)]
    midc = [(50, 58, 28), (60, 70, 32), (72, 82, 38)]
    lite = [(104, 104, 48), (124, 112, 54), (140, 120, 60)]
    # big dark leaf masses (depth)
    for _ in range(170):
        x, y = rng.uniform(-60, W + 60), rng.uniform(-100, H + 100)
        leaf(cv_, x, y, rng.uniform(230, 400), rng.uniform(70, 125), rng.uniform(0, 6.28), jitter(dark[rng.integers(3)], rng, 4), rng, 240, vein=False)
    # mid leaves
    for _ in range(620):
        x, y = rng.uniform(-40, W + 40), rng.uniform(-80, H + 80)
        leaf(cv_, x, y, rng.uniform(70, 150), rng.uniform(26, 50), rng.uniform(0, 6.28), jitter(midc[rng.integers(3)], rng, 4), rng, 215)
    # warm-lit leaves, density follows the light
    placed = 0
    while placed < 120:
        x, y = rng.uniform(-40, W + 40), rng.uniform(-80, H * 0.6)
        if rng.random() < near_light(x, y) * 1.4:
            leaf(cv_, x, y, rng.uniform(50, 100), rng.uniform(20, 38), rng.uniform(0, 6.28), jitter(lite[rng.integers(3)], rng, 5), rng, 150)
            placed += 1
    # delicate vines with paired leaves
    for v in range(7):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        ang0 = rng.uniform(0, 6.28)
        pts = []
        for s in range(26):
            ang0 += rng.normal(0, 0.28)
            x0 += math.cos(ang0) * 34; y0 += math.sin(ang0) * 34
            pts.append((x0, y0))
        cv_.line(pts, (44, 54, 30), 2.4, 170, cover=False)
        for (px, py) in pts[::2]:
            for sgn in (-1, 1):
                leaf(cv_, px, py, 38, 15, math.atan2(py - pts[0][1], px - pts[0][0]) + sgn * 1.0, jitter((78, 98, 48), rng, 5), rng, 190, vein=False)
    # tiny scattered flowers, denser toward edges and the light
    for _ in range(190):
        x, y = rng.uniform(-30, W + 30), rng.uniform(-60, H + 60)
        edge = max(abs(x - W / 2) / (W / 2), abs(y - H / 2) / (H / 2))
        in_title = (280 < x < 1060) and (90 < y < 340)
        if (not in_title) and rng.random() < 0.30 + 0.60 * edge:
            blossom(cv_, x, y, rng.uniform(10, 21), rng, 190)
    rgb, _ = finish(cv_, wobble=2.0, grain=0.10, seed=3)
    # soft vignette
    gx2, gy2 = np.meshgrid(np.linspace(-1, 1, CW, dtype=np.float32), np.linspace(-1, 1, CH, dtype=np.float32))
    vig = 1 - 0.30 * np.clip((gx2 ** 2 * 0.8 + gy2 ** 2 * 0.55) - 0.25, 0, 1)
    rgb = np.clip(rgb * vig[..., None], 0, 255)
    gray = rgb.mean(axis=2, keepdims=True)
    rgb = gray + (rgb - gray) * 0.80                      # muted
    rgb = rgb * np.array([1.06, 1.0, 0.88], np.float32)   # warm cast
    rgb = np.clip(rgb * 0.92 + 10, 0, 255)                 # faded blacks
    Image.fromarray(rgb.astype(np.uint8)).save(f'{OUT}/background.jpg', quality=93)


def foliage_cluster(cv, x, y, rng, n, spread, base_cols, ang_bias=None):
    for _ in range(n):
        a = (rng.uniform(0, 6.28) if ang_bias is None else ang_bias + rng.normal(0, 0.9))
        leaf(cv, x + rng.normal(0, spread), y + rng.normal(0, spread), rng.uniform(70, 150), rng.uniform(30, 56), a,
             jitter(base_cols[rng.integers(len(base_cols))], rng, 6), rng, 245)


def make_midground():
    rng = np.random.default_rng(23)
    cv_ = Canvas()
    cols = [(66, 78, 38), (78, 90, 42), (90, 100, 48), (58, 68, 34)]
    woody = (66, 50, 36)
    # B1: right edge flowering branch sweeping up-left through the free area right of the head
    xs, ys = branch(cv_, [(1210, 640), (1120, 600), (1000, 540), (880, 500), (770, 470)], 14, 4, woody, rng)
    for i in range(6, 90, 7):
        foliage_cluster(cv_, xs[i], ys[i], rng, 3, 26, cols, ang_bias=-2.4)
    for i in (20, 38, 54, 70, 86):
        for _ in range(3):
            blossom(cv_, xs[i] + rng.normal(0, 24), ys[i] + rng.normal(0, 24), rng.uniform(34, 58), rng, 255)
    # B2: top-left corner, kept above y~110 so the title area stays calm
    xs2, ys2 = branch(cv_, [(-60, 40), (60, 80), (180, 92), (300, 62), (400, 20)], 12, 3, woody, rng)
    for i in range(4, 90, 6):
        foliage_cluster(cv_, xs2[i], ys2[i], rng, 3, 20, cols, ang_bias=0.6)
    for i in (26, 48, 70):
        for _ in range(2):
            blossom(cv_, xs2[i] + rng.normal(0, 20), ys2[i] + rng.normal(0, 20), rng.uniform(30, 48), rng, 255)
    # B3: top-right along the top edge, leaves hanging down
    xs3, ys3 = branch(cv_, [(1210, -30), (1100, 30), (980, 56), (860, 40), (760, 0)], 13, 3, woody, rng)
    for i in range(4, 90, 6):
        foliage_cluster(cv_, xs3[i], ys3[i], rng, 3, 24, cols, ang_bias=1.9)
    for i in (18, 40, 64, 84):
        for _ in range(2):
            blossom(cv_, xs3[i] + rng.normal(0, 22), ys3[i] + rng.normal(0, 22), rng.uniform(32, 54), rng, 255)
    # sparse small blossoms drifting on tiny twigs in the free right-middle area
    for _ in range(9):
        blossom(cv_, rng.uniform(760, 1100), rng.uniform(350, 640), rng.uniform(16, 26), rng, 235)
    rgb, al = finish(cv_, wobble=2.0, grain=0.07, seed=5)
    out = np.dstack([rgb, al * 255]).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(f'{OUT}/midground.png')


def make_foreground():
    rng = np.random.default_rng(37)
    cv_ = Canvas()
    # tulip cluster in the bottom-left corner (over the lower trouser leg only, off the hands and keys)
    for (x, y, h) in [(70, 1930, 330), (150, 1950, 270), (22, 1960, 230)]:
        tulip(cv_, x, y, h, rng, 255, 1.0)
    # a few extra leaf blades
    for _ in range(4):
        leaf(cv_, rng.uniform(0, 220), 1960, rng.uniform(190, 280), 30, -math.pi / 2 + rng.normal(0, 0.45), jitter((70, 94, 50), rng, 6), rng, 255, bend=0.35, vein=False)
    rgb, al = finish(cv_, wobble=1.8, grain=0.08, seed=7)
    out = np.dstack([rgb, al * 255]).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(f'{OUT}/foreground.png')
    # out-of-focus leaves framing the top corners (separate soft layer)
    cv2_ = Canvas()
    for (x, y, L, ang) in [(-40, -30, 420, 0.95), (-10, 40, 330, 0.55), (1130, -30, 430, 2.2), (1100, 50, 330, 2.6)]:
        leaf(cv_ if False else cv2_, x, y, L, 120, ang, jitter((34, 44, 26), rng, 3), rng, 240, vein=False)
    rgb2, al2 = finish(cv2_, wobble=1.5, grain=0.04, seed=9, blur=7)
    Image.fromarray(np.dstack([rgb2, al2 * 255]).astype(np.uint8), 'RGBA').save(f'{OUT}/foreground_blur.png')


def make_paper():
    rng = np.random.default_rng(51)
    base = 0.5 + 0.12 * fbm(H, W, rng, (220, 70, 22), (1, 0.7, 0.5))
    fibres = np.zeros((H, W), np.float32)
    for _ in range(1400):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        a = rng.uniform(0, math.pi)
        L = rng.uniform(10, 38)
        cv2.line(fibres, (int(x), int(y)), (int(x + math.cos(a) * L), int(y + math.sin(a) * L)), float(rng.uniform(-0.5, 0.5)), 1, cv2.LINE_AA)
    fibres = cv2.GaussianBlur(fibres, (0, 0), 0.7)
    fine = cv2.GaussianBlur(rng.normal(size=(H, W)).astype(np.float32), (0, 0), 0.8)
    tex = np.clip(base + 0.12 * fibres + 0.05 * fine / fine.std(), 0, 1)
    Image.fromarray((tex * 255).astype(np.uint8), 'L').save(f'{OUT}/paper.png')


if __name__ == '__main__':
    make_background(); print('background done')
    make_midground(); print('midground done')
    make_foreground(); print('foreground done')
    make_paper(); print('paper done')
