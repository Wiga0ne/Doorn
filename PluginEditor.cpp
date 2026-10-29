#include "PluginEditor.h"
#include "BinaryData.h"
#include "Layout.h"

using namespace juce;

namespace
{
    // Positions dans le repere de reference 760 x 958 (fond 1520 x 1916 = 2 x 760 x 958),
    // generees par tools/make_background.py dans Layout.h (pedale agrandie en v1.1, commandes a l'echelle)
    const Point<float>* const knobPos = layout::knobPos;
    const float knobR = layout::knobR, miniR = layout::miniR;
    const Point<float> eqPos = layout::eqPos, modePos = layout::modePos;
    const float leverHalf = 48.0f * layout::sc;     // demi-cote du sprite de l'inverseur (96 unites en v1.0)
    const Point<float> ledPos = layout::ledPos;
    const float ledR = 8.6f * layout::sc;
    const Rectangle<float> glowRect = layout::glowRect;
    const Point<float> boostPos = layout::boostPos, bypassPos = layout::bypassPos;
    const float footR = 60.0f * layout::sc;
    // ligne d'etat et barre de presets : entre les inscriptions des inverseurs et la LED
    const Rectangle<float> statusRect { 196.0f, 590.0f, 368.0f, 50.0f };   // v2.10 : plus grande et plus contrastee
    const Rectangle<float> presetRect { 186.0f, 645.0f, 388.0f, 37.0f };

    const float rotStart = MathConstants<float>::pi * (7.0f / 6.0f);    // -150 degres
    const float rotEnd   = MathConstants<float>::pi * (17.0f / 6.0f);   // +150 degres

    const Colour redCore (0xffffd6c8), redMid (0xffff2616), redDeep (0xff8c0504);
    const Colour inkWhite (0xffececec);

    const char* const valueIds[] = { "gain", "boost", "level", "treble", "mids", "bass", "eq", "mode", "boostOn", "active", "gate" };
    constexpr int numValueIds = 11;
}

//==============================================================================
// POTARDS
//==============================================================================
bool DoornKnob::hitTest (int x, int y)
{
    const auto c = getLocalBounds().toFloat().getCentre();
    return c.getDistanceFrom ({ (float) x, (float) y }) <= getWidth() * 0.5f;
}

void DoornKnobLookAndFeel::drawRotarySlider (Graphics& g, int x, int y, int w, int h,
                                             float pos, float startAngle, float endAngle, Slider& s)
{
    const auto* k = dynamic_cast<DoornKnob*> (&s);
    const bool mini = k != nullptr && k->isMini;
    const auto c = Rectangle<float> ((float) x, (float) y, (float) w, (float) h).getCentre();
    const float R = (float) jmin (w, h) * 0.5f;          // = rayon du potard a l'ecran
    const float a = startAngle + pos * (endAngle - startAngle);

    if (! mini)
    {
        // fleche blanche peinte sur le chapeau (forme du visuel) ; lumiere fixe en haut a gauche :
        // la peinture est un peu plus claire tournee vers la lumiere, ombre tres legere en bas a droite
        Path p;
        p.startNewSubPath (0.0f, -0.757f * R);
        p.lineTo ( 0.180f * R, -0.270f * R);
        p.lineTo ( 0.0f,       -0.360f * R);
        p.lineTo (-0.180f * R, -0.270f * R);
        p.closeSubPath();
        const auto tr = AffineTransform::rotation (a).translated (c);
        const float lightFacing = 0.5f + 0.5f * std::cos (a + MathConstants<float>::pi * 0.25f);
        g.setColour (Colours::black.withAlpha (0.42f));
        g.fillPath (p, tr.translated (R * 0.008f, R * 0.010f));
        g.setColour (Colour::greyLevel (0.90f + 0.08f * lightFacing));
        g.fillPath (p, tr);
    }
    else
    {
        // petit potard BOOST transparent (fume) : eclaire de l'interieur quand le boost est enclenche,
        // le curseur (barrette) apparait alors nettement ; boost coupe = curseur sombre a peine visible
        const float lit = k != nullptr ? k->lit : 0.0f;
        const Colour warm (0xffffd9a0);
        if (lit > 0.001f)
        {
            ColourGradient glow (warm.withAlpha (0.78f * lit), c.x, c.y, warm.withAlpha (0.0f), c.x + R * 0.98f, c.y, true);
            glow.addColour (0.55, warm.withAlpha (0.42f * lit));
            g.setGradientFill (glow);
            g.fillEllipse (c.x - R * 0.98f, c.y - R * 0.98f, R * 1.96f, R * 1.96f);
        }
        const float r0 = 0.22f * R, r1 = 0.88f * R, bw = 0.20f * R;
        const Point<float> p0 = c + Point<float> (std::sin (a), -std::cos (a)) * r0;
        const Point<float> p1 = c + Point<float> (std::sin (a), -std::cos (a)) * r1;
        Path bar; bar.addLineSegment ({ p0, p1 }, bw);
        // eteint : barrette grise dans l'ombre du dome fume ; allume : blanche, avec un leger halo de diffusion
        if (lit > 0.001f)
        {
            g.setColour (Colours::white.withAlpha (0.30f * lit));
            g.strokePath (bar, PathStrokeType (bw * 2.2f, PathStrokeType::curved, PathStrokeType::rounded));
        }
        g.setColour (Colours::black.withAlpha (0.25f * (1.0f - lit)));
        g.drawLine ({ p0.translated (0.6f, 0.8f), p1.translated (0.6f, 0.8f) }, bw);
        g.setColour (Colour (0xff6d7376).interpolatedWith (Colours::white, lit).withAlpha (0.80f + 0.20f * lit));
        g.strokePath (bar, PathStrokeType (bw, PathStrokeType::curved, PathStrokeType::rounded));
        // reflet du dome par-dessus (fixe)
        ColourGradient sh (Colours::white.withAlpha (0.18f), c.x - R * 0.35f, c.y - R * 0.55f,
                           Colours::white.withAlpha (0.0f), c.x, c.y, true);
        g.setGradientFill (sh);
        g.fillEllipse (c.x - R * 0.85f, c.y - R * 0.85f, R * 1.1f, R * 0.9f);
    }
}

