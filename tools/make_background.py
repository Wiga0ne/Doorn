"""
Doorn (Studio Wiga) - construction du fond du plugin a partir du visuel fourni.

- detoure la pedale (fond blanc de la photo),
- efface les reperes des potards (ils sont redessines et tournent dans le plugin),
- efface les inverseurs et les footswitches d'origine (remplaces par les rendus 3D
  et par le footswitch d'Echoflex) en reprenant la texture de la facade,
- corrige les inscriptions (« byprns » -> « bypass », « cq » -> « eq »),
- ajoute le nom « Doorn » et le logo Studio Wiga,
- pose la pedale sur un fond sombre dans le cadre 1520 x 1916 (= 2 x 760 x 958, cadrage Echoflex),
- calcule les calques d'eclairage de la facade par la LED (rouge et ambre).

Usage : python3 tools/make_background.py design/front.png ../echoflex/background.jpg .
"""
import sys, os, json, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC, ECHO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), 'assets')

# v1.1 : pedale agrandie au maximum dans la meme fenetre (hauteur limitante) :
# haut des jacks a ~6 px du bord, bas du boitier a ~8 px (l'ombre portee peut etre rognee)
S = 1.385           # echelle photo -> fond 2x (1.30 en v1.0)
SC = S / 1.30       # facteur d'agrandissement des commandes par rapport a la v1.0
TOP = 6.0 - 22.7 * S  # position de la ligne y = 300 de la photo dans le fond 2x
RIM_Y = 347         # bord superieur du boitier sur la photo (les jacks du dessus sont retires)
W2, H2 = 1520, 1916

def T(x, y):        # photo -> fond 2x
    return (760.0 + (x - 1025.0) * S, TOP + (y - 300.0) * S)

# ---------------------------------------------------------------- reperes (photo)
KNOBS = {'gain': (807, 549), 'level': (1242, 547), 'treble': (804, 849),
         'mids': (1026, 849), 'bass': (1241, 846)}
KNOB_R = 70
MINI = (1025.5, 551.5); MINI_R = 30
TOGGLES = {'eq': (811.5, 1090.5), 'mode': (1239.5, 1088.5)}
LED = (1028.5, 1335.5)
FOOT = {'boost': (833, 1516), 'bypass': (1223, 1516)}

A = np.asarray(Image.open(SRC).convert('RGB')).astype(np.float32)
H, W = A.shape[:2]
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)

def lum(a): return a.mean(-1)
def sat(a): return a.max(-1) - a.min(-1)

def bilinear(img, x, y):
    x = np.clip(x, 0, W - 2); y = np.clip(y, 0, H - 2)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)

# ---------------------------------------------------------------- detourage
d = np.abs(A - 247.0).max(-1)
m = (d > 14).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
m = (lab == 1 + np.argmax(st[1:, 4])).astype(np.uint8) * 255
ff = m.copy(); fm = np.zeros((H + 2, W + 2), np.uint8); cv2.floodFill(ff, fm, (0, 0), 128)
MASK = (ff != 128).astype(np.float32)
# jacks du dessus retires : la pedale commence au bord du boitier
# jacks d'origine du dessus retires (remplaces par les embases du kit Studio Wiga)
MASK[:RIM_Y] = 0
src_rim = A[RIM_Y:RIM_Y + 10, 975:1075].copy()
for xa, xb in ((768, 960), (1092, 1284)):
    for x in range(xa, xb):
        k = min(1.0, (x - xa) / 10.0, (xb - x) / 10.0)
        A[RIM_Y:RIM_Y + 10, x] = A[RIM_Y:RIM_Y + 10, x] * (1 - k) + src_rim[:, (x - xa) % 100] * k
MASK = cv2.GaussianBlur(cv2.erode(MASK, np.ones((3, 3), np.uint8)), (0, 0), 0.8)

# ---------------------------------------------------------------- 1. reperes des potards
def polar_fill(cx, cy, mask, rot_deg):
    """remplace les pixels du masque par la moyenne des pixels au meme rayon
    tournes de +/- rot_deg (le chapeau est de revolution : reflets identiques)."""
    ys, xs = np.where(mask)
    dx = xs - cx; dy = ys - cy
    out = np.zeros((len(xs), 3), np.float32); wsum = 0
    for k, sgn in enumerate((1, -1)):
        for f in (1.0, 1.35):
            a = math.radians(rot_deg * f * sgn)
            ca, sa = math.cos(a), math.sin(a)
            sx = cx + dx * ca - dy * sa; sy = cy + dx * sa + dy * ca
            out += bilinear(A, sx, sy); wsum += 1
    A[ys, xs] = out / wsum

