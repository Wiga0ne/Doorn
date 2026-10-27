#pragma once
//==============================================================================
// DOORN (Studio Wiga) - moteur audio, sans dependance JUCE (testable hors plugin).
//
// Reproduction de la Lichtlaerm Audio Thorn (signature Lennart Bossu / Amenra),
// elle-meme derivee de la Providence Stampede SDT-1 :
//
//  IN -> buffer + passe-haut (serrage du grave, plus serre avec le BOOST)
//     -> pre-accentuation des mediums (« singing midrange »)
//     -> [sur-echantillonnage x4]
//     -> etage 1 : ampli op alimente par pompe de charge (~18 V : grande reserve),
//                  ecretage doux sur les rails + leger biais (harmoniques paires)
//     -> etage 2 : gain + diodes a la masse (SDT-1 silicium, SDT-2 silicium + etage
//                  de compression en plus, Laerm seuil plus haut type LED, asymetrique)
//     -> filtre de sortie de l'ampli op (fizz)
//     -> [decimation]
//     -> etage de sortie « ampli » (grave genereux, aigus adoucis)
//     -> EQ actif 3 bandes (Bass / Mids 1 kHz / Treble), bypassable : en OFF il est
//        completement retire du trajet du signal
//     -> LEVEL -> OUT
//
//  BOOST : gain ajoute avant l'ecretage (additif, pas un etage independant) :
//          plus de sustain, attaque resserree (passe-haut d'entree remonte).
//==============================================================================

#include <cmath>
#include <vector>
#include <algorithm>
#include <cstring>

// v1.6 : son metal / stoner de la Thorn : mordant du boost dans la voix de base, grave epais mais ferme,
// haut chaud, grain un peu fuzz ; dynamique de jeu rendue (anti-compression)
#ifndef DOORN_SCOOP_HZ
 #define DOORN_SCOOP_HZ 650.0
#endif
#ifndef DOORN_SCOOP_DB
 #define DOORN_SCOOP_DB -12.0
#endif
#ifndef DOORN_SCOOP_Q
 #define DOORN_SCOOP_Q 0.60
#endif
#ifndef DOORN_LOW_DB
 #define DOORN_LOW_DB -2.5
#endif
#ifndef DOORN_HIGH_DB
 #define DOORN_HIGH_DB 0.0
#endif
#ifndef DOORN_LP_SCALE
 #define DOORN_LP_SCALE 1.0
#endif
#ifndef DOORN_G0
 #define DOORN_G0 20.0f
#endif
#ifndef DOORN_G1
 #define DOORN_G1 52.0f
#endif
#ifndef DOORN_GEXP
 #define DOORN_GEXP 1.0f
#endif

namespace doorn
{
    constexpr double pi = 3.14159265358979323846;