//==============================================================================
// INVERSEUR
//==============================================================================
LeverSwitch::LeverSwitch (RangedAudioParameter& p, int numPositions)
    : attachment (p, [this] (float v)
                  {
                      const int np = jlimit (0, positions - 1, roundToInt (v));
                      if (np != pos)
                      {
                          const int from = frameFor (pos);
                          pos = np;
                          targetFrame = frameFor (pos);
                          shownFrame = (from + targetFrame) / 2;          // position intermediaire ~55 ms
                          if (shownFrame == from || shownFrame == targetFrame) shownFrame = targetFrame;
                          transitionUntil = Time::getMillisecondCounterHiRes() + 55.0;
                          repaint();
                      }
                  }),
      positions (numPositions)
{
    attachment.sendInitialUpdate();
    shownFrame = targetFrame = frameFor (pos);
    setMouseCursor (MouseCursor::PointingHandCursor);
}

int LeverSwitch::frameFor (int p) const
{
    if (positions == 2) return p == 0 ? 0 : 4;
    return jlimit (0, 4, p * 2);
}

void LeverSwitch::tick (double now)
{
    if (shownFrame != targetFrame && now >= transitionUntil)
    {
        shownFrame = targetFrame;
        repaint();
    }
}

void LeverSwitch::paint (Graphics& g)
{
    if (! strip.isValid()) return;
    const int fs = strip.getWidth();
    g.setImageResamplingQuality (Graphics::highResamplingQuality);
    g.drawImage (strip, 0, 0, getWidth(), getHeight(), 0, shownFrame * fs, fs, fs);
}

void LeverSwitch::moveTo (int np)
{
    np = jlimit (0, positions - 1, np);
    if (np == pos) return;
    attachment.setValueAsCompleteGesture ((float) np);
    if (onUserChange) onUserChange();
}

void LeverSwitch::mouseDown (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) { if (onRightClick) onRightClick(); return; }
    if (positions == 2) { moveTo (1 - pos); return; }
    // inverseur 3 positions : clic au-dessus du centre = levier vers le haut, en dessous = vers le bas
    const bool upper = e.position.y < getHeight() * 0.5f;
    if (upper) moveTo (pos > 0 ? pos - 1 : pos);
    else       moveTo (pos < positions - 1 ? pos + 1 : pos);
}

void LeverSwitch::mouseWheelMove (const MouseEvent&, const MouseWheelDetails& w)
{
    if (std::abs (w.deltaY) > 0.0f) moveTo (pos + (w.deltaY > 0 ? -1 : 1));
}

//==============================================================================
// FOOTSWITCH
//==============================================================================
FootSwitchArea::FootSwitchArea (RangedAudioParameter& p, std::atomic<float>* holdMomentary)
    : hold (holdMomentary),
      attachment (p, [this] (float v) { value = v > 0.5f; repaint(); })
{
    attachment.sendInitialUpdate();
    setMouseCursor (MouseCursor::PointingHandCursor);
}

bool FootSwitchArea::hitTest (int x, int y)
{
    const auto c = getLocalBounds().toFloat().getCentre();
    return c.getDistanceFrom ({ (float) x, (float) y }) <= (float) getWidth() * 0.5f;
}

void FootSwitchArea::paint (Graphics& g)
{
    if (pressed)
    {
        g.setColour (Colours::black.withAlpha (0.25f));
        g.fillEllipse (getLocalBounds().toFloat().reduced ((float) getWidth() * 0.23f));
    }
}

void FootSwitchArea::mouseDown (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) { if (onRightClick) onRightClick(); return; }
    pressed = true;
    downTime = Time::getMillisecondCounterHiRes();
    turnedOnByPress = ! value;
    repaint();
    attachment.setValueAsCompleteGesture (value ? 0.0f : 1.0f);    // bascule des l'appui (comme Echoflex)
    if (onUserChange) onUserChange();
}

void FootSwitchArea::mouseUp (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) return;
    // « Smart relay » : appui maintenu = momentane -> on relache, ca se coupe
    const bool momentary = hold != nullptr && hold->load() > 0.5f;
    if (pressed && momentary && turnedOnByPress && Time::getMillisecondCounterHiRes() - downTime > 450.0 && value)
    {
        attachment.setValueAsCompleteGesture (0.0f);
        if (onUserChange) onUserChange();
    }
    pressed = false;
    repaint();
}

