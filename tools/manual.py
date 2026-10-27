# DOORN (Studio Wiga) - notice PDF bilingue (anglais puis francais), illustree avec le rendu reel du plugin.
# Usage : python3 tools/manual.py <dossier des captures (tools/render)> <fichier PDF de sortie>
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, NextPageTemplate, Frame, Paragraph, Spacer, Image as RLImage,
                                Table, TableStyle, PageBreak, CondPageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = sys.argv[1]
OUT = sys.argv[2]
VERSION = "2.7.0"
TMP = os.path.dirname(os.path.abspath(OUT))
FONTS = os.path.join(ROOT, "assets", "fonts")

for n, f in (("Pop", "Poppins-Regular"), ("PopL", "Poppins-Light"), ("PopM", "Poppins-Medium"), ("PopB", "Poppins-Bold")):
    pdfmetrics.registerFont(TTFont(n, os.path.join(FONTS, f + ".ttf")))
pdfmetrics.registerFont(TTFont("Title", os.path.join(ROOT, "assets", "AlegreyaSC-Regular.ttf")))

ACC = colors.HexColor("#B08D52"); ACC_L = colors.HexColor("#D8B97E")      # or des fissures du visuel
DARK = colors.HexColor("#161A26"); GREY = colors.HexColor("#646A78"); LIGHT = colors.HexColor("#F1ECE2")

# ---------- capture annotee ----------
src = Image.open(os.path.join(SHOTS, "doorn_status.png")).convert("RGB")
k = src.height / 958.0
import json
LAY = json.load(open(os.path.join(ROOT, "tools", "layout.json")))
_k = LAY["knobs"]
marks = [  # (numero, x, y) dans le repere 760 x 958 du plugin (tools/layout.json)
    (1, *_k["gain"]), (2, *LAY["mini"]), (3, *_k["level"]), (4, *_k["treble"]), (5, *_k["mids"]), (6, *_k["bass"]),
    (7, *LAY["toggles"]["eq"]), (8, *LAY["toggles"]["mode"]), (9, *LAY["led"]), (10, *LAY["foot"]["boost"]), (11, *LAY["foot"]["bypass"]),
    (12, 278, 620), (13, 240, 660), (14, 494, 14), (15, 270, 14)]
ann = src.copy(); dr = ImageDraw.Draw(ann)
fnt = ImageFont.truetype(os.path.join(FONTS, "Poppins-Bold.ttf"), 34)
for n, x, y in marks:
    ox = {1: -52, 2: 0, 3: 52, 4: -52, 5: 0, 6: 52, 7: -46, 8: 46, 9: 34, 10: -66, 11: 66, 12: -10, 13: -14, 14: 0, 15: 0}[n]
    oy = {2: -36, 5: -56, 9: 0, 12: 0, 13: 0}.get(n, -40 if n in (1, 3, 4, 6) else 0)
    cx, cy, r = (x + ox) * k, (y + oy) * k, 27
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=(176, 141, 82), width=5)
    dr.text((cx, cy + 1), str(n), font=fnt, fill=(20, 26, 38), anchor="mm")
annotated = os.path.join(TMP, "doorn_annotated.png"); ann.save(annotated)

# les 3 modes : gros plan sur l'inverseur MODE (SDT-2 / Laerm / SDT-1)
def crop_u(path, box):
    im = Image.open(os.path.join(SHOTS, path)).convert("RGB")
    return im.crop(tuple(int(v * k) for v in box))
modes = [crop_u(p, (440, 470, 610, 600)) for p in ("doorn_sdt2.png", "doorn_laerm.png", "doorn_status.png")]
gap = 18
mstrip = Image.new("RGB", (sum(m.width for m in modes) + gap * 2, modes[0].height), (255, 255, 255))
x = 0
for m in modes: mstrip.paste(m, (x, 0)); x += m.width + gap
modes_img = os.path.join(TMP, "doorn_modes.png"); mstrip.save(modes_img)

# LED (effet actif / bypass) et potard BOOST transparent (eteint / eclaire quand le boost est enclenche)
_m = LAY["mini"]; _l = LAY["led"]
kb = (_m[0] - 82, _m[1] - 70, _m[0] + 82, _m[1] + 110)
kl = (_l[0] - 82, _l[1] - 110, _l[0] + 82, _l[1] + 70)
leds = [crop_u("doorn_bypass.png", kl), crop_u("doorn_boost.png", kl), crop_u("doorn_status.png", kb), crop_u("doorn_boost.png", kb)]
lstrip = Image.new("RGB", (sum(m.width for m in leds) + gap * 3, leds[0].height), (255, 255, 255))
x = 0
for m in leds: lstrip.paste(m, (x, 0)); x += m.width + gap
leds_img = os.path.join(TMP, "doorn_leds.png"); lstrip.save(leds_img)

# barre de presets + ligne d'etat
bar = crop_u("doorn_status.png", (220, 592, 540, 678))
bar_img = os.path.join(TMP, "doorn_bar.png"); bar.save(bar_img)

# couverture : pedale detouree (silhouette tools/pedal_mask.png), reflet au sol, halo dore tres doux
shot = Image.open(os.path.join(SHOTS, "doorn_laerm.png")).convert("RGB")
msk = Image.open(os.path.join(ROOT, "tools", "pedal_mask.png")).convert("L").resize(shot.size, Image.LANCZOS)
cut = Image.new("RGBA", shot.size, (0, 0, 0, 0)); cut.paste(shot, (0, 0), msk)
cut = cut.crop(cut.getbbox())
cw, ch = cut.size
pad = int(cw * 0.16)
canvas = Image.new("RGBA", (cw + 2 * pad, int(ch * 1.30) + pad), (0, 0, 0, 255))
yy, xx = np.mgrid[0:canvas.height, 0:canvas.width].astype(np.float64)
gcx, gcy = canvas.width / 2, pad + ch * 0.45
glow = np.exp(-(((xx - gcx) / (cw * 0.62)) ** 2 + ((yy - gcy) / (ch * 0.48)) ** 2)) * 34
edge = np.clip(np.minimum.reduce([xx, canvas.width - 1 - xx, yy, canvas.height - 1 - yy]) / (pad * 0.9), 0, 1)
glow *= edge ** 2
halo = np.dstack([glow * 0.92, glow * 0.74, glow * 0.45, np.full_like(glow, 255)]).astype(np.uint8)
canvas = Image.alpha_composite(canvas, Image.fromarray(halo, "RGBA"))
refl = cut.transpose(Image.FLIP_TOP_BOTTOM)
ra = np.array(refl).astype(np.float64)
fade = np.clip(1 - np.arange(refl.height) / (refl.height * 0.22), 0, 1) ** 1.6 * 0.22
ra[..., 3] *= fade[:, None]
canvas.alpha_composite(Image.fromarray(ra.astype(np.uint8), "RGBA"), (pad, pad + ch + 6))
canvas.alpha_composite(cut, (pad, pad))
canvas = canvas.crop((0, 0, canvas.width, pad + int(ch * 1.20)))
cover = os.path.join(TMP, "doorn_cover_cutout.png"); canvas.convert("RGB").save(cover)

