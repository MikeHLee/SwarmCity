#!/usr/bin/env python3
"""
Generate dot_swarm animated GIF logo and sprite icon.

    pip install pillow numpy
    python generate_logo.py

Outputs:
    logo.gif  – animated swarm (60 frames, 15fps)
    icon.png  – 256×256 pixelated sprite icon
"""

import math
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ─── CANVAS & ANIMATION ───────────────────────────────────────────────────────
W, H        = 700, 280      # pixels
N_FRAMES    = 90
FRAME_MS    = 66            # ~15 fps
WARMUP      = 400           # physics warm-up steps before recording
SEED        = 7

# ─── HEX GRID ─────────────────────────────────────────────────────────────────
HEX_SIZE    = 13            # circumradius in px (flat-top hexagons)

# ─── BOIDS ────────────────────────────────────────────────────────────────────
N_BOIDS     = 72
DOT_R       = 4             # dot radius px
MAX_SPEED   = 2.8
MAX_FORCE   = 0.09
SEP_R       = 28
ALI_R       = 55
COH_R       = 80
SEP_W       = 1.6
ALI_W       = 1.0
COH_W       = 1.0
CTR_W       = 0.018         # pull toward canvas centre

# ─── COLORS ───────────────────────────────────────────────────────────────────
BG          = (255, 255, 255)
HEX_TEXT    = (10,  10,  10)      # filled hex for letters
HEX_OUTLINE = (210, 210, 210)     # empty hex border
HEX_FILL    = (255, 255, 255)     # empty hex fill
DOT_COLOR   = (15,  15,  15)      # boid dot


# ═══════════════════════════════════════════════════════════════════════════════
# HEX GEOMETRY
# ═══════════════════════════════════════════════════════════════════════════════

def flat_hex_corners(cx, cy, r):
    """6 corners of a flat-top hexagon centred at (cx, cy) with circumradius r."""
    return [
        (cx + r * math.cos(math.radians(60 * i)),
         cy + r * math.sin(math.radians(60 * i)))
        for i in range(6)
    ]


def build_hex_grid(w, h, size):
    """Return list of (cx, cy) covering canvas with flat-top hexagons."""
    col_step = size * 1.5            # horizontal advance per column
    row_step = size * math.sqrt(3)   # vertical advance per row
    centers  = []
    col = 0
    x   = size
    while x < w + size:
        row    = 0
        y_off  = (row_step / 2) if col % 2 else 0
        y      = y_off - row_step / 2
        while y < h + size:
            centers.append((x, y))
            y   += row_step
            row += 1
        x   += col_step
        col += 1
    return centers


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT → HEX MASK
# ═══════════════════════════════════════════════════════════════════════════════

def _load_font(size):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def make_text_mask(text, w, h, hex_size):
    """Render `text` and return greyscale PIL image (dark = letter pixel)."""
    font_size = int(hex_size * 4.8)
    font      = _load_font(font_size)

    probe  = Image.new("L", (1, 1))
    d      = ImageDraw.Draw(probe)
    bbox   = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Centre text, with a slight upward nudge for visual balance
    tx = (w - tw) // 2 - bbox[0]
    ty = (h - th) // 2 - bbox[1] - int(hex_size * 0.5)

    mask = Image.new("L", (w, h), 255)
    ImageDraw.Draw(mask).text((tx, ty), text, fill=0, font=font)
    return mask


# ═══════════════════════════════════════════════════════════════════════════════
# BOID PHYSICS
# ═══════════════════════════════════════════════════════════════════════════════

