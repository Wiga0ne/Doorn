#include "PluginProcessor.h"
#include "PluginEditor.h"

using namespace juce;

//==============================================================================
// Presets d'usine - reglages notes comme sur la pedale (0 a 10, 5 = midi / EQ plat)
//==============================================================================
static const DoornPreset factoryPresets[] =
{
    //  nom                    gain boost level treb  mids  bass  eq mode boostOn
    { "Signature Start",       7.5f, 7.5f, 7.5f, 10.f, 3.75f, 7.5f, 1, 2, 0 },   // reglage de depart du test Guitar Pedal X
    { "Wall of Thorns",        8.5f, 6.0f, 7.0f, 8.0f, 3.5f,  7.0f, 1, 2, 0 },
    { "V4 EQ Bypass",          7.5f, 5.0f, 7.0f, 5.0f, 5.0f,  5.0f, 0, 2, 0 },   // EQ retire, comme Lennart dans un Ampeg V4
    { "Living Gate Saturation",8.0f, 5.0f, 8.0f, 7.0f, 6.0f,  6.0f, 1, 0, 0 },
    { "Laerm Open",            6.5f, 5.0f, 6.0f, 7.0f, 5.5f,  6.0f, 1, 1, 0 },
    { "Laerm Lead Boost",      7.0f, 8.0f, 6.0f, 6.5f, 7.0f,  5.0f, 1, 1, 1 },
    { "Stampede Crunch",       3.0f, 5.0f, 7.5f, 6.0f, 6.0f,  5.0f, 1, 2, 0 },
    { "Hardcore Bite",         9.5f, 4.0f, 6.5f, 8.5f, 6.5f,  4.5f, 1, 2, 0 },
    { "Sludge Sustain",        10.f, 5.0f, 7.0f, 5.0f, 2.5f,  9.0f, 1, 0, 1 },
    { "Thorn Reference",       4.3f, 0.0f, 5.8f, 5.8f, 5.0f,  8.0f, 1, 2, 0 },   // reglages de la vraie pedale (photo + enregistrement)
};

int DoornAudioProcessor::getNumFactoryPresets() { return (int) std::size (factoryPresets); }

const DoornPreset& DoornAudioProcessor::getFactoryPreset (int i)
{
    return factoryPresets[(size_t) jlimit (0, getNumFactoryPresets() - 1, i)];
}

const char* DoornAudioProcessor::knobId (int i)
{
    static const char* ids[numKnobs] = { "gain", "boost", "level", "treble", "mids", "bass" };
    return ids[jlimit (0, numKnobs - 1, i)];
}

//==============================================================================
DoornAudioProcessor::DoornAudioProcessor()
    : AudioProcessor (BusesProperties()
                        .withInput  ("Input",  AudioChannelSet::stereo(), true)
                        .withOutput ("Output", AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, "DOORN", createLayout())
{
    setLatencySamples (doorn::Engine::latencyInt());
    for (int i = 0; i < numRaw; ++i) rawPtr[i] = apvts.getRawParameterValue (rawIds[i]);
    for (int i = 0; i < numQueued; ++i) { pendingValue[i] = 0.0f; pendingSet[i] = false; }
    startTimerHz (60);
}

AudioProcessorValueTreeState::ParameterLayout DoornAudioProcessor::createLayout()
{
    std::vector<std::unique_ptr<RangedAudioParameter>> p;
    const auto& d = factoryPresets[0];

    auto knob = [] (const String& id, const String& name, float def)
    {
        return std::make_unique<AudioParameterFloat> (
            ParameterID { id, 1 }, name, NormalisableRange<float> (0.0f, 10.0f, 0.01f), def,
            AudioParameterFloatAttributes().withStringFromValueFunction (
                [] (float v, int) { return String (roundToInt (v * 10.0f)) + " %"; }));
    };

    p.push_back (knob ("gain",   "Gain",   d.gain));
    p.push_back (knob ("boost",  "Boost",  d.boost));
    p.push_back (knob ("level",  "Level",  d.level));
    p.push_back (knob ("treble", "Treble", d.treble));
    p.push_back (knob ("mids",   "Mids",   d.mids));
    p.push_back (knob ("bass",   "Bass",   d.bass));
    p.push_back (std::make_unique<AudioParameterBool>   (ParameterID { "eq", 1 },      "EQ", d.eq != 0));
    p.push_back (std::make_unique<AudioParameterChoice> (ParameterID { "mode", 1 },    "Mode", modeNames(), d.mode));
    p.push_back (std::make_unique<AudioParameterBool>   (ParameterID { "boostOn", 1 }, "Boost Footswitch", d.boostOn != 0));
    p.push_back (std::make_unique<AudioParameterBool>   (ParameterID { "active", 1 },  "Bypass Footswitch", true));
    // reglages (menu clic droit)
    p.push_back (std::make_unique<AudioParameterBool>   (ParameterID { "holdMomentary", 1 }, "Hold = Momentary", true));
    p.push_back (std::make_unique<AudioParameterChoice> (ParameterID { "midiFsMode", 1 }, "MIDI Footswitch Mode",
                                                         StringArray { "Latching (127 / 0)", "Momentary (toggle)" }, 0));
    // v2.6 noise gate integre (le grand gain de la Thorn fait monter le souffle et le ronflement quand on ne joue pas)
    p.push_back (std::make_unique<AudioParameterChoice> (ParameterID { "gate", 1 }, "Noise Gate", gateNames(), 2));
    return { p.begin(), p.end() };
}

bool DoornAudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto in = layouts.getMainInputChannelSet(), out = layouts.getMainOutputChannelSet();
    if (out != AudioChannelSet::mono() && out != AudioChannelSet::stereo()) return false;
    return in == out;
}

