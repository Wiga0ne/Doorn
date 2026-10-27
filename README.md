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
| BOOST (petit potard + footswitch) | Boost réglable, **additif** : s'ajoute au gain, resserre l'attaque, ajoute du sustain | 0 à +20 dB avant l'écrêtage, passe-haut d'entrée remonté (grave plus serré), jusqu'à +4 dB de niveau et poussée vers 1,6 kHz (bien audible) |
| TREBLE / MIDS / BASS | EQ actif 3 bandes, médium à 1 kHz | Grave : plateau 90 Hz + bosse de punch vers 120 Hz −15 / +18 dB (après la distorsion, sans compression), cloche 1 kHz ±12 dB, plateau aigu 3 kHz −15 / +22 dB (brillance vers 4,5 kHz qui arrive progressivement) ; midi = plat, courses BASS / TREBLE douces et continues (fines autour de midi, plus fortes vers les butées, aucun saut). Voix du circuit calée sur un enregistrement de la vraie Thorn : voix stoner médium / médium-aigu (poussée 900 Hz et 2,3 kHz) sur un bas présent (grave vers 100 Hz, corps vers 220 / 320 Hz), grave serré (grave retiré avant l'écrêtage puis rendu après, liaison de 180 Hz entre étages, grave qui suit le jeu), mordant à 1,8 kHz avant l'écrêtage, définition sans sifflement (v2.8) : aigus limités avant l'écrêtage (2 pôles 5 / 7 kHz, pour ne pas amplifier le souffle et l'intermodulation des partiels aigus de la corde), clarté vers 3,2 kHz après l'écrêtage, là où ses harmoniques restent nettes, sortie refermée au-dessus de ~9 kHz, écrêtage franc, mordant intégré sans boost, sortie qui suit la dynamique du jeu (pas d'effet compressé), caractère metal / stoner : couche fuzz façon Big Muff mélangée à la distorsion (environ 40 % fuzz / 60 % distorsion dans le son, grain fuzz) et bosse de corps vers 220 Hz (gras) |
| EQ off / on | L'EQ off retire complètement le tone stack du circuit (Lennart dans un Ampeg V4, EQ off) | En OFF, l'EQ n'est plus dans le trajet du signal (fondu sans clic) |
| Mode SDT-1 | Le son de la Stampede d'origine | Silicium à la masse, médiums qui chantent, harmoniques paires |
| Mode SDT-2 | Plus compressé et saturé, un peu moins fort (Living Gate) | Étage de compression en plus, plus sombre, ≈ −3 dB |
| Mode Laerm | Plus ouvert, plus direct, plus fort | Seuil d'écrêtage plus haut (type LED), bande passante plus large, ≈ +4 dB |
| Footswitch BYPASS | Relais « Smart Relay » | Clic = on / off ; **appui maintenu** (> 0,45 s) quand l'effet était coupé = fonctionnement momentané (désactivable, clic droit > Settings) |
| Footswitch BOOST | Boost on / off | Même comportement que BYPASS |
| Noise gate (ajout Doorn) | — (la Thorn est bruyante à fort gain) | Clic droit > *Noise gate* : Off / Light / Medium (défaut) / Strong. Détection sur l'entrée, en avance de 32 échantillons sur le signal traité (attaques intactes), hystérésis 6 dB, maintien 60 ms, fermeture douce 120 ms ; n'agit que sur l'effet. Souffle de −80 dBFS en entrée : −9 dBFS en sortie sans gate, silence avec |
| LED | Une seule LED entre les footswitchs | Rouge = effet actif ; la façade s'éclaire autour. Boost engagé : le potard BOOST transparent s'éclaire de l'intérieur et son curseur devient visible |

Sources : fiche Lichtlaerm Audio (lichtlaermaudio.com/shop/thorn), test Guitar Pedal X, Effects Database,
manuel Providence SDT-2, tests MusicRadar / Vintage Guitar de la Stampede DT, Premier Guitar (Rig Rundown Amenra,
Kurt Ballou), guide de montage GCI Brutalist Jr (clone de la SDT-1), photo du circuit imprimé de la Thorn
(LT1054 = pompe de charge, ATtiny85 + 2 relais Omron G6K = Smart Relay).

## Interface

- Fenêtre ouverte à **493 px de haut** (391 × 493), impossible de la réduire en dessous, proportions bloquées, jusqu'à 150 % (mêmes réglages qu'Echoflex). Clic droit > *Window size* : défaut / 75 % / 100 %.
- **Barre de presets** sous la ligne d'état : flèches = preset précédent / suivant, clic sur le nom = menu (presets d'usine, presets utilisateur 1 à 9).
- **Ligne d'état** : uniquement le réglage de la commande que l'on bouge (potards en %, inverseurs, footswitchs), en police Poppins, grande et lisible ; apparaît quand un réglage bouge, puis s'efface.
- **Anti-gel v2** : moteur de rendu logiciel forcé sous Windows (réappliqué à chaque nouvelle fenêtre hôte), fenêtre opaque, timer 30 Hz qui ne redessine que ce qui a changé (aucun redessin au repos), aucun calcul lourd dans le dessin (caches d'images reconstruits par le timer seulement, après stabilisation de la taille ou changement d'échelle), chien de garde qui relance le rendu si un redessin n'arrive pas en 1,5 s, jamais de redimensionnement forcé par la fenêtre ; côté audio, aucun appel à l'hôte ni allocation depuis le thread audio (les changements MIDI passent par une file vidée sur le thread de messages, paramètres lus par pointeurs mis en cache). JUCE 8.0.15.
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
- `PluginProcessor.*`, `PluginEditor.*` : plugin JUCE 8.0.15.
- `background.jpg`, `toggle_strip.png`, `glow_red.png`, `Poppins-Medium.ttf` : visuel intégré.
- `tools/make_background.py` (fond), `tools/switch_photo.py` (inverseurs), `tools/controls_art.py` (footswitch), `tools/render/` (captures de la vraie fenêtre sous Linux).
- `design/` : visuel fourni, photo du circuit imprimé, photo des switchs.
- Polices : Poppins (ligne d'état), Fondamento et Alegreya SC (inscriptions du fond) (SIL Open Font License, `assets/OFL_*.txt`).