class Boid:
    def __init__(self, x, y):
        angle     = random.uniform(0, 2 * math.pi)
        speed     = random.uniform(1.2, MAX_SPEED)
        self.pos  = np.array([x, y], dtype=float)
        self.vel  = np.array([math.cos(angle) * speed,
                               math.sin(angle) * speed], dtype=float)
        self.acc  = np.zeros(2)

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _limit(v, mag):
        n = np.linalg.norm(v)
        return v / n * mag if n > mag and n > 0 else v

    def _steer(self, desired):
        n = np.linalg.norm(desired)
        if n > 0:
            desired = desired / n * MAX_SPEED
        return self._limit(desired - self.vel, MAX_FORCE)

    # ── flocking ────────────────────────────────────────────────────────────

    def flock(self, others):
        sep = ali = coh = np.zeros(2)
        sc = ac = cc = 0

        for o in others:
            if o is self:
                continue
            d   = np.linalg.norm(self.pos - o.pos)
            dv  = self.pos - o.pos
            if 0 < d < SEP_R:
                sep += dv / (d * d); sc += 1
            if 0 < d < ALI_R:
                ali += o.vel;        ac += 1
            if 0 < d < COH_R:
                coh += o.pos;        cc += 1

        force = np.zeros(2)
        if sc: force += self._steer(sep / sc) * SEP_W
        if ac: force += self._steer(ali / ac) * ALI_W
        if cc: force += self._steer(coh / cc - self.pos) * COH_W

        # Gentle centre attraction
        force += (np.array([W / 2, H / 2]) - self.pos) * CTR_W

        self.acc = force

    def update(self):
        self.vel  = self._limit(self.vel + self.acc, MAX_SPEED)
        self.pos += self.vel
        self.pos[0] %= W       # wrap horizontally
        self.pos[1] %= H       # wrap vertically
        self.acc  = np.zeros(2)


# ═══════════════════════════════════════════════════════════════════════════════
# RENDERING
# ═══════════════════════════════════════════════════════════════════════════════

def render_frame(boids, hex_centers, dark_set):
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    for i, (cx, cy) in enumerate(hex_centers):
        pts = flat_hex_corners(cx, cy, HEX_SIZE - 1.2)
        if i in dark_set:
            draw.polygon(pts, fill=HEX_TEXT)
        else:
            draw.polygon(pts, fill=HEX_FILL, outline=HEX_OUTLINE)

    for b in boids:
        x, y = b.pos
        draw.ellipse([x - DOT_R, y - DOT_R, x + DOT_R, y + DOT_R],
                     fill=DOT_COLOR)

    return img


# ═══════════════════════════════════════════════════════════════════════════════
# SPRITE ICON  (pixel-art hex face, 256 × 256)
# ═══════════════════════════════════════════════════════════════════════════════

