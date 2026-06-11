"""Generate tactical-board style thumbnail banners for diagnosis cases.

No image-generation model is required: each banner is drawn deterministically
with Pillow so the look stays consistent across all 105 cases and matches the
site's navy/blue aesthetic. Banners carry NO text — the card UI overlays the
category badge, position badge and title itself.

Run:  python3 tools/generate_case_thumbnails.py
Out:  assets/case-thumbnails/<slug>.png  (880x460, 2x-supersampled)
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

# Render at 2x then downscale for clean anti-aliased edges.
W, H = 880, 460
SS = 2
CW, CH = W * SS, H * SS

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "case-thumbnails")

RGB = tuple[int, int, int]


def hx(s: str) -> RGB:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


@dataclass
class Theme:
    slug: str
    category: str  # for reference only, not drawn
    top: RGB
    bottom: RGB
    accent: RGB
    rival: RGB = hx("e2e8f0")
    motif: str = "pass"
    extras: dict = field(default_factory=dict)


THEMES = [
    Theme("pass-not-coming", "準備", hx("0b2447"), hx("19376d"), hx("5b8def"), motif="pass"),
    Theme("stops-after-receiving", "距離感", hx("0d1b3e"), hx("1b3a7a"), hx("6aa3ff"), motif="first_touch"),
    Theme("trap-too-big", "重心", hx("06303a"), hx("0f5560"), hx("29c2a8"), motif="control"),
    Theme("beaten-on-defense", "判断", hx("0a1730"), hx("14284f"), hx("4f7fd6"), rival=hx("ff6b6b"), motif="defense"),
    Theme("weak-shot", "身体操作", hx("101a33"), hx("233a63"), hx("7aa0e0"), motif="shot"),
]


def lerp(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def gradient(top: RGB, bottom: RGB) -> Image.Image:
    """Diagonal-ish vertical gradient base."""
    base = Image.new("RGB", (1, CH))
    px = base.load()
    for y in range(CH):
        px[0, y] = lerp(top, bottom, y / (CH - 1))
    return base.resize((CW, CH))


def overlay() -> Image.Image:
    return Image.new("RGBA", (CW, CH), (0, 0, 0, 0))


def rgba(c: RGB, a: int) -> tuple[int, int, int, int]:
    return (c[0], c[1], c[2], a)


def draw_pitch(d: ImageDraw.ImageDraw) -> None:
    """Subtle tactical-board markings in low-opacity white."""
    line = rgba((255, 255, 255), 26)
    lw = 3 * SS
    # outer touch line inset
    m = 26 * SS
    d.rounded_rectangle([m, m, CW - m, CH - m], radius=10 * SS, outline=line, width=lw)
    # halfway line
    d.line([(CW // 2, m), (CW // 2, CH - m)], fill=line, width=lw)
    # centre circle
    r = 64 * SS
    d.ellipse([CW // 2 - r, CH // 2 - r, CW // 2 + r, CH // 2 + r], outline=line, width=lw)


def soft_pill(img: Image.Image, accent: RGB) -> None:
    """Translucent rounded highlight echoing the site's existing card style."""
    pill = overlay()
    pd = ImageDraw.Draw(pill)
    pad = 60 * SS
    pd.rounded_rectangle(
        [pad, pad, CW - pad, CH - pad],
        radius=80 * SS,
        fill=rgba((255, 255, 255), 10),
    )
    img.alpha_composite(pill)
    # accent glow blob, top-right
    blob = overlay()
    bd = ImageDraw.Draw(blob)
    cx, cy, r = int(CW * 0.82), int(CH * 0.26), 150 * SS
    bd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgba(accent, 36))
    img.alpha_composite(blob)


def marker(d: ImageDraw.ImageDraw, x: float, y: float, color: RGB, r: int = 16) -> None:
    r *= SS
    d.ellipse([x - r, y - r, x + r, y + r], fill=rgba((255, 255, 255), 235))
    ir = int(r * 0.66)
    d.ellipse([x - ir, y - ir, x + ir, y + ir], fill=rgba(color, 255))


def ball(d: ImageDraw.ImageDraw, x: float, y: float, r: int = 18) -> None:
    r *= SS
    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255), outline=(30, 41, 59), width=SS)
    # simplified pentagon pattern
    pr = r * 0.42
    d.regular_polygon((x, y, pr), n_sides=5, rotation=-90, fill=(30, 41, 59))
    for ang in range(-90, 270, 72):
        rad = math.radians(ang)
        px, py = x + math.cos(rad) * r * 0.72, y + math.sin(rad) * r * 0.72
        d.regular_polygon((px, py, pr * 0.55), n_sides=5, rotation=ang + 90, fill=(30, 41, 59))