def ring_fill(cx, cy, mask, rmax):
    """efface en interpolant, sur chaque cercle centre sur le potard, entre les angles
    voisins non masques (le reflet du chapeau varie doucement avec l'angle)."""
    NA = 1440
    th = np.linspace(-math.pi, math.pi, NA, endpoint=False)
    ys, xs = np.where(mask)
    rr = np.hypot(xs - cx, ys - cy); aa = np.arctan2(ys - cy, xs - cx)
    for r0 in range(0, int(rmax) + 2):
        sel = (rr >= r0 - 0.5) & (rr < r0 + 0.5)
        if not sel.any():
            continue
        r_ = max(r0, 0.5)
        px = cx + r_ * np.cos(th); py = cy + r_ * np.sin(th)
        prof = bilinear(A, px, py)
        mpx = np.clip(np.round(px).astype(int), 0, W - 1); mpy = np.clip(np.round(py).astype(int), 0, H - 1)
        bad = mask[mpy, mpx]
        if bad.all():
            continue
        good = np.where(~bad)[0]
        ext = np.concatenate([good - NA, good, good + NA])
        for c in range(3):
            vals = np.tile(prof[good, c], 3)
            prof[:, c] = np.interp(np.arange(NA), ext, vals)
        idx = ((aa[sel] + math.pi) / (2 * math.pi) * NA).astype(int) % NA
        A[ys[sel], xs[sel]] = prof[idx]

