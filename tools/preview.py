"""
Doorn - apercu PNG de l'interface (meme dessin que le plugin : reperes de potards
redessines, inverseurs 3D, LED et calque d'eclairage de la facade).
Usage : python3 tools/preview.py assets out.png [gain boost level treble mids bass eq mode on boostOn]
"""
import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw

AS = sys.argv[1]; OUTP = sys.argv[2]
vals = [float(v) for v in sys.argv[3:]] if len(sys.argv) > 3 else [7.5, 7.5, 7.5, 10, 3.75, 7.5, 1, 2, 1, 0]
gain, boost, level, treble, mids, bass, eq, mode, on, bon = vals
L = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'layout.json')))
K = 2.0     # fond 2x

bg = Image.open(os.path.join(AS, 'background.jpg')).convert('RGBA')
ledLevel = 1.0 if on > 0.5 else 0.0
glow = 'glow_amber.png' if bon > 0.5 else 'glow_red.png'
if ledLevel > 0:
    g = Image.open(os.path.join(AS, glow)).convert('RGBA')
    gx, gy, rw, rh = L['glowRect']
    a_ = np.asarray(g.split()[3]).astype(np.float32) * ledLevel; g.putalpha(Image.fromarray(a_.astype(np.uint8)))
    bg.alpha_composite(g, (round(gx * K), round(gy * K)))

SS = 4
over = Image.new('RGBA', (bg.width * SS // 2, bg.height * SS // 2), (0, 0, 0, 0))
d = ImageDraw.Draw(over)
U = SS   # pixels par unite dans le calque

def rot(px, py, a):
    return (px * math.cos(a) - py * math.sin(a), px * math.sin(a) + py * math.cos(a))

def knob_arrow(c, R, v):
    a = math.radians(-150 + 300 * v / 10.0)
    pts = [(0, -0.757), (0.18, -0.27), (0, -0.36), (-0.18, -0.27)]
    p = [rot(x * R, y * R, a) for x, y in pts]
    # ombre tres legere sous la peinture puis peinture blanche (lumiere fixe en haut a gauche)
    br = int(232 + 18 * math.cos(a + math.radians(45)))
    d.polygon([((c[0] + x + 0.35) * U, (c[1] + y + 0.45) * U) for x, y in p], fill=(0, 0, 0, 110))
    d.polygon([((c[0] + x) * U, (c[1] + y) * U) for x, y in p], fill=(br, br, br - 4, 255))

for name, v in (('gain', gain), ('level', level), ('treble', treble), ('mids', mids), ('bass', bass)):
    knob_arrow(L['knobs'][name], L['knobR'], v)

# petit potard BOOST : barrette blanche sous le chapeau fume
c = L['mini']; a = math.radians(-150 + 300 * boost / 10.0)
r0, r1, wdt = 7.8, 18.6, 5.6
p0 = rot(0, -r0, a); p1 = rot(0, -r1, a)
d.line([((c[0] + p0[0]) * U, (c[1] + p0[1]) * U), ((c[0] + p1[0]) * U, (c[1] + p1[1]) * U)],
       fill=(225, 228, 226, 235), width=int(wdt * U))
for pp in (p0, p1):
    d.ellipse([((c[0] + pp[0]) - wdt / 2) * U, ((c[1] + pp[1]) - wdt / 2) * U,
               ((c[0] + pp[0]) + wdt / 2) * U, ((c[1] + pp[1]) + wdt / 2) * U], fill=(225, 228, 226, 235))

over = over.resize(bg.size, Image.LANCZOS)
bg.alpha_composite(over)

# inverseurs
strip = Image.open(os.path.join(AS, 'toggle_strip.png')).convert('RGBA')
n = strip.width
def toggle(c, frame):
    sz = round(192 * L['sc']); fr = strip.crop((0, frame * n, n, (frame + 1) * n)).resize((sz, sz), Image.LANCZOS)
    bg.alpha_composite(fr, (round(c[0] * K - sz / 2), round(c[1] * K - sz / 2)))
toggle(L['toggles']['eq'], 4 if eq > 0.5 else 0)        # levier en bas = ON
toggle(L['toggles']['mode'], {0: 0, 1: 2, 2: 4}[int(mode)])   # haut sdt-2 / milieu laerm / bas sdt-1

# lentille de la LED
if ledLevel > 0:
    lay = Image.new('RGBA', bg.size, (0, 0, 0, 0))
    cx, cy = L['led'][0] * K, L['led'][1] * K; r = 8.6 * K
    core, mid, deep = ((255, 236, 200), (255, 160, 40), (190, 80, 0)) if bon > 0.5 else ((255, 214, 200), (255, 38, 22), (140, 5, 4))
    yy, xx = np.mgrid[0:bg.height, 0:bg.width]
    dd = np.hypot(xx - (cx - r * 0.1), yy - (cy - r * 0.12)) / r
    t = np.clip(dd, 0, 1.05)
    col = np.zeros((bg.height, bg.width, 4), np.float32)
    for i in range(3):
        col[..., i] = np.interp(t, [0, 0.30, 0.62, 1.05], [core[i], (core[i] + mid[i]) / 2, mid[i], deep[i]])
    inside = np.hypot(xx - cx, yy - cy) <= r
    col[..., 3] = inside * 255
    lay = Image.fromarray(col.astype(np.uint8), 'RGBA')
    bg.alpha_composite(lay)
    sp = Image.new('RGBA', bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(sp).ellipse([cx - r * 0.62, cy - r * 0.70, cx - r * 0.02, cy - r * 0.20], fill=(255, 255, 255, 150))
    bg.alpha_composite(sp)

bg.convert('RGB').save(OUTP)
print(OUTP)