void DoornAudioProcessor::setParamValue (const String& id, float plain)
{
    if (auto* prm = apvts.getParameter (id))
    {
        prm->beginChangeGesture();
        prm->setValueNotifyingHost (prm->convertTo0to1 (plain));
        prm->endChangeGesture();
    }
}

// Anti-gel : jamais d'appel a l'hote (setValueNotifyingHost) ni d'allocation depuis le thread audio.
// Le MIDI met la valeur en file ; un timer du thread de messages la transmet au DAW et a la fenetre.
const char* DoornAudioProcessor::queuedId (int i)
{
    static const char* ids[numQueued] = { "gain", "boost", "level", "treble", "mids", "bass", "eq", "mode", "boostOn", "active" };
    return ids[jlimit (0, numQueued - 1, i)];
}

void DoornAudioProcessor::setParamFromAudio (const char* id, float plain)
{
    for (int i = 0; i < numQueued; ++i)
        if (std::strcmp (id, queuedId (i)) == 0)
        {
            pendingValue[i].store (plain, std::memory_order_relaxed);
            pendingSet[i].store (true, std::memory_order_release);
            return;
        }
}

void DoornAudioProcessor::timerCallback()
{
    for (int i = 0; i < numQueued; ++i)
        if (pendingSet[i].exchange (false, std::memory_order_acquire))
            if (auto* prm = apvts.getParameter (queuedId (i)))
                prm->setValueNotifyingHost (prm->convertTo0to1 (pendingValue[i].load (std::memory_order_relaxed)));
}

//==============================================================================
void DoornAudioProcessor::prepareToPlay (double sampleRate, int)
{
    sr = sampleRate;
    engine.prepare (sr, jmax (1, getTotalNumOutputChannels()));
    for (auto& r : ramps) { r.active = false; r.left = 0; }
    setLatencySamples (doorn::Engine::latencyInt());
}

//==============================================================================
// MIDI
//==============================================================================
// position brute 0..1 -> valeur du potard 0..1 : course de la pedale apprise automatiquement
// (une pedale qui n'envoie que 2..116 donne quand meme 0 et 100 %), petites zones mortes aux butees
float DoornAudioProcessor::mapCC (int k, float raw01)
{
    auto& r = ramps[k];
    if (raw01 < r.lo) r.lo = raw01;
    if (raw01 > r.hi) r.hi = raw01;
    float v = raw01;
    if (r.hi - r.lo > 0.4f) v = (raw01 - r.lo) / (r.hi - r.lo);
    constexpr float dz = 0.02f;
    return jlimit (0.0f, 1.0f, (v - dz) / (1.0f - 2.0f * dz));
}

