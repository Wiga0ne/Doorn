# DOORN : rendu physique (champ de hauteurs + eclairage) des commandes mobiles, repris de Crycat v1.3.0
#   Lumiere principale : en haut a gauche ; chaque position est rendue avec la MEME lumiere (jamais de miroir).
#   Sorties (images 2x, repere 760 x 958 du plugin) :
#     toggle_strip.png : inverseur a levier, 5 positions empilees (haut, intermediaire, centre, intermediaire, bas)
#     tools/fs.png     : footswitch d'ECHOFLEX (photo reelle), detoure sur son hexagone, ombres comprises
#                        (incruste dans le fond par make_background.py)
import os, math
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AS, SSAA = 2, 3
PX = AS * SSAA

L = np.array([-0.46, -0.62, 0.64]); L /= np.linalg.norm(L)
V = np.array([0.0, 0.0, 1.0])
H = (L + V) / np.linalg.norm(L + V)

# ------------------------------------------------------------------ outils
class Canvas:
    def __init__(self, w_u, h_u, cx_u, cy_u):
        self.W, self.H = round(w_u * PX), round(h_u * PX)
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float64)
        self.x = (xx + 0.5) / PX - cx_u          # repère local en unités, origine sur l'axe de la commande
        self.y = (yy + 0.5) / PX - cy_u
        self.h = np.zeros((self.H, self.W))      # hauteur (unités)
        self.mat = np.zeros((self.H, self.W), np.int32)   # 0 = façade (transparente), sinon id de matière
        self.extra = {}

    def put(self, hgt, mask, mat_id):
        """ pose une pièce : elle ne remplace que là où elle est plus haute """
        m = mask & (hgt > self.h - 1e-9)
        self.h[m] = hgt[m]; self.mat[m] = mat_id
        return m

def normals(c, hmap):
    gy, gx = np.gradient(hmap, 1.0 / PX)
    n = np.dstack([-gx, -gy, np.ones_like(hmap)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)

def soft_shadow(c, samples=10, spread=0.10, max_u=40.0):
    """ ombre douce par lancer de rayons dans le champ de hauteurs (vers la lumière, plusieurs directions) """
    hmap = c.h
    vis = np.zeros_like(hmap)
    rng = np.random.default_rng(1)
    step = 0.5 / PX * 2
    nsteps = int(max_u / step)
    for s in range(samples):
        d = L + rng.normal(0, spread, 3) * np.array([1, 1, 0.5]); d /= np.linalg.norm(d)
        horiz = math.hypot(d[0], d[1]); tanE = d[2] / max(horiz, 1e-6)
        dx, dy = d[0] / horiz, d[1] / horiz
        occl = np.zeros_like(hmap, bool)
        for k in range(1, nsteps):
            t = k * step
            sx, sy = int(round(dx * t * PX)), int(round(dy * t * PX))
            if abs(sx) >= c.W or abs(sy) >= c.H: break
            sh = np.full_like(hmap, -1.0)
            ys0, ys1 = max(0, -sy), min(c.H, c.H - sy); xs0, xs1 = max(0, -sx), min(c.W, c.W - sx)
            sh[ys0:ys1, xs0:xs1] = hmap[ys0 + sy:ys1 + sy, xs0 + sx:xs1 + sx]
            occl |= sh > hmap + t * tanE + 0.05
        vis += ~occl
    return vis / samples

def env_chrome(n, gloss=1.0):
    """ métal poli : environnement de studio (boîte à lumière en haut à gauche, sol sombre) lu par le vecteur réfléchi """
    nz = n[..., 2]
    r = np.dstack([2 * nz * n[..., 0], 2 * nz * n[..., 1], 2 * nz * nz - 1])
    # direction de la boîte à lumière principale
    k = np.clip((r @ L), -1, 1)
    sky = 0.5 - 0.5 * r[..., 1]                          # haut de l'image = ciel clair
    base = 40 + 120 * np.clip(sky, 0, 1) ** 1.6
    box = 210 * np.clip((k - 0.55) / 0.45, 0, 1) ** (1.5 / gloss)
    rim = 40 * np.clip(-r[..., 0] * 0.6 - r[..., 1] * 0.3, 0, 1)    # petite boîte d'appoint
    return base + box + rim

def shade(c, n, vis, tint, kind, rough=0.35, amb=0.18, led=None):
    """ kind : 'chrome' (miroir), 'satin' (nickel brossé), 'dark' (zamak sombre) """
    ndl = np.clip(n @ L, 0, 1) * (0.25 + 0.75 * vis)
    ndh = np.clip(n @ H, 0, 1)
    shin = 12 + 220 * (1 - rough) ** 2
    spec = ndh ** shin * (0.35 + 0.65 * vis)
    if kind == "chrome":
        col = env_chrome(n) * (0.55 + 0.45 * vis) + 255 * spec * 0.9
        col = col[..., None] * np.asarray(tint)
    elif kind == "satin":
        e = env_chrome(n, gloss=0.6)
        col = (0.45 * e + 150 * ndl + 30 * amb)[..., None] * np.asarray(tint) + (210 * spec)[..., None]
    else:
        col = (60 * ndl + 25 * amb)[..., None] * np.asarray(tint) + (90 * spec)[..., None]
    if led is not None:                                   # lumière ambre de la LED (point lumineux bas, à droite)
        lp, lcol, lpow = led
        dxl = lp[0] - c.x; dyl = lp[1] - c.y; dzl = lp[2] - c.h
        d2 = dxl ** 2 + dyl ** 2 + dzl ** 2
        ldir = np.dstack([dxl, dyl, dzl]) / np.sqrt(d2)[..., None]
        ndl2 = np.clip((n * ldir).sum(2), 0, 1)
        hl = ldir + V; hl /= np.linalg.norm(hl, axis=2, keepdims=True)
        sp2 = np.clip((n * hl).sum(2), 0, 1) ** shin
        e = lpow / d2
        col = col + (e * (0.5 * ndl2 + 2.5 * sp2))[..., None] * np.asarray(lcol)
    return col

def _finish_unused(c, rgb, shadow_on_panel, out, size_px):
    """ sprite RGBA : pièce opaque + ombre portée sur la façade (noire semi-transparente) ; réduction anti-crénelée """
    obj = (c.mat > 0).astype(np.float64)
    obj = cv2.GaussianBlur(obj, (0, 0), 0.35 * SSAA)
    alpha = np.clip(obj + shadow_on_panel * (1 - obj), 0, 1)
    rgbp = rgb * obj[..., None]                          # couleur prémultipliée (l'ombre est noire)
    rgba = np.dstack([rgbp, alpha * 255])
    # réduction en espace prémultiplié
    small = cv2.resize(rgba, size_px, interpolation=cv2.INTER_AREA)
    a = small[..., 3:4] / 255.0
    col = np.where(a > 1e-4, small[..., :3] / np.maximum(a, 1e-4), 0)
    img = np.dstack([np.clip(col, 0, 255), np.clip(small[..., 3], 0, 255)]).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(ROOT, out))