//==============================================================================
// EDITEUR
//==============================================================================
DoornAudioProcessorEditor::DoornAudioProcessorEditor (DoornAudioProcessor& p)
    : AudioProcessorEditor (&p), proc (p),
      eqSwitch   (*p.apvts.getParameter ("eq"), 2),
      modeSwitch (*p.apvts.getParameter ("mode"), 3),
      boostFs  (*p.apvts.getParameter ("boostOn"), p.apvts.getRawParameterValue ("holdMomentary")),
      bypassFs (*p.apvts.getParameter ("active"),  p.apvts.getRawParameterValue ("holdMomentary"))
{
    background = ImageCache::getFromMemory (BinaryData::background_jpg, BinaryData::background_jpgSize);
    glowRed    = ImageCache::getFromMemory (BinaryData::glow_red_png,   BinaryData::glow_red_pngSize);
    const auto strip = ImageCache::getFromMemory (BinaryData::toggle_strip_png, BinaryData::toggle_strip_pngSize);
    // police lisible et standard (sans empattement) pour la ligne d'etat et la barre de presets
    labelFace = Typeface::createSystemTypefaceFor (BinaryData::PoppinsMedium_ttf, BinaryData::PoppinsMedium_ttfSize);

    rightClickFwd.callback = [this] (Component* c)
    {
        int idx = -1;
        for (int i = 0; i < DoornAudioProcessor::numKnobs; ++i)
            if (c == &knobs[i]) idx = i;
        showContextMenu (idx);
    };

    for (int i = 0; i < DoornAudioProcessor::numKnobs; ++i)
    {
        auto& s = knobs[i];
        s.isMini = (i == 1);
        s.setSliderStyle (Slider::RotaryHorizontalVerticalDrag);
        s.setTextBoxStyle (Slider::NoTextBox, false, 0, 0);
        s.setRotaryParameters (rotStart, rotEnd, true);
        s.setMouseDragSensitivity (220);
        s.setDoubleClickReturnValue (true, 5.0);
        s.setLookAndFeel (&lnf);
        s.setMouseCursor (MouseCursor::PointingHandCursor);
        s.addMouseListener (&rightClickFwd, false);
        s.onDragStart = [this] { proc.currentPreset = -1; };
        addAndMakeVisible (s);
        knobAtt[i] = std::make_unique<AudioProcessorValueTreeState::SliderAttachment> (proc.apvts, DoornAudioProcessor::knobId (i), s);
    }

    eqSwitch.onRightClick   = [this] { showContextMenu (6); };
    modeSwitch.onRightClick = [this] { showContextMenu (7); };
    for (auto* l : { &eqSwitch, &modeSwitch })
    {
        l->strip = strip;
        l->onUserChange = [this] { proc.currentPreset = -1; };
        addAndMakeVisible (*l);
    }
    boostFs.onRightClick  = [this] { showContextMenu (8); };
    bypassFs.onRightClick = [this] { showContextMenu (9); };
    boostFs.onUserChange  = [this] { proc.currentPreset = -1; };
    addAndMakeVisible (boostFs);
    addAndMakeVisible (bypassFs);

    for (int i = 0; i < numValueIds; ++i)
        lastValues[i] = proc.raw (valueIds[i]);
    lastPresetCounter = proc.presetCounter.load();
    lastMidiCount = proc.midiCounter.load();
    ledLevel = proc.raw ("active") > 0.5f ? 1.0f : 0.0f;
    boostLit = proc.raw ("boostOn") > 0.5f ? 1.0f : 0.0f;
    knobs[1].lit = boostLit;

    // Taille par defaut = taille minimale (impossible de reduire en dessous), proportions bloquees
    const int defaultW = roundToInt ((float) defaultH * (float) baseW / (float) baseH);
    setResizable (true, true);
    setResizeLimits (defaultW, defaultH, baseW * 3 / 2, baseH * 3 / 2);
    if (auto* cons = getConstrainer())
        cons->setFixedAspectRatio ((double) baseW / (double) baseH);
    setOpaque (true);                      // anti-gel : l'hote ne redessine jamais ce qui est derriere la fenetre
    setSize (defaultW, defaultH);
    rebuildCaches();
    startTimerHz (30);
}

DoornAudioProcessorEditor::~DoornAudioProcessorEditor()
{
    stopTimer();
    for (auto& s : knobs)
    {
        s.removeMouseListener (&rightClickFwd);
        s.setLookAndFeel (nullptr);
    }
}

//==============================================================================
void DoornAudioProcessorEditor::setScaledHeight (int h)
{
    h = jmax ((int) defaultH, h);
    setSize (roundToInt ((float) h * (float) baseW / (float) baseH), h);
}

Rectangle<int> DoornAudioProcessorEditor::scaled (Rectangle<float> r) const
{
    const float s = (float) getHeight() / (float) baseH;
    return r.transformedBy (AffineTransform::scale (s)).getSmallestIntegerContainer();
}

float DoornAudioProcessorEditor::physicalScale() const
{
    return jlimit (1.0f, 4.0f, (float) Component::getApproximateScaleFactorForComponent (this));
}

void DoornAudioProcessorEditor::showStatus()
{
    statusUntil = Time::getMillisecondCounterHiRes() + 2500.0;
}