def arrow(d: ImageDraw.ImageDraw, p0, p1, color: RGB, width: int = 7, head: int = 22, dashed: bool = False) -> None:
    width *= SS
    head *= SS
    x0, y0 = p0
    x1, y1 = p1
    ang = math.atan2(y1 - y0, x1 - x0)
    shaft_x = x1 - math.cos(ang) * head
    shaft_y = y1 - math.sin(ang) * head
    if dashed:
        total = math.hypot(shaft_x - x0, shaft_y - y0)
        seg = 16 * SS
        n = max(1, int(total // seg))
        for i in range(0, n, 2):
            a = i / n
            b = min((i + 1) / n, 1.0)
            d.line(
                [(x0 + (shaft_x - x0) * a, y0 + (shaft_y - y0) * a),
                 (x0 + (shaft_x - x0) * b, y0 + (shaft_y - y0) * b)],
                fill=rgba(color, 255), width=width,
            )
    else:
        d.line([(x0, y0), (shaft_x, shaft_y)], fill=rgba(color, 255), width=width)
    # arrowhead
    left = (x1 - math.cos(ang - 0.5) * head, y1 - math.sin(ang - 0.5) * head)
    right = (x1 - math.cos(ang + 0.5) * head, y1 - math.sin(ang + 0.5) * head)
    d.polygon([(x1, y1), left, right], fill=rgba(color, 255))


def goal(d: ImageDraw.ImageDraw, x: float, color: RGB) -> None:
    """Goal frame near the right edge."""
    top, bot = int(CH * 0.34), int(CH * 0.66)
    depth = 26 * SS
    lw = 5 * SS
    c = rgba((255, 255, 255), 230)
    d.line([(x, top), (x, bot)], fill=c, width=lw)
    d.line([(x, top), (x + depth, top - 6 * SS)], fill=c, width=lw)
    d.line([(x, bot), (x + depth, bot + 6 * SS)], fill=c, width=lw)
    d.line([(x + depth, top - 6 * SS), (x + depth, bot + 6 * SS)], fill=c, width=lw)


def draw_motif(d: ImageDraw.ImageDraw, t: Theme) -> None:
    cx, cy = CW / 2, CH / 2
    if t.motif == "pass":
        # passer -> open space pass lane, with a covered teammate
        ball(d, CW * 0.26, CH * 0.62)
        marker(d, CW * 0.26, CH * 0.62, t.accent)        # passer
        marker(d, CW * 0.62, CH * 0.34, t.accent)        # receiver moving to space
        marker(d, CW * 0.55, CH * 0.66, t.rival)         # marker/opponent
        arrow(d, (CW * 0.30, CH * 0.60), (CW * 0.60, CH * 0.38), t.accent)
        arrow(d, (CW * 0.50, CH * 0.30), (CW * 0.62, CH * 0.34), t.accent, width=5, head=16, dashed=True)
    elif t.motif == "first_touch":
        # receive then push ball forward into space
        ball(d, CW * 0.34, CH * 0.52)
        marker(d, CW * 0.30, CH * 0.52, t.accent)
        arrow(d, (CW * 0.38, CH * 0.52), (CW * 0.66, CH * 0.40), t.accent)
        arrow(d, (CW * 0.38, CH * 0.56), (CW * 0.60, CH * 0.66), t.accent, width=5, head=16, dashed=True)
    elif t.motif == "control":
        # tight control radius around the ball
        ball(d, cx, cy)
        for rr, al in ((42, 70), (66, 40)):
            r = rr * SS
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=rgba(t.accent, al), width=4 * SS)
        marker(d, cx - 70 * SS, cy + 50 * SS, t.accent)
        arrow(d, (cx - 56 * SS, cy + 38 * SS), (cx - 22 * SS, cy + 12 * SS), t.accent, width=5, head=16)
    elif t.motif == "defense":
        # attacker dribbles past defender (being beaten)
        ball(d, CW * 0.34, CH * 0.50)
        marker(d, CW * 0.30, CH * 0.50, t.rival)         # attacker
        marker(d, CW * 0.52, CH * 0.52, t.accent)        # defender
        # curved dribble path going past defender
        pts = [(CW * 0.37, CH * 0.50), (CW * 0.50, CH * 0.30), (CW * 0.66, CH * 0.40)]
        for i in range(len(pts) - 1):
            arrow(d, pts[i], pts[i + 1], t.rival, width=6, head=18 if i == len(pts) - 2 else 0)
        arrow(d, (CW * 0.50, CH * 0.52), (CW * 0.42, CH * 0.50), t.accent, width=5, head=16, dashed=True)
    elif t.motif == "shot":
        goal(d, CW * 0.84, t.accent)
        ball(d, CW * 0.30, CH * 0.56)
        marker(d, CW * 0.24, CH * 0.58, t.accent)
        # power arc toward goal
        arrow(d, (CW * 0.34, CH * 0.55), (CW * 0.80, CH * 0.50), t.accent, width=9, head=26)


def render(t: Theme) -> Image.Image:
    img = gradient(t.top, t.bottom).convert("RGBA")
    soft_pill(img, t.accent)
    d = ImageDraw.Draw(img, "RGBA")
    draw_pitch(d)
    draw_motif(d, t)
    # subtle vignette
    vig = overlay()
    ImageDraw.Draw(vig).rounded_rectangle([0, 0, CW, CH], radius=2, outline=rgba((0, 0, 0), 60), width=20 * SS)
    img.alpha_composite(vig)
    return img.resize((W, H), Image.LANCZOS).convert("RGB")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for t in THEMES:
        out = os.path.join(OUT_DIR, f"{t.slug}.png")
        render(t).save(out, "PNG", optimize=True)
        print("wrote", os.path.relpath(out, os.path.join(os.path.dirname(__file__), "..")))


if __name__ == "__main__":
    main()