def panel_shadow(c, vis_panel, amount=0.62):
    # là où il n'y a pas de pièce : ombre = 1 - visibilité de la lumière, adoucie, + ombre de contact (occlusion ambiante)
    sh = (1 - vis_panel) * amount
    occ = cv2.GaussianBlur((c.mat > 0).astype(np.float64), (0, 0), 1.6 * PX) * 0.35
    return np.clip(sh + occ, 0, 0.85) * (c.mat == 0)

def hexagon_r(x, y, inr, pointy=True):
    """ « rayon » d'hexagone (distance normalisée à la manière d'un cercle : hex = inr quand la valeur vaut inr) """
    a = np.arctan2(y, x) + (math.pi / 2 if pointy else 0)
    return np.hypot(x, y) * np.cos(((a + math.pi / 6) % (math.pi / 3)) - math.pi / 6)


# ------------------------------------------------------------------ footswitch : celui d'ECHOFLEX (photo reelle)
EF_PTS = [(1.7, -56.7), (51.7, -26.7), (51.7, 31.7), (5.0, 58.3), (-48.3, 30.0), (-49.3, -26.7)]   # hexagone (unités Echoflex)
EF_CENTROID = (1.5, 1.5)
EF_FLATS = 100.5                       # largeur entre plats (unités Echoflex)
FS_FLATS = 124.0                       # largeur entre plats sur Doorn : couvre entierement la bague du design
FS_K = FS_FLATS / EF_FLATS
FS_W = 200.0                           # sprite carre (unites Doorn), ombre comprise

