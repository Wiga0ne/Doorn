// Captures PNG de la fenetre reelle de Doorn (meme code que le plugin), pour l'apercu et la notice.
#include "PluginProcessor.h"
#include "PluginEditor.h"
using namespace juce;
int main (int argc, char** argv)
{
    ScopedJuceInitialiser_GUI init;
    const String out = argc > 1 ? argv[1] : ".";
    DoornAudioProcessor proc;
    proc.prepareToPlay (48000.0, 256);
    std::unique_ptr<AudioProcessorEditor> ed (proc.createEditor());
    auto* ded = static_cast<DoornAudioProcessorEditor*> (ed.get());
    std::printf ("taille par defaut : %d x %d\n", ed->getWidth(), ed->getHeight());

    auto shot = [&] (const String& name, int preset, bool active, bool boost, bool status, int height)
    {
        ded->setScaledHeight (height);
        proc.applyFactoryPreset (preset);
        proc.setParamValue ("active", active ? 1.f : 0.f);
        proc.setParamValue ("boostOn", boost ? 1.f : 0.f);
        AudioBuffer<float> b (2, 256); MidiBuffer m;
        for (int i = 0; i < 20; ++i) { b.clear(); proc.processBlock (b, m); }
        for (int i = 0; i < 30; ++i) MessageManager::getInstance()->runDispatchLoopUntil (40);
        if (status) ded->showStatus(); else for (int i = 0; i < 100; ++i) MessageManager::getInstance()->runDispatchLoopUntil (40);
        for (int i = 0; i < 12; ++i) MessageManager::getInstance()->runDispatchLoopUntil (40);
        auto img = ed->createComponentSnapshot (ed->getLocalBounds(), true, 2.0f);
        File f (out + "/" + name + ".png"); f.deleteFile();
        FileOutputStream os (f); PNGImageFormat().writeImageToStream (img, os);
        std::printf ("%s (%d x %d)\n", f.getFullPathName().toRawUTF8(), img.getWidth(), img.getHeight());
    };
    shot ("doorn_default",   0, true,  false, false, DoornAudioProcessorEditor::defaultH);
    shot ("doorn_status",    0, true,  false, true,  DoornAudioProcessorEditor::baseH);
    shot ("doorn_boost",     5, true,  true,  false, DoornAudioProcessorEditor::baseH);
    shot ("doorn_bypass",    2, false, false, false, DoornAudioProcessorEditor::baseH);
    shot ("doorn_sdt2",      3, true,  false, false, DoornAudioProcessorEditor::baseH);
    shot ("doorn_laerm",     4, true,  false, false, DoornAudioProcessorEditor::baseH);

    // test pedale d'expression : course 2..116 sur CC 20 (gain)
    {
        auto sendCC = [&] (int v)
        {
            AudioBuffer<float> b (2, 256); MidiBuffer m; m.addEvent (MidiMessage::controllerEvent (1, 20, v), 0);
            proc.processBlock (b, m);
            for (int k = 0; k < 20; ++k) { MidiBuffer e; b.clear(); proc.processBlock (b, e); }
            return proc.raw ("gain");
        };
        const float a = sendCC (2), c = sendCC (116), mid = sendCC (59);
        std::printf ("pedale 2..116 -> gain %.2f / %.2f, mi-course %.2f\n", a, c, mid);
    }
    ed.reset();
    return 0;
}
