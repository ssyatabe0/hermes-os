"""Generate brand-consistent thumbnail banners for diagnosis cases (v2).

Design system ("サッカー診断センター" brand):
* Base: the brand's deep navy (logo / primary buttons) on every banner, with
  only a subtle per-category tint so the five cards read as one series.
* Accent: brand gold (logo ring / heading underline) marks the *correct*
  play; white is neutral; a muted red marks the opponent where needed.
* Composition: large cropped centre-circle geometry + fine dot grid for an
  analytical "diagnosis" look; focal motif sits centre-right because the
  category chip overlays the top-left of the card UI.
* Banners carry no text — the card UI supplies badges and title.

Run:  python3 tools/generate_case_thumbnails.py
Out:  assets/case-thumbnails/<slug>.png  (880x460)
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter

W, H = 880, 460
SS = 2  # supersample factor
CW, CH = W * SS, H * SS

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "case-thumbnails")

RGB = tuple[int, int, int]


def hx(s: str) -> RGB:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# --- brand palette ----------------------------------------------------------

NAVY_TOP = hx("0D1836")      # deep navy shared by all banners
GOLD = hx("E3AC3F")          # brand accent (logo ring / underline)
GOLD_SOFT = hx("F2C46B")
BALL_DARK = hx("1E2A4A")
OPPONENT = hx("E2695F")      # muted red, opponents only
LINE_W = (255, 255, 255)


@dataclass(frozen=True)
class Theme:
    slug: str
    category: str          # reference only, never drawn
    tint: RGB              # gradient end (subtle per-category shift)
    motif: str


THEMES = [
    Theme("pass-not-coming", "準備", hx("1E3C8C"), "pass"),
    Theme("stops-after-receiving", "距離感", hx("24478F"), "first_touch"),
    Theme("trap-too-big", "重心", hx("0F5E66"), "control"),
    Theme("beaten-on-defense", "判断", hx("1B3157"), "defense"),
    Theme("weak-shot", "身体操作", hx("2A3F73"), "shot"),
]


# --- low-level helpers ------------------------------------------------------

def lerp(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def rgba(c: RGB, a: int) -> tuple[int, int, int, int]:
    return (c[0], c[1], c[2], a)


def layer() -> Image.Image:
    return Image.new("RGBA", (CW, CH), (0, 0, 0, 0))


def diag_gradient(c0: RGB, c1: RGB) -> Image.Image:
    """Top-left navy -> bottom-right tint, built small then upscaled."""
    gw, gh = 110, 58
    img = Image.new("RGB", (gw, gh))
    px = img.load()
    for y in range(gh):
        for x in range(gw):
            t = (x / (gw - 1) * 0.55 + y / (gh - 1) * 0.45)
            px[x, y] = lerp(c0, c1, t)
    return img.resize((CW, CH), Image.BICUBIC)


def glow(img: Image.Image, xy: tuple[float, float], r: float, color: RGB, alpha: int, blur: float) -> None:
    g = layer()
    d = ImageDraw.Draw(g)
    x, y = xy
    d.ellipse([x - r, y - r, x + r, y + r], fill=rgba(color, alpha))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))


def shadow(img: Image.Image, xy: tuple[float, float], rx: float, ry: float, alpha: int = 90) -> None:
    s = layer()
    d = ImageDraw.Draw(s)
    x, y = xy
    d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=(0, 0, 0, alpha))
    img.alpha_composite(s.filter(ImageFilter.GaussianBlur(10 * SS)))


def dot_grid(img: Image.Image) -> None:
    d = ImageDraw.Draw(img)
    step = 40 * SS
    r = 1.6 * SS
    for row, y in enumerate(range(step // 2, CH, step)):
        off = step // 2 if row % 2 else 0
        for x in range(step // 2 + off, CW, step):
            d.ellipse([x - r, y - r, x + r, y + r], fill=rgba(LINE_W, 14))


def pitch_geometry(img: Image.Image, cx: float, cy: float) -> None:
    """Large cropped centre circle + halfway line, low-opacity white."""
    d = ImageDraw.Draw(img)
    lw = 3 * SS
    for radius, alpha in ((CH * 0.52, 34), (CH * 0.78, 20)):
        d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                  outline=rgba(LINE_W, alpha), width=lw)
    d.line([(cx, 0), (cx, CH)], fill=rgba(LINE_W, 24), width=lw)
    d.ellipse([cx - 6 * SS, cy - 6 * SS, cx + 6 * SS, cy + 6 * SS], fill=rgba(LINE_W, 40))


def vignette(img: Image.Image) -> None:
    gw, gh = 110, 58
    mask = Image.new("L", (gw, gh))
    px = mask.load()
    for y in range(gh):
        for x in range(gw):
            nx, ny = x / (gw - 1) - 0.5, y / (gh - 1) - 0.5
            dist = math.hypot(nx * 2, ny * 2)
            px[x, y] = int(max(0.0, dist - 0.72) / 0.62 * 120)
    dark = Image.new("RGBA", (CW, CH), (5, 9, 24, 255))
    dark.putalpha(mask.resize((CW, CH), Image.BICUBIC))
    img.alpha_composite(dark)


# --- drawable elements ------------------------------------------------------

def bezier(points: list[tuple[float, float]], n: int = 48) -> list[tuple[float, float]]:
    """Sample a quadratic/cubic bezier polyline."""
    out = []
    for i in range(n + 1):
        t = i / n
        pts = points
        while len(pts) > 1:
            pts = [(pts[j][0] + (pts[j + 1][0] - pts[j][0]) * t,
                    pts[j][1] + (pts[j + 1][1] - pts[j][1]) * t) for j in range(len(pts) - 1)]
        out.append(pts[0])
    return out


def path_arrow(img: Image.Image, pts: list[tuple[float, float]], color: RGB,
               width: float = 8, head: float = 24, dashed: bool = False,
               glow_alpha: int = 70) -> None:
    """Arrow along a polyline with round caps, arrowhead, soft glow."""
    width *= SS
    head *= SS
    # soft glow underneath
    if glow_alpha:
        g = layer()
        gd = ImageDraw.Draw(g)
        gd.line(pts, fill=rgba(color, glow_alpha), width=int(width * 2.4), joint="curve")
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(8 * SS)))
    d = ImageDraw.Draw(img)
    # shaft (stop short of tip so the head stays crisp)
    (x1, y1), (x0, y0) = pts[-1], pts[-2]
    ang = math.atan2(y1 - y0, x1 - x0)
    tip_back = (x1 - math.cos(ang) * head * 0.9, y1 - math.sin(ang) * head * 0.9)
    shaft = pts[:-1] + [tip_back]
    if dashed:
        for i in range(len(shaft) - 1):
            seg = shaft[i], shaft[i + 1]
            length = math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])
            n = max(1, int(length / (18 * SS)))
            for k in range(0, n, 2):
                a, b = k / n, min((k + 1) / n, 1.0)
                d.line([(seg[0][0] + (seg[1][0] - seg[0][0]) * a, seg[0][1] + (seg[1][1] - seg[0][1]) * a),
                        (seg[0][0] + (seg[1][0] - seg[0][0]) * b, seg[0][1] + (seg[1][1] - seg[0][1]) * b)],
                       fill=rgba(color, 255), width=int(width))
    else:
        d.line(shaft, fill=rgba(color, 255), width=int(width), joint="curve")
        sx, sy = shaft[0]
        d.ellipse([sx - width / 2, sy - width / 2, sx + width / 2, sy + width / 2], fill=rgba(color, 255))
    left = (x1 - math.cos(ang - 0.46) * head, y1 - math.sin(ang - 0.46) * head)
    right = (x1 - math.cos(ang + 0.46) * head, y1 - math.sin(ang + 0.46) * head)
    d.polygon([(x1, y1), left, right], fill=rgba(color, 255))


def ball(img: Image.Image, x: float, y: float, r: float = 26) -> None:
    r *= SS
    shadow(img, (x + 4 * SS, y + r * 0.85), r * 1.05, r * 0.38, 110)
    d = ImageDraw.Draw(img)
    d.ellipse([x - r, y - r, x + r, y + r], fill=hx("F8FAFC"), outline=BALL_DARK, width=SS)
    pr = r * 0.40
    d.regular_polygon((x, y, pr), n_sides=5, rotation=-90, fill=BALL_DARK)
    for ang in range(-90, 270, 72):
        rad = math.radians(ang)
        px, py = x + math.cos(rad) * r * 0.74, y + math.sin(rad) * r * 0.74
        d.regular_polygon((px, py, pr * 0.52), n_sides=5, rotation=ang + 90, fill=BALL_DARK)
    # top-left sheen
    glow(img, (x - r * 0.4, y - r * 0.45), r * 0.5, (255, 255, 255), 70, 6 * SS)


def marker(img: Image.Image, x: float, y: float, color: RGB, r: float = 15) -> None:
    r *= SS
    shadow(img, (x + 2 * SS, y + r * 0.9), r, r * 0.35, 90)
    d = ImageDraw.Draw(img)
    d.ellipse([x - r, y - r, x + r, y + r], fill=rgba((255, 255, 255), 245))
    ir = r * 0.68
    d.ellipse([x - ir, y - ir, x + ir, y + ir], fill=rgba(color, 255))


def goal_with_net(img: Image.Image, x: float) -> None:
    d = ImageDraw.Draw(img)
    top, bot = CH * 0.30, CH * 0.72
    depth = 44 * SS
    lw = 6 * SS
    back_top, back_bot = top - 10 * SS, bot + 10 * SS
    # net grid (behind frame)
    net = rgba(LINE_W, 60)
    for i in range(1, 7):
        yy = back_top + (back_bot - back_top) * i / 7
        d.line([(x, top + (bot - top) * i / 7), (x + depth, yy)], fill=net, width=SS)
    for i in range(1, 5):
        xx = x + depth * i / 5
        d.line([(xx, back_top + 2 * SS), (xx, back_bot - 2 * SS)], fill=net, width=SS)
    # frame
    frame = rgba((255, 255, 255), 235)
    d.line([(x, top), (x, bot)], fill=frame, width=lw)
    d.line([(x, top), (x + depth, back_top)], fill=frame, width=lw)
    d.line([(x, bot), (x + depth, back_bot)], fill=frame, width=lw)
    d.line([(x + depth, back_top), (x + depth, back_bot)], fill=frame, width=lw)


# --- motifs -----------------------------------------------------------------
# Focal action sits centre/right; top-left stays quiet for the category chip.

def motif_pass(img: Image.Image) -> None:
    passer = (CW * 0.24, CH * 0.72)
    receiver = (CW * 0.74, CH * 0.32)
    opponent = (CW * 0.52, CH * 0.62)
    glow(img, receiver, 90 * SS, GOLD_SOFT, 34, 30 * SS)   # the open space
    path_arrow(img, bezier([passer, (CW * 0.5, CH * 0.42), (CW * 0.68, CH * 0.36)]), GOLD)
    path_arrow(img, [(CW * 0.60, CH * 0.14), (receiver[0] - 8 * SS, receiver[1] - 14 * SS)],
               GOLD_SOFT, width=5, head=16, dashed=True, glow_alpha=0)
    marker(img, *opponent, OPPONENT)
    marker(img, *receiver, GOLD)
    ball(img, passer[0] + 30 * SS, passer[1] + 6 * SS, r=22)
    marker(img, *passer, hx("3E63C4"))


def motif_first_touch(img: Image.Image) -> None:
    recv = (CW * 0.34, CH * 0.58)
    target = (CW * 0.78, CH * 0.38)
    glow(img, target, 80 * SS, GOLD_SOFT, 36, 28 * SS)
    path_arrow(img, bezier([(recv[0] + 26 * SS, recv[1] - 4 * SS), (CW * 0.58, CH * 0.44), target]), GOLD, width=9, head=26)
    path_arrow(img, [(recv[0] + 10 * SS, recv[1] + 22 * SS), (CW * 0.60, CH * 0.72)], hx("7E9BD8"), width=5, head=16, dashed=True, glow_alpha=0)
    ball(img, recv[0] + 26 * SS, recv[1] - 4 * SS, r=24)
    marker(img, *recv, hx("3E63C4"))


def motif_control(img: Image.Image) -> None:
    c = (CW * 0.56, CH * 0.50)
    glow(img, c, 120 * SS, hx("2BB3A3"), 40, 40 * SS)
    d = ImageDraw.Draw(img)
    for rr, alpha, wdt in ((70, 200, 4), (108, 90, 3), (150, 45, 3)):
        r = rr * SS
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=rgba(GOLD, alpha), width=wdt * SS)
    ball(img, *c, r=28)
    player = (CW * 0.30, CH * 0.68)
    path_arrow(img, [(player[0] + 20 * SS, player[1] - 14 * SS), (c[0] - 60 * SS, c[1] + 30 * SS)], GOLD, width=6, head=18, glow_alpha=40)
    marker(img, *player, hx("2BB3A3"))


def motif_defense(img: Image.Image) -> None:
    attacker = (CW * 0.30, CH * 0.56)
    defender = (CW * 0.56, CH * 0.52)
    # attacker's dribble slipping past (the problem, muted red)
    path_arrow(img, bezier([(attacker[0] + 26 * SS, attacker[1] - 6 * SS),
                            (CW * 0.50, CH * 0.26), (CW * 0.76, CH * 0.36)]), OPPONENT, width=7, head=20, glow_alpha=50)
    # correct jockey position: step toward the dribble lane (gold)
    path_arrow(img, [(defender[0], defender[1] - 10 * SS), (CW * 0.50, CH * 0.32)], GOLD, width=6, head=18, dashed=True, glow_alpha=0)
    ball(img, attacker[0] + 28 * SS, attacker[1] - 4 * SS, r=22)
    marker(img, *attacker, OPPONENT)
    marker(img, *defender, hx("3E63C4"))


def motif_shot(img: Image.Image) -> None:
    goal_with_net(img, CW * 0.80)
    b = (CW * 0.30, CH * 0.58)
    target = (CW * 0.79, CH * 0.44)
    # motion streaks behind the ball
    d = ImageDraw.Draw(img)
    for i, off in enumerate((26, 44, 62)):
        d.line([(b[0] - off * SS - 26 * SS, b[1] + (i - 1) * 12 * SS),
                (b[0] - off * SS, b[1] + (i - 1) * 12 * SS)],
               fill=rgba(LINE_W, 90 - i * 25), width=4 * SS)
    path_arrow(img, bezier([(b[0] + 30 * SS, b[1] - 4 * SS), (CW * 0.56, CH * 0.42), target]), GOLD, width=10, head=30)
    glow(img, target, 60 * SS, GOLD_SOFT, 50, 22 * SS)
    ball(img, *b, r=26)
    marker(img, b[0] - 44 * SS, b[1] + 26 * SS, hx("3E63C4"))


MOTIFS = {
    "pass": motif_pass,
    "first_touch": motif_first_touch,
    "control": motif_control,
    "defense": motif_defense,
    "shot": motif_shot,
}


# --- render -----------------------------------------------------------------

def render(t: Theme) -> Image.Image:
    img = diag_gradient(NAVY_TOP, t.tint).convert("RGBA")
    dot_grid(img)
    pitch_geometry(img, CW * 0.58, CH * 0.50)
    glow(img, (CW * 0.88, CH * 0.12), 130 * SS, t.tint, 90, 60 * SS)  # ambient corner light
    MOTIFS[t.motif](img)
    vignette(img)
    return img.resize((W, H), Image.LANCZOS).convert("RGB")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for t in THEMES:
        out = os.path.join(OUT_DIR, f"{t.slug}.png")
        render(t).save(out, "PNG", optimize=True)
        print("wrote", os.path.relpath(out, os.path.join(os.path.dirname(__file__), "..")))


if __name__ == "__main__":
    main()