def footswitch_echoflex(led_on):
    src = np.asarray(Image.open(os.path.join(ROOT, "assets", "echoflex_footswitch_source.png")).convert("RGB")).astype(np.float64)
    n = round(FS_W * AS)                       # taille du sprite (px, 2x)
    sc = FS_K * AS / 2.0                       # px source -> px sprite
    # source recentrée sur le centroïde de l'hexagone, mise à l'échelle (Lanczos)
    M = np.float32([[sc, 0, n / 2 - (150 + 2 * EF_CENTROID[0]) * sc], [0, sc, n / 2 - (150 + 2 * EF_CENTROID[1]) * sc]])
    rgb = cv2.warpAffine(src, M, (n, n), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    # détourage sur l'hexagone (léger retrait, bord adouci)
    pts = np.array([[n / 2 + (x - EF_CENTROID[0]) * FS_K * AS * 0.992, n / 2 + (y - EF_CENTROID[1]) * FS_K * AS * 0.992] for x, y in EF_PTS])
    m = np.zeros((n * 4, n * 4), np.uint8); cv2.fillPoly(m, [np.round(pts * 4).astype(np.int32)], 255)
    a = cv2.resize(m, (n, n), interpolation=cv2.INTER_AREA).astype(np.float64) / 255.0
    a = cv2.GaussianBlur(a, (0, 0), 0.6)
    if led_on:
        # la LED ambre (à droite) se reflète sur les flancs et la bague moletée tournés vers elle
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        ux = (xx - n / 2) / (AS * FS_K * 50.0)
        w = np.clip(ux, 0, 1) ** 2 * (rgb.mean(2) / 255.0)
        rgb = rgb + (w * 70.0)[..., None] * np.array([1.0, 0.58, 0.18])
    # ombre portée (lumière en haut à gauche) + ombre de contact
    def shift(img, dx, dy): return cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, dy]]), (n, n))
    cast = cv2.GaussianBlur(shift(a, 4.5 * AS, 6.5 * AS), (0, 0), 4.5 * AS) * 0.55
    contact = cv2.GaussianBlur(shift(a, 1.0 * AS, 1.5 * AS), (0, 0), 1.6 * AS) * 0.45
    sh = np.clip(cast + contact, 0, 0.8) * (1 - a)
    alpha = np.clip(a + sh, 0, 1)
    col = np.where(alpha[..., None] > 1e-4, rgb * (a / np.maximum(alpha, 1e-4))[..., None], 0)    # l'ombre est noire
    out = np.dstack([np.clip(col, 0, 255), alpha * 255]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(os.path.join(ROOT, "tools", "fs.png"))


# ------------------------------------------------------------------ chrome contraste (studio photo)
def env_studio(n, blur=1.0):
    """ environnement de studio lu par le vecteur reflechi : grande boite a lumiere en haut a gauche,
    murs clairs cote lumiere, horizon net et sol sombre -> le chrome a ses bandes claires / sombres tranchees """
    nz = n[..., 2]
    r = np.dstack([2 * nz * n[..., 0], 2 * nz * n[..., 1], 2 * nz * nz - 1])
    el = np.degrees(np.arcsin(np.clip(r[..., 2], -1, 1)))
    az = np.degrees(np.arctan2(r[..., 1], r[..., 0]))            # -135 = haut gauche (y vers le bas)
    daz = np.abs(((az + 135.0) + 180.0) % 360.0 - 180.0)
    side = np.cos(np.radians(daz))                                # 1 cote lumiere, -1 oppose
    ceiling = 175 + 35 * side
    wall = 120 + 95 * side
    floor = 34 + 14 * np.clip(side, 0, 1)
    sm = lambda v, a, b: np.clip((v - a) / max(b - a, 1e-6), 0, 1)
    col = floor + (wall - floor) * sm (el, -2.0 * blur, 2.0 * blur)
    col = col + (ceiling - col) * sm (el, 38, 62)
    box = 255 * sm (-daz, -48, -28) * sm (el, 14, 22) * (1 - sm (el, 64, 72))
    col = np.maximum(col, box)
    col = col + 60 * np.exp(-((daz - 180) / 20) ** 2) * sm (el, 4, 10) * (1 - sm (el, 26, 34))   # petite boite d'appoint
    return col

def shade_chrome(n, vis, tint, gain=1.0):
    e = env_studio(n)
    occl = 0.45 + 0.55 * vis
    ndh = np.clip(n @ H, 0, 1)
    spec = 255 * ndh ** 380 * vis
    return (e * occl * gain + spec)[..., None] * np.asarray(tint)

# ------------------------------------------------------------------ inverseur a levier (vertical), 5 positions
TW = 96.0                                   # sprite carre (unites), centre sur l'axe du levier

def toggle(t):              # t : -1 = levier en haut, 0 = centre, 1 = en bas (valeurs intermediaires = en mouvement)
    c = Canvas(TW, TW, TW / 2, TW / 2)
    x, y = c.x, c.y
    r = np.hypot(x, y)
    # bague chromee (comme le visuel), ecrou hexagonal satine, fut filete chrome
    ring = (r < 20.0) & (r > 12.6)
    rr_ = np.clip((r - 12.6) / (20.0 - 12.6), 0, 1)
    ringh = 0.4 + 2.2 * np.sqrt(np.clip(1 - (2 * rr_ - 1) ** 2, 0, 1))        # profil arrondi de la bague
    c.put(ringh, ring, 4)
    c.put(np.full_like(r, 0.6), r <= 12.6, 4)
    hx = hexagon_r(x, y, 11.5, pointy=False)
    nut = np.minimum(4.6, (11.5 - hx) * 2.6)
    nut = np.minimum(nut, 4.6 - np.clip(r - 10.4, 0, None) * 1.1)
    c.put(np.clip(nut, 0, None) + 1.4, (hx < 11.5) & (nut > 0), 1)
    bush = np.where(r < 6.4, 8.4 - 0.6 * np.clip((r - 5.4), 0, None) ** 2, 0)
    c.put(bush + 0.08 * np.sin(np.arctan2(y, x) * 2 + r * 6) * (r < 6.4), r < 6.4, 5)
    # levier : capsule effilee du pivot vers l'extremite en boule, inclinee de 58 degres en butee
    tilt = math.radians(58) * t
    ax = np.array([0.0, math.sin(tilt), math.cos(tilt)])
    p0 = np.array([0.0, 0.0, 8.2])
    Lb = 22.0 + 8.0 * abs(t)              # vu de dessus, le levier vertical parait plus court
    best = np.full_like(r, -1.0)
    for s in np.linspace(0, 1, 140):
        cen = p0 + ax * Lb * s
        # tige large de section constante, bout simplement arrondi (demi-sphere du meme rayon, pas de boule)
        R0 = 7.4 + 0.6 * s
        s0 = 1.0 - 8.0 / Lb
        rad = R0 if s <= s0 else R0 * math.sqrt(max(0.0, 1 - ((s - s0) / (1 - s0)) ** 2))
        d2 = (x - cen[0]) ** 2 + (y - cen[1]) ** 2
        zz = cen[2] + np.sqrt(np.clip(rad ** 2 - d2, 0, None))
        best = np.where(d2 < rad ** 2, np.maximum(best, zz), best)
    c.put(best, best > 0, 2)
    vis = soft_shadow(c, samples=16, spread=0.12, max_u=50)
    n = normals(c, c.h)
    lever = shade_chrome(n, vis, (1.0, 0.99, 0.975), 1.05)
    nutc  = 0.55 * shade_chrome(n, vis, (0.97, 0.96, 0.95), 0.95) + 0.45 * shade(c, n, vis, (0.95, 0.94, 0.93), "satin", rough=0.45)
    ringc = shade_chrome(n, vis, (0.98, 0.98, 0.99), 0.95)
    bushc = shade_chrome(n, vis, (0.98, 0.98, 0.99), 0.9)
    m = c.mat[..., None]
    rgb = np.where(m == 2, lever, np.where(m == 1, nutc, np.where(m == 4, ringc, bushc)))
    sh = panel_shadow(c, vis, amount=0.50)
    obj = (c.mat > 0).astype(np.float64)
    obj = cv2.GaussianBlur(obj, (0, 0), 0.35 * SSAA)
    alpha = np.clip(obj + sh * (1 - obj), 0, 1)
    rgba = np.dstack([rgb * obj[..., None], alpha * 255])
    size = round(TW * AS * 2)                  # 4 px par unite (ecrans HiDPI)
    small = cv2.resize(rgba, (size, size), interpolation=cv2.INTER_AREA)
    a = small[..., 3:4] / 255.0
    col = np.where(a > 1e-4, small[..., :3] / np.maximum(a, 1e-4), 0)
    return np.dstack([np.clip(col, 0, 255), np.clip(small[..., 3], 0, 255)]).astype(np.uint8)

if __name__ == "__main__":
    footswitch_echoflex(False)
    frames = [toggle(t) for t in (-1.0, -0.5, 0.0, 0.5, 1.0)]
    Image.fromarray(np.concatenate(frames, 0), "RGBA").save(os.path.join(ROOT, "toggle_strip.png"), optimize=True)
    print("toggle_strip.png", frames[0].shape, "fs.png")