//==============================================================================
// Caches d'affichage : fond et calques lumineux deja a la taille de la fenetre
//==============================================================================
void DoornAudioProcessorEditor::rebuildCaches (float sc)
{
    if (sc <= 0.0f) sc = cacheScale > 0.0f ? cacheScale : physicalScale();
    const int w = getWidth(), h = getHeight();
    if (w <= 0 || h <= 0) return;
    if (w == cacheW && h == cacheH && std::abs (sc - cacheScale) < 0.01f && bgScaled.isValid()) return;

    cacheW = w; cacheH = h; cacheScale = sc;
    const int pw = roundToInt ((float) w * sc), ph = roundToInt ((float) h * sc);
    bgScaled = (pw >= background.getWidth()) ? background : background.rescaled (pw, ph, Graphics::highResamplingQuality);

    const float s = (float) h / (float) baseH;
    const int gpx = roundToInt (glowRect.getWidth() * s * sc);
    glowRedS   = (gpx >= glowRed.getWidth())   ? glowRed   : glowRed.rescaled   (gpx, gpx, Graphics::highResamplingQuality);

    repaint();
}

void DoornAudioProcessorEditor::resized()
{
    // anti-gel : jamais de setSize ici (mise a l'echelle Windows 125 / 150 % : tolerance de quelques px) ;
    // les limites du constrainer suffisent, sinon boucle de redimensionnement avec l'hote

    for (int i = 0; i < DoornAudioProcessor::numKnobs; ++i)
    {
        const float r = (i == 1) ? miniR : knobR;
        knobs[i].setBounds (scaled ({ knobPos[i].x - r, knobPos[i].y - r, r * 2.0f, r * 2.0f }));
    }
    auto lever = [this] (LeverSwitch& l, Point<float> c)
    {
        l.setBounds (scaled ({ c.x - leverHalf, c.y - leverHalf, leverHalf * 2.0f, leverHalf * 2.0f }));
    };
    lever (eqSwitch, eqPos);
    lever (modeSwitch, modePos);
    boostFs.setBounds  (scaled ({ boostPos.x - footR,  boostPos.y - footR,  footR * 2.0f, footR * 2.0f }));
    bypassFs.setBounds (scaled ({ bypassPos.x - footR, bypassPos.y - footR, footR * 2.0f, footR * 2.0f }));
    resizeSettle = 4;
}

//==============================================================================
// Anti-gel de la fenetre (Windows) : moteur de rendu logiciel
//==============================================================================
// Anti-gel v2 (Studio Wiga) :
//  1. moteur de rendu logiciel force sur Windows (Direct2D peut figer la fenetre dans certains hotes),
//     applique a chaque nouvelle fenetre hote (peer) et reverifie toutes les secondes, jamais en boucle ;
//  2. aucun calcul lourd dans paint() : les caches d'images sont reconstruits par le timer seulement,
//     apres stabilisation de la taille ou quand l'echelle d'affichage change (au plus toutes les 250 ms) ;
//  3. chien de garde : si un redessin demande n'est pas arrive au bout de 1,5 s alors que la fenetre est
//     visible, le moteur de rendu est reapplique et toute la fenetre est redessinee ;
//  4. cote audio : aucun appel a l'hote ni allocation depuis le thread audio (voir PluginProcessor).
void DoornAudioProcessorEditor::useSoftwareRenderer()
{
    auto* peer = getPeer();
    if (peer != lastPeer) { lastPeer = peer; repaint(); }
   #if JUCE_WINDOWS
    if (peer != nullptr)
    {
        int sw = peer->getAvailableRenderingEngines().indexOf ("Software Renderer");
        if (sw < 0) sw = 0;
        if (peer->getCurrentRenderingEngine() != sw)
            peer->setCurrentRenderingEngine (sw);
    }
   #endif
}

void DoornAudioProcessorEditor::parentHierarchyChanged() { useSoftwareRenderer(); }
void DoornAudioProcessorEditor::visibilityChanged()      { useSoftwareRenderer(); if (isShowing()) repaint(); }

void DoornAudioProcessorEditor::askRepaint (Rectangle<int> r)
{
    if (repaintAskedMs <= 0.0) repaintAskedMs = Time::getMillisecondCounterHiRes();
    repaint (r);
}

//==============================================================================
String DoornAudioProcessorEditor::buildStatusLine() const
{
    // seulement le reglage de la commande qui vient de bouger
    const int i = lastChanged;
    if (i < 0) return {};
    const String id = valueIds[i];
    const float v = proc.raw (valueIds[i]);
    if (i < 6) return id + "  " + String (roundToInt (v * 10.0f)) + " %";
    if (id == "eq")      return v > 0.5f ? "eq on" : "eq off";
    if (id == "mode")    return DoornAudioProcessor::modeNames()[jlimit (0, 2, roundToInt (v))].toLowerCase();
    if (id == "boostOn") return v > 0.5f ? "boost on" : "boost off";
    if (id == "gate")    return "noise gate " + DoornAudioProcessor::gateNames()[jlimit (0, 3, roundToInt (v))].toLowerCase();
    return v > 0.5f ? "effect on" : "bypass";
}

String DoornAudioProcessorEditor::buildPresetLine() const
{
    const int cp = proc.currentPreset.load();
    String s;
    if (cp >= 0 && cp < DoornAudioProcessor::getNumFactoryPresets())
        s << "P" << (cp + 1) << "  " << DoornAudioProcessor::getFactoryPreset (cp).name;
    else if (cp > 100) s << "User " << (cp - 100);
    else               s << "Edited";
    s << "  -  " << DoornAudioProcessor::modeNames()[roundToInt (proc.raw ("mode"))];
    if (proc.raw ("boostOn") > 0.5f) s << " + boost";
    if (proc.raw ("active") < 0.5f)  s << "  (bypass)";
    return s;
}

