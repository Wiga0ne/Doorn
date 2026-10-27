"""
Doorn (Studio Wiga) - inverseurs a levier tires de la photo de la vraie Thorn
(design/switch_photo/thorn_switches.png : switch EQ levier en bas, switch MODE levier au centre).

Les deux positions photographiees sont reprises telles quelles ; la troisieme (levier en haut) est
fabriquee a partir des memes pixels, sans miroir de l'eclairage :
  - base : bague chromee + fut de la photo « centre », dome retire (interieur sombre du fut reconstitue) ;
  - tige : celle de la photo « bas », retournee verticalement (un cylindre vu de dessus garde son
    eclairage gauche / droite quand on le retourne de haut en bas) ;
  - bout arrondi : le dome de la photo « centre » (vu presque dans l'axe, donc eclaire comme il faut),
    legerement aplati par la perspective, pose au-dessus du pivot.
Ombre portee de la bague et du levier ajoutee vers le bas a droite (lumiere en haut a gauche).

Sortie : toggle_strip.png, 5 images carrees (96 unites, 4 px / unite) : haut, (centre), centre, (centre), bas.
"""
import os
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = np.asarray(Image.open(os.path.join(ROOT, 'design', 'switch_photo', 'thorn_switches.png')).convert('RGB')).astype(np.float32)

DOWN_C = (76.0, 57.5)        # centre de la bague, switch EQ (levier en bas)
CENT_C = (654.5, 57.5)       # centre de la bague, switch MODE (levier au centre)
R_OUT = 38.6                 # rayon exterieur de la bague (px photo)
TW, PXU = 96, 4              # sprite : 96 unites a 4 px par unite
N = TW * PXU
K = 20.0 * PXU / R_OUT       # bague = 20 unites de rayon (comme le rendu precedent, couvre la bague du visuel)
PAD = 60                     # demi-cote de la zone prise dans la photo (px photo)

