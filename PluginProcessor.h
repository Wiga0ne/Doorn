#pragma once
#include <cstring>

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_audio_utils/juce_audio_utils.h>
#include <atomic>
#include "DoornDSP.h"

//==============================================================================
// DOORN (Studio Wiga) - reproduction de la distorsion Lichtlaerm Audio Thorn
// (signature Lennart Bossu / Amenra, d'apres la Providence Stampede SDT-1).
// Voir README.md et DoornDSP.h.
//==============================================================================

struct DoornPreset
{
    const char* name;
    float gain, boost, level, treble, mids, bass;   // 0..10 comme sur la pedale
    int   eq;                                       // 1 = EQ on, 0 = EQ retire du circuit
    int   mode;                                     // 0 = SDT-2, 1 = Laerm, 2 = SDT-1
    int   boostOn;
};

class DoornAudioProcessor : public juce::AudioProcessor,
                            private juce::AsyncUpdater,
                            private juce::Timer
{
public:
    DoornAudioProcessor();
    ~DoornAudioProcessor() override = default;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override {}
    bool isBusesLayoutSupported (const BusesLayout&) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    using AudioProcessor::processBlock;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    const juce::String getName() const override { return "Doorn"; }
    bool acceptsMidi() const override  { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }

    // presets d'usine (menu du DAW, menu de la fenetre, Program Change 1 a 10)
    static int getNumFactoryPresets();
    static const DoornPreset& getFactoryPreset (int index);
    int getNumPrograms() override { return getNumFactoryPresets(); }
    int getCurrentProgram() override;
    void setCurrentProgram (int index) override { applyFactoryPreset (index); }
    const juce::String getProgramName (int index) override { return getFactoryPreset (index).name; }
    void changeProgramName (int, const juce::String&) override {}
    void applyFactoryPreset (int index);

    // presets utilisateur 1 a 9
    bool saveUserPreset (int slot);
    bool loadUserPreset (int slot);
    bool hasUserPreset (int slot) const;
    static juce::File getUserPresetFile();

    void getStateInformation (juce::MemoryBlock&) override;
    void setStateInformation (const void*, int) override;

    juce::AudioProcessorValueTreeState apvts;
    static juce::AudioProcessorValueTreeState::ParameterLayout createLayout();
    void setParamValue (const juce::String& id, float plain);
    // anti-gel : pointeurs des parametres mis en cache au demarrage (aucune recherche par chaine dans processBlock)
    float raw (const char* id) const
    {
        for (int i = 0; i < numRaw; ++i)
            if (rawPtr[i] != nullptr && std::strcmp (id, rawIds[i]) == 0) return rawPtr[i]->load (std::memory_order_relaxed);
        return apvts.getRawParameterValue (id)->load();
    }
    static constexpr int numRaw = 12;
    static constexpr const char* rawIds[numRaw] = { "gain", "boost", "level", "treble", "mids", "bass",
                                                     "eq", "mode", "boostOn", "active", "holdMomentary", "midiFsMode" };
    std::atomic<float>* rawPtr[numRaw] {};

    static juce::StringArray modeNames() { return { "SDT-2", "Laerm", "SDT-1" }; }

    // ---- informations pour la fenetre ----
    std::atomic<int>   currentPreset { 0 };      // >= 0 usine, 100 + n utilisateur, -1 = modifie
    std::atomic<int>   presetCounter { 0 };      // incremente a chaque chargement de preset
    std::atomic<int>   lastMidiCC { -1 }, lastMidiValue { 0 }, lastMidiProgram { -1 }, midiCounter { 0 };
    std::atomic<float> outLevel { 0.0f };        // niveau de sortie (animation de la LED)
    std::atomic<float> boostShown { 0.0f };      // boost reellement engage (lisse)

    enum MidiMap
    {
        ccGain = 20, ccBoost = 21, ccLevel = 22, ccTreble = 23, ccMids = 24, ccBass = 25,
        ccEq = 26,            // >= 64 : EQ on
        ccMode = 27,          // 0-42 SDT-2, 43-84 Laerm, 85-127 SDT-1
        ccBoostFs = 28,       // footswitch BOOST
        ccBypassFs = 29       // footswitch BYPASS (effet on / off)
    };
    static constexpr int numKnobs = 6;
    static const char* knobId (int i);

private:
    void handleMidi (juce::MidiBuffer& midi, int numSamples);
    void setParamFromAudio (const char* id, float plain);   // thread audio : met en file, applique sur le thread de messages
    void timerCallback() override;                           // anti-gel : vide la file (aucun appel a l'hote depuis l'audio)
    static constexpr int numQueued = 10;
    static const char* queuedId (int i);
    std::atomic<float> pendingValue[numQueued];
    std::atomic<bool>  pendingSet[numQueued];
    void handleAsyncUpdate() override;
    float mapCC (int knob, float raw01);

    doorn::Engine engine;
    double sr = 48000.0;

    // pedale d'expression : rampe lineaire vers chaque nouvelle valeur sur l'intervalle mesure entre deux CC
    struct ExprRamp
    {
        bool  active = false;
        float value = 0.0f, target = 0.0f, step = 0.0f;
        int   left = 0;
        juce::int64 lastTime = 0;
        int   msb = -1;
        float lo = 1.0f, hi = 0.0f;          // course reellement envoyee par la pedale (apprise automatiquement)
    } ramps[numKnobs];
    juce::int64 sampleClock = 0;

    // footswitches MIDI : etat precedent (mode momentane = bascule a chaque appui)
    int prevBoostCC = 0, prevBypassCC = 0;

    // changements demandes par le thread audio, appliques sur le thread de messages
    std::atomic<int> pendingPreset { -1 };

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (DoornAudioProcessor)
};