void DoornAudioProcessor::handleMidi (MidiBuffer& midi, int numSamples)
{
    const bool latching = raw ("midiFsMode") < 0.5f;

    for (const auto meta : midi)
    {
        const auto m = meta.getMessage();
        const juce::int64 when = sampleClock + meta.samplePosition;

        if (m.isController())
        {
            const int cc = m.getControllerNumber(), v = m.getControllerValue();
            bool known = true;

            auto knobFromCC = [&] (int k, float raw01)
            {
                auto& r = ramps[k];
                const float target = mapCC (k, raw01) * 10.0f;
                if (! r.active) r.value = raw (knobId (k));
                // rampe sur l'intervalle mesure entre deux CC (2 a 40 ms) -> mouvement continu
                const double interval = (double) (when - r.lastTime);
                r.left = (int) jlimit (0.002 * sr, 0.040 * sr, interval);
                r.lastTime = when;
                r.target = target;
                r.step = (r.target - r.value) / (float) r.left;
                r.active = true;
                setParamFromAudio (knobId (k), target);      // le DAW et la fenetre suivent la pedale
                currentPreset = -1;
            };

            if (cc >= ccGain && cc <= ccBass)
            {
                const int k = cc - ccGain;
                ramps[k].msb = v;
                knobFromCC (k, (float) v / 127.0f);
            }
            else if (cc >= ccGain + 32 && cc <= ccBass + 32)
            {
                // CC 14 bits (CC n + CC n+32) : resolution fine si la pedale l'envoie
                const int k = cc - 32 - ccGain;
                if (ramps[k].msb >= 0)
                    knobFromCC (k, (float) (ramps[k].msb * 128 + v) / 16383.0f);
            }
            else if (cc == ccEq)   { setParamFromAudio ("eq", v >= 64 ? 1.0f : 0.0f); currentPreset = -1; }
            else if (cc == ccMode) { setParamFromAudio ("mode", v < 43 ? 0.0f : (v < 85 ? 1.0f : 2.0f)); currentPreset = -1; }
            else if (cc == ccBoostFs || cc == ccBypassFs)
            {
                const char* id = cc == ccBoostFs ? "boostOn" : "active";
                int& prev = cc == ccBoostFs ? prevBoostCC : prevBypassCC;
                // etat courant = valeur en file si elle existe (bascules rapides sans attendre le timer)
                const int qi = cc == ccBoostFs ? 8 : 9;
                const float cur = pendingSet[qi].load() ? pendingValue[qi].load() : raw (id);
                if (latching)                   setParamFromAudio (id, v >= 64 ? 1.0f : 0.0f);
                else if (v >= 64 && prev < 64)  setParamFromAudio (id, cur > 0.5f ? 0.0f : 1.0f);
                prev = v;
            }
            else known = false;

            if (known)
            {
                lastMidiCC = cc; lastMidiValue = v; ++midiCounter;
            }
        }
        else if (m.isProgramChange())
        {
            const int pc = m.getProgramChangeNumber();
            if (pc < getNumFactoryPresets()) { pendingPreset = pc; triggerAsyncUpdate(); }
            lastMidiProgram = pc; lastMidiCC = -2; ++midiCounter;
        }
    }
    midi.clear();
    ignoreUnused (numSamples);
}

void DoornAudioProcessor::handleAsyncUpdate()
{
    const int p = pendingPreset.exchange (-1);
    if (p >= 0) applyFactoryPreset (p);
}

//==============================================================================
void DoornAudioProcessor::processBlock (AudioBuffer<float>& buffer, MidiBuffer& midi)
{
    ScopedNoDenormals noDenormals;
    const int n = buffer.getNumSamples();
    handleMidi (midi, n);
    if (n == 0) return;

    for (int c = getTotalNumInputChannels(); c < getTotalNumOutputChannels(); ++c)
        buffer.clear (c, 0, n);

    doorn::Params p;
    float* knobs[numKnobs] = { &p.gain, &p.boost, &p.level, &p.treble, &p.mids, &p.bass };
    for (int k = 0; k < numKnobs; ++k)
    {
        auto& r = ramps[k];
        if (r.active)
        {
            const int adv = jmin (r.left, n);
            r.value += r.step * (float) adv;
            r.left -= adv;
            if (r.left <= 0) { r.value = r.target; r.active = false; }
            *knobs[k] = r.value;
        }
        else
            *knobs[k] = raw (knobId (k));
    }
    p.eq      = raw ("eq") > 0.5f;
    p.mode    = jlimit (0, 2, roundToInt (raw ("mode")));
    p.boostOn = raw ("boostOn") > 0.5f;
    p.active  = raw ("active") > 0.5f;
    p.gate    = jlimit (0, 3, roundToInt (raw ("gate")));

    const int nCh = jmin (2, buffer.getNumChannels());
    float* io[2] = { buffer.getWritePointer (0), nCh > 1 ? buffer.getWritePointer (1) : nullptr };
    engine.process (io, n, p);

    float pk = 0.0f;
    for (int c = 0; c < nCh; ++c) pk = jmax (pk, buffer.getMagnitude (c, 0, n));
    outLevel = pk;
    boostShown = engine.lastBoostMix;
    sampleClock += n;
}