    inline float clampf (float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
    inline float dbToGain (float db) { return std::pow (10.0f, db * 0.05f); }

    //--------------------------------------------------------------------------
    struct Biquad
    {
        double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
        double z1 = 0, z2 = 0;

        void set (double nb0, double nb1, double nb2, double na0, double na1, double na2)
        {
            b0 = nb0 / na0; b1 = nb1 / na0; b2 = nb2 / na0; a1 = na1 / na0; a2 = na2 / na0;
        }
        void lowpass (double sr, double fc, double q = 0.7071)
        {
            fc = std::min (std::max (fc, 10.0), sr * 0.45);
            const double w = 2 * pi * fc / sr, c = std::cos (w), al = std::sin (w) / (2 * q);
            set ((1 - c) / 2, 1 - c, (1 - c) / 2, 1 + al, -2 * c, 1 - al);
        }
        void highpass (double sr, double fc, double q = 0.7071)
        {
            fc = std::min (std::max (fc, 5.0), sr * 0.45);
            const double w = 2 * pi * fc / sr, c = std::cos (w), al = std::sin (w) / (2 * q);
            set ((1 + c) / 2, -(1 + c), (1 + c) / 2, 1 + al, -2 * c, 1 - al);
        }
        void peak (double sr, double fc, double q, double db)
        {
            fc = std::min (std::max (fc, 10.0), sr * 0.45);
            const double A = std::pow (10.0, db / 40.0);
            const double w = 2 * pi * fc / sr, c = std::cos (w), al = std::sin (w) / (2 * q);
            set (1 + al * A, -2 * c, 1 - al * A, 1 + al / A, -2 * c, 1 - al / A);
        }
        void lowShelf (double sr, double fc, double db, double s = 0.8)
        {
            fc = std::min (std::max (fc, 10.0), sr * 0.45);
            const double A = std::pow (10.0, db / 40.0);
            const double w = 2 * pi * fc / sr, c = std::cos (w), sn = std::sin (w);
            const double al = sn / 2 * std::sqrt ((A + 1 / A) * (1 / s - 1) + 2), sa = 2 * std::sqrt (A) * al;
            set (A * ((A + 1) - (A - 1) * c + sa), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sa),
                 (A + 1) + (A - 1) * c + sa, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sa);
        }
        void highShelf (double sr, double fc, double db, double s = 0.8)
        {
            fc = std::min (std::max (fc, 10.0), sr * 0.45);
            const double A = std::pow (10.0, db / 40.0);
            const double w = 2 * pi * fc / sr, c = std::cos (w), sn = std::sin (w);
            const double al = sn / 2 * std::sqrt ((A + 1 / A) * (1 / s - 1) + 2), sa = 2 * std::sqrt (A) * al;
            set (A * ((A + 1) + (A - 1) * c + sa), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sa),
                 (A + 1) - (A - 1) * c + sa, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sa);
        }
        inline float process (float xf) noexcept
        {
            const double x = xf;
            const double y = b0 * x + z1;
            z1 = b1 * x - a1 * y + z2;
            z2 = b2 * x - a2 * y;
            return (float) y;
        }
        void reset() { z1 = z2 = 0; }
    };

    struct OnePole   // passe-bas / passe-haut du 1er ordre
    {
        float a = 0, z = 0;
        void setLP (double sr, double fc) { a = (float) std::exp (-2 * pi * fc / sr); }
        inline float lp (float x) noexcept { z = x + a * (z - x); return z; }
        inline float hp (float x) noexcept { z = x + a * (z - x); return x - z; }
        void reset() { z = 0; }
    };

    // Lissage a 2 poles (deux 1er ordre en cascade) : pas de marche d'escalier
    struct Smooth2
    {
        float c = 0.01f, s1 = 0, s2 = 0;
        void setTime (double sr, double ms) { c = (float) (1.0 - std::exp (-1.0 / (ms * 0.001 * sr))); }
        void reset (float v) { s1 = s2 = v; }
        inline float next (float target) noexcept { s1 += (target - s1) * c; s2 += (s1 - s2) * c; return s2; }
        bool settled (float target) const { return std::abs (s2 - target) < 1.0e-5f && std::abs (s1 - target) < 1.0e-5f; }
    };

    //--------------------------------------------------------------------------
    // Sur-echantillonnage x4 : filtre RIF a phase lineaire (sinc fenetre de Kaiser)
    // en polyphase pour la montee et la descente.
    struct Oversampler4
    {
        static constexpr int factor = 4;
        static constexpr int taps = 128;          // multiple de 4
        float h[taps] {};
        float hist[taps * 2] {};                  // ligne a retard (entree x4) doublee pour lecture contigue
        int   pos = 0;
        float upHist[taps / factor * 2] {};
        int   upPos = 0;

        static double bessel0 (double x)
        {
            double s = 1, t = 1;
            for (int k = 1; k < 30; ++k) { t *= (x / (2 * k)) * (x / (2 * k)); s += t; }
            return s;
        }

        void design()
        {
            const double fc = 0.5 / factor * 0.90;   // coupure ~ 0,45 x Fs d'origine
            const double beta = 8.6;
            double sum = 0;
            for (int n = 0; n < taps; ++n)
            {
                const double m = n - (taps - 1) * 0.5;
                const double x = 2 * fc * m;
                const double sinc = std::abs (x) < 1e-12 ? 1.0 : std::sin (pi * x) / (pi * x);
                const double r = 2.0 * n / (taps - 1) - 1.0;
                const double w = bessel0 (beta * std::sqrt (std::max (0.0, 1 - r * r))) / bessel0 (beta);
                h[n] = (float) (2 * fc * sinc * w);
                sum += h[n];
            }
            for (auto& v : h) v = (float) (v / sum);
            reset();
        }
        void reset()
        {
            std::fill (std::begin (hist), std::end (hist), 0.0f);
            std::fill (std::begin (upHist), std::end (upHist), 0.0f);
            pos = upPos = 0;
        }
        // latence totale (montee + descente) en echantillons a la frequence d'origine
        static double latency() { return (taps - 1) / (double) factor; }

        // 1 echantillon -> 4 echantillons
        inline void up (float x, float* out) noexcept
        {
            constexpr int L = taps / factor;
            upPos = (upPos + L - 1) % L;
            upHist[upPos] = x; upHist[upPos + L] = x;
            const float* hp = upHist + upPos;
            for (int ph = 0; ph < factor; ++ph)
            {
                float acc = 0;
                for (int k = 0; k < L; ++k)
                    acc += h[k * factor + ph] * hp[k];
                out[ph] = acc * factor;
            }
        }
        // 4 echantillons -> 1 echantillon
        inline float down (const float* in) noexcept
        {
            for (int i = 0; i < factor; ++i)
            {
                pos = (pos + taps - 1) % taps;
                hist[pos] = in[i]; hist[pos + taps] = in[i];
            }
            const float* hp = hist + pos;
            float acc = 0;
            for (int k = 0; k < taps; ++k)
                acc += h[k] * hp[k];
            return acc;
        }
    };

    //--------------------------------------------------------------------------
    enum Mode { modeSDT2 = 0, modeLaerm = 1, modeSDT1 = 2 };

    struct Params
    {
        float gain = 7.5f, boost = 7.5f, level = 7.5f;     // 0..10
        float treble = 10.0f, mids = 3.75f, bass = 7.5f;   // 0..10 (5 = plat)
        bool  eq = true, boostOn = false, active = true;
        int   mode = modeSDT1;
    };

    struct ModeVoice
    {
        float hpHz, prePeakHz, prePeakQ, prePeakDb;
        float gainOffsetDb;
        float vfPos, vfNeg, knee;     // seuil des diodes (positif / negatif), durete du coude
        float extraComp;              // etage de compression supplementaire (SDT-2)
        float postLP;                 // filtre de sortie de l'ampli op (sur-echantillonne)
        float lowShelfDb, highShelfHz, highShelfDb, presenceDb;
        float makeupDb;               // volume relatif des modes
        float bias;                   // asymetrie (harmoniques paires)
    };

    inline const ModeVoice& voice (int m)
    {
        static const ModeVoice v[3] =
        {
            // v1.6 : le mordant du boost est integre a la voix de base (passe-haut d'entree plus haut, attaque mise en avant,
            // ecretage plus franc, plus de presence) ; le boost s'ajoute toujours par-dessus
            // SDT-2 : plus compresse et sature, plus sombre, un peu moins fort
            { 200.0f, 950.0f, 0.75f, 6.0f,   5.0f,  0.28f, 0.26f, 5.0f, 1.0f, 6200.0f,  5.5f, 5000.0f, -3.5f, 2.0f, -1.0f, 0.09f },
            // LAERM : plus ouvert, plus direct, plus fort (seuil haut type LED)
            { 165.0f, 1300.0f, 0.60f, 4.0f, -1.5f,  0.70f, 0.60f, 5.5f, 0.0f, 10000.0f, 4.5f, 7000.0f, -1.0f, 3.0f, -1.6f, 0.05f },
            // SDT-1 : la Stampede d'origine (silicium a la masse, mediums chantants)
            { 185.0f, 1100.0f, 0.70f, 6.0f,   2.0f,  0.34f, 0.31f, 6.0f, 0.0f, 7800.0f,  5.5f, 5600.0f, -2.0f, 2.5f,  0.0f, 0.09f },
        };
        return v[std::min (2, std::max (0, m))];
    }

    //--------------------------------------------------------------------------
    class Channel
    {
    public:
        void prepare (double sampleRate)
        {
            sr = sampleRate; srO = sr * Oversampler4::factor;
            os.design();
            dcIn.setLP (sr, 18.0);
            bassLP.lowpass (sr, 170.0, 0.6);
            envA = (float) (1.0 - std::exp (-1.0 / (0.002 * sr)));     // suivi du jeu : attaque 2 ms
            envR = (float) (1.0 - std::exp (-1.0 / (0.030 * sr)));     //               relachement 30 ms
            refR = (float) (1.0 - std::exp (-1.0 / (0.700 * sr)));     // reference : crete lente (700 ms)
            dcOut.setLP (sr, 12.0);
            inter.setLP (srO, 45.0);
            reset();
        }
        void reset()
        {
            os.reset();
            for (auto* b : { &hp, &hp2, &preMud, &outScoop, &outSub, &prePeak, &preLP, &post1, &post2, &outLow, &outHigh, &outPres, &eqBass, &eqMid, &eqTreb })
                b->reset();
            dcIn.reset(); dcOut.reset(); inter.reset(); st1lp.reset(); bassLP.reset(); env = ref = 0.0f;
        }

        // filtres dependant des reglages (appele par blocs de 16 echantillons avec des valeurs lissees)
        void updateFilters (const ModeVoice& v, float hpHz, float st1Fc, float bassDb, float midDb, float trebDb)
        {
            hp.highpass (sr, hpHz, 0.85);
            hp2.highpass (sr, hpHz * 0.8, 0.6);               // v1.5 : 4e ordre avant l'ecretage -> basses nettes, sans bave
            preMud.peak (sr, 300.0, 0.9, -6.0);                // creux bas-medium avant l'ecretage : accords nets, pas de bouillie
            prePeak.peak (sr, v.prePeakHz, v.prePeakQ, v.prePeakDb);
            preLP.lowpass (sr, 7200.0, 0.65);
            st1lp.setLP (srO, st1Fc);
            post1.lowpass (srO, v.postLP * DOORN_LP_SCALE, 0.62);
            post2.lowpass (srO, v.postLP * DOORN_LP_SCALE * 1.6, 0.55);
            outLow.peak (sr, 100.0, 0.8, v.lowShelfDb + DOORN_LOW_DB + 2.0);   // grave epais facon stoner, mais ferme (bosse, pas de plateau)
            outSub.highpass (sr, 55.0, 0.7);
            outHigh.highShelf (sr, v.highShelfHz, v.highShelfDb + DOORN_HIGH_DB);
            outScoop.peak (sr, DOORN_SCOOP_HZ, DOORN_SCOOP_Q, DOORN_SCOOP_DB);   // creux des mediums de la Thorn
            outPres.peak (sr, 2900.0, 0.9, v.presenceDb);
            eqBass.lowShelf (sr, 100.0, bassDb, 0.7);
            eqMid.peak (sr, 1000.0, 0.85, midDb);
            eqTreb.highShelf (sr, 3000.0, trebDb, 0.7);
        }

        // un echantillon ; g1 / g2 : gains des deux etages, eqMix : 0 = EQ retire, 1 = EQ actif
        inline float process (float x, const ModeVoice& v, float g1, float g2, float eqMix) noexcept
        {
            x = dcIn.hp (x);
            // suivi du niveau de jeu (avant la distorsion) pour des basses qui suivent l'attaque
            const float ax = std::abs (x);
            env += (ax - env) * (ax > env ? envA : envR);
            ref = std::max (env, ref + (env - ref) * refR);
            x = hp2.process (hp.process (x));
            x = prePeak.process (preMud.process (x));
            x = preLP.process (x);

            float up[Oversampler4::factor];
            os.up (x, up);
            for (int i = 0; i < Oversampler4::factor; ++i)
            {
                // etage 1 : gain + rails (pompe de charge ~18 V -> marge, coude doux), biais leger
                float s = up[i] * g1 + v.bias * 0.25f;
                s = s * 0.90f;                                   // rails a ~18 V : l'etage 1 reste propre plus longtemps
                s = (s / std::pow (1.0f + std::pow (std::abs (s), 3.0f), 1.0f / 3.0f)) * 1.6f;
                s = st1lp.lp (s);
                s = inter.hp (s);                               // liaison entre etages (enleve le biais)

                // etage 2 : gain puis diodes a la masse
                float t = s * g2 + v.bias * 0.08f;
                if (v.extraComp > 0.0f)                         // SDT-2 : etage de compression en plus
                    t = std::tanh (t * 1.25f) * 1.5f;
                const float vf = t >= 0.0f ? v.vfPos : v.vfNeg;
                t = t / std::pow (1.0f + std::pow (std::abs (t) / vf, v.knee), 1.0f / v.knee);
                t = post2.process (post1.process (t));
                up[i] = t;
            }
            float y = os.down (up);

            y = dcOut.hp (y);
            // basses dynamiques (v1.5) : la distorsion maintient le grave quand la note s'eteint (bave) ;
            // ici le grave suit le jeu : plein a l'attaque, il retombe (jusqu a -10 dB) quand la note s'eteint
            {
                const float rel = ref > 1.0e-6f ? clampf (env / ref, 0.0f, 1.0f) : 1.0f;
                const float bg = 0.30f + 0.70f * rel;
                const float lo = bassLP.process (y);
                y += (bg - 1.0f) * lo;
                // anti-compression (v1.6) : la sortie suit a nouveau le jeu (attaques devant, notes qui retombent),
                // comme un ampli qui « respire » ; jusqu'a -9 dB quand la note s'eteint
                y *= clampf (std::pow (rel + 1.0e-4f, 0.33f), 0.35f, 1.0f);
            }
            y = outPres.process (outHigh.process (outScoop.process (outLow.process (outSub.process (y)))));
            const float e = eqTreb.process (eqMid.process (eqBass.process (y)));
            return y + (e - y) * eqMix;
        }

    private:
        double sr = 48000.0, srO = 192000.0;
        Oversampler4 os;
        Biquad hp, hp2, preMud, outScoop, outSub, prePeak, preLP, post1, post2, outLow, outHigh, outPres, eqBass, eqMid, eqTreb;
        OnePole dcIn, dcOut, inter, st1lp;
        Biquad bassLP;
        float env = 0.0f, ref = 0.0f, envA = 0.01f, envR = 0.001f, refR = 0.0001f;
    };

    //--------------------------------------------------------------------------
    class Engine
    {
    public:
        static constexpr int maxChannels = 2;

        void prepare (double sampleRate, int numChannels)
        {
            sr = sampleRate;
            nCh = std::min (maxChannels, std::max (1, numChannels));
            for (auto& c : ch) c.prepare (sr);
            for (auto* s : { &sGain, &sBoost, &sLevel, &sTreb, &sMid, &sBass, &sEq, &sBoostOn, &sMakeup })
                s->setTime (sr, 14.0);
            sActive.setTime (sr, 3.0);
            sMode.setTime (sr, 6.0);
            first = true;
            counter = 0;
            std::memset (dryLine, 0, sizeof (dryLine));
            dryPos = 0;
            dryDelay = latencyInt();
        }

        static double latencySamples() { return Oversampler4::latency(); }
        static int latencyInt() { return (int) std::lround (Oversampler4::latency()); }

        // gain du potard GAIN (dB) : courbe audio, passe en « fuzz » au-dela de 13 h
        static float gainDb (float knob)
        {
            const float g = clampf (knob / 10.0f, 0.0f, 1.0f);
            return DOORN_G0 + DOORN_G1 * std::pow (g, DOORN_GEXP);   // v1.3 : beaucoup de gain des le debut de la course
        }
        static float boostDb (float knob) { return 14.0f * clampf (knob / 10.0f, 0.0f, 1.0f); }
        static float eqDb (float knob, float range) { return (clampf (knob, 0.0f, 10.0f) - 5.0f) / 5.0f * range; }
        // LEVEL : 0 = coupe, midi ~ -15 dB, 15 h ~ -7 dB, maxi 0 dB (courbe audio)
        static float levelDb (float knob)
        {
            const float l = clampf (knob / 10.0f, 0.0f, 1.0f);
            return l <= 0.0f ? -90.0f : -60.0f + 60.0f * std::pow (l, 0.42f);
        }

        // buffers non entrelaces ; in == out autorise
        void process (float* const* io, int numSamples, const Params& p)
        {
            const ModeVoice& v = voice (p.mode);
            if (first)
            {
                sGain.reset (p.gain); sBoost.reset (p.boost); sLevel.reset (p.level);
                sTreb.reset (p.treble); sMid.reset (p.mids); sBass.reset (p.bass);
                sEq.reset (p.eq ? 1.0f : 0.0f); sBoostOn.reset (p.boostOn ? 1.0f : 0.0f);
                sActive.reset (p.active ? 1.0f : 0.0f); sMakeup.reset (v.makeupDb);
                sMode.reset (1.0f);
                curMode = p.mode; first = false;
                refresh (v);
            }

            for (int i = 0; i < numSamples; ++i)
            {
                // changement de mode : court fondu (comme le relais) pour eviter le clic
                if (p.mode != curMode)
                {
                    const float m = sMode.next (0.0f);
                    if (m < 0.002f) { curMode = p.mode; sMode.reset (0.0f); refresh (voice (curMode)); }
                }
                else
                    sMode.next (1.0f);

                const ModeVoice& cv = voice (curMode);
                const float gn  = sGain.next (p.gain);
                const float bo  = sBoost.next (p.boost);
                const float bon = sBoostOn.next (p.boostOn ? 1.0f : 0.0f);
                const float lv  = sLevel.next (p.level);
                sTreb.next (p.treble); sMid.next (p.mids); sBass.next (p.bass);
                const float eqm = sEq.next (p.eq ? 1.0f : 0.0f);
                const float act = sActive.next (p.active ? 1.0f : 0.0f);
                const float mk  = sMakeup.next (cv.makeupDb);

                if ((counter++ & 15) == 0)
                    refresh (cv);

                // repartition du gain total sur les deux etages
                const float totalDb = gainDb (gn) + boostDb (bo) * bon + cv.gainOffsetDb;
                const float g1 = dbToGain (std::min (totalDb, 30.0f) * 0.85f - 2.0f);
                const float g2 = dbToGain (std::max (0.0f, totalDb - 30.0f) + 3.0f) * 0.6f;
                const float out = dbToGain (levelDb (lv) + mk + outTrim) * sMode.s2;

                for (int c = 0; c < nCh; ++c)
                {
                    const float x = io[c][i];
                    const float wet = ch[c].process (x, cv, g1, g2, eqm) * out;
                    // signal direct retarde de la latence du sur-echantillonnage (bypass aligne, compensation du DAW)
                    float* dl = dryLine[c];
                    dl[dryPos] = x;
                    const float dry = dl[(dryPos + dryLen - dryDelay) % dryLen];
                    // le chemin traite tourne toujours (aucun saut a l'enclenchement) ;
                    // bypass = signal direct, comme le relais
                    io[c][i] = safety (dry + (wet - dry) * act);
                }
                lastBoostMix = bon;
                dryPos = (dryPos + 1) % dryLen;
            }
        }

        float outTrim = 5.5f;           // calibrage : SDT-1, gain 15 h, level midi ~ niveau d'une guitare DI
        float lastBoostMix = 0.0f;

    private:
        void refresh (const ModeVoice& v)
        {
            const float bon = sBoostOn.s2;
            const float bo  = sBoost.s2 / 10.0f;
            const float hpHz = v.hpHz + 45.0f * bon * (0.35f + 0.65f * bo);     // le boost resserre le grave
            // filtre de l'ampli op : la bande passante baisse quand le gain monte
            const float gTot = gainDb (sGain.s2) + boostDb (sBoost.s2) * bon;
            const float st1Fc = 14000.0f - 70.0f * clampf (gTot, 0.0f, 60.0f);
            for (int c = 0; c < nCh; ++c)
                ch[c].updateFilters (v, hpHz, st1Fc, eqDb (sBass.s2, 15.0f), eqDb (sMid.s2, 12.0f), eqDb (sTreb.s2, 15.0f));
        }

        static inline float safety (float x) noexcept
        {
            const float ax = std::abs (x);
            if (ax < 0.95f) return x;
            return std::copysign (0.95f + 0.05f * std::tanh ((ax - 0.95f) / 0.05f), x);
        }

        double sr = 48000.0;
        int nCh = 2;
        static constexpr int dryLen = 64;
        float dryLine[maxChannels][dryLen] {};
        int dryPos = 0, dryDelay = 32;
        Channel ch[maxChannels];
        Smooth2 sGain, sBoost, sLevel, sTreb, sMid, sBass, sEq, sBoostOn, sActive, sMakeup, sMode;
        int curMode = modeSDT1;
        bool first = true;
        unsigned counter = 0;
    };
}
