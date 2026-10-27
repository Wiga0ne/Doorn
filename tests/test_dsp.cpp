// Test hors plugin du moteur Doorn : stabilite, niveaux par mode, temps de calcul, export WAV.
// g++ -O2 -std=c++17 tests/test_dsp.cpp -o /tmp/test_dsp && /tmp/test_dsp out_dir
#include "../DoornDSP.h"
#include <cstdio>
#include <cstdint>
#include <chrono>
#include <random>
#include <string>

using namespace doorn;

static std::vector<float> guitar (double sr, double seconds)
{
    // cordes pincees (Karplus-Strong) : accord de quinte grave + note seule, niveau DI
    std::vector<float> out ((size_t) (sr * seconds), 0.0f);
    std::mt19937 rng (7);
    std::uniform_real_distribution<float> u (-1.0f, 1.0f);
    auto pluck = [&] (double f, double t0, float amp)
    {
        const int N = (int) (sr / f);
        std::vector<float> buf (N);
        for (auto& b : buf) b = u (rng);
        size_t start = (size_t) (t0 * sr); int p = 0; float last = 0;
        for (size_t i = start; i < out.size(); ++i)
        {
            const float s = buf[p];
            const float nxt = 0.996f * 0.5f * (s + buf[(p + 1) % N]);
            buf[p] = nxt; p = (p + 1) % N;
            last = 0.7f * last + 0.3f * s;
            out[i] += amp * last;
        }
    };
    pluck (61.74, 0.05, 0.22);   // B1 (accordage en Si comme Amenra)
    pluck (92.50, 0.05, 0.16);   // F#2
    pluck (123.47, 0.05, 0.13);  // B2
    pluck (246.94, 1.6, 0.20);   // note seule
    return out;
}

static void writeWav (const std::string& path, const std::vector<float>& x, int sr)
{
    FILE* f = std::fopen (path.c_str(), "wb");
    if (! f) return;
    const uint32_t n = (uint32_t) x.size(), bytes = n * 2;
    auto w32 = [&] (uint32_t v) { std::fwrite (&v, 4, 1, f); };
    auto w16 = [&] (uint16_t v) { std::fwrite (&v, 2, 1, f); };
    std::fwrite ("RIFF", 1, 4, f); w32 (36 + bytes); std::fwrite ("WAVEfmt ", 1, 8, f);
    w32 (16); w16 (1); w16 (1); w32 (sr); w32 (sr * 2); w16 (2); w16 (16);
    std::fwrite ("data", 1, 4, f); w32 (bytes);
    for (float v : x) { int s = (int) std::lround (clampf (v, -1, 1) * 32767); w16 ((uint16_t) (int16_t) s); }
    std::fclose (f);
}

static double rms (const std::vector<float>& x, size_t from = 0)
{
    double s = 0; for (size_t i = from; i < x.size(); ++i) s += (double) x[i] * x[i];
    return std::sqrt (s / std::max<size_t> (1, x.size() - from));
}

int main (int argc, char** argv)
{
    const std::string dir = argc > 1 ? argv[1] : ".";
    const double sr = 48000;
    const auto in = guitar (sr, 3.2);
    const double inR = rms (in, 2400);
    std::printf ("input rms %.1f dBFS\n", 20 * std::log10 (inR));

    struct Case { const char* name; Params p; };
    std::vector<Case> cases;
    Params base;   // reglage de depart GPX
    for (int m = 0; m < 3; ++m)
    {
        Params p = base; p.mode = m; p.level = 5.0f;
        cases.push_back ({ m == 0 ? "sdt2_noon" : m == 1 ? "laerm_noon" : "sdt1_noon", p });
    }
    { Params p = base; cases.push_back ({ "gpx_start", p }); }
    { Params p = base; p.boostOn = true; cases.push_back ({ "gpx_boost", p }); }
    { Params p = base; p.eq = false; cases.push_back ({ "gpx_eq_off", p }); }
    { Params p = base; p.gain = 2.5f; p.level = 5; cases.push_back ({ "crunch", p }); }
    { Params p = base; p.gain = 0.0f; p.level = 10; cases.push_back ({ "gain0_level10", p }); }
    { Params p = base; p.gain = 10; p.boost = 10; p.boostOn = true; p.level = 10; p.treble = 10; p.bass = 10; p.mids = 10;
      p.mode = modeLaerm; cases.push_back ({ "everything_max", p }); }

    for (auto& c : cases)
    {
        Engine e; e.prepare (sr, 1);
        std::vector<float> buf = in;
        float* ptr[1] = { buf.data() };
        const auto t0 = std::chrono::high_resolution_clock::now();
        for (size_t i = 0; i < buf.size(); i += 256)
        {
            float* p2[1] = { buf.data() + i };
            e.process (p2, (int) std::min<size_t> (256, buf.size() - i), c.p);
        }
        const auto t1 = std::chrono::high_resolution_clock::now();
        (void) ptr;
        bool bad = false; float pk = 0;
        for (float v : buf) { if (! std::isfinite (v)) bad = true; pk = std::max (pk, std::abs (v)); }
        const double ms = std::chrono::duration<double, std::milli> (t1 - t0).count();
        std::printf ("%-16s rms %+6.1f dB (vs in %+5.1f)  peak %.2f  cpu %.1f%% %s\n", c.name,
                     20 * std::log10 (rms (buf, 2400) + 1e-12), 20 * std::log10 ((rms (buf, 2400) + 1e-12) / inR), pk,
                     100.0 * ms / (buf.size() / sr * 1000.0), bad ? "NaN!" : "");
        writeWav (dir + "/" + c.name + ".wav", buf, (int) sr);
    }

    // aliasing : sinus 3 kHz pleine distorsion -> energie hors harmoniques
    {
        Engine e; e.prepare (sr, 1);
        Params p = base; p.gain = 10; p.eq = false; p.level = 5;
        std::vector<float> s ((size_t) sr);
        for (size_t i = 0; i < s.size(); ++i) s[i] = 0.2f * (float) std::sin (2 * pi * 3001.0 * i / sr);
        float* p2[1] = { s.data() };
        e.process (p2, (int) s.size(), p);
        writeWav (dir + "/sine3k.wav", s, (int) sr);
    }

    // bypass : sortie == entree retardee ? (le bypass est un vrai direct, sans latence ajoutee ici)
    {
        Engine e; e.prepare (sr, 1);
        Params p = base; p.active = false;
        std::vector<float> s = in; float* p2[1] = { s.data() };
        e.process (p2, (int) s.size(), p);
        double err = 0; for (size_t i = 0; i < s.size(); ++i) { const size_t d = (size_t) Engine::latencyInt(); err = std::max (err, (double) std::abs (s[i] - (i >= d ? in[i - d] : 0.0f))); }
        std::printf ("bypass (retard %d) max error %.2e\n", Engine::latencyInt(), err);
    }
    std::printf ("latency %.2f samples\n", Engine::latencySamples());
    return 0;
}
