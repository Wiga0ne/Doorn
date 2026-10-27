# Doorn (Studio Wiga) — VST3

Distorsion high gain au format pédale simple (référence de format : Echoflex), reproduction de la
**Lichtlaerm Audio Thorn**, la pédale signature de Lennart Bossu (Amenra), elle-même rétro-conçue à partir de la
**Providence Stampede SDT-1**. *Doorn* veut dire « épine » en néerlandais.
Usage personnel. Windows 11 et macOS (binaire universel).

## Installation via GitHub

1. Le push sur `main` lance la compilation (onglet **Actions**) : Windows (`windows-2022`) et macOS.
2. Télécharger l'artefact :
   - **Windows** : copier `Doorn.vst3` dans `C:\Program Files\Common Files\VST3\`
   - **macOS** : dézipper puis copier `Doorn.vst3` dans `~/Library/Audio/Plug-Ins/VST3/`
     (premier lancement : `xattr -cr ~/Library/Audio/Plug-Ins/VST3/Doorn.vst3` si macOS le bloque)
3. Relancer l'analyse des plugins. Le plugin apparaît comme **Doorn (Studio Wiga)**.

## La pédale d'origine et le plugin

| Élément | Thorn / SDT-1 | Dans Doorn |
|---|---|---|
| GAIN | Distorsion dure, mur de son, passe en fuzz au-delà de 13 h | 20 à 72 dB répartis sur deux étages d'ampli op (alimentation ~18 V par pompe de charge : grande réserve), écrêtage par diodes à la masse, sur-échantillonnage x4 |
| LEVEL | Volume de sortie | Courbe audio, 0 = coupé, maxi = 0 dBFS de marge |
| BOOST (petit potard + footswitch) | Boost réglable, **additif** : s'ajoute au gain, resserre l'attaque, ajoute du sustain | 0 à +14 dB avant l'écrêtage + passe-haut d'entrée remonté (grave plus serré) |
| TREBLE / MIDS / BASS | EQ actif 3 bandes, médium à 1 kHz | Plateau grave 100 Hz ±15 dB, cloche 1 kHz ±12 dB, plateau aigu 3 kHz ±15 dB ; midi = plat. Voix du circuit calée sur un enregistrement de la vraie Thorn : médiums creusés (≈ −12 dB vers 650 Hz), grave serré (passe-haut 4e ordre avant l'écrêtage, grave qui suit le jeu), écrêtage franc, mordant intégré sans boost, sortie qui suit la dynamique du jeu (pas d'effet compressé), caractère metal / stoner |
| EQ off / on | L'EQ off retire complètement le tone stack du circuit (Lennart dans un Ampeg V4, EQ off) | En OFF, l'EQ n'est plus dans le trajet du signal (fondu sans clic) |
| Mode SDT-1 | Le son de la Stampede d'origine | Silicium à la masse, médiums qui chantent, harmoniques paires |
| Mode SDT-2 | Plus compressé et saturé, un peu moins fort (Living Gate) | Étage de compression en plus, plus sombre, ≈ −3 dB |
| Mode Laerm | Plus ouvert, plus direct, plus fort | Seuil d'écrêtage plus haut (type LED), bande passante plus large, ≈ +4 dB |
| Footswitch BYPASS | Relais « Smart Relay » | Clic = on / off ; **appui maintenu** (> 0,45 s) quand l'effet était coupé = fonctionnement momentané (désactivable, clic droit > Settings) |
| Footswitch BOOST | Boost on / off | Même comportement que BYPASS |
| LED | Une seule LED entre les footswitchs | Rouge = effet actif ; la façade s'éclaire autour. Boost engagé : le potard BOOST transparent s'éclaire de l'intérieur et son curseur devient visible |

Sources : fiche Lichtlaerm Audio (lichtlaermaudio.com/shop/thorn), test Guitar Pedal X, Effects Database,
manuel Providence SDT-2, tests MusicRadar / Vintage Guitar de la Stampede DT, Premier Guitar (Rig Rundown Amenra,
Kurt Ballou), guide de montage GCI Brutalist Jr (clone de la SDT-1), photo du circuit imprimé de la Thorn
(LT1054 = pompe de charge, ATtiny85 + 2 relais Omron G6K = Smart Relay).

## Interface

- Fenêtre ouverte à **493 px de haut** (391 × 493), impossible de la réduire en dessous, proportions bloquées, jusqu'à 150 % (mêmes réglages qu'Echoflex). Clic droit > *Window size* : défaut / 75 % / 100 %.
- **Barre de presets** sous la ligne d'état : flèches = preset précédent / suivant, clic sur le nom = menu (presets d'usine, presets utilisateur 1 à 9).
- **Ligne d'état** : uniquement le réglage de la commande que l'on bouge (potards en %, inverseurs, footswitchs), en police Poppins, grande et lisible ; apparaît quand un réglage bouge, puis s'efface.
- **Anti-gel** (Windows) : moteur de rendu logiciel forcé, timer 30 Hz qui ne redessine que ce qui a changé (LED fixe, aucun redessin au repos), images en cache, jamais de redimensionnement forcé par la fenêtre.
- Potards : seul le repère blanc tourne, les reflets du chapeau restent fixes (lumière en haut à gauche). Double-clic = midi.
- Inverseurs : photo des switchs de la vraie Thorn (positions bas et centre), position haute reconstituée avec la même lumière ; clic = bascule (inverseur 3 positions : clic au-dessus / en dessous du pivot), molette possible.
- Footswitchs : celui d'Echoflex (référence Studio Wiga), bouton assombri tant qu'on appuie.
- Jacks du kit Studio Wiga en haut (OUT à gauche, IN à droite), logo Studio Wiga, nom **DOORN** à la place de « THORN ».

## MIDI

| Message | Fonction |
|---|---|
| CC 20 / 21 / 22 | Gain / Boost (niveau) / Level |
| CC 23 / 24 / 25 | Treble / Mids / Bass |
| CC 52 à 57 | Poids faible 14 bits des CC 20 à 25 (si la pédale l'envoie) |
| CC 26 | EQ (≥ 64 on) |
| CC 27 | Mode (0-42 SDT-2, 43-84 Laerm, 85-127 SDT-1) |
| CC 28 | Footswitch BOOST |
| CC 29 | Footswitch BYPASS |
| Program Change 1 à 10 | Presets d'usine |

Footswitchs MIDI à accrochage (127 = on / 0 = off, par défaut) ou momentanés (bascule à chaque appui) : clic droit > Settings.
Pédale d'expression sans saccades : rampe vers chaque nouvelle valeur sur l'intervalle mesuré entre deux CC,
course de la pédale apprise automatiquement (0 et 100 % exacts même si elle n'envoie que 2 à 116), zones mortes aux butées.
Tous les paramètres sont aussi automatisables dans le DAW.

## Presets d'usine

1. Signature Start (réglage de départ du test Guitar Pedal X) · 2. Wall of Thorns · 3. V4 EQ Bypass · 4. Living Gate Saturation ·
5. Laerm Open · 6. Laerm Lead Boost · 7. Stampede Crunch · 8. Hardcore Bite · 9. Sludge Sustain · 10. Thorn Reference (réglages d'une vraie Thorn, sur lesquels le son a été calé)

## Fichiers

- `DoornDSP.h` : moteur audio (sans JUCE, testé par `tests/test_dsp.cpp`).
- `PluginProcessor.*`, `PluginEditor.*` : plugin JUCE 8.0.4.
- `background.jpg`, `toggle_strip.png`, `glow_red.png`, `Poppins-Medium.ttf` : visuel intégré.
- `tools/make_background.py` (fond), `tools/switch_photo.py` (inverseurs), `tools/controls_art.py` (footswitch), `tools/render/` (captures de la vraie fenêtre sous Linux).
- `design/` : visuel fourni, photo du circuit imprimé, photo des switchs.
- Polices : Poppins (ligne d'état), Fondamento et Alegreya SC (inscriptions du fond) (SIL Open Font License, `assets/OFL_*.txt`).