def patch(c):
    """zone de la photo centree sur la bague, remise a l'echelle du sprite (Lanczos) + leger renforcement"""
    cx, cy = c
    M = np.float32([[K, 0, N / 2 - cx * K], [0, K, N / 2 - cy * K]])
    img = cv2.warpAffine(P, M, (N, N), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    blur = cv2.GaussianBlur(img, (0, 0), 2.2)
    return np.clip(img + 0.55 * (img - blur), 0, 255)

yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
X, Y = (xx + 0.5 - N / 2) / K, (yy + 0.5 - N / 2) / K       # coordonnees en px photo, origine = centre de la bague
R = np.hypot(X, Y)

def smooth_mask(m, s=1.1):
    return np.clip(cv2.GaussianBlur(m.astype(np.float32), (0, 0), s * K / 2), 0, 1)

def ellipse(cx, cy, rx, ry):
    return ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1.0

ring_mask = R <= R_OUT + 0.4

# ---------------------------------------------------------------- position BAS (photo telle quelle)
down = patch(DOWN_C)
TIP_D = (-1.5, 33.5, 16.5, 13.0)          # bout du levier (centre x, y, demi-axes) en px photo
m_down = smooth_mask(ring_mask | ellipse(*TIP_D))

# ---------------------------------------------------------------- position CENTRE (photo telle quelle)
cent = patch(CENT_C)

def ring_repair(img, a0, a1, r0, r1):
    """refait un secteur de la bague (angles a0..a1, en degres, 90 = bas) en interpolant, a chaque rayon,
    entre les angles voisins intacts : la bague redevient ronde, son eclairage varie doucement avec l'angle"""
    out = img.copy()
    NA = 1440
    th = np.linspace(-np.pi, np.pi, NA, endpoint=False)
    deg = (np.degrees(th) + 360) % 360
    bad = (deg >= a0) & (deg <= a1)
    good = np.where(~bad)[0]
    ext = np.concatenate([good - NA, good, good + NA])
    A = (np.degrees(np.arctan2(Y, X)) + 360) % 360
    sel_all = (A >= a0 - 6) & (A <= a1 + 6) & (R >= r0) & (R <= r1)
    for rr in np.arange(r0, r1 + 0.01, 0.25):
        px = N / 2 + rr * np.cos(th) * K - 0.5
        py = N / 2 + rr * np.sin(th) * K - 0.5
        prof = np.stack([cv2.remap(img[..., c], px.astype(np.float32)[None, :], py.astype(np.float32)[None, :],
                                   cv2.INTER_LINEAR)[0] for c in range(3)], -1)
        for c in range(3):
            prof[:, c] = np.interp(np.arange(NA), ext, np.tile(prof[good, c], 3))
        sel = sel_all & (np.abs(R - rr) <= 0.125)
        idx = ((np.arctan2(Y[sel], X[sel]) + np.pi) / (2 * np.pi) * NA).astype(int) % NA
        # fondu sur 6 degres aux bords du secteur
        w = np.clip(np.minimum(A[sel] - (a0 - 6), (a1 + 6) - A[sel]) / 6.0, 0, 1)[:, None]
        out[sel] = img[sel] * (1 - w) + prof[idx] * w
    return out

# bas de la bague coupe sur la photo (bord sombre aplati) : secteur refait
cent = ring_repair(cent, 40, 140, 26.0, R_OUT + 0.6)
m_cent = smooth_mask(ring_mask)

# ---------------------------------------------------------------- position HAUT (fabriquee)
up = cent.copy()
# 1. interieur du fut sans le dome : sombre, un peu plus clair vers le haut a gauche (comme l'anneau noir de la photo)
dark_ring = (R > 23.5) & (R < 27.5)
dark = np.median(cent[dark_ring], 0) * 0.55     # le fut est plus sombre que l anneau (pas de dome qui eclaire)
hole = R < 25.5
grad = 1.0 + 0.25 * np.clip(-(X * 0.6 + Y * 0.8) / 25.0, -1, 1)
up_hole = dark[None, None, :] * grad[..., None]
a_h = smooth_mask(hole, 0.8)
up = up * (1 - a_h[..., None]) + up_hole * a_h[..., None]

# 2. tige de la photo « bas » retournee verticalement (du pivot vers le haut)
down_flip = down[::-1].copy()                       # retournement autour du centre de la bague
shaft = (np.abs(X + 1.0) < 11.5) & (Y > -30.0) & (Y < 6.0)
# la tige n'est prise que la ou elle est claire (le reste = interieur sombre deja en place)
L = down_flip.mean(-1)
a_s = smooth_mask(shaft & ((X + 1.0) ** 2 / 11.0 ** 2 + 0 * Y <= 1.0), 0.9)
# vers le pivot, la tige s'enfonce dans le fut sombre (fondu progressif, comme sur la photo « bas »)
a_s *= np.clip((7.0 - Y) / 6.0, 0, 1)
up = up * (1 - a_s[..., None]) + down_flip * a_s[..., None]

# 3. bout arrondi : dome de la photo « centre », aplati par la perspective, au-dessus du pivot
dome_c = (0.0, 0.0); DR = 22.0
TIP_U = (-1.0, -32.5)
sx, sy = 1.08, 0.90
src_x = (X - TIP_U[0]) / sx + dome_c[0]
src_y = (Y - TIP_U[1]) / sy + dome_c[1]
map_x = (src_x * K + N / 2 - 0.5).astype(np.float32)
map_y = (src_y * K + N / 2 - 0.5).astype(np.float32)
dome_img = cv2.remap(cent, map_x, map_y, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
tip_mask = ((X - TIP_U[0]) / (17.0 * sx)) ** 2 + ((Y - TIP_U[1]) / (17.0 * sy)) ** 2 <= 1.0
a_t = smooth_mask(tip_mask, 0.9)
# ombre de contact du bout sur la tige
sh_t = smooth_mask(((X - TIP_U[0] - 1.5) / (17.0 * sx)) ** 2 + ((Y - TIP_U[1] - 3.0) / (17.0 * sy)) ** 2 <= 1.0, 2.2)
up *= (1 - 0.45 * sh_t * (1 - a_t))[..., None]
up = up * (1 - a_t[..., None]) + dome_img * a_t[..., None]
m_up = smooth_mask(ring_mask | tip_mask)

# ---------------------------------------------------------------- ombres portees (vers le bas a droite) et sprites
def sprite(rgb, m):
    def shift(img, dx, dy): return cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, dy]]), (N, N))
    cast = cv2.GaussianBlur(shift(m, 2.8 * PXU, 3.8 * PXU), (0, 0), 3.0 * PXU) * 0.55
    contact = cv2.GaussianBlur(shift(m, 0.6 * PXU, 0.9 * PXU), (0, 0), 1.0 * PXU) * 0.45
    sh = np.clip(cast + contact, 0, 0.8) * (1 - m)
    alpha = np.clip(m + sh, 0, 1)
    col = np.where(alpha[..., None] > 1e-4, rgb * (m / np.maximum(alpha, 1e-4))[..., None], 0)
    return np.dstack([np.clip(col, 0, 255), alpha * 255]).astype(np.uint8)

frames = [sprite(up, m_up), sprite(cent, m_cent), sprite(cent, m_cent), sprite(cent, m_cent), sprite(down, m_down)]
Image.fromarray(np.concatenate(frames, 0), 'RGBA').save(os.path.join(ROOT, 'toggle_strip.png'), optimize=True)
print('toggle_strip.png', N, 'x', N * 5)
