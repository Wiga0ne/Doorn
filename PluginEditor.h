#pragma once

#include "PluginProcessor.h"
#include <juce_gui_basics/juce_gui_basics.h>

//==============================================================================
// Potards : le chapeau noir (et ses reflets) fait partie de la photo de fond et reste fixe ;
// seul le repere blanc tourne (fleche des grands potards, barrette du petit potard BOOST).
//==============================================================================
class DoornKnobLookAndFeel : public juce::LookAndFeel_V4
{
public:
    void drawRotarySlider (juce::Graphics&, int x, int y, int w, int h,
                           float pos, float startAngle, float endAngle, juce::Slider&) override;
};

class DoornKnob : public juce::Slider
{
public:
    DoornKnob() = default;
    bool isMini = false;
    bool hitTest (int x, int y) override;
};

//==============================================================================
// Inverseur a levier (rendu 3D, 5 positions : haut, intermediaire, centre, intermediaire, bas)
//==============================================================================
class LeverSwitch : public juce::Component
{
public:
    LeverSwitch (juce::RangedAudioParameter& p, int numPositions);
    void paint (juce::Graphics&) override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails&) override;
    void tick (double nowMs);             // appele par le timer de l'editeur
    juce::Image strip;                     // 5 images carrees empilees
    std::function<void()> onRightClick, onUserChange;
    int getPosition() const { return pos; }

private:
    int frameFor (int position) const;
    void moveTo (int newPos);
    juce::ParameterAttachment attachment;
    int positions, pos = 0, shownFrame = 0, targetFrame = 0;
    double transitionUntil = 0.0;
};

//==============================================================================
// Footswitch (reference Echoflex) : bascule a l'appui, bouton assombri tant qu'on appuie.
// « Smart relay » : appui maintenu (> 0,45 s) quand l'effet etait coupe = fonctionnement momentane.
//==============================================================================
class FootSwitchArea : public juce::Component
{
public:
    FootSwitchArea (juce::RangedAudioParameter& p, std::atomic<float>* holdMomentary);
    void paint (juce::Graphics&) override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseUp (const juce::MouseEvent&) override;
    bool hitTest (int x, int y) override;
    bool isOn() const { return value; }
    bool isPressed() const { return pressed; }
    std::function<void()> onRightClick, onUserChange;

private:
    bool value = false, pressed = false, turnedOnByPress = false;
    double downTime = 0.0;
    std::atomic<float>* hold = nullptr;
    juce::ParameterAttachment attachment;
};

//==============================================================================
struct RightClickForwarder : public juce::MouseListener
{
    std::function<void()> callback;
    void mouseDown (const juce::MouseEvent& e) override
    {
        if (e.mods.isPopupMenu() && callback) callback();
    }
};

//==============================================================================
class DoornAudioProcessorEditor : public juce::AudioProcessorEditor,
                                  private juce::Timer
{
public:
    explicit DoornAudioProcessorEditor (DoornAudioProcessor&);
    ~DoornAudioProcessorEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;
    void parentHierarchyChanged() override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseMove (const juce::MouseEvent&) override;
    void mouseExit (const juce::MouseEvent&) override;

    // Repere de reference (100 %) et taille par defaut = taille minimale (identique a Echoflex)
    static constexpr int baseW = 760;
    static constexpr int baseH = 958;
    static constexpr int defaultH = 493;

    void setScaledHeight (int h);
    void showStatus();

private:
    void timerCallback() override;
    void useSoftwareRenderer();
    void showContextMenu();
    void showPresetMenu();
    void stepPreset (int delta);
    void rebuildCaches (float scale = 0.0f);
    float physicalScale() const;
    juce::Rectangle<int> scaled (juce::Rectangle<float> r) const;
    juce::String buildStatusLine() const;
    juce::String buildPresetLine() const;
    void drawLed (juce::Graphics&);
    void drawStatus (juce::Graphics&);
    void drawPresetBar (juce::Graphics&);

    DoornAudioProcessor& proc;
    DoornKnobLookAndFeel lnf;
    RightClickForwarder rightClickFwd;

    juce::Image background, bgScaled, glowRed, glowAmber, glowRedS, glowAmberS;
    int cacheW = 0, cacheH = 0;
    float cacheScale = 0.0f;
    int resizeSettle = 0;
    juce::Typeface::Ptr labelFace;

    DoornKnob knobs[DoornAudioProcessor::numKnobs];
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> knobAtt[DoornAudioProcessor::numKnobs];
    LeverSwitch eqSwitch, modeSwitch;
    FootSwitchArea boostFs, bypassFs;

    // animation
    float ledLevel = 0.0f, ledAmber = 0.0f;
    int lastChanged = -1;               // commande affichee dans la ligne d'etat
    float drawnLed = -1.0f, drawnAmber = -1.0f;
    float statusAlpha = 0.0f, drawnStatus = -1.0f;
    double statusUntil = 0.0;
    juce::String lastLine1, lastPreset;
    float lastValues[16];
    int lastPresetCounter = 0, lastMidiCount = 0, midiFlash = 0;
    int hoverZone = 0, drawnHover = -1;       // 1 = fleche gauche, 2 = nom, 3 = fleche droite

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (DoornAudioProcessorEditor)
};