//==============================================================================
void DoornAudioProcessorEditor::timerCallback()
{
    const double now = Time::getMillisecondCounterHiRes();
    if (getPeer() != lastPeer || now - lastRendererCheckMs > 1000.0) { lastRendererCheckMs = now; useSoftwareRenderer(); }

    // caches : reconstruits ici seulement (jamais dans paint)
    if (resizeSettle > 0 && --resizeSettle == 0) rebuildCaches();
    else if (resizeSettle == 0 && now - lastScaleCheckMs > 250.0)
    {
        lastScaleCheckMs = now;
        const float sc = physicalScale();
        if (std::abs (sc - cacheScale) > 0.01f) rebuildCaches (sc);
    }

    // chien de garde : un redessin demande n'arrive pas -> on relance le moteur de rendu et on redessine tout
    if (repaintAskedMs > 0.0 && isShowing() && now - repaintAskedMs > 1500.0 && lastPaintMs < repaintAskedMs)
    {
        repaintAskedMs = 0.0;
        lastPeer = nullptr;
        useSoftwareRenderer();
        repaint();
    }

    eqSwitch.tick (now);
    modeSwitch.tick (now);

    // la ligne d'etat apparait quand un reglage bouge, reste 2,5 s puis s'efface
    int changed = -1, numChanged = 0;
    for (int i = 0; i < numValueIds; ++i)
    {
        const float v = proc.raw (valueIds[i]);
        if (std::abs (v - lastValues[i]) > 1.0e-4f) { lastValues[i] = v; changed = i; ++numChanged; }
    }
    const int pcount = proc.presetCounter.load();
    if (pcount != lastPresetCounter) { lastPresetCounter = pcount; numChanged = 0; }   // preset : affiche dans la barre de presets
    if (numChanged == 1) { lastChanged = changed; showStatus(); learnLineUntil = 0.0; }
    for (int i = 0; i < DoornAudioProcessor::numKnobs; ++i)
        if (knobs[i].isMouseButtonDown()) { lastChanged = i; showStatus(); learnLineUntil = 0.0; }
    // MIDI Learn : attente puis confirmation 2 s dans la ligne d'etat
    const int lt = proc.learnTarget.load();
    const int learned = proc.lastLearned.exchange (-1);
    if (learned >= 0)
    {
        const int cc = proc.ccMap[learned].load();
        learnLine = String (DoornAudioProcessor::learnDef (learned).name) + " = CC " + String (cc);
        learnLineUntil = now + 2000.0;
        statusUntil = jmax (statusUntil, learnLineUntil);
    }
    else if (lt >= 0)
    {
        learnLine = "MIDI LEARN: move a control for " + String (DoornAudioProcessor::learnDef (lt).name);
        learnLineUntil = now + 200.0;
        statusUntil = jmax (statusUntil, now + 200.0);
    }

    const int mc = proc.midiCounter.load();
    if (mc != lastMidiCount) { lastMidiCount = mc; midiFlash = 8; }
    if (midiFlash > 0) --midiFlash;

    const float target = now < statusUntil ? 1.0f : 0.0f;
    statusAlpha += (target - statusAlpha) * (target > statusAlpha ? 0.45f : 0.12f);
    if (statusAlpha < 0.005f) statusAlpha = 0.0f;
    if (statusAlpha > 0.995f) statusAlpha = 1.0f;

    // LED : rouge = effet actif, ambre = boost engage ; fondu (0,45 a l'allumage / 0,28 a l'extinction)
    const bool on = proc.raw ("active") > 0.5f;
    ledLevel += ((on ? 1.0f : 0.0f) - ledLevel) * (on ? 0.45f : 0.28f);
    if (ledLevel < 0.003f) ledLevel = 0.0f;
    if (ledLevel > 0.997f) ledLevel = 1.0f;
    // lumiere du potard BOOST : fondu (0,45 a l'allumage / 0,28 a l'extinction, comme les LED)
    const float boostT = proc.raw ("boostOn") > 0.5f ? 1.0f : 0.0f;
    boostLit += (boostT - boostLit) * (boostT > boostLit ? 0.45f : 0.28f);
    if (std::abs (boostLit - boostT) < 0.003f) boostLit = boostT;
    if (std::abs (boostLit - knobs[1].lit) > 0.003f || (boostLit == boostT && knobs[1].lit != boostT))
    {
        knobs[1].lit = boostLit;
        knobs[1].repaint();
        askRepaint (scaled (Rectangle<float> (knobPos[1].x - miniR * 2.2f, knobPos[1].y - miniR * 2.2f, miniR * 4.4f, miniR * 4.4f)));
    }

    const float ledNow = ledLevel;        // pas de scintillement : au repos, aucun redessin (anti-gel)
    if (std::abs (ledNow - drawnLed) > 0.004f)
    {
        drawnLed = ledNow;
        askRepaint (scaled (glowRect));
    }

    // (le message de learn reste pendant le fondu de sortie)
    const auto l1 = (learnLineUntil > 0.0 && now < learnLineUntil + 800.0 ? learnLine : buildStatusLine()), pl = buildPresetLine();
    const bool textChanged = l1 != lastLine1;
    lastLine1 = l1;
    if (std::abs (statusAlpha - drawnStatus) > 0.003f || (statusAlpha > 0.0f && textChanged))
    {
        drawnStatus = statusAlpha;
        askRepaint (scaled (statusRect.expanded (4.0f)));
    }
    if (pl != lastPreset || hoverZone != drawnHover || midiFlash > 0)
    {
        lastPreset = pl; drawnHover = hoverZone;
        askRepaint (scaled (presetRect.expanded (3.0f)));
    }
}