def make_icon(frames, idx=None):
    """
    Build a 256×256 sprite icon.
    Uses a specific frame of the swarm scaled + a hard-coded hex-face overlay.
    """
    SZ      = 256
    ISIZE   = 18        # hex size for icon grid
    IBG     = (255, 255, 255)
    IDARK   = (10,  10,  10)
    IGRAY   = (180, 180, 180)

    icon = Image.new("RGB", (SZ, SZ), IBG)
    draw = ImageDraw.Draw(icon)

    # ── hex grid for icon ──
    icx = build_hex_grid(SZ, SZ, ISIZE)

    # ── simple hex-face design (row, col offsets from centre) ──
    # We use axial coords: each filled = True means "dark hex"
    # Design a robot-bee face: oval outline, two hex eyes, dot-mouth
    cx_ctr = SZ / 2
    cy_ctr = SZ / 2

    col_step = ISIZE * 1.5
    row_step = ISIZE * math.sqrt(3)

    def hex_center(col, row):
        x = col * col_step
        y = row * row_step + (row_step / 2 if col % 2 else 0)
        return (x, y)

    # Collect all icon hex centers with their grid coords
    icon_centers = []
    col = 0
    x   = ISIZE
    while x < SZ + ISIZE:
        row   = 0
        y_off = (row_step / 2) if col % 2 else 0
        y     = y_off - row_step / 2
        while y < SZ + ISIZE:
            icon_centers.append((col, row, x, y))
            y   += row_step
            row += 1
        x   += col_step
        col += 1

    # Find col/row of approximate centre
    best_dist = 1e9
    mid_col = mid_row = 0
    for (c, r, px, py) in icon_centers:
        d = (px - cx_ctr)**2 + (py - cy_ctr)**2
        if d < best_dist:
            best_dist = d
            mid_col, mid_row = c, r

    # ── face definition (dc=col offset, dr=row offset, dark?) ──
    # Oval body
    face_dark = set()

    # Oval outline – 7 wide, 9 tall (approx)
    body_coords = [
        (-2, -4), (-1, -4), (0, -4), (1, -4),
        (-3, -3), (2, -3),
        (-3, -2), (2, -2),
        (-4, -1), (3, -1),
        (-4, 0),  (3, 0),
        (-4, 1),  (3, 1),
        (-3, 2),  (2, 2),
        (-3, 3),  (2, 3),
        (-2, 4),  (-1, 4), (0, 4), (1, 4),
    ]
    for dc, dr in body_coords:
        face_dark.add((mid_col + dc, mid_row + dr))

    # Eyes (two filled clusters)
    for dc, dr in [(-2, -1), (-2, 0), (-1, -1)]:   # left eye
        face_dark.add((mid_col + dc, mid_row + dr))
    for dc, dr in [(1, -1), (2, -1), (1, 0)]:       # right eye
        face_dark.add((mid_col + dc, mid_row + dr))

    # Antennae
    for dc, dr in [(-1, -6), (0, -5), (1, -6)]:
        face_dark.add((mid_col + dc, mid_row + dr))

    # Mouth (hex smile)
    for dc, dr in [(-2, 2), (-1, 3), (0, 3), (1, 3), (2, 2)]:
        face_dark.add((mid_col + dc, mid_row + dr))

    # Wings (light gray)
    wing_gray = set()
    for dc, dr in [(-5, -3), (-6, -2), (-6, -1), (-5, -2),
                    (4, -3),  (5, -2),  (5, -1),  (4, -2)]:
        wing_gray.add((mid_col + dc, mid_row + dr))

    # ── render ──
    for (c, r, px, py) in icon_centers:
        pts = flat_hex_corners(px, py, ISIZE - 1.5)
        key = (c, r)
        if key in face_dark:
            draw.polygon(pts, fill=IDARK)
        elif key in wing_gray:
            draw.polygon(pts, fill=IGRAY, outline=(120, 120, 120))
        else:
            draw.polygon(pts, fill=IBG, outline=(220, 220, 220))

    return icon


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    random.seed(SEED)
    np.random.seed(SEED)

    print("Building hex grid…")
    hex_centers = build_hex_grid(W, H, HEX_SIZE)

    print("Rendering text mask…")
    mask     = make_text_mask("DOT SWARM", W, H, HEX_SIZE)
    mask_arr = np.array(mask)

    dark_set = set()
    for i, (cx, cy) in enumerate(hex_centers):
        ix, iy = int(cx), int(cy)
        if 0 <= ix < W and 0 <= iy < H and mask_arr[iy, ix] < 128:
            dark_set.add(i)

    print(f"  {len(hex_centers)} hex cells, {len(dark_set)} text cells")

    print("Spawning boids…")
    boids = [Boid(random.uniform(0, W), random.uniform(0, H))
             for _ in range(N_BOIDS)]

    print(f"Warm-up ({WARMUP} steps)…")
    for _ in range(WARMUP):
        for b in boids: b.flock(boids)
        for b in boids: b.update()

    print(f"Recording {N_FRAMES} frames…")
    frames = []
    for fi in range(N_FRAMES):
        for b in boids: b.flock(boids)
        for b in boids: b.update()
        frames.append(render_frame(boids, hex_centers, dark_set))
        if fi % 15 == 0:
            print(f"  {fi}/{N_FRAMES}")

    # ── save GIF ────────────────────────────────────────────────────────────
    out_gif = "logo.gif"
    print(f"Saving {out_gif}…")
    # Convert to palette mode for smaller GIF
    pal_frames = [f.convert("P", palette=Image.ADAPTIVE, colors=16)
                  for f in frames]
    pal_frames[0].save(
        out_gif,
        save_all=True,
        append_images=pal_frames[1:],
        optimize=True,
        duration=FRAME_MS,
        loop=0,
        disposal=2,
    )

    # ── save static icon ────────────────────────────────────────────────────
    print("Building sprite icon…")
    icon = make_icon(frames)
    icon.save("icon.png")
    print("Saved icon.png")

    # ── also update docs/logo.png with a nice static frame ──────────────────
    mid_frame = frames[N_FRAMES // 3]
    mid_frame.save("docs/logo.png")
    print("Updated docs/logo.png (static mid-frame)")

    print("\nDone! Files written:")
    print("  logo.gif   – animated swarm logo")
    print("  icon.png   – 256×256 sprite icon")
    print("  docs/logo.png – static preview frame")


if __name__ == "__main__":
    try:
        import numpy   # noqa
        from PIL import Image   # noqa
    except ImportError:
        print("Missing deps. Run:  pip install pillow numpy")
        sys.exit(1)
    main()