for name, (cx, cy) in KNOBS.items():
    r = np.hypot(XX - cx, YY - cy); ang = np.degrees(np.arctan2(XX - cx, -(YY - cy)))
    reg = (r > 4) & (r < 60) & (np.abs(ang) < 45)
    mk = reg & (lum(A) > 70)
    mk = cv2.dilate(mk.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & (r < 61) & (np.abs(ang) < 50)
    ring_fill(cx, cy, mk, 61)

# petit potard BOOST (chapeau fume, repere blanc a ~7 h 30)
cx, cy = MINI
r = np.hypot(XX - cx, YY - cy)
mk = (r < 27) & (lum(A) > 150)
mk = cv2.dilate(mk.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & (r < 28)
ring_fill(cx, cy, mk, 28)

# ---------------------------------------------------------------- 2. greffes de texture
def lap_blend(a, b, m, levels=5):
    """melange multi-echelle (pyramide de Laplace) : raccord invisible des basses frequences"""
    ga, gb, gm = [a], [b], [m]
    for _ in range(levels):
        ga.append(cv2.pyrDown(ga[-1])); gb.append(cv2.pyrDown(gb[-1])); gm.append(cv2.pyrDown(gm[-1]))
    out = ga[-1] * (1 - gm[-1][..., None]) + gb[-1] * gm[-1][..., None]
    for i in range(levels - 1, -1, -1):
        size = (ga[i].shape[1], ga[i].shape[0])
        la = ga[i] - cv2.pyrUp(ga[i + 1], dstsize=size)
        lb = gb[i] - cv2.pyrUp(gb[i + 1], dstsize=size)
        out = cv2.pyrUp(out, dstsize=size) + la * (1 - gm[i][..., None]) + lb * gm[i][..., None]
    return out


def transplant(dst, R, donor, op, feather=6):
    """reprend la texture de la facade d'une zone voisine (retournee) pour effacer un objet"""
    cx, cy = dst; dx, dy = donor
    n = 64 * int(math.ceil((R + feather + 24) / 64.0))      # multiple de 32 pour la pyramide
    patch = A[int(dy) - n:int(dy) + n, int(dx) - n:int(dx) + n].copy()
    if 'h' in op: patch = patch[:, ::-1]
    if 'v' in op: patch = patch[::-1]
    if 'r' in op: patch = np.ascontiguousarray(np.rot90(patch))
    yy, xx = np.mgrid[-n:n, -n:n].astype(np.float32)
    rr = np.hypot(xx + 0.5, yy + 0.5)
    al = np.clip((R + feather - rr) / feather, 0, 1).astype(np.float32)
    y0, x0 = int(cy) - n, int(cx) - n
    tgt = A[y0:y0 + 2 * n, x0:x0 + 2 * n].copy()
    hard = lap_blend(tgt, np.ascontiguousarray(patch), al)
    # au centre (sous l'objet efface) : la greffe telle quelle
    A[y0:y0 + 2 * n, x0:x0 + 2 * n] = hard


# footswitchs et inverseurs d'origine : pas d'effacement (aucune greffe de texture, donc aucune tache) ;
# l'hexagone du footswitch et la bague chromee de l'inverseur les recouvrent entierement

# ---------------------------------------------------------------- 3. inscriptions
KNOCK = np.array([9, 12, 24], np.float32)      # bleu nuit des reserves sous les inscriptions

def text_alpha(box):
    x0, y0, x1, y1 = box
    c = A[y0:y1, x0:x1]
    L = lum(c)
    return np.clip((L - 45) / (225 - 45), 0, 1) * (sat(c) < 70)

def erase(box, extra=3):
    x0, y0, x1, y1 = box
    sub = A[y0 - 8:y1 + 8, x0 - 8:x1 + 8]
    L = lum(sub)
    mk = ((L > 90) & (sat(sub) < 70)).astype(np.uint8)
    inner = np.zeros_like(mk); inner[8:-8, 8:-8] = 1
    mk = cv2.dilate(mk * inner, np.ones((2 * extra + 1, 2 * extra + 1), np.uint8))
    img = np.clip(sub, 0, 255).astype(np.uint8)
    fixed = cv2.inpaint(img, mk, 4, cv2.INPAINT_TELEA).astype(np.float32)
    A[y0 - 8:y1 + 8, x0 - 8:x1 + 8] = fixed

def paste_glyphs(src_box, dst_xy, scale=1.0):
    x0, y0, x1, y1 = src_box
    al = text_alpha(src_box)
    col = np.array([236, 236, 232], np.float32)
    if scale != 1.0:
        al = cv2.resize(al, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC).clip(0, 1)
    h, w = al.shape
    X0, Y0 = dst_xy
    t = A[Y0:Y0 + h, X0:X0 + w]
    A[Y0:Y0 + h, X0:X0 + w] = t * (1 - al[..., None]) + col * al[..., None]

# « byprns » -> « byp » + « ass » pris dans « bass » (meme corps, meme ligne de base)
erase((1216, 1360, 1260, 1395))
paste_glyphs((1229, 917, 1270, 950), (1217, 917 + 443))
# « cq » -> « eq » : e pris dans « level », ramene a la hauteur d'x de « eq »
erase((886, 1076, 899, 1101), extra=2)
paste_glyphs((1216, 637, 1232, 660), (885, 1077), scale=0.86)

# inscription « 9v » retiree (pas d'alimentation dans le plugin) ; jacks et OUT / IN gardes en haut
band = A[379:432, 955:1095]
bm = ((lum(band) > 95) & (sat(band) < 90)).astype(np.uint8)
bm = cv2.dilate(bm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
# fond local = moyenne normalisee des pixels voisins hors masque (suit le degrade de la facade)
keep = ((bm == 0) & (sat(band) < 40) & (lum(band) < 50)).astype(np.float32)
num = cv2.GaussianBlur(band * keep[..., None], (0, 0), 9)
den = cv2.GaussianBlur(keep, (0, 0), 9)[..., None] + 1e-4
local = num / den
rng = np.random.default_rng(5)
grain = cv2.GaussianBlur(rng.normal(0, 1, band.shape[:2]).astype(np.float32), (0, 0), 0.7) * 1.6
fill = local + grain[..., None]
soft = cv2.GaussianBlur(bm.astype(np.float32), (0, 0), 1.0)
A[379:432, 955:1095] = band * (1 - soft[..., None]) + fill * soft[..., None]

# ---------------------------------------------------------------- 4. nom et logo
def knockout(box, radius=16, soft=7):
    x0, y0, x1, y1 = box
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius, fill=255)
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(soft))).astype(np.float32) / 255
    # bords irreguliers comme les reserves du visuel
    noise = cv2.GaussianBlur(np.random.default_rng(3).random((H, W)).astype(np.float32), (0, 0), 3)
    m = np.clip((m - 0.5) * 3.2 + (noise - 0.5) * 1.4 + 0.5, 0, 1)
    A[:] = A * (1 - m[..., None]) + KNOCK * m[..., None]