//==============================================================================
void DoornAudioProcessorEditor::drawLed (Graphics& g)
{
    const float level = ledLevel;
    if (level <= 0.003f) return;

    // la facade recoit la lumiere de la LED (calques precalcules : fond x eclairement x couleur)
    const auto gr = glowRect;
    if (glowRedS.isValid())
    {
        g.setOpacity (level);
        g.drawImage (glowRedS, gr);
    }
    g.setOpacity (1.0f);

    const Colour core = redCore, mid = redMid, deep = redDeep;
    const auto c = ledPos; const float r = ledR;

    // halo optique tres faible autour de la lentille
    ColourGradient halo (mid.withAlpha (0.22f * level), c.x, c.y, mid.withAlpha (0.0f), c.x + r * 2.6f, c.y, true);
    g.setGradientFill (halo);
    g.fillEllipse (c.x - r * 2.6f, c.y - r * 2.6f, r * 5.2f, r * 5.2f);

    ColourGradient body (core.withAlpha (level), c.x - r * 0.10f, c.y - r * 0.12f,
                         deep.withAlpha (level), c.x + r * 1.05f, c.y + r * 0.2f, true);
    body.addColour (0.30, core.interpolatedWith (mid, 0.55f).withAlpha (level));
    body.addColour (0.62, mid.withAlpha (level));
    g.setGradientFill (body);
    g.fillEllipse (c.x - r, c.y - r, r * 2.0f, r * 2.0f);

    g.setColour (deep.darker (0.6f).withAlpha (0.55f * level));
    g.drawEllipse (c.x - r + 0.6f, c.y - r + 0.6f, r * 2.0f - 1.2f, r * 2.0f - 1.2f, r * 0.12f);

    ColourGradient sp (Colours::white.withAlpha (0.75f * level), c.x - r * 0.30f, c.y - r * 0.42f,
                       Colours::white.withAlpha (0.0f), c.x - r * 0.30f + r * 0.32f, c.y - r * 0.42f, true);
    g.setGradientFill (sp);
    g.fillEllipse (c.x - r * 0.62f, c.y - r * 0.70f, r * 0.64f, r * 0.52f);
}

void DoornAudioProcessorEditor::drawStatus (Graphics& g)
{
    const float a = statusAlpha;
    if (a <= 0.0f) return;
    g.setColour (Colour (0xff070a14).withAlpha (0.93f * a));
    g.fillRoundedRectangle (statusRect, 8.0f);
    g.setColour (Colour (0xffb79f6e).withAlpha (0.45f * a));       // filet couleur des fissures dorees
    g.drawRoundedRectangle (statusRect.reduced (0.75f), 9.0f, 1.3f);

    // messages MIDI Learn plus longs : meme police, plus petite, sur deux lignes au besoin
    const bool longLine = lastLine1.length() > 18;
    const Font f (FontOptions (labelFace).withHeight (longLine ? 21.0f : 38.0f));
    g.setFont (f);
    g.setColour (inkWhite.withAlpha (a));
    g.drawFittedText (lastLine1, statusRect.reduced (10.0f, 0.0f).toNearestInt(), Justification::centred, longLine ? 2 : 1, 0.75f);
}

void DoornAudioProcessorEditor::drawPresetBar (Graphics& g)
{
    const auto r = presetRect;
    g.setColour (Colour (0xff070a14).withAlpha (0.85f));
    g.fillRoundedRectangle (r, r.getHeight() * 0.5f);
    g.setColour (Colour (0xffb79f6e).withAlpha (hoverZone != 0 ? 0.65f : 0.32f));
    g.drawRoundedRectangle (r.reduced (0.6f), r.getHeight() * 0.5f, 1.1f);

    const float aw = 34.0f;
    auto arrow = [&] (Rectangle<float> ar, bool left, bool hot)
    {
        Path p;
        const auto c = ar.getCentre();
        const float s = 6.5f;
        if (left) p.addTriangle (c.x + s * 0.6f, c.y - s, c.x + s * 0.6f, c.y + s, c.x - s * 0.8f, c.y);
        else      p.addTriangle (c.x - s * 0.6f, c.y - s, c.x - s * 0.6f, c.y + s, c.x + s * 0.8f, c.y);
        g.setColour (inkWhite.withAlpha (hot ? 1.0f : 0.62f));
        g.fillPath (p);
    };
    arrow (r.withWidth (aw), true, hoverZone == 1);
    arrow (r.withTrimmedLeft (r.getWidth() - aw), false, hoverZone == 3);

    g.setFont (Font (FontOptions (labelFace).withHeight (25.0f)));
    g.setColour ((midiFlash > 0 ? Colour (0xffffc070) : inkWhite).withAlpha (hoverZone == 2 ? 1.0f : 0.88f));
    g.drawFittedText (lastPreset, r.reduced (aw, 0.0f).toNearestInt(), Justification::centred, 1, 0.7f);
}

