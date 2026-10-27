// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    const juce::Point<float> knobPos[6] = { { 229.03f, 159.71f }, { 380.35f, 161.44f }, { 530.27f, 158.33f }, { 226.96f, 367.46f }, { 380.69f, 367.46f }, { 529.58f, 365.39f } };
    const float knobR = 48.48f, miniR = 20.77f, sc = 1.0654f;
    const juce::Point<float> eqPos { 232.15f, 534.70f }, modePos { 528.54f, 533.32f }, ledPos { 382.42f, 704.36f };
    const juce::Point<float> boostPos { 247.04f, 829.36f }, bypassPos { 517.12f, 829.36f };
    const juce::Rectangle<float> glowRect { 254.50f, 576.50f, 256.00f, 256.00f };
}