//==============================================================================
// Presets
//==============================================================================
int DoornAudioProcessor::getCurrentProgram()
{
    const int c = currentPreset.load();
    return (c >= 0 && c < getNumFactoryPresets()) ? c : 0;
}

void DoornAudioProcessor::applyFactoryPreset (int index)
{
    const auto& p = getFactoryPreset (index);
    setParamValue ("gain", p.gain);     setParamValue ("boost", p.boost);  setParamValue ("level", p.level);
    setParamValue ("treble", p.treble); setParamValue ("mids", p.mids);    setParamValue ("bass", p.bass);
    setParamValue ("eq", (float) p.eq); setParamValue ("mode", (float) p.mode);
    setParamValue ("boostOn", (float) p.boostOn);
    currentPreset = jlimit (0, getNumFactoryPresets() - 1, index);
    ++presetCounter;
}

File DoornAudioProcessor::getUserPresetFile()
{
    return File::getSpecialLocation (File::userApplicationDataDirectory)
             .getChildFile ("Studio Wiga").getChildFile ("Doorn").getChildFile ("UserPresets.xml");
}

static const char* presetIds[] = { "gain", "boost", "level", "treble", "mids", "bass", "eq", "mode", "boostOn" };

bool DoornAudioProcessor::saveUserPreset (int slot)
{
    if (slot < 1 || slot > 9) return false;
    auto file = getUserPresetFile();
    file.getParentDirectory().createDirectory();
    std::unique_ptr<XmlElement> root;
    if (file.existsAsFile()) root = XmlDocument::parse (file);
    if (root == nullptr || ! root->hasTagName ("UserPresets")) root = std::make_unique<XmlElement> ("UserPresets");
    for (auto* e = root->getFirstChildElement(); e != nullptr; e = e->getNextElement())
        if (e->getIntAttribute ("slot") == slot) { root->removeChildElement (e, true); break; }
    auto* e = root->createNewChildElement ("Preset");
    e->setAttribute ("slot", slot);
    for (auto* id : presetIds) e->setAttribute (id, (double) raw (id));
    const bool ok = root->writeTo (file);
    if (ok) { currentPreset = 100 + slot; ++presetCounter; }
    return ok;
}

bool DoornAudioProcessor::loadUserPreset (int slot)
{
    const auto file = getUserPresetFile();
    if (! file.existsAsFile()) return false;
    auto root = XmlDocument::parse (file);
    if (root == nullptr) return false;
    for (auto* e = root->getFirstChildElement(); e != nullptr; e = e->getNextElement())
        if (e->getIntAttribute ("slot") == slot)
        {
            for (auto* id : presetIds)
                if (e->hasAttribute (id)) setParamValue (id, (float) e->getDoubleAttribute (id));
            currentPreset = 100 + slot; ++presetCounter;
            return true;
        }
    return false;
}

bool DoornAudioProcessor::hasUserPreset (int slot) const
{
    const auto file = getUserPresetFile();
    if (! file.existsAsFile()) return false;
    if (auto root = XmlDocument::parse (file))
        for (auto* e = root->getFirstChildElement(); e != nullptr; e = e->getNextElement())
            if (e->getIntAttribute ("slot") == slot) return true;
    return false;
}

//==============================================================================
void DoornAudioProcessor::getStateInformation (MemoryBlock& dest)
{
    auto state = apvts.copyState();
    state.setProperty ("currentPreset", currentPreset.load(), nullptr);
    if (auto xml = state.createXml()) copyXmlToBinary (*xml, dest);
}

void DoornAudioProcessor::setStateInformation (const void* data, int size)
{
    if (auto xml = getXmlFromBinary (data, size))
        if (xml->hasTagName (apvts.state.getType()))
        {
            auto state = ValueTree::fromXml (*xml);
            currentPreset = (int) state.getProperty ("currentPreset", 0);
            apvts.replaceState (state);
            ++presetCounter;
        }
}

//==============================================================================
AudioProcessorEditor* DoornAudioProcessor::createEditor() { return new DoornAudioProcessorEditor (*this); }

AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new DoornAudioProcessor(); }