void DoornAudioProcessorEditor::paint (Graphics& g)
{
    lastPaintMs = Time::getMillisecondCounterHiRes();
    repaintAskedMs = 0.0;
    g.fillAll (Colours::black);
    // anti-gel : aucun rescale ici, on dessine le cache existant (ou l'original en attendant le timer)
    const Image& bg = bgScaled.isValid() ? bgScaled : background;
    g.setImageResamplingQuality (&bg == &background ? Graphics::highResamplingQuality : Graphics::lowResamplingQuality);
    if (bg.isValid())
        g.drawImage (bg, getLocalBounds().toFloat());

    const float s = (float) getHeight() / (float) baseH;
    g.addTransform (AffineTransform::scale (s));
    drawLed (g);
    if (boostLit > 0.001f)
    {
        // la lumiere du potard transparent eclaire un peu la facade autour
        const auto c = knobPos[1];
        const Colour warm (0xffffcf8a);
        ColourGradient h (warm.withAlpha (0.34f * boostLit), c.x, c.y, warm.withAlpha (0.0f), c.x + miniR * 2.1f, c.y, true);
        h.addColour (0.45, warm.withAlpha (0.10f * boostLit));
        g.setGradientFill (h);
        g.fillEllipse (c.x - miniR * 2.1f, c.y - miniR * 2.1f, miniR * 4.2f, miniR * 4.2f);
    }
    drawStatus (g);
    drawPresetBar (g);
}

//==============================================================================
// Souris : barre de presets (fleches = precedent / suivant, nom = menu deroulant), clic droit = menu
//==============================================================================
static int presetZoneAt (Point<float> p)
{
    if (! presetRect.contains (p)) return 0;
    if (p.x < presetRect.getX() + 34.0f) return 1;
    if (p.x > presetRect.getRight() - 34.0f) return 3;
    return 2;
}

void DoornAudioProcessorEditor::mouseMove (const MouseEvent& e)
{
    const float s = (float) getHeight() / (float) baseH;
    hoverZone = presetZoneAt (e.position / s);
    setMouseCursor (hoverZone != 0 ? MouseCursor::PointingHandCursor : MouseCursor::NormalCursor);
}

void DoornAudioProcessorEditor::mouseExit (const MouseEvent&) { hoverZone = 0; }

void DoornAudioProcessorEditor::mouseDown (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) { showContextMenu(); return; }
    const float s = (float) getHeight() / (float) baseH;
    switch (presetZoneAt (e.position / s))
    {
        case 1: stepPreset (-1); break;
        case 2: showPresetMenu(); break;
        case 3: stepPreset (1); break;
        default: break;
    }
}

void DoornAudioProcessorEditor::stepPreset (int delta)
{
    const int n = DoornAudioProcessor::getNumFactoryPresets();
    int cp = proc.currentPreset.load();
    if (cp < 0 || cp >= n) cp = delta > 0 ? -1 : 0;
    proc.applyFactoryPreset ((cp + delta + n) % n);
}

void DoornAudioProcessorEditor::showPresetMenu()
{
    PopupMenu m;
    m.addSectionHeader ("Factory presets");
    for (int i = 0; i < DoornAudioProcessor::getNumFactoryPresets(); ++i)
        m.addItem (100 + i, String (i + 1) + ". " + DoornAudioProcessor::getFactoryPreset (i).name, true, proc.currentPreset.load() == i);
    m.addSeparator();
    PopupMenu load, save;
    for (int slot = 1; slot <= 9; ++slot)
    {
        const bool exists = proc.hasUserPreset (slot);
        load.addItem (200 + slot, "User " + String (slot) + (exists ? "" : "  (empty)"), exists, proc.currentPreset.load() == 100 + slot);
        save.addItem (300 + slot, "User " + String (slot) + (exists ? "  (overwrite)" : ""));
    }
    m.addSubMenu ("Load user preset", load);
    m.addSubMenu ("Save user preset", save);

    m.showMenuAsync (PopupMenu::Options().withTargetScreenArea (localAreaToGlobal (scaled (presetRect))),
        [safe = Component::SafePointer<DoornAudioProcessorEditor> (this)] (int r)
        {
            if (safe == nullptr || r == 0) return;
            auto& pr = safe->proc;
            if      (r >= 100 && r < 200) pr.applyFactoryPreset (r - 100);
            else if (r > 200 && r < 300)  pr.loadUserPreset (r - 200);
            else if (r > 300 && r < 400)  pr.saveUserPreset (r - 300);
            safe->showStatus();
        });
}

void DoornAudioProcessorEditor::addMidiMenu (PopupMenu& menu, int learnIdx)
{
    auto ccText = [this] (int i)
    {
        const int cc = proc.ccMap[i].load();
        return cc >= 0 ? "CC " + String (cc) : String (CharPointer_UTF8 ("\xe2\x80\x94"));
    };
    const int lt = proc.learnTarget.load();

    // clic droit sur une commande : MIDI Learn de cette commande en tete du menu
    if (learnIdx >= 0)
    {
        const String name = DoornAudioProcessor::learnDef (learnIdx).name;
        menu.addItem (1000 + learnIdx, "MIDI Learn: " + name + " (" + ccText (learnIdx) + ")", true, lt == learnIdx);
        menu.addItem (1100 + learnIdx, "Clear MIDI: " + name, proc.ccMap[learnIdx].load() >= 0);
        if (lt >= 0) menu.addItem (1200, "Cancel MIDI learn");
        menu.addSeparator();
    }
}