FONT = os.path.join(ASSETS, 'Fondamento-Regular.ttf')

def contour(al, grow=3, soft=2.2, strength=0.88):
    """detourage : ombre sombre qui suit la forme des lettres (pas de cartouche)"""
    k = 2 * grow + 1
    m = cv2.dilate(al, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    m = cv2.GaussianBlur(m, (0, 0), soft) * strength
    A[:] = A * (1 - m[..., None]) + KNOCK * m[..., None]

TITLE_ALPHA = np.zeros((H, W), np.float32)

def draw_text(text, cx, cy, size, track=0, font=None, grow=3):
    f = ImageFont.truetype(font or FONT, size)
    tmp = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(tmp)
    widths = [dr.textlength(ch, font=f) for ch in text]
    tw = sum(widths) + track * (len(text) - 1)
    bb = dr.textbbox((0, 0), text, font=f)
    x = cx - tw / 2; y = cy - (bb[1] + bb[3]) / 2
    for ch, w_ in zip(text, widths):
        dr.text((x, y), ch, font=f, fill=255); x += w_ + track
    # graisse : le visuel a un trait assez gras
    al = np.asarray(tmp.filter(ImageFilter.MaxFilter(3))).astype(np.float32) / 255
    al = cv2.GaussianBlur(al, (0, 0), 0.6)
    col = np.array([236, 236, 236], np.float32)     # blanc neutre
    contour(al, grow=grow, soft=2.2)
    TITLE_ALPHA[:] = np.maximum(TITLE_ALPHA, al)
    A[:] = A * (1 - al[..., None]) + col * al[..., None]
    ys, xs = np.where(al > 0.1)
    return xs.min(), ys.min(), xs.max(), ys.max()

# mesure du titre pour la reserve
TITLE_FONT = os.path.join(ASSETS, 'AlegreyaSC-Regular.ttf')   # petites capitales a empattements, comme « THORN »
f = ImageFont.truetype(TITLE_FONT, 44)
tmpd = ImageDraw.Draw(Image.new('L', (10, 10)))
bb = tmpd.textbbox((0, 0), 'DOORN', font=f)
tw = bb[2] - bb[0] + 4 * 6
TITLE_C = (1028, 1549)      # comme « THORN » : entre les deux footswitchs, un peu sous leur centre
TITLE_BOX = draw_text('DOORN', TITLE_C[0], TITLE_C[1], 44, track=2, font=TITLE_FONT, grow=2)


# logo Studio Wiga sous les footswitches
logo = Image.open(os.path.join(ASSETS, 'logo_studio_wiga_blanc.png')).convert('RGBA')
LW = 172
logo = logo.resize((LW, round(logo.height * LW / logo.width)), Image.LANCZOS)
lx, ly = 1028 - LW // 2, 1650 - logo.height // 2
la = np.asarray(logo).astype(np.float32) / 255
lfull = np.zeros((H, W), np.float32); lfull[ly:ly + logo.height, lx:lx + LW] = la[..., 3]
contour(lfull, grow=3, soft=1.8)
reg = A[ly:ly + logo.height, lx:lx + LW]
A[ly:ly + logo.height, lx:lx + LW] = reg * (1 - la[..., 3:]) + la[..., :3] * 255 * la[..., 3:]

# ---------------------------------------------------------------- 5. mise en page dans le cadre
pedal = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8))
mask_img = Image.fromarray((MASK * 255).astype(np.uint8))
nw, nh = round(W * S), round(H * S)
ox, oy = T(0, 0)
pedal_s = pedal.resize((nw, nh), Image.LANCZOS)
mask_s = mask_img.resize((nw, nh), Image.LANCZOS)

# fond : noir bleute, texture de la facade tres assombrie et floue, vignette
canvas = np.zeros((H2, W2, 3), np.float32)
yy, xx = np.mgrid[0:H2, 0:W2].astype(np.float32)
base = np.array([10, 12, 19], np.float32)
canvas[:] = base
tex = np.asarray(pedal.crop((700, 400, 1350, 1600)).resize((W2, H2), Image.LANCZOS)
                 .filter(ImageFilter.GaussianBlur(26))).astype(np.float32)