def img(path, width):
    im = Image.open(path); h = width * im.height / im.width
    return RLImage(path, width=width, height=h)

# ---------- styles ----------
st = {
    "h1": ParagraphStyle("h1", fontName="PopB", fontSize=20, leading=24, textColor=ACC, spaceAfter=8, spaceBefore=4, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="PopM", fontSize=13, leading=17, textColor=DARK, spaceAfter=4, spaceBefore=10, keepWithNext=1),
    "p": ParagraphStyle("p", fontName="Pop", fontSize=9.6, leading=14, textColor=DARK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="Pop", fontSize=8.2, leading=11.5, textColor=GREY),
    "cell": ParagraphStyle("cell", fontName="Pop", fontSize=8.4, leading=11, textColor=DARK),
    "hcell": ParagraphStyle("hcell", fontName="Pop", fontSize=7.2, leading=9.2, textColor=DARK),
    "cellb": ParagraphStyle("cellb", fontName="PopM", fontSize=8.4, leading=11, textColor=DARK),
    "cover": ParagraphStyle("cover", fontName="Title", fontSize=44, leading=50, textColor=colors.white, alignment=TA_CENTER),
    "coversub": ParagraphStyle("coversub", fontName="Pop", fontSize=12, leading=16, textColor=colors.HexColor("#BDB8AE"), alignment=TA_CENTER),
    "coverlang": ParagraphStyle("coverlang", fontName="PopM", fontSize=8.5, leading=11, textColor=ACC_L),
}
def P(t, s="p"): return Paragraph(t, st[s])
def bullets(items): return [P("&bull;&nbsp;&nbsp;" + i) for i in items]
def table(rows, widths, header=True, small=False):
    data = [[P(c, "cellb" if (header and r == 0) else ("hcell" if small else "cell")) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#DED6C6")),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header: style += [("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACC)]
    t.setStyle(TableStyle(style)); return t

# ---------- donnees (identiques au code livre : PluginProcessor.cpp) ----------
MODES = ["SDT-2", "Laerm", "SDT-1"]
FACTORY = [  # nom, gain, boost, level, treble, mids, bass, eq, mode, boostOn
    ("Signature Start",        7.5, 7.5, 7.5, 8.0, 3.75, 7.5, 1, 2, 0),
    ("Wall of Thorns",         8.5, 6.0, 7.0, 7.0, 3.5, 7.0, 1, 2, 0),
    ("V4 EQ Bypass",           7.5, 5.0, 7.0, 5.0, 5.0, 5.0, 0, 2, 0),
    ("Living Gate Saturation", 8.0, 5.0, 8.0, 7.0, 6.0, 6.0, 1, 0, 0),
    ("Laerm Open",             6.5, 5.0, 6.0, 7.0, 5.5, 6.0, 1, 1, 0),
    ("Laerm Lead Boost",       7.0, 8.0, 6.0, 6.5, 7.0, 5.0, 1, 1, 1),
    ("Stampede Crunch",        3.0, 5.0, 7.5, 6.0, 6.0, 5.0, 1, 2, 0),
    ("Hardcore Bite",          9.5, 4.0, 6.5, 7.5, 6.5, 4.5, 1, 2, 0),
    ("Sludge Sustain",         10,  5.0, 7.0, 5.0, 2.5, 9.0, 1, 0, 1),
    ("Thorn Reference",        4.3, 0.0, 5.8, 5.8, 5.0, 8.0, 1, 2, 0)]
FACT_DESC = {
 "en": ["The starting point from the Guitar Pedal X review: gain, boost and level at 3 o'clock, treble full, mids at 10:30, bass at 3 o'clock, EQ on.",
        "More gain and a deeper mid scoop: the dense wall for slow, heavy riffs.",
        "EQ lifted from the circuit, the way Lennart Bossu runs his Thorn into an Ampeg V4: direct, raw, the amp does the shaping.",
        "SDT-2 voicing: more compressed and saturated, darker, sustaining chords.",
        "Laerm voicing at moderate gain: open, direct, louder, great for chords that must stay readable.",
        "Laerm with the boost engaged and the mids pushed: a lead that cuts through the mix.",
        "Low gain on the SDT-1: the edgy crunch side of the Stampede (it never really goes clean).",
        "Near-full gain, bright and mid-forward: the biting hardcore attack of the Stampede.",
        "Full gain, SDT-2, boost on, heavy bass and scooped mids: long, thick sustain for sludge and doom.",
        "The settings of a real Thorn on which the sound was matched: gain at 11 o'clock, level and treble at 1 o'clock, mids at noon, bass at 3 o'clock, EQ on, SDT-1, boost off."],
 "fr": ["Le réglage de départ du test Guitar Pedal X : gain, boost et level à 15 h, aigus à fond, médiums à 10 h 30, graves à 15 h, EQ en marche.",
        "Plus de gain et des médiums plus creusés : le mur dense pour les riffs lents et lourds.",
        "EQ retiré du circuit, comme Lennart Bossu avec sa Thorn dans un Ampeg V4 : direct, brut, l'ampli fait le travail de tonalité.",
        "Voix SDT-2 : plus compressée et saturée, plus sombre, des accords qui tiennent.",
        "Voix Laerm à gain modéré : ouverte, directe, plus forte, idéale pour des accords qui restent lisibles.",
        "Laerm avec le boost enclenché et les médiums poussés : un solo qui passe devant le mix.",
        "Peu de gain sur la SDT-1 : le côté crunch mordant de la Stampede (elle ne devient jamais vraiment claire).",
        "Gain presque au maximum, brillant et en avant dans les médiums : l'attaque hardcore mordante de la Stampede.",
        "Gain à fond, SDT-2, boost enclenché, graves lourds et médiums creusés : un sustain long et épais pour le sludge et le doom.",
        "Les réglages d'une vraie Thorn sur laquelle le son a été calé : gain à 11 h, level et aigus à 13 h, médiums à midi, graves à 15 h, EQ on, SDT-1, boost coupé."]}

def pc(v): return f"{round(v * 10)} %"

# ---------- textes ----------
T = {
"en": dict(
 lang="ENGLISH", sub="High gain distortion &nbsp;·&nbsp; VST3 for Windows and macOS", ver="User manual &nbsp;·&nbsp; version " + VERSION,
 intro_t="1. Introduction",
 intro=["<b>DOORN</b> (Dutch for <i>thorn</i>) is a Studio Wiga plugin modelled on the <b>Lichtlaerm Audio Thorn</b>, the signature distortion of <b>Lennart Bossu</b> (Amenra, Oathbreaker). The Thorn itself was reverse-engineered from Lennart's own <b>Providence Stampede SDT-1</b>, the rare Japanese hard distortion also used by Kurt Ballou of Converge, expanded with three voicings, a footswitchable additive boost and an active 3-band EQ that can be lifted out of the circuit.",
        "The sound is a wall of distortion rather than an overdrive: an aggressive, biting edge with a singing midrange, strong even harmonics that make pinch harmonics jump out, and a big low end that stays defined on chords. It is close to a cranked amp head, and it never really goes clean, even with the gain down.",
        "In the plugin the circuit is modelled stage by stage: input buffer and high-pass (tightness), mid pre-emphasis, two op-amp gain stages running on about 18 V (the Thorn uses an internal charge pump, the LT1054 on its circuit board, for a high headroom), clipping diodes to ground, op-amp roll-off, an amp-like output stage, then the bypassable EQ and the level. The distortion is computed with 4x oversampling to stay smooth and free of aliasing."],
 inst_t="2. Installation",
 inst=[("Windows", "Download the <b>Doorn-VST3-Windows</b> artifact from the Actions tab of the GitHub repository Wiga0ne/Doorn, unzip it and copy the <b>Doorn.vst3</b> folder into <b>C:\\Program Files\\Common Files\\VST3</b>."),
       ("macOS", "Download <b>Doorn-VST3-macOS</b>, unzip it and copy <b>Doorn.vst3</b> into <b>~/Library/Audio/Plug-Ins/VST3</b>. If macOS blocks it, run <b>xattr -cr ~/Library/Audio/Plug-Ins/VST3/Doorn.vst3</b> in the Terminal. The binary is universal (Apple Silicon and Intel)."),
       ("Reaper", "Options &gt; Preferences &gt; Plug-ins &gt; VST &gt; <b>Re-scan</b>. The plugin appears as <b>Doorn (Studio Wiga)</b>. To control it from your MIDI footswitches and expression pedals, the track must receive MIDI from the controller (record-arm or input monitoring, MIDI input set to your device, e.g. the M-Vave Chocolate Plus).")],
 ov_t="3. Interface overview",
 ov_rows=[["#", "Control", "Role"],
   ["1", "GAIN", "Amount of distortion. Drag up / down, mouse wheel, double-click = noon."],
   ["2", "BOOST (small knob)", "Level of the boost, from 0 to +20 dB. Only heard when the BOOST footswitch is on: the transparent knob then lights up from inside and its cursor shows clearly."],
   ["3", "LEVEL", "Output volume."],
   ["4", "TREBLE", "Treble shelf at 3 kHz: cut down to -15 dB, boost up to +22 dB with sparkle around 4.5 kHz that comes in progressively; flat at noon, smooth travel with no jump."],
   ["5", "MIDS", "Mid bell at 1 kHz, ±12 dB, flat at noon."],
   ["6", "BASS", "Bass with punch: shelf at 90 Hz plus a presence bump around 120 Hz, -15 / +18 dB, flat at noon, smooth travel with no jump; after the distortion, so it never adds compression."],
   ["7", "EQ switch", "Up = off (EQ lifted out of the circuit), down = on."],
   ["8", "Mode switch", "Up = SDT-2, centre = Laerm, down = SDT-1."],
   ["9", "LED", "Red = effect on, off = bypass. The panel around it is lit by the LED."],
   ["10", "BOOST footswitch", "Boost on / off (hold = momentary)."],
   ["11", "BYPASS footswitch", "Effect on / off (hold = momentary)."],
   ["12", "Status line", "Setting of the knob or switch you just moved (knobs in %); appears when something moves."],
   ["13", "Preset bar", "Arrows = previous / next factory preset, click on the name = preset menu."],
   ["14", "IN", "Input jack."],
   ["15", "OUT", "Output jack."]],
 ctl_t="4. Controls in detail",
 ctl=[("GAIN", "From about 26 dB to 72 dB of gain spread over two op-amp stages. The gain comes in early: the knob already gives a hard, edgy crunch at its start, and the full fuzz-like wall the Stampede is known for is there from about 9 o'clock; further up, the grain thickens and the sustain grows. As the gain rises, the op-amp bandwidth narrows slightly, which keeps the top end from turning into fizz, exactly like the real circuit. The low end is filtered steeply before the clipping and follows your picking after it: full on the attack, it drops back as the note dies, so palm mutes stay tight. Most of the bass is kept out of the clipping and added back after it, which is why the low-mids stay clean even at full gain; a broad low-mid bump around 320 Hz, added after the clipping, gives chords their body. A parallel fuzz layer (two cascaded, slightly asymmetric clipping stages, the way a Big Muff works) is blended with the distortion, and now leads it, for the thick, woolly fuzz grain of stoner guitars, and a wide bump around 220 Hz after the clipping gives the sound its fat. The output also follows your picking dynamics (the clipping alone would flatten them): attacks come out in front and notes drop back naturally, so the sound never feels squashed."),
      ("BOOST", "As on the Thorn, the boost is <b>additive</b>: it is not a separate pedal in front, it adds its gain (0 to +20 dB, set with the small knob, plus up to +4 dB of output and a push around 1.6 kHz so you clearly hear it come in) to the GAIN and raises the input high-pass a little, so the attack gets tighter and the sustain longer. The small knob sets the amount; the BOOST footswitch turns it on and off."),
      ("LEVEL", "Audio taper: 0 = muted, noon about −15 dB, 3 o'clock about −7 dB, full = 0 dB. The three modes are levelled like on the pedal: SDT-2 slightly quieter, Laerm louder."),
      ("TREBLE · MIDS · BASS", "Active 3-band EQ after the distortion: bass shelf at 90 Hz with a punch bump around 120 Hz (-15 / +18 dB, after the clipping: more body without more compression), mid bell at <b>1 kHz</b> (±12 dB) for surgical presence shaping, treble shelf at 3 kHz (-15 / +22 dB, with extra sparkle around 4.5 kHz when turned up). At noon each band is flat; BASS and TREBLE follow a smooth curve: fine around noon, stronger towards the ends, never a sudden change. The circuit itself has a stoner mid / high-mid voice (Orange / Sunn style): a push around 900 Hz and 2.3 kHz so the sound cuts through, on top of a full low end with presence (bass bump around 100 Hz and body around 220 / 320 Hz, all added after the clipping so they stay tight)."),
      ("EQ off / on", "With the switch up (off), the EQ is completely lifted out of the signal path, as on the Thorn: the three EQ knobs then have no effect and the raw voice of the circuit goes straight to the amp (Lennart's setting into an Ampeg V4). The change is crossfaded, without any click."),
      ("Modes", "<b>SDT-1</b> (down): the original Stampede, silicon diodes to ground, singing mids. <b>Laerm</b> (centre): Lichtlaerm's own voicing, higher clipping threshold (LED-like), wider bandwidth, more open, more direct and louder (about +4 dB). <b>SDT-2</b> (up): an extra compression stage, more saturated and darker, slightly quieter (about −3 dB), the tones of Living Gate. Changing mode crossfades in a few milliseconds.")],
 modes_cap="The mode switch on SDT-2 (lever up), Laerm (centre) and SDT-1 (lever down).",
 fs_t="5. Footswitches, LED and MIDI",
 fs=["<b>Footswitches</b>: same footswitch and behaviour as Echoflex. They switch as soon as you press them and the cap darkens while held. <b>Smart relay</b> (as on the Thorn): if you hold a footswitch for more than 0.45 s after turning something on, it works as a momentary switch and turns off when you release it. Right-click &gt; <b>Settings</b> to disable this.",
     "<b>LED</b>: red when the effect is on, off in bypass, with a fade-in / fade-out and the panel really lit around it. <b>Boost</b>: when the boost is engaged, the transparent BOOST knob lights up from inside (warm light, the panel around it catches a little of it) and its cursor becomes clearly visible; boost off, the cursor stays dark under the smoked cap.",
     "<b>Bypass</b>: true bypass sound (the dry signal is passed through, time-aligned with the oversampling latency reported to the DAW).",
     "<b>Expression pedals</b>: every knob can be driven by a MIDI CC (table below). Movements are never stepped: Doorn measures the time between two messages from your pedal and ramps to each new value over that time; 14-bit pedals are supported, and the real travel of your pedal is learnt automatically, so a pedal that only sends 2 to 116 still reaches exactly 0 and 100 %.",
     "<b>MIDI footswitches</b>: latching (127 = on / 0 = off, default) or momentary (toggle on each press), right-click &gt; Settings. All parameters can also be automated and MIDI-learnt in the DAW.",
     "<b>Noise gate</b> (right-click &gt; Noise gate): silences hiss and hum as soon as you stop playing, opens instantly on the next note (no attack is ever cut) and lets notes fade smoothly. Off, Light, <b>Medium</b> (default) or Strong (noisy pickups). Acts on the effect only"],
 led_cap="LED in bypass and with the effect on; BOOST knob with the boost off and on (lit, cursor visible).",
 midi_hdr=["Message", "Function"],
 midi=[["CC 20 / 21 / 22", "Gain / Boost level / Level"], ["CC 23 / 24 / 25", "Treble / Mids / Bass"],
       ["CC 52 to 57", "Fine (14-bit) part of CC 20 to 25"], ["CC 26", "EQ (64 or more = on)"],
       ["CC 27", "Mode (0-42 SDT-2, 43-84 Laerm, 85-127 SDT-1)"], ["CC 28", "BOOST footswitch"], ["CC 29", "BYPASS footswitch"],
       ["Program Change 1-10", "Factory presets"]],
 win_t="6. Window",
 win=["Doorn uses the single pedal format of Echoflex: the window opens at its default size, <b>391 x 493 pixels</b>, and can never be made smaller than that. Drag the bottom-right corner to enlarge it up to 150 % (proportions are kept), or right-click &gt; <b>Window size</b>: Default, 75 %, 100 %.",
      "The <b>status line</b> shows only the setting of the knob, switch or footswitch you just moved (knobs in %, e.g. <i>gain 76 %</i>, <i>eq off</i>, <i>laerm</i>, <i>boost on</i>), in large, clear lettering; it appears when a setting moves and fades out after 2.5 s. The <b>preset bar</b> under it always shows the current preset, mode and boost / bypass state."],
 bar_cap="Status line (the control you just moved) and preset bar.",
 pre_t="7. Presets",
 pre=["Use the arrows of the preset bar, click its name, right-click anywhere, or use the preset menu of your DAW. Right-click &gt; <b>Save user preset</b> stores up to 9 presets of your own."],
 fac_hdr=["PC", "Preset", "Gain / Boost / Level", "Treble / Mids / Bass", "EQ · Mode", "Description"],
 tips_t="8. Tips",
 tips=["In Reaper place Doorn <b>before</b> your amp simulator (for example before Two Notes Genome) with a fairly clean amp, as you would with the real pedal. With a crunch amp, lower the gain: the Stampede already has a lot.",
       "For low tunings (B standard like Amenra, or a 7-string in G and lower), keep BASS around noon to 1 o'clock and use the BOOST: it tightens the low end without losing weight.",
       "The original reviewer's favourite modes are SDT-1 and Laerm; SDT-2 is perfect for long, saturated chords.",
       "If some hiss remains when you stop playing, set right-click &gt; Noise gate to Strong; for very tight stops on staccato riffs, NGATE from Studio Wiga can still be added after Doorn."],
 tech_t="9. Specifications and version history",
 tech=[["Format", "VST3 (Windows 64-bit, macOS universal)"], ["Channels", "Mono or stereo"],
       ["Latency", "32 samples (oversampling filter), reported to the DAW"], ["Gain", "about 26 to 72 dB, + 0 to 20 dB boost"],
       ["EQ", "bass 90 Hz + 120 Hz punch -15 / +18 dB, mids 1 kHz ±12 dB, treble 3 kHz -15 / +22 dB, bypassable"],
       ["Processing", "4x oversampling, smoothed parameters, no denormals"], ["CPU", "about 4 % of one core at 48 kHz (stereo)"]],
 hist=[["1.0.0", "First version: Thorn / Stampede SDT-1 model with SDT-1, SDT-2 and Laerm voicings, additive boost, bypassable 3-band EQ, smart relay footswitches, MIDI and expression pedals, 10 factory presets and 9 user presets, Echoflex single pedal format"],
       ["1.0.1 - 1.4.0", "Status line limited to the control you move, anti-freeze, tighter sound, bigger pedal, red-only LED with lit BOOST knob, sound matched on a recording of the real Thorn, readable status font"],
       ["1.5.0 - 1.9.0", "More gain and bite without the boost, tight low end (bass kept out of the clipping and given back after it), output that follows your picking, BASS with punch, clearly audible boost"],
       ["2.0.0 - 2.3.0", "Stoner grain and fat: parallel Big Muff-style fuzz layer that now leads the distortion (fuzz about 62 %), body bump around 220 Hz, stoner mid / high-mid voice (push around 900 Hz and 2.3 kHz, no longer muffled), low end and low-mids back with presence, headroom kept so nothing gets squashed"],
       ["2.4.0", "TREBLE goes much higher: up to +21 dB (instead of +15) with extra sparkle around 4.5 kHz; the cut side is unchanged"],
       ["2.5.0", "BASS goes higher too (up to +18 dB); BASS and TREBLE travel is smooth and natural, no sudden change at noon; stronger anti-freeze for the window (no heavy work while drawing, watchdog, no host call from the audio thread), JUCE 8.0.15"],
       ["2.6.0", "Built-in noise gate (right-click &gt; Noise gate: Off / Light / Medium / Strong, Medium by default): no more hiss or hum when you stop playing, attacks never cut, notes fade naturally"],
       ["2.7.0", "Clearer, more defined sound on every preset: the circuit's low-pass filters are opened up, more high harmonics before the clipping, definition around 4 kHz and air around 6 kHz, anti-fizz above 11 kHz, lighter nasal mid push; lows and mids kept. Presets with TREBLE at max lowered (Signature Start, Wall of Thorns, Hardcore Bite)"]],
 ver_h=["Version", "Changes"]),
"fr": dict(
 lang="FRANÇAIS", sub="Distorsion high gain &nbsp;·&nbsp; VST3 pour Windows et macOS", ver="Notice d'utilisation &nbsp;·&nbsp; version " + VERSION,
 intro_t="1. Présentation",
 intro=["<b>DOORN</b> (« épine » en néerlandais) est un plugin Studio Wiga inspiré de la <b>Lichtlaerm Audio Thorn</b>, la distorsion signature de <b>Lennart Bossu</b> (Amenra, Oathbreaker). La Thorn a elle-même été rétro-conçue à partir de la <b>Providence Stampede SDT-1</b> de Lennart, une distorsion dure japonaise rare, aussi utilisée par Kurt Ballou de Converge ; Lichtlaerm y a ajouté trois voix, un boost additif au pied et un EQ actif 3 bandes que l'on peut retirer du circuit.",
        "Le son est un mur de distorsion plutôt qu'un overdrive : un mordant agressif, des médiums qui chantent, de fortes harmoniques paires qui font ressortir les harmoniques pincées, et un grave énorme qui reste défini sur les accords. C'est proche d'une tête d'ampli poussée à fond, et cela ne devient jamais vraiment clair, même gain baissé.",
        "Dans le plugin, le circuit est reproduit étage par étage : buffer d'entrée et passe-haut (tenue du grave), pré-accentuation des médiums, deux étages de gain à ampli op alimentés sous environ 18 V (la Thorn utilise une pompe de charge interne, le LT1054 visible sur son circuit imprimé, pour une grande réserve de dynamique), diodes d'écrêtage à la masse, filtrage de l'ampli op, étage de sortie façon ampli, puis l'EQ bypassable et le volume. La distorsion est calculée avec un sur-échantillonnage x4 pour rester douce et sans repliement."],
 inst_t="2. Installation",
 inst=[("Windows", "Téléchargez l'artefact <b>Doorn-VST3-Windows</b> dans l'onglet Actions du dépôt GitHub Wiga0ne/Doorn, décompressez-le et copiez le dossier <b>Doorn.vst3</b> dans <b>C:\\Program Files\\Common Files\\VST3</b>."),
       ("macOS", "Téléchargez <b>Doorn-VST3-macOS</b>, décompressez-le et copiez <b>Doorn.vst3</b> dans <b>~/Bibliothèque/Audio/Plug-Ins/VST3</b>. Si macOS le bloque, tapez <b>xattr -cr ~/Library/Audio/Plug-Ins/VST3/Doorn.vst3</b> dans le Terminal. Le binaire est universel (Apple Silicon et Intel)."),
       ("Reaper", "Options &gt; Préférences &gt; Plug-ins &gt; VST &gt; <b>Re-scan</b>. Le plugin apparaît sous le nom <b>Doorn (Studio Wiga)</b>. Pour le piloter avec vos footswitchs et pédales d'expression MIDI, la piste doit recevoir le MIDI du contrôleur (armement ou monitoring d'entrée, entrée MIDI réglée sur votre appareil, par exemple la M-Vave Chocolate Plus).")],
 ov_t="3. Vue d'ensemble de l'interface",
 ov_rows=[["#", "Commande", "Rôle"],
   ["1", "GAIN", "Quantité de distorsion. Glisser vers le haut / le bas, molette, double-clic = midi."],
   ["2", "BOOST (petit potard)", "Niveau du boost, de 0 à +20 dB. Ne s'entend que si le footswitch BOOST est enclenché : le potard transparent s'éclaire alors de l'intérieur et son curseur apparaît nettement."],
   ["3", "LEVEL", "Volume de sortie."],
   ["4", "TREBLE", "Plateau d'aigus à 3 kHz : coupe jusqu'à -15 dB, montée jusqu'à +22 dB avec une brillance vers 4,5 kHz qui arrive progressivement ; plat à midi, course douce sans saut."],
   ["5", "MIDS", "Cloche de médiums à 1 kHz, ±12 dB, plate à midi."],
   ["6", "BASS", "Graves avec du punch : plateau à 90 Hz plus une bosse de présence vers 120 Hz, -15 / +18 dB, plat à midi, course douce sans saut ; après la distorsion, il n'ajoute jamais de compression."],
   ["7", "Inverseur EQ", "En haut = off (EQ retiré du circuit), en bas = on."],
   ["8", "Inverseur de mode", "En haut = SDT-2, au centre = Laerm, en bas = SDT-1."],
   ["9", "LED", "Rouge = effet actif, éteinte = bypass. La façade autour est éclairée par la LED."],
   ["10", "Footswitch BOOST", "Boost on / off (appui maintenu = momentané)."],
   ["11", "Footswitch BYPASS", "Effet on / off (appui maintenu = momentané)."],
   ["12", "Ligne d'état", "Réglage du potard ou de l'inverseur que vous venez de bouger (potards en %) ; apparaît quand un réglage bouge."],
   ["13", "Barre de presets", "Flèches = preset usine précédent / suivant, clic sur le nom = menu des presets."],
   ["14", "IN", "Jack d'entrée."],
   ["15", "OUT", "Jack de sortie."]],
 ctl_t="4. Les commandes en détail",
 ctl=[("GAIN", "D'environ 26 dB à 72 dB de gain, répartis sur deux étages d'ampli op. Le gain arrive tôt : le potard donne déjà un crunch dur et mordant en début de course, et le mur façon fuzz qui a fait la réputation de la Stampede est là dès 9 h environ ; plus haut, le grain s'épaissit et le sustain s'allonge. Quand le gain monte, la bande passante de l'ampli op se resserre un peu, ce qui évite que les aigus ne grésillent, exactement comme sur le vrai circuit. Le grave est filtré fortement avant l'écrêtage et suit votre jeu après : plein à l'attaque, il redescend quand la note s'éteint, les palm mutes restent nets. L'essentiel du grave est tenu à l'écart de l'écrêtage et rendu après : les bas-médiums restent nets même gain à fond ; une bosse large de bas-médiums vers 320 Hz, ajoutée après l'écrêtage, donne du corps aux accords. Une couche fuzz en parallèle (deux écrêtages en cascade légèrement asymétriques, comme une Big Muff) est mélangée à la distorsion, et passe maintenant devant, pour le grain fuzz épais et laineux des guitares stoner, et une bosse large vers 220 Hz après l'écrêtage donne le gras du son. La sortie suit aussi la dynamique de votre jeu (l'écrêtage seul l'aplatirait) : les attaques ressortent et les notes retombent naturellement, le son n'est jamais écrasé."),
      ("BOOST", "Comme sur la Thorn, le boost est <b>additif</b> : ce n'est pas une pédale séparée placée devant, il ajoute son gain (0 à +20 dB, réglé avec le petit potard, plus jusqu'à +4 dB de niveau et une poussée vers 1,6 kHz pour bien l'entendre arriver) au GAIN et remonte un peu le passe-haut d'entrée : l'attaque se resserre et le sustain s'allonge. Le petit potard règle la quantité ; le footswitch BOOST l'enclenche et le coupe."),
      ("LEVEL", "Courbe audio : 0 = coupé, midi environ −15 dB, 15 h environ −7 dB, à fond = 0 dB. Les trois modes sont équilibrés comme sur la pédale : SDT-2 un peu moins fort, Laerm plus fort."),
      ("TREBLE · MIDS · BASS", "EQ actif 3 bandes après la distorsion : plateau de graves à 90 Hz avec une bosse de punch vers 120 Hz (-15 / +18 dB, après l'écrêtage : plus de corps sans plus de compression), cloche de médiums à <b>1 kHz</b> (±12 dB) pour sculpter précisément la présence, plateau d'aigus à 3 kHz (-15 / +22 dB, avec de la brillance en plus vers 4,5 kHz quand on le monte). À midi, chaque bande est plate ; BASS et TREBLE suivent une courbe douce : fins autour de midi, plus forts vers les butées, jamais de changement brusque. Le circuit lui-même a une voix stoner médium / médium-aigu (façon Orange / Sunn) : une poussée vers 900 Hz et 2,3 kHz pour que le son perce, sur un bas plein et présent (bosse de grave vers 100 Hz et corps vers 220 / 320 Hz, tous ajoutés après l'écrêtage pour rester serrés)."),
      ("EQ off / on", "Inverseur en haut (off) : l'EQ est entièrement retiré du trajet du signal, comme sur la Thorn ; les trois potards d'EQ n'ont alors plus d'effet et la voix brute du circuit part directement dans l'ampli (le réglage de Lennart dans un Ampeg V4). Le changement se fait en fondu, sans aucun clic."),
      ("Modes", "<b>SDT-1</b> (en bas) : la Stampede d'origine, diodes silicium à la masse, médiums qui chantent. <b>Laerm</b> (au centre) : la voix propre à Lichtlaerm, seuil d'écrêtage plus haut (type LED), bande passante plus large, plus ouverte, plus directe et plus forte (environ +4 dB). <b>SDT-2</b> (en haut) : un étage de compression en plus, plus saturée et plus sombre, un peu moins forte (environ −3 dB), les sons de Living Gate. Le changement de mode se fait en fondu en quelques millisecondes.")],
 modes_cap="L'inverseur de mode sur SDT-2 (levier en haut), Laerm (au centre) et SDT-1 (levier en bas).",
 fs_t="5. Footswitchs, LED et MIDI",
 fs=["<b>Footswitchs</b> : même footswitch et même fonctionnement qu'Echoflex. Ils basculent dès l'appui et le bouton s'assombrit tant qu'on appuie. <b>Smart relay</b> (comme sur la Thorn) : si vous maintenez un footswitch plus de 0,45 s après avoir enclenché quelque chose, il fonctionne en momentané et se coupe quand vous relâchez. Clic droit &gt; <b>Settings</b> pour désactiver ce comportement.",
     "<b>LED</b> : rouge quand l'effet est actif, éteinte en bypass, avec allumage / extinction en fondu et la façade réellement éclairée autour. <b>Boost</b> : quand le boost est enclenché, le potard BOOST transparent s'éclaire de l'intérieur (lumière chaude, la façade autour en reçoit un peu) et son curseur devient bien visible ; boost coupé, le curseur reste sombre sous le chapeau fumé.",
     "<b>Bypass</b> : son direct (le signal sec passe, aligné dans le temps sur la latence du sur-échantillonnage annoncée au DAW).",
     "<b>Pédales d'expression</b> : chaque potard peut être piloté par un CC MIDI (tableau ci-dessous). Les mouvements ne sont jamais saccadés : Doorn mesure le temps entre deux messages de votre pédale et rejoint chaque nouvelle valeur par une rampe pendant ce temps ; les pédales 14 bits sont prises en charge et la course réelle de votre pédale est apprise automatiquement : une pédale qui n'envoie que 2 à 116 atteint quand même exactement 0 et 100 %.",
     "<b>Footswitchs MIDI</b> : à accrochage (127 = on / 0 = off, par défaut) ou momentanés (bascule à chaque appui), clic droit &gt; Settings. Tous les paramètres sont aussi automatisables et assignables en MIDI learn dans le DAW.",
     "<b>Noise gate</b> (clic droit &gt; Noise gate) : coupe le souffle et le ronflement dès qu'on arrête de jouer, s'ouvre instantanément à la note suivante (aucune attaque coupée), laisse les notes s'éteindre en douceur. Off, Light, <b>Medium</b> (par défaut) ou Strong (micros bruyants). N'agit que sur l'effet"],
 led_cap="LED en bypass et effet actif ; potard BOOST boost coupé et enclenché (éclairé, curseur visible).",
 midi_hdr=["Message", "Fonction"],
 midi=[["CC 20 / 21 / 22", "Gain / niveau du Boost / Level"], ["CC 23 / 24 / 25", "Treble / Mids / Bass"],
       ["CC 52 à 57", "Partie fine (14 bits) des CC 20 à 25"], ["CC 26", "EQ (64 ou plus = on)"],
       ["CC 27", "Mode (0-42 SDT-2, 43-84 Laerm, 85-127 SDT-1)"], ["CC 28", "Footswitch BOOST"], ["CC 29", "Footswitch BYPASS"],
       ["Program Change 1-10", "Presets usine"]],
 win_t="6. Fenêtre",
 win=["Doorn utilise le format pédale simple d'Echoflex : la fenêtre s'ouvre à sa taille par défaut, <b>391 x 493 pixels</b>, et ne peut jamais être réduite en dessous. Tirez le coin en bas à droite pour l'agrandir jusqu'à 150 % (les proportions sont conservées), ou clic droit &gt; <b>Window size</b> : Default, 75 %, 100 %.",
      "La <b>ligne d'état</b> affiche seulement le réglage du potard, de l'inverseur ou du footswitch que vous venez de bouger (potards en %, par ex. <i>gain 76 %</i>, <i>eq off</i>, <i>laerm</i>, <i>boost on</i>), en grands caractères bien lisibles ; elle apparaît quand un réglage bouge et s'efface au bout de 2,5 s. La <b>barre de presets</b> en dessous affiche en permanence le preset, le mode et l'état boost / bypass."],
 bar_cap="Ligne d'état (la commande que vous venez de bouger) et barre de presets.",
 pre_t="7. Presets",
 pre=["Utilisez les flèches de la barre de presets, cliquez sur son nom, faites un clic droit n'importe où, ou passez par le menu de presets de votre DAW. Clic droit &gt; <b>Save user preset</b> enregistre jusqu'à 9 presets personnels."],
 fac_hdr=["PC", "Preset", "Gain / Boost / Level", "Treble / Mids / Bass", "EQ · Mode", "Description"],
 tips_t="8. Conseils d'utilisation",
 tips=["Dans Reaper, placez Doorn <b>avant</b> votre simulateur d'ampli (par exemple avant Two Notes Genome) avec un ampli assez clair, comme avec la vraie pédale. Avec un ampli crunch, baissez le gain : la Stampede en a déjà beaucoup.",
       "Pour les accordages bas (Si standard comme Amenra, ou une 7 cordes en Sol et plus bas), gardez BASS entre midi et 13 h et servez-vous du BOOST : il resserre le grave sans perdre de poids.",
       "Les modes préférés du testeur d'origine sont SDT-1 et Laerm ; SDT-2 est parfait pour les longs accords saturés.",
       "S'il reste du souffle quand vous arrêtez de jouer, passez clic droit &gt; Noise gate sur Strong ; pour des arrêts très secs sur les riffs saccadés, NGATE de Studio Wiga peut toujours être ajouté après Doorn."],
 tech_t="9. Caractéristiques techniques et historique des versions",
 tech=[["Format", "VST3 (Windows 64 bits, macOS universel)"], ["Canaux", "Mono ou stéréo"],
       ["Latence", "32 échantillons (filtre de sur-échantillonnage), annoncée au DAW"], ["Gain", "environ 26 à 72 dB, + 0 à 20 dB de boost"],
       ["EQ", "graves 90 Hz + punch 120 Hz -15 / +18 dB, médiums 1 kHz ±12 dB, aigus 3 kHz -15 / +22 dB, bypassable"],
       ["Traitement", "sur-échantillonnage x4, paramètres lissés, pas de dénormaux"], ["Processeur", "environ 4 % d'un cœur à 48 kHz (stéréo)"]],
 hist=[["1.0.0", "Première version : modèle Thorn / Stampede SDT-1 avec les voix SDT-1, SDT-2 et Laerm, boost additif, EQ 3 bandes bypassable, footswitchs smart relay, MIDI et pédales d'expression, 10 presets usine et 9 presets utilisateur, format pédale simple d'Echoflex"],
       ["1.0.1 - 1.4.0", "Ligne d'état limitée à la commande que l'on bouge, anti-gel, son plus serré, pédale agrandie, LED rouge seule et potard BOOST éclairé, son calé sur un enregistrement de la vraie Thorn, police de ligne d'état lisible"],
       ["1.5.0 - 1.9.0", "Plus de gain et de mordant sans boost, grave serré (tenu à l'écart de l'écrêtage puis rendu après), sortie qui suit le jeu, BASS avec du punch, boost bien audible"],
       ["2.0.0 - 2.3.0", "Grain et gras stoner : couche fuzz en parallèle façon Big Muff qui passe devant la distorsion (fuzz environ 62 %), bosse de corps vers 220 Hz, voix stoner médium / médium-aigu (poussée vers 900 Hz et 2,3 kHz, fini le son sourd), grave et bas-médiums de retour avec de la présence, marge gardée pour ne rien écraser"],
       ["2.4.0", "TREBLE monte beaucoup plus : jusqu'à +21 dB (au lieu de +15) avec de la brillance en plus vers 4,5 kHz ; la coupe ne change pas"],
       ["2.5.0", "BASS monte plus aussi (jusqu'à +18 dB) ; courses de BASS et TREBLE douces et naturelles, plus de changement brusque à midi ; anti-gel renforcé pour la fenêtre (aucun calcul lourd au dessin, chien de garde, aucun appel à l'hôte depuis le thread audio), JUCE 8.0.15"],
       ["2.6.0", "Noise gate intégré (clic droit &gt; Noise gate : Off / Light / Medium / Strong, Medium par défaut) : plus de souffle ni de ronflement quand on arrête de jouer, attaques jamais coupées, notes qui s'éteignent naturellement"],
       ["2.7.0", "Son plus clair et plus défini sur tous les presets : filtres passe-bas du circuit ouverts, plus d'harmoniques aiguës avant l'écrêtage, définition vers 4 kHz et air vers 6 kHz, anti-grésillement au-dessus de 11 kHz, poussée nasale des médiums allégée ; graves et médiums conservés. Presets avec TREBLE au maximum baissés (Signature Start, Wall of Thorns, Hardcore Bite)"]],
 ver_h=["Version", "Changements"]),
}

W = A4[0] - 36 * mm
def section(lang):
    t = T[lang]; f = []
    f.append(NextPageTemplate("p"))
    f.append(Spacer(1, 2 * mm))
    f.append(P(t["lang"], "coverlang"))
    f.append(Spacer(1, 2 * mm))
    f.append(img(cover, W * 0.56))
    f.append(Spacer(1, 1 * mm))
    f.append(P("D O O R N", "cover"))
    f.append(P(t["sub"], "coversub"))
    f.append(Spacer(1, 2 * mm))
    f.append(P(t["ver"], "coversub"))
    f.append(Spacer(1, 6 * mm))
    f.append(img(os.path.join(ROOT, "assets", "logo_studio_wiga_blanc.png"), 52 * mm))
    f.append(PageBreak())
    f.append(P(t["intro_t"], "h1")); f += [P(x) for x in t["intro"]]
    f.append(P(t["inst_t"], "h1"))
    for h, x in t["inst"]: f.append(P(h, "h2")); f.append(P(x))
    f.append(PageBreak())
    f.append(P(t["ov_t"], "h1"))
    ov = Table([[img(annotated, 92 * mm), table(t["ov_rows"], [9 * mm, 25 * mm, W - 96 * mm - 34 * mm])]],
               colWidths=[96 * mm, W - 96 * mm])
    ov.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    f.append(ov)
    f.append(PageBreak())
    f.append(P(t["ctl_t"], "h1"))
    for h, x in t["ctl"]: f.append(P(h, "h2")); f.append(P(x))
    f.append(KeepTogether([Spacer(1, 3 * mm), img(modes_img, W * 0.50), P(t["modes_cap"], "small")]))
    f.append(P(t["fs_t"], "h1")); f += bullets(t["fs"])
    f.append(KeepTogether([Spacer(1, 2 * mm), img(leds_img, W * 0.60), P(t["led_cap"], "small")]))
    f.append(Spacer(1, 3 * mm))
    f.append(KeepTogether([table([t["midi_hdr"]] + t["midi"], [42 * mm, W - 42 * mm])]))
    f.append(P(t["win_t"], "h1")); f.append(P(t["win"][0]))
    wt = Table([[[P(t["win"][1])], [img(bar_img, 62 * mm), P(t["bar_cap"], "small")]]], colWidths=[W - 66 * mm, 66 * mm])
    wt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
    f.append(wt)
    f.append(CondPageBreak(150 * mm))
    f.append(P(t["pre_t"], "h1")); f += [P(x) for x in t["pre"]]
    rows = [t["fac_hdr"]]
    for i, (n, g, b, l, tr, mi, ba, eq, mo, bo) in enumerate(FACTORY):
        em = ("on" if eq else "off") + " · " + MODES[mo] + (" + boost" if bo else "")
        rows.append([str(i + 1), "<b>" + n + "</b>", f"{pc(g)} / {pc(b)} / {pc(l)}", f"{pc(tr)} / {pc(mi)} / {pc(ba)}", em, FACT_DESC[lang][i]])
    f.append(table(rows, [10 * mm, 29 * mm, 27 * mm, 27 * mm, 22 * mm, W - 115 * mm]))
    f.append(P(t["tips_t"], "h1")); f += bullets(t["tips"])
    f.append(KeepTogether([P(t["tech_t"], "h1"), table(t["tech"], [30 * mm, W - 30 * mm], header=False)])); f.append(Spacer(1, 4 * mm))
    f.append(table([t["ver_h"]] + t["hist"], [22 * mm, W - 22 * mm], small=True))
    f.append(PageBreak())
    return f

def deco(c, doc):
    c.saveState()
    c.setFillColor(DARK); c.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, A4[1] - 6.8 * mm, A4[0], 0.8 * mm, stroke=0, fill=1)
    c.setFont("Pop", 7.5); c.setFillColor(GREY)
    c.drawString(18 * mm, 10 * mm, "Doorn (Studio Wiga) · v" + VERSION)
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    c.restoreState()

doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                      title="DOORN - Manual / Notice v" + VERSION, author="Studio Wiga")
def cover_bg(c, doc):
    c.saveState(); c.setFillColor(colors.black); c.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, A4[1] - 3 * mm, A4[0], 3 * mm, stroke=0, fill=1); c.restoreState()
doc.addPageTemplates([PageTemplate(id="cover", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="fc")], onPage=cover_bg),
                      PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=deco)])
en = section("en"); fr = section("fr")
en[-1:] = [NextPageTemplate("cover"), PageBreak()]
story = en + fr[:-1]
doc.build(story)
print(OUT)