void DoornAudioProcessorEditor::handleMidiMenu (int r)
{
    if (r >= 1000 && r < 1000 + DoornAudioProcessor::numLearn)      proc.learnTarget.store (r - 1000);
    else if (r >= 1100 && r < 1100 + DoornAudioProcessor::numLearn) { proc.ccMap[r - 1100].store (-1); }
    else if (r == 1200) proc.learnTarget.store (-1);
    else if (r == 1201) { proc.learnTarget.store (-1); proc.resetMidiMap(); }
}

void DoornAudioProcessorEditor::showContextMenu (int learnIdx)
{
    PopupMenu menu;
    addMidiMenu (menu, learnIdx);
    PopupMenu sizes;
    const int defaultW = roundToInt ((float) defaultH * (float) baseW / (float) baseH);
    sizes.addItem (1, "Default (" + String (defaultW) + " x " + String (defaultH) + ")", true, getHeight() == defaultH);
    sizes.addItem (2, "75 %",  true, getHeight() == roundToInt (baseH * 0.75f));
    sizes.addItem (3, "100 %", true, getHeight() == baseH);
    menu.addSubMenu ("Window size", sizes);
    menu.addSeparator();

    PopupMenu factory;
    for (int i = 0; i < DoornAudioProcessor::getNumFactoryPresets(); ++i)
        factory.addItem (100 + i, String (i + 1) + ". " + DoornAudioProcessor::getFactoryPreset (i).name, true, proc.currentPreset.load() == i);
    menu.addSubMenu ("Factory presets", factory);
    PopupMenu load, save;
    for (int slot = 1; slot <= 9; ++slot)
    {
        const bool exists = proc.hasUserPreset (slot);
        load.addItem (200 + slot, "User " + String (slot) + (exists ? "" : "  (empty)"), exists, proc.currentPreset.load() == 100 + slot);
        save.addItem (300 + slot, "User " + String (slot) + (exists ? "  (overwrite)" : ""));
    }
    menu.addSubMenu ("Load user preset", load);
    menu.addSubMenu ("Save user preset", save);
    menu.addSeparator();

    PopupMenu gate;
    const int gNow = jlimit (0, 3, roundToInt (proc.raw ("gate")));
    const char* gateHelp[4] = { "Off", "Light (very quiet setup)", "Medium (default)", "Strong (noisy pickups / hum)" };
    for (int i = 0; i < 4; ++i) gate.addItem (50 + i, gateHelp[i], true, gNow == i);
    menu.addSubMenu ("Noise gate", gate);

    PopupMenu settings;
    settings.addItem (40, "Smart relay: hold footswitch = momentary", true, proc.raw ("holdMomentary") > 0.5f);
    settings.addSeparator();
    settings.addItem (41, "MIDI footswitches latching (127 = on / 0 = off)", true, proc.raw ("midiFsMode") < 0.5f);
    settings.addItem (42, "MIDI footswitches momentary (toggle each press)", true, proc.raw ("midiFsMode") > 0.5f);
    menu.addSubMenu ("Settings", settings);

    PopupMenu midi;
    for (int i = 0; i < DoornAudioProcessor::numLearn; ++i)
    {
        const int cc = proc.ccMap[i].load();
        midi.addItem (1000 + i, "Learn: " + String (DoornAudioProcessor::learnDef (i).name)
                                 + " (" + (cc >= 0 ? "CC " + String (cc) : String (CharPointer_UTF8 ("\xe2\x80\x94"))) + ")",
                      true, proc.learnTarget.load() == i);
    }
    midi.addSeparator();
    if (proc.learnTarget.load() >= 0) midi.addItem (1200, "Cancel MIDI learn");
    midi.addItem (1201, "Reset MIDI to defaults (CC 20-29)");
    midi.addSeparator();
    midi.addItem (910, "CC n+32 = fine (14-bit) for knobs on CC 0-31", false);
    midi.addItem (911, "Program Change 1-13  Factory presets", false);
    menu.addSubMenu ("MIDI", midi);
    menu.addSeparator();
    menu.addItem (999, "Doorn distortion v" + String (JucePlugin_VersionString) + " - STUDIO WIGA", false);

    menu.showMenuAsync (PopupMenu::Options().withTargetComponent (this),
        [safe = Component::SafePointer<DoornAudioProcessorEditor> (this)] (int r)
        {
            if (safe == nullptr || r == 0) return;
            auto& ed = *safe;
            auto& pr = ed.proc;
            if      (r == 1) ed.setScaledHeight (defaultH);
            else if (r == 2) ed.setScaledHeight (roundToInt (baseH * 0.75f));
            else if (r == 3) ed.setScaledHeight (baseH);
            else if (r == 40) pr.setParamValue ("holdMomentary", pr.raw ("holdMomentary") > 0.5f ? 0.0f : 1.0f);
            else if (r == 41) pr.setParamValue ("midiFsMode", 0.0f);
            else if (r == 42) pr.setParamValue ("midiFsMode", 1.0f);
            else if (r >= 50 && r <= 53) pr.setParamValue ("gate", (float) (r - 50));
            else if (r >= 100 && r < 200) pr.applyFactoryPreset (r - 100);
            else if (r > 200 && r < 300)  pr.loadUserPreset (r - 200);
            else if (r > 300 && r < 400)  pr.saveUserPreset (r - 300);
            else if (r >= 1000) { ed.handleMidiMenu (r); return; }
            ed.showStatus();
        });
}