tex = np.asarray(Image.fromarray(tex.astype(np.uint8)).transpose(Image.FLIP_LEFT_RIGHT)).astype(np.float32)
canvas += tex * 0.10
vig = np.clip(1.15 - 0.85 * (((xx - 760) / 900) ** 2 + ((yy - 958) / 1150) ** 2), 0.35, 1.0)
canvas *= vig[..., None]

# ombre portee de la pedale (lumiere en haut a gauche -> ombre en bas a droite)
sh = Image.new('L', (W2, H2), 0)
sh.paste(mask_s, (round(ox + 16), round(oy + 24)))
sh = np.asarray(sh.filter(ImageFilter.GaussianBlur(26))).astype(np.float32) / 255
canvas *= (1 - 0.72 * sh)[..., None]
sh2 = Image.new('L', (W2, H2), 0)
sh2.paste(mask_s, (round(ox + 4), round(oy + 6)))
sh2 = np.asarray(sh2.filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
canvas *= (1 - 0.6 * sh2)[..., None]

full = Image.new('RGB', (W2, H2)); full.paste(pedal_s, (round(ox), round(oy)))
fm_ = Image.new('L', (W2, H2), 0); fm_.paste(mask_s, (round(ox), round(oy)))
fa = np.asarray(fm_).astype(np.float32)[..., None] / 255
SIL = fa[..., 0].copy()             # silhouette (boitier + jacks) pour la couverture de la notice
canvas = canvas * (1 - fa) + np.asarray(full).astype(np.float32) * fa

# embases jack du kit Studio Wiga, sortant du dessus du boitier aux places d'origine (OUT a gauche, IN a droite)
JL = 196.0 * SC                              # longueur de l'embase dans le fond 2x
jk = Image.open(os.path.join(ASSETS, 'embase_jack_gauche_OUT.png')).convert('RGBA')
jk = jk.crop(jk.getbbox()).rotate(-90, expand=True)          # dome vers le haut
jk = jk.crop(jk.getbbox())
jk = jk.resize((round(JL), max(1, round(jk.height * JL / jk.width))), Image.LANCZOS)
ja = np.asarray(jk).astype(np.float32) / 255
rim2 = T(0, RIM_Y)[1]
for xc in (857, 1200):          # centres des inscriptions OUT / IN du visuel
    cx2 = T(xc, 0)[0]
    jx, jy = round(cx2 - jk.width / 2), round(rim2 - jk.height + 3)
    sm = np.asarray(Image.fromarray((ja[..., 3] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))).astype(np.float32) / 255
    canvas[jy + 4:jy + 4 + jk.height, jx + 6:jx + 6 + jk.width] *= (1 - 0.55 * sm)[..., None]
    reg = canvas[jy:jy + jk.height, jx:jx + jk.width]
    canvas[jy:jy + jk.height, jx:jx + jk.width] = reg * (1 - ja[..., 3:]) + ja[..., :3] * 255 * ja[..., 3:]
    SIL[jy:jy + jk.height, jx:jx + jk.width] = np.maximum(SIL[jy:jy + jk.height, jx:jx + jk.width], ja[..., 3])
Image.fromarray((SIL * 255).astype(np.uint8)).save(os.path.join(HERE, 'pedal_mask.png'))


# ---------------------------------------------------------------- 6. footswitches (photo Echoflex, rendu tools/controls_art.py)
_fs = Image.open(os.path.join(HERE, 'fs.png')).convert('RGBA')
_fs = _fs.resize((round(_fs.width * SC), round(_fs.height * SC)), Image.LANCZOS)
fs_sprite = np.asarray(_fs).astype(np.float32) / 255
for k, c in FOOT.items():
    cx, cy = T(*c)
    h_, w_ = fs_sprite.shape[:2]
    x0, y0 = round(cx - w_ / 2), round(cy - h_ / 2)
    al = fs_sprite[..., 3:]
    reg = canvas[y0:y0 + h_, x0:x0 + w_]
    canvas[y0:y0 + h_, x0:x0 + w_] = reg * (1 - al) + fs_sprite[..., :3] * 255 * al

bg = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
bg.save(os.path.join(OUT, 'background.jpg'), quality=93, subsampling=0)

# ---------------------------------------------------------------- 7. calques d'eclairage de la LED
lx2, ly2 = T(*LED)
RAD = int(round(240 * SC))
x0, y0 = round(lx2 - RAD), round(ly2 - RAD)
sub = canvas[y0:y0 + 2 * RAD, x0:x0 + 2 * RAD].copy()
gy, gx = np.mgrid[0:2 * RAD, 0:2 * RAD].astype(np.float32)
dd = np.hypot(gx + x0 - lx2, gy + y0 - ly2)

def lamb(h):          # source ponctuelle a la hauteur h au-dessus de la facade (loi cos / d^2)
    return (h * h / (h * h + dd * dd)) ** 1.5

I = 1.35 * lamb(16) + 0.32 * lamb(70) + 0.10 * lamb(170)
# le titre reste blanc neutre (pas de teinte de la LED)
ta = Image.fromarray((TITLE_ALPHA * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
tfull = Image.new('L', (W2, H2), 0); tfull.paste(ta, (round(ox), round(oy)))
tmask = np.asarray(tfull.filter(ImageFilter.MaxFilter(3))).astype(np.float32)[y0:y0 + 2 * RAD, x0:x0 + 2 * RAD] / 255
halo = 0.10 * lamb(26)
for name, col in (('glow_red', (1.00, 0.16, 0.07)), ('glow_amber', (1.00, 0.55, 0.12))):
    c = np.array(col, np.float32)
    lit = sub * (1 + I[..., None] * c * 2.4) + halo[..., None] * c * 255
    lit = lit * (1 - tmask[..., None]) + sub * tmask[..., None]
    # calque avec transparence : opaque seulement la ou la LED eclaire vraiment, retombe a 0 bien avant le bord
    # (sinon le carre du calque se voit quand la LED s'allume : leger decalage de reechantillonnage)
    edge = np.clip((RAD - dd) / (RAD * 0.35), 0, 1) ** 2
    a = np.clip((I + halo * 3.0) * 2.2, 0, 1) * edge
    a = np.where(tmask > 0, np.maximum(a, 0), a)
    rgba = np.dstack([np.clip(lit, 0, 255), a * 255]).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(os.path.join(OUT, name + '.png'), optimize=True)

# ---------------------------------------------------------------- 8. reperes pour le code (unites 760 x 958)
def U(p): x, y = T(*p); return [round(x / 2, 2), round(y / 2, 2)]
info = {
    'knobs': {k: U(v) for k, v in KNOBS.items()}, 'knobR': round(KNOB_R * S / 2, 2),
    'mini': U(MINI), 'miniR': round(MINI_R * S / 2, 2),
    'toggles': {k: U(v) for k, v in TOGGLES.items()},
    'led': U(LED),
    'foot': {k: U(v) for k, v in FOOT.items()}, 'footCirc': 124.0 / math.sqrt(3),
    'glowRect': [x0 / 2, y0 / 2, RAD, RAD], 'sc': SC,
    'title': U(TITLE_C),
}
json.dump(info, open(os.path.join(HERE, 'layout.json'), 'w'), indent=1)

# en-tete C++ genere : le plugin lit directement ces reperes
k = info['knobs']
def P2(p): return '{ %.2ff, %.2ff }' % (p[0], p[1])
with open(os.path.join(os.path.dirname(HERE), 'Layout.h'), 'w') as fo:
    fo.write('// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)\n#pragma once\n')
    fo.write('#include <juce_graphics/juce_graphics.h>\nnamespace layout\n{\n')
    fo.write('    const juce::Point<float> knobPos[6] = { %s, %s, %s, %s, %s, %s };\n' % (P2(k['gain']), P2(info['mini']), P2(k['level']), P2(k['treble']), P2(k['mids']), P2(k['bass'])))
    fo.write('    const float knobR = %.2ff, miniR = %.2ff, sc = %.4ff;\n' % (info['knobR'], info['miniR'], SC))
    fo.write('    const juce::Point<float> eqPos %s, modePos %s, ledPos %s;\n' % (P2(info['toggles']['eq']), P2(info['toggles']['mode']), P2(info['led'])))
    fo.write('    const juce::Point<float> boostPos %s, bypassPos %s;\n' % (P2(info['foot']['boost']), P2(info['foot']['bypass'])))
    g = info['glowRect']
    fo.write('    const juce::Rectangle<float> glowRect { %.2ff, %.2ff, %.2ff, %.2ff };\n}\n' % (g[0], g[1], g[2], g[3]))
print(json.dumps(info))
