// Doorn hors plugin : traite un WAV mono 16 bits (48 kHz) avec les reglages donnes.
// g++ -O2 -std=c++17 tools/process.cpp -o process && ./process in.wav out.wav gain boost level treble mids bass eq mode boostOn
#include "../DoornDSP.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <vector>
using namespace doorn;
int main (int argc, char** argv)
{
    if (argc < 12) { std::fprintf (stderr, "usage\n"); return 1; }
    FILE* f = std::fopen (argv[1], "rb"); if (! f) return 1;
    std::vector<unsigned char> d; unsigned char buf[65536]; size_t n;
    while ((n = std::fread (buf, 1, sizeof buf, f)) > 0) d.insert (d.end(), buf, buf + n);
    std::fclose (f);
    size_t p = 12, dataPos = 0, dataLen = 0; int sr = 48000;
    while (p + 8 <= d.size())
    {
        const uint32_t len = d[p + 4] | d[p + 5] << 8 | d[p + 6] << 16 | (uint32_t) d[p + 7] << 24;
        if (! std::memcmp (&d[p], "fmt ", 4)) sr = d[p + 12] | d[p + 13] << 8 | d[p + 14] << 16;
        if (! std::memcmp (&d[p], "data", 4)) { dataPos = p + 8; dataLen = len; break; }
        p += 8 + len;
    }
    std::vector<float> x (dataLen / 2);
    for (size_t i = 0; i < x.size(); ++i) x[i] = (int16_t) (d[dataPos + 2 * i] | d[dataPos + 2 * i + 1] << 8) / 32768.0f;
    Params pr; pr.gain = (float) atof (argv[3]); pr.boost = (float) atof (argv[4]); pr.level = (float) atof (argv[5]);
    pr.treble = (float) atof (argv[6]); pr.mids = (float) atof (argv[7]); pr.bass = (float) atof (argv[8]);
    pr.eq = atoi (argv[9]) != 0; pr.mode = atoi (argv[10]); pr.boostOn = atoi (argv[11]) != 0;
    Engine e; e.prepare (sr, 1);
    for (size_t i = 0; i < x.size(); i += 256) { float* q[1] = { x.data() + i }; e.process (q, (int) std::min<size_t> (256, x.size() - i), pr); }
    FILE* o = std::fopen (argv[2], "wb");
    const uint32_t nn = (uint32_t) x.size(), bytes = nn * 2;
    auto w32 = [&] (uint32_t v) { std::fwrite (&v, 4, 1, o); }; auto w16 = [&] (uint16_t v) { std::fwrite (&v, 2, 1, o); };
    std::fwrite ("RIFF", 1, 4, o); w32 (36 + bytes); std::fwrite ("WAVEfmt ", 1, 8, o); w32 (16); w16 (1); w16 (1); w32 (sr); w32 (sr * 2); w16 (2); w16 (16);
    std::fwrite ("data", 1, 4, o); w32 (bytes);
    for (float v : x) { const int s = (int) std::lround (clampf (v, -1, 1) * 32767); w16 ((uint16_t) (int16_t) s); }
    std::fclose (o);
    return 0;
}
