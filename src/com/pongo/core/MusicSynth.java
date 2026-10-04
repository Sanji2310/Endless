package com.pongo.core;

import java.util.Random;

/**
 * Offline music synthesizer for the soundtrack (Soundtrack.java writes the songs). Pure Java, no Android, no samples:
 * every instrument is modelled (additive piano and bells, FM electric piano, Karplus-Strong koto / shamisen / harp /
 * guitar, PolyBLEP pads and leads, breathy flutes, synthesized drums) and mixed into a stereo bus with a Freeverb
 * style reverb, a ping-pong delay and a soft-knee master compressor.
 *
 * A Song is rendered once (at load, on a background thread) into a seamless loop: notes and echoes that ring past the
 * loop end are folded back onto its start, so the loop plays forever without a seam.
 *
 * Times are in beats; pitches are MIDI note numbers (60 = middle C).
 */
public final class MusicSynth {
    public static final int RATE = 22050;

    // ------------------------------------------------------------------ instruments
    public static final int PIANO = 0, EPIANO = 1, GLOCK = 2, MUSICBOX = 3, HARP = 4, KOTO = 5, SHAMISEN = 6,
            PAD = 7, STRINGS = 8, FLUTE = 9, SHAKU = 10, LEAD = 11, SUPERSAW = 12, BASS = 13, SUBBASS = 14,
            SYNBASS = 15, GUITAR = 16, CLEANGTR = 17, CHOIR = 18, BRASS = 19, CELESTA = 20,
            KICK = 40, SNARE = 41, CLAP = 42, HAT = 43, OHAT = 44, SHAKER = 45, RIDE = 46, CRASH = 47, TAIKO = 48,
            TOM = 49, WOOD = 50, RIM = 51, CHIMES = 52, TRIANGLE = 53, SNAP = 54, KAKKO = 55, REVCYM = 56, SWELL = 57;

    // ------------------------------------------------------------------ tables / helpers
    private static final int TN = 4096;
    private static final float[] SIN = new float[TN + 1];

    static {
        for (int i = 0; i <= TN; i++) SIN[i] = (float) Math.sin(2 * Math.PI * i / TN);
    }

    /** sin(2 pi p), p in cycles. */
    static float sn(float p) {
        p -= (float) Math.floor(p);
        float x = p * TN;
        int i = (int) x;
        float f = x - i;
        return SIN[i] + (SIN[i + 1] - SIN[i]) * f;
    }

    public static float hz(float midi) { return (float) (440.0 * Math.pow(2.0, (midi - 69) / 12.0)); }

    private static float blep(float t, float dt) {
        if (t < dt) { t /= dt; return t + t - t * t - 1f; }
        if (t > 1f - dt) { t = (t - 1f) / dt; return t * t + t + t + 1f; }
        return 0f;
    }

    /** Band-limited saw, phase t in [0,1). */
    static float saw(float t, float dt) { return 2f * t - 1f - blep(t, dt); }

    static float square(float t, float dt, float pw) {
        float v = t < pw ? 1f : -1f;
        v += blep(t, dt);
        float t2 = t - pw; if (t2 < 0) t2 += 1f;
        v -= blep(t2, dt);
        return v;
    }

    /** Zavalishin TPT state variable filter. */
    static final class Svf {
        float ic1, ic2, a1, a2, a3, k;
        void set(float fc, float q) {
            fc = Math.max(20f, Math.min(fc, RATE * 0.45f));
            float g = (float) Math.tan(Math.PI * fc / RATE);
            k = 1f / q;
            a1 = 1f / (1f + g * (g + k)); a2 = g * a1; a3 = g * a2;
        }
        float v1, v2;
        float run(float v0) {
            float v3 = v0 - ic2;
            v1 = a1 * ic1 + a2 * v3;
            v2 = ic2 + a2 * ic1 + a3 * v3;
            ic1 = 2 * v1 - ic1; ic2 = 2 * v2 - ic2;
            return v2;
        }
        float lp(float x) { return run(x); }
        float bp(float x) { run(x); return v1; }
        float hp(float x) { run(x); return x - k * v1 - v2; }
    }

    static float clamp(float x, float a, float b) { return x < a ? a : x > b ? b : x; }

    /** Attack / decay-to-sustain / release envelope at sample i of a note gated for `gate` samples. */
    static float adsr(int i, int gate, float a, float d, float s, float r) {
        float t = i / (float) RATE, g = gate / (float) RATE;
        float e;
        if (t < a) e = t / a;
        else e = s + (1 - s) * (float) Math.exp(-(t - a) / Math.max(1e-4f, d));
        if (t > g) {
            float eg = g < a ? g / a : s + (1 - s) * (float) Math.exp(-(g - a) / Math.max(1e-4f, d));
            e = eg * (float) Math.exp(-(t - g) / Math.max(1e-4f, r));
        }
        return e;
    }

    // ------------------------------------------------------------------ the song bus

    public final float bpm;
    public final int beatsPerBar;
    public final int loopLen, tail, len;
    public final float spb;               // samples per beat
    final float[] L, R, rev, dly;
    private final Random rnd;
    /** Global swing for off 16ths (0 straight .. 0.33 hard). */
    public float swing;
    public float humanize = 0.006f;
    public float revSize = 0.82f, revDamp = 0.35f, revWet = 0.9f;
    public float dlyBeats = 0.75f, dlyFb = 0.35f, dlyWet = 0.8f;
    public float masterTarget = 0.16f;   // RMS target (about -16 dBFS)

    public MusicSynth(float bpm, int beatsPerBar, int bars, long seed) {
        this.bpm = bpm;
        this.beatsPerBar = beatsPerBar;
        spb = RATE * 60f / bpm;
        loopLen = Math.round(bars * beatsPerBar * spb);
        tail = (int) (RATE * 4.5f);
        len = loopLen + tail;
        L = new float[len]; R = new float[len]; rev = new float[len]; dly = new float[len];
        rnd = new Random(seed);
        if (logNotes) log = new java.util.ArrayList<float[]>();
    }

    public int bars() { return Math.round(loopLen / (beatsPerBar * spb)); }

    /** Sample index of a beat (wrapped into the loop) with swing and a little human timing. */
    private int at(float beat, boolean human) {
        float sixteenth = beat * 4f;
        float frac = sixteenth - (float) Math.floor(sixteenth + 1e-4f);
        int st = (int) Math.floor(sixteenth + 1e-4f);
        if (swing > 0 && frac < 0.01f && (st & 1) == 1) beat += swing * 0.25f;
        float s = beat * spb;
        if (human && humanize > 0) s += (float) rnd.nextGaussian() * humanize * RATE * 0.5f;
        int i = Math.round(s) % loopLen;
        if (i < 0) i += loopLen;
        return i;
    }

    /** Energy written per instrument (for checking the mix balance in tools/preview/MusicSim). */
    public final double[] energy = new double[64];

    private void mixIn(float[] v, int start, float gain, float pan, float revSend, float dlySend) {
        float pl = (float) Math.cos((pan + 1) * Math.PI / 4) * 1.4142f, pr = (float) Math.sin((pan + 1) * Math.PI / 4) * 1.4142f;
        for (int i = 0; i < v.length; i++) {
            int j = start + i;
            if (j >= len) j -= loopLen;       // past the tail: wrap onto the loop start
            float x = v[i] * gain;
            L[j] += x * pl; R[j] += x * pr;
            if (revSend > 0) rev[j] += x * revSend;
            if (dlySend > 0) dly[j] += x * dlySend;
        }
    }

    /** One note. dur in beats (gate length); vel 0..1; pan -1..1. */
    public void note(int inst, float beat, float dur, float midi, float vel, float pan, float revSend) {
        note(inst, beat, dur, midi, vel, pan, revSend, 0f);
    }

    /** Debug: every note written (inst, beat, dur, midi, vel) when non-null. */
    public java.util.ArrayList<float[]> log;
    public static boolean logNotes;

    /** Debug: render only this instrument (-1: all). */
    public static int solo = -1;

    /** Role of the notes being written: MELODY lines win, ACCOMP (chords, arpeggios, bass) notes that would rub a
     *  semitone (or minor 9th) against a held melody note are dropped at render time. */
    public static final int FREE = 0, MELODY = 1, ACCOMP = 2, PADS = 3;
    public int role = FREE;
    private final java.util.ArrayList<float[]> events = new java.util.ArrayList<float[]>();

    public void note(int inst, float beat, float dur, float midi, float vel, float pan, float revSend, float dlySend) {
        if (solo >= 0 && inst != solo) return;
        events.add(new float[]{inst, beat, dur, midi, vel, pan, revSend, dlySend, role});
    }

    /** Drops notes that would hold a semitone (or minor 9th) against a note of a higher-priority role: chord pads yield
     *  to arpeggios and bass lines, and those yield to the melody (>= 0.4 beat of overlap counts). */
    private void resolveClashes() {
        for (float[] e : events) {
            if (e[8] < ACCOMP || e[0] >= KICK) continue;
            int a = Math.round(e[3]);
            for (float[] m : events) {
                if (m[8] == FREE || m[8] >= e[8] || m[0] >= KICK || m[4] <= 0f) continue;
                float lo = Math.max(e[1], m[1]), hi = Math.min(e[1] + e[2], m[1] + m[2]);
                if (hi - lo < 0.4f) continue;
                if (Math.abs(a - Math.round(m[3])) % 12 == 1) { e[4] = 0f; break; }
            }
        }
    }

    private void play(float[] e) {
        int inst = (int) e[0];
        float beat = e[1], dur = e[2], midi = e[3], vel = e[4];
        if (vel <= 0f) return;
        if (log != null) log.add(new float[]{inst, beat, dur, midi, vel});
        float pan = e[5], revSend = e[6], dlySend = e[7];
        int s = at(beat, inst < KICK);
        int gate = Math.max(1, Math.round(dur * spb));
        float v = clamp(vel * (1f + (float) rnd.nextGaussian() * 0.04f), 0.05f, 1.2f);
        float[] w = voice(inst, midi, gate, v);
        double en = 0;
        for (float x : w) en += x * x;
        energy[inst] += en;
        mixIn(w, s, 1f, pan, revSend, dlySend);
    }

    // ------------------------------------------------------------------ voices

    float[] voice(int inst, float midi, int gate, float vel) {
        float f = hz(midi);
        switch (inst) {
            case PIANO: return piano(f, gate, vel);
            case EPIANO: return epiano(f, gate, vel);
            case GLOCK: return bars(f, gate, vel, new float[]{1f, 2.76f, 5.40f, 8.93f}, new float[]{1f, .45f, .25f, .12f}, 1.6f, 0.002f);
            case CELESTA: return bars(f, gate, vel, new float[]{1f, 2f, 3.01f, 4.2f}, new float[]{1f, .35f, .12f, .06f}, 1.1f, 0.003f);
            case MUSICBOX: return bars(f, gate, vel, new float[]{1f, 3.0f, 5.93f, 9.1f}, new float[]{1f, .25f, .12f, .05f}, 1.3f, 0.001f);
            case HARP: return pluck(f, gate, vel, 0.996f, 0.55f, 0.18f, false);
            case KOTO: return koto(f, gate, vel);
            case SHAMISEN: return shamisen(f, gate, vel);
            case CLEANGTR: return pluck(f, gate, vel, 0.995f, 0.75f, 0.25f, false);
            case GUITAR: return guitar(f, gate, vel);
            case PAD: return pad(f, gate, vel, 5, 0.6f, 1.2f, 900f, 0.010f);
            case STRINGS: return strings(f, gate, vel);
            case CHOIR: return choir(f, gate, vel);
            case BRASS: return brass(f, gate, vel);
            case FLUTE: return flute(f, gate, vel, false);
            case SHAKU: return flute(f, gate, vel, true);
            case LEAD: return lead(f, gate, vel);
            case SUPERSAW: return pad(f, gate, vel, 7, 0.01f, 0.25f, 3200f, 0.018f);
            case BASS: return bass(f, gate, vel);
            case SUBBASS: return subbass(f, gate, vel);
            case SYNBASS: return synbass(f, gate, vel);
            case KICK: return kick(vel);
            case SNARE: return snare(vel);
            case CLAP: return clap(vel);
            case HAT: return hat(vel, 0.045f);
            case OHAT: return hat(vel, 0.32f);
            case SHAKER: return shaker(vel);
            case RIDE: return ride(vel);
            case CRASH: return crash(vel);
            case TAIKO: return taiko(vel, f);
            case TOM: return tom(vel, f);
            case WOOD: return wood(vel, f, 0.07f, 18f);
            case KAKKO: return wood(vel, f, 0.11f, 9f);
            case RIM: return rim(vel);
            case CHIMES: return chimes(vel, gate);
            case TRIANGLE: return bars(f, (int) (RATE * 1.5f), vel * 0.5f, new float[]{1f, 2.9f, 5.1f, 7.3f}, new float[]{1f, .6f, .4f, .25f}, 2.2f, 0.001f);
            case SNAP: return snap(vel);
            case REVCYM: return revcym(vel, gate);
            case SWELL: return swell(vel, gate);
        }
        return new float[1];
    }

    /** Two-string additive piano with stretched partials, a hammer knock and string beating. */
    private float[] piano(float f, int gate, float vel) {
        float t1 = clamp(3.2f * (float) Math.sqrt(220f / f), 0.5f, 7f);
        int n = Math.min(gate + (int) (0.35f * RATE), (int) (t1 * 2.2f * RATE) + RATE / 5);
        n = Math.max(n, RATE / 8);
        float[] o = new float[n];
        float bright = 0.45f + 0.4f * vel;
        int kmax = Math.min(14, (int) (RATE * 0.45f / f));
        float B = 0.00035f;
        for (int k = 1; k <= kmax; k++) {
            float fk = k * f * (float) Math.sqrt(1 + B * k * k);
            if (fk > RATE * 0.45f) break;
            float amp = (float) (Math.pow(bright, k - 1) / Math.pow(k, 0.9)) * (k == 1 ? 1f : 0.9f);
            float dk = t1 / (1f + 0.55f * (k - 1));
            float fast = dk * 0.18f;
            float ph1 = rnd.nextFloat(), ph2 = rnd.nextFloat();
            float d1 = fk / RATE, d2 = fk * 1.0009f / RATE;
            float e1 = (float) Math.exp(-1.0 / (dk * RATE)), e2 = (float) Math.exp(-1.0 / (fast * RATE));
            float env = 1f, envF = 1f;
            for (int i = 0; i < n; i++) {
                float e = 0.65f * env + 0.35f * envF;
                o[i] += amp * e * (sn(ph1) + 0.8f * sn(ph2)) * 0.55f;
                ph1 += d1; ph2 += d2; if (ph1 > 1) ph1 -= 1; if (ph2 > 1) ph2 -= 1;
                env *= e1; envF *= e2;
            }
        }
        // hammer knock
        Svf h = new Svf(); h.set(Math.min(f * 4, 4000), 1.2f);
        int hk = (int) (0.012f * RATE);
        for (int i = 0; i < hk && i < n; i++) o[i] += h.bp(rnd.nextFloat() * 2 - 1) * 0.35f * vel * (1 - i / (float) hk);
        // damper
        float rel = (float) Math.exp(-1.0 / (0.09f * RATE));
        float g = 1f;
        for (int i = 0; i < n; i++) {
            float a = Math.min(1f, i / (0.002f * RATE));
            if (i > gate) g *= rel;
            o[i] *= a * g * vel * 0.5f;
        }
        return o;
    }

    /** FM electric piano (Rhodes-like): bell-ish tine at the attack, warm sine body, gentle tremolo. */
    private float[] epiano(float f, int gate, float vel) {
        int n = gate + (int) (0.4f * RATE);
        float[] o = new float[n];
        float pc = 0, pm = 0, pt = 0, ptm = 0;
        float dc = f / RATE, dm = f / RATE, dt = f * 14f / RATE;
        float dk = clamp(2.2f * (float) Math.sqrt(262f / f), 0.6f, 4f);
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float idx = (0.4f + 2.2f * vel) * (float) Math.exp(-t * 3.5f) + 0.25f;
            float mod = sn(pm) * idx;
            float tine = sn(pt + 0.7f * sn(ptm)) * (float) Math.exp(-t * 28f) * 0.3f * vel;
            float body = sn(pc + mod * 0.16f);
            float env = (float) Math.exp(-t / dk) * Math.min(1f, t / 0.002f);
            if (i > gate) env *= (float) Math.exp(-(i - gate) / (0.12f * RATE));
            float trem = 1f + 0.12f * sn(t * 4.6f);
            o[i] = (body + tine) * env * trem * vel * 0.36f;
            pc += dc; pm += dm; pt += dt; ptm += dt * 0.5f;
        }
        return o;
    }

    /** Struck bar (glockenspiel, music box, celesta, triangle): inharmonic partials, higher ones die faster. */
    private float[] bars(float f, int gate, float vel, float[] ratio, float[] amp, float decay, float click) {
        int n = (int) (RATE * decay * 1.6f) + Math.min(gate, RATE);
        float[] o = new float[n];
        for (int k = 0; k < ratio.length; k++) {
            float fk = f * ratio[k];
            if (fk > RATE * 0.45f) continue;
            float dk = decay / (1f + k * 1.4f);
            float e = (float) Math.exp(-1.0 / (dk * RATE)), env = amp[k];
            float ph = 0, d = fk / RATE;
            for (int i = 0; i < n; i++) { o[i] += sn(ph) * env; ph += d; env *= e; }
        }
        int ck = (int) (click * RATE);
        for (int i = 0; i < n; i++) {
            float a = ck > 0 ? Math.min(1f, i / (float) ck) : 1f;
            o[i] *= a * vel * 0.35f;
        }
        return o;
    }

    /** Karplus-Strong plucked string with a tuned fractional delay. */
    private float[] pluck(float f, int gate, float vel, float sustain, float bright, float pickPos, boolean buzz) {
        float period = RATE / f;
        float T60 = clamp(3.0f * (float) Math.sqrt(220f / f), 0.4f, 5f) * (sustain > 0.995f ? 1.3f : 1f);
        int n = Math.min(gate + (int) (0.15f * RATE), (int) (T60 * RATE));
        n = Math.max(n, RATE / 6);
        float[] o = new float[n];
        float damp = 0.5f - 0.18f * bright;   // one-zero loop filter weight; it delays the loop by `damp` samples
        double w = 2 * Math.PI * f / RATE;
        double lfDelay = Math.atan2(damp * Math.sin(w), (1 - damp) + damp * Math.cos(w)) / w;   // exact, at f
        int N = (int) Math.floor(period - lfDelay - 0.1);
        if (N < 2) N = 2;
        double frac = period - lfDelay - N;
        // allpass coefficient with exactly `frac` samples of phase delay at f
        float c = (float) (Math.sin((1 - frac) * w / 2) / Math.sin((1 + frac) * w / 2));
        float[] d = new float[N];
        // excitation: filtered noise with a pick-position comb
        Svf lp = new Svf(); lp.set(Math.min(f * (1.5f + 7 * bright * vel), 5500f), 0.6f);
        float[] ex = new float[N];
        for (int i = 0; i < N; i++) ex[i] = lp.lp(rnd.nextFloat() * 2 - 1);
        int pk = Math.max(1, (int) (N * pickPos));
        for (int i = 0; i < N; i++) d[i] = ex[i] - 0.8f * ex[(i + pk) % N];
        float loss = (float) Math.pow(10, -3.0 * period / (T60 * RATE));
        float ap = 0, apX = 0, prev = 0;
        int p = 0;
        for (int i = 0; i < n; i++) {
            float x = d[p];
            float y = (1 - damp) * x + damp * prev;
            prev = x;
            float a = c * y + apX - c * ap;   // first-order allpass: the fractional part of the delay
            apX = y; ap = a;
            float out = a * loss;
            if (i > gate) out *= 0.9985f;
            d[p] = out;
            o[i] = x;
            if (++p >= N) p = 0;
        }
        if (buzz) {   // sawari: the string grazing the neck adds a bright rectified edge (outside the loop, DC-blocked)
            float hp = 0, px = 0;
            for (int i = 0; i < n; i++) {
                float x = o[i] + 0.35f * Math.abs(o[i]);
                hp = 0.995f * (hp + x - px); px = x;
                o[i] = hp;
            }
        }
        for (int i = 0; i < n; i++) {
            float env = i > gate ? (float) Math.exp(-(i - gate) / (0.06f * RATE)) : 1f;
            env *= Math.min(1f, i / (0.0015f * RATE));   // 1.5 ms pick attack, no click
            o[i] *= vel * 0.7f * env;
        }
        return o;
    }

    /** Koto: bright pluck, a small pitch push after the attack (oshide), quick body decay. */
    private float[] koto(float f, int gate, float vel) {
        float[] o = pluck(f, gate, vel, 0.996f, 0.9f, 0.12f, false);
        // soundboard resonance + a little attack zing
        Svf bp = new Svf(); bp.set(f * 3f, 2f);
        for (int i = 0; i < o.length; i++) o[i] = o[i] * 0.85f + bp.bp(o[i]) * 0.4f;
        return o;
    }

    /** Shamisen: thin bright pluck with the sawari buzz and a skin "thwack". */
    private float[] shamisen(float f, int gate, float vel) {
        float[] o = pluck(f, Math.min(gate, (int) (0.5f * RATE)), vel, 0.99f, 1f, 0.08f, true);
        int k = (int) (0.02f * RATE);
        Svf bp = new Svf(); bp.set(1400f, 1.5f);
        for (int i = 0; i < k && i < o.length; i++) o[i] += bp.bp(rnd.nextFloat() * 2 - 1) * 0.6f * vel * (1 - i / (float) k);
        return o;
    }

    /** Overdriven guitar (anime opening power chords / chugs): KS string through drive and a speaker cab filter. */
    private float[] guitar(float f, int gate, float vel) {
        float[] a = pluck(f, gate, 1f, 0.996f, 0.9f, 0.15f, false);
        float[] b = pluck(f * 1.003f, gate, 1f, 0.996f, 0.9f, 0.2f, false);
        Svf cab = new Svf(); cab.set(3200f, 0.8f);
        Svf hp = new Svf(); hp.set(90f, 0.7f);
        float drive = 6f;
        for (int i = 0; i < a.length; i++) {
            float x = (a[i] + (i < b.length ? b[i] : 0)) * drive;
            x = (float) Math.tanh(x);
            x = cab.lp(hp.hp(x));
            float env = i > gate ? (float) Math.exp(-(i - gate) / (0.03f * RATE)) : 1f;
            a[i] = x * 0.35f * vel * env;
        }
        return a;
    }

    /** Detuned PolyBLEP saw stack through a resonant low-pass: soft pads (slow) and supersaw stabs (fast). */
    private float[] pad(float f, int gate, float vel, int voices, float att, float rel, float cutoff, float detune) {
        int n = gate + (int) (rel * 3f * RATE);
        float[] o = new float[n];
        float[] ph = new float[voices], dt = new float[voices];
        for (int v = 0; v < voices; v++) {
            float det = voices == 1 ? 0 : (v / (float) (voices - 1) - 0.5f) * 2f * detune;
            dt[v] = f * (1 + det) / RATE;
            ph[v] = rnd.nextFloat();
        }
        Svf flt = new Svf();
        float g = 1f / (float) Math.sqrt(voices);
        for (int i = 0; i < n; i++) {
            if ((i & 15) == 0) {
                float t = i / (float) RATE;
                float env = Math.min(1f, t / Math.max(att, 0.01f));
                flt.set(cutoff * (0.5f + 0.7f * env * vel) * (1 + 0.15f * sn(t * 0.3f)), 0.9f);
            }
            float s = 0;
            for (int v = 0; v < voices; v++) {
                s += saw(ph[v], dt[v]);
                ph[v] += dt[v]; if (ph[v] >= 1) ph[v] -= 1;
            }
            o[i] = flt.lp(s * g) * adsr(i, gate, att, 2f, 0.85f, rel) * vel * 0.35f;
        }
        return o;
    }

    /** String section: detuned saws with delayed vibrato, a bowing filter swell and a soft attack. */
    private float[] strings(float f, int gate, float vel) {
        int n = gate + (int) (0.9f * RATE);
        float[] o = new float[n];
        int V = 4;
        float[] ph = new float[V], det = {-0.006f, -0.002f, 0.003f, 0.007f}, vr = {5.1f, 5.6f, 4.8f, 5.9f};
        for (int v = 0; v < V; v++) ph[v] = rnd.nextFloat();
        Svf flt = new Svf(), body = new Svf();
        body.set(1100f, 0.6f);
        float vp = 0;
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float vib = Math.min(1f, Math.max(0f, (t - 0.25f) / 0.5f)) * 0.004f;
            float env = adsr(i, gate, 0.18f, 1.5f, 0.9f, 0.35f);
            if ((i & 15) == 0) flt.set(f * 2f + 2400f * env * (0.6f + 0.4f * vel), 0.7f);
            float s = 0;
            for (int v = 0; v < V; v++) {
                float fr = f * (1 + det[v] + vib * sn(t * vr[v] + v * 0.25f));
                float d = fr / RATE;
                s += saw(ph[v], d);
                ph[v] += d; if (ph[v] >= 1) ph[v] -= 1;
            }
            float x = flt.lp(s * 0.5f);
            x = x * 0.8f + body.bp(x) * 0.5f;
            o[i] = x * env * vel * 0.4f;
            vp += 0;
        }
        return o;
    }

    /** "Aah" choir pad: pulse stack through two formant band-passes. */
    private float[] choir(float f, int gate, float vel) {
        int n = gate + (int) (1.0f * RATE);
        float[] o = new float[n];
        float[] ph = new float[3], det = {-0.005f, 0f, 0.006f};
        Svf f1 = new Svf(), f2 = new Svf(), f3 = new Svf();
        f1.set(750f, 4f); f2.set(1200f, 5f); f3.set(2600f, 6f);
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float s = 0;
            for (int v = 0; v < 3; v++) {
                float d = f * (1 + det[v] + 0.003f * sn(t * 5f + v * 0.3f)) / RATE;
                s += saw(ph[v], d);
                ph[v] += d; if (ph[v] >= 1) ph[v] -= 1;
            }
            float x = f1.bp(s) * 1.0f + f2.bp(s) * 0.6f + f3.bp(s) * 0.25f;
            o[i] = x * adsr(i, gate, 0.35f, 2f, 0.9f, 0.6f) * vel * 0.17f;
        }
        return o;
    }

    /** Synth brass: saw pair with a filter "blat" on the attack. */
    private float[] brass(float f, int gate, float vel) {
        int n = gate + (int) (0.3f * RATE);
        float[] o = new float[n];
        float p1 = 0, p2 = 0.3f;
        Svf flt = new Svf();
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float env = adsr(i, gate, 0.04f, 0.3f, 0.75f, 0.15f);
            if ((i & 7) == 0) flt.set(f * (1.5f + 5f * env * vel * (0.7f + 0.6f * (float) Math.exp(-t * 6))), 1.1f);
            float d1 = f / RATE, d2 = f * 1.004f / RATE;
            float s = saw(p1, d1) + saw(p2, d2);
            p1 += d1; p2 += d2; if (p1 >= 1) p1 -= 1; if (p2 >= 1) p2 -= 1;
            o[i] = flt.lp(s * 0.5f) * env * vel * 0.45f;
        }
        return o;
    }

    /** Flute (western) or shakuhachi (bamboo: breathier, scoops up into the note, wider late vibrato). */
    private float[] flute(float f, int gate, float vel, boolean shaku) {
        int n = gate + (int) (0.2f * RATE);
        float[] o = new float[n];
        float ph = 0;
        Svf br = new Svf(); br.set(f * 2f, shaku ? 2.5f : 4f);
        Svf br2 = new Svf(); br2.set(f, 6f);
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float scoop = shaku ? -0.03f * (float) Math.exp(-t * 9f) : -0.006f * (float) Math.exp(-t * 25f);
            float vibAmt = Math.min(1f, Math.max(0f, (t - (shaku ? 0.35f : 0.2f)) / 0.4f)) * (shaku ? 0.012f : 0.006f);
            float fr = f * (1 + scoop + vibAmt * sn(t * (shaku ? 5.2f : 5.5f)));
            float d = fr / RATE;
            float tone = sn(ph) + 0.22f * sn(2 * ph) + 0.07f * sn(3 * ph) + (shaku ? 0.12f * sn(ph * 2 + 0.25f) : 0);
            ph += d; if (ph > 1) ph -= 1;
            float nz = rnd.nextFloat() * 2 - 1;
            float breath = br.bp(nz) * (shaku ? 0.55f : 0.25f) + br2.bp(nz) * (shaku ? 0.6f : 0.3f);
            float env = adsr(i, gate, shaku ? 0.09f : 0.05f, 0.8f, 0.85f, 0.09f);
            float chiff = (float) Math.exp(-t * 30f) * (shaku ? 0.8f : 0.4f);
            o[i] = (tone * (0.75f + 0.25f * env) + breath * (1 + chiff * 3)) * env * vel * 0.38f;
        }
        return o;
    }

    /** J-pop synth lead: pulse/saw blend, delayed vibrato, a bright filter blip on the attack. */
    private float[] lead(float f, int gate, float vel) {
        int n = gate + (int) (0.18f * RATE);
        float[] o = new float[n];
        float p1 = 0, p2 = 0.5f;
        Svf flt = new Svf();
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float vib = Math.min(1f, Math.max(0f, (t - 0.18f) / 0.25f)) * 0.008f * sn(t * 5.8f);
            float fr = f * (1 + vib - 0.01f * (float) Math.exp(-t * 40f));
            float d = fr / RATE;
            float s = 0.6f * square(p1, d, 0.42f) + 0.5f * saw(p2, d * 1.005f);
            p1 += d; p2 += d * 1.005f; if (p1 >= 1) p1 -= 1; if (p2 >= 1) p2 -= 1;
            float env = adsr(i, gate, 0.008f, 0.4f, 0.8f, 0.08f);
            if ((i & 7) == 0) flt.set(f * 3f + 3500f * (float) Math.exp(-t * 7f) * vel + 1200f, 0.9f);
            o[i] = flt.lp(s) * env * vel * 0.4f;
        }
        return o;
    }

    /** Finger bass: sine fundamental + a filtered saw growl, plucky. */
    private float[] bass(float f, int gate, float vel) {
        int n = gate + (int) (0.06f * RATE);
        float[] o = new float[n];
        float p = 0, ps = 0;
        Svf flt = new Svf();
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float d = f / RATE;
            if ((i & 7) == 0) flt.set(f * 2f + 900f * (float) Math.exp(-t * 14f) * vel, 1.0f);
            float s = sn(p) * 0.9f + flt.lp(saw(ps, d)) * 0.6f;
            p += d; ps += d; if (p > 1) p -= 1; if (ps > 1) ps -= 1;
            float env = adsr(i, gate, 0.004f, 0.5f, 0.6f, 0.03f);
            o[i] = (float) Math.tanh(s * 1.3f) * env * vel * 0.55f;
        }
        return o;
    }

    private float[] subbass(float f, int gate, float vel) {
        int n = gate + (int) (0.1f * RATE);
        float[] o = new float[n];
        float p = 0;
        for (int i = 0; i < n; i++) {
            float s = sn(p) + 0.15f * sn(2 * p);
            p += f / RATE;
            o[i] = s * adsr(i, gate, 0.01f, 1.5f, 0.85f, 0.08f) * vel * 0.6f;
        }
        return o;
    }

    /** Synth bass for the driving zones: square/saw with a filter pluck. */
    private float[] synbass(float f, int gate, float vel) {
        int n = gate + (int) (0.05f * RATE);
        float[] o = new float[n];
        float p1 = 0, p2 = 0.25f, ps = 0;
        Svf flt = new Svf();
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float d = f / RATE;
            if ((i & 7) == 0) flt.set(f * 1.5f + 1800f * (float) Math.exp(-t * 18f) * vel, 1.3f);
            float s = saw(p1, d) * 0.6f + square(p2, d * 0.999f, 0.5f) * 0.4f;
            p1 += d; p2 += d * 0.999f; if (p1 >= 1) p1 -= 1; if (p2 >= 1) p2 -= 1;
            float sub = sn(ps) * 0.6f; ps += d; if (ps > 1) ps -= 1;
            o[i] = (flt.lp(s) + sub) * adsr(i, gate, 0.003f, 0.3f, 0.7f, 0.025f) * vel * 0.5f;
        }
        return o;
    }

    // ------------------------------------------------------------------ drums

    private float[] kick(float vel) {
        int n = (int) (0.42f * RATE);
        float[] o = new float[n];
        float ph = 0;
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float f = 48f + 140f * (float) Math.exp(-t * 28f);
            ph += f / RATE;
            float body = sn(ph) * (float) Math.exp(-t * 7.5f);
            float click = (rnd.nextFloat() * 2 - 1) * (float) Math.exp(-t * 300f) * 0.35f;
            o[i] = (float) Math.tanh((body + click) * 1.6f) * vel * 0.75f;
        }
        return o;
    }

    private float[] snare(float vel) {
        int n = (int) (0.3f * RATE);
        float[] o = new float[n];
        Svf bp = new Svf(); bp.set(3800f, 0.7f);
        Svf hp = new Svf(); hp.set(900f, 0.7f);
        float p = 0;
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float tone = sn(p) * (float) Math.exp(-t * 28f) * 0.55f;
            p += (190f + 40f * (float) Math.exp(-t * 60f)) / RATE;
            float nz = hp.hp(bp.bp(rnd.nextFloat() * 2 - 1) * 1.5f) * (float) Math.exp(-t * 15f);
            o[i] = (tone + nz * 0.9f) * vel * 1.05f;
        }
        return o;
    }

    private float[] clap(float vel) {
        int n = (int) (0.25f * RATE);
        float[] o = new float[n];
        Svf bp = new Svf(); bp.set(1300f, 1.6f);
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float e = 0;
            for (int k = 0; k < 3; k++) { float tk = t - k * 0.011f; if (tk >= 0) e = Math.max(e, (float) Math.exp(-tk * 120f)); }
            e = Math.max(e, t > 0.022f ? 0.5f * (float) Math.exp(-(t - 0.022f) * 18f) : 0);
            o[i] = bp.bp(rnd.nextFloat() * 2 - 1) * e * vel * 1.9f;
        }
        return o;
    }

    private float[] hat(float vel, float dec) {
        int n = (int) ((dec * 3 + 0.02f) * RATE);
        float[] o = new float[n];
        Svf hp = new Svf(); hp.set(7000f, 0.8f);
        float[] ph = new float[6];
        float[] fr = {317f, 465f, 541f, 728f, 1002f, 1291f};
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float m = 0;
            for (int k = 0; k < 6; k++) { m += ph[k] < 0.5f ? 1 : -1; ph[k] += fr[k] * 3.1f / RATE; if (ph[k] > 1) ph[k] -= 1; }
            float x = hp.hp(m * 0.2f + (rnd.nextFloat() * 2 - 1) * 0.6f);
            o[i] = x * (float) Math.exp(-t / dec) * vel * 0.32f;
        }
        return o;
    }

    private float[] shaker(float vel) {
        int n = (int) (0.12f * RATE);
        float[] o = new float[n];
        Svf hp = new Svf(); hp.set(5500f, 0.9f);
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float e = Math.min(1f, t / 0.02f) * (float) Math.exp(-t * 30f);
            o[i] = hp.hp(rnd.nextFloat() * 2 - 1) * e * vel * 0.3f;
        }
        return o;
    }

    private float[] ride(float vel) {
        float[] o = bars(620f, RATE, vel * 0.5f, new float[]{1f, 1.47f, 2.09f, 2.56f, 3.44f}, new float[]{.5f, .6f, .5f, .4f, .3f}, 1.6f, 0f);
        float[] h = hat(vel * 0.7f, 0.35f);
        for (int i = 0; i < Math.min(o.length, h.length); i++) o[i] = o[i] * 0.4f + h[i];
        return o;
    }

    private float[] crash(float vel) {
        int n = (int) (2.4f * RATE);
        float[] o = new float[n];
        Svf hp = new Svf(); hp.set(3500f, 0.6f);
        Svf lp = new Svf(); lp.set(10000f, 0.5f);
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float e = (float) Math.exp(-t * 1.6f) * Math.min(1f, t / 0.003f);
            o[i] = lp.lp(hp.hp(rnd.nextFloat() * 2 - 1)) * e * vel * 0.3f;
        }
        return o;
    }

    private float[] revcym(float vel, int gate) {
        int n = gate;
        float[] o = new float[n];
        Svf hp = new Svf(); hp.set(3000f, 0.6f);
        for (int i = 0; i < n; i++) {
            float x = i / (float) n;
            o[i] = hp.hp(rnd.nextFloat() * 2 - 1) * x * x * x * vel * 0.4f;
        }
        return o;
    }

    /** Riser: filtered noise sweeping up over the gate. */
    private float[] swell(float vel, int gate) {
        int n = gate;
        float[] o = new float[n];
        Svf bp = new Svf();
        for (int i = 0; i < n; i++) {
            float x = i / (float) n;
            if ((i & 15) == 0) bp.set(300f + 6000f * x * x, 1.5f);
            o[i] = bp.bp(rnd.nextFloat() * 2 - 1) * x * x * vel * 0.5f;
        }
        return o;
    }

    /** Taiko: big low membrane with a pitch drop and a stick slap. f sets the drum size. */
    private float[] taiko(float vel, float f) {
        int n = (int) (1.1f * RATE);
        float[] o = new float[n];
        float ph = 0, ph2 = 0;
        Svf lp = new Svf(); lp.set(600f, 0.8f);
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float fr = f * (1 + 0.5f * (float) Math.exp(-t * 18f));
            ph += fr / RATE; ph2 += fr * 1.58f / RATE;
            float body = (sn(ph) + 0.35f * sn(ph2) * (float) Math.exp(-t * 9f)) * (float) Math.exp(-t * 4.2f);
            float slap = lp.lp(rnd.nextFloat() * 2 - 1) * (float) Math.exp(-t * 45f) * 0.7f;
            o[i] = (float) Math.tanh((body + slap) * 1.4f) * vel * 0.7f;
        }
        return o;
    }

    private float[] tom(float vel, float f) {
        int n = (int) (0.5f * RATE);
        float[] o = new float[n];
        float ph = 0;
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            ph += f * (1 + 0.4f * (float) Math.exp(-t * 25f)) / RATE;
            o[i] = (sn(ph) * (float) Math.exp(-t * 8f) + (rnd.nextFloat() * 2 - 1) * 0.2f * (float) Math.exp(-t * 60f)) * vel * 0.6f;
        }
        return o;
    }

    /** Woodblock / kakko: a short resonant knock. */
    private float[] wood(float vel, float f, float dur, float q) {
        int n = (int) (dur * RATE);
        float[] o = new float[n];
        Svf bp = new Svf(); bp.set(f, q);
        for (int i = 0; i < n; i++) {
            float t = i / (float) RATE;
            float ex = i < 40 ? (rnd.nextFloat() * 2 - 1) * (float) Math.sin(Math.PI * i / 40f) * 3f : 0;
            o[i] = bp.bp(ex) * vel * 0.5f * (float) Math.exp(-t * 30f);
        }
        return o;
    }

    private float[] rim(float vel) {
        int n = (int) (0.06f * RATE);
        float[] o = new float[n];
        Svf bp = new Svf(); bp.set(1800f, 6f);
        for (int i = 0; i < n; i++) {
            float ex = i < 30 ? (rnd.nextFloat() * 2 - 1) * 6f : 0;
            o[i] = bp.bp(ex) * vel * 0.4f * (float) Math.exp(-i / (0.012f * RATE));
        }
        return o;
    }

    private float[] snap(float vel) {
        int n = (int) (0.08f * RATE);
        float[] o = new float[n];
        Svf bp = new Svf(); bp.set(2400f, 2f);
        for (int i = 0; i < n; i++) o[i] = bp.bp(rnd.nextFloat() * 2 - 1) * vel * 0.9f * (float) Math.exp(-i / (0.01f * RATE));
        return o;
    }

    /** Wind chimes / mark tree glissando, spread over the gate. */
    private float[] chimes(float vel, int gate) {
        int n = gate + (int) (2.5f * RATE);
        float[] o = new float[n];
        int k = 14;
        for (int j = 0; j < k; j++) {
            float f = hz(96 - j * 1.5f + rnd.nextFloat());
            int st = (int) (gate * j / (float) k);
            float[] b = bars(f, RATE, vel * (0.5f + 0.5f * rnd.nextFloat()), new float[]{1f, 2.76f, 5.4f}, new float[]{1f, .4f, .2f}, 1.8f, 0.001f);
            for (int i = 0; i < b.length && st + i < n; i++) o[st + i] += b[i] * 0.5f;
        }
        return o;
    }

    // ------------------------------------------------------------------ effects + master

    private static void freeverb(float[] in, float[] outL, float[] outR, float size, float damp, float wet) {
        int[] cl = {1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617};
        int[] al = {556, 441, 341, 225};
        float scale = RATE / 44100f;
        float fb = 0.7f + 0.28f * size, d1 = damp * 0.4f, d2 = 1 - d1;
        for (int side = 0; side < 2; side++) {
            float[] out = side == 0 ? outL : outR;
            int spread = side * 23;
            float[][] cb = new float[8][];
            int[] cp = new int[8];
            float[] cs = new float[8];
            for (int c = 0; c < 8; c++) cb[c] = new float[(int) ((cl[c] + spread) * scale)];
            float[][] ab = new float[4][];
            int[] apos = new int[4];
            for (int a = 0; a < 4; a++) ab[a] = new float[(int) ((al[a] + spread) * scale)];
            for (int i = 0; i < in.length; i++) {
                float x = in[i] * 0.015f, acc = 0;
                for (int c = 0; c < 8; c++) {
                    float[] b = cb[c];
                    float y = b[cp[c]];
                    cs[c] = y * d2 + cs[c] * d1;
                    b[cp[c]] = x + cs[c] * fb;
                    if (++cp[c] >= b.length) cp[c] = 0;
                    acc += y;
                }
                for (int a = 0; a < 4; a++) {
                    float[] b = ab[a];
                    float bo = b[apos[a]];
                    b[apos[a]] = acc + bo * 0.5f;
                    acc = bo - acc;
                    if (++apos[a] >= b.length) apos[a] = 0;
                }
                out[i] += acc * wet * 3f;
            }
        }
    }

    private void pingpong(float[] in, float[] outL, float[] outR) {
        int d = Math.round(dlyBeats * spb);
        float[] bl = new float[d], br = new float[d];
        int p = 0;
        float lpL = 0, lpR = 0;
        for (int i = 0; i < in.length; i++) {
            float yl = bl[p], yr = br[p];
            lpL += (yl - lpL) * 0.35f; lpR += (yr - lpR) * 0.35f;
            bl[p] = in[i] + lpR * dlyFb;
            br[p] = lpL * dlyFb;
            outL[i] += yl * dlyWet; outR[i] += yr * dlyWet;
            if (++p >= d) p = 0;
        }
    }

    /** One-shot (a stinger): the tail is kept after the end instead of folded onto the start. */
    public boolean oneShot;
    /** Stingers: the beat where the next theme should come in (under the ringing tail); 0 = the end. */
    public float handoffBeats;

    /** Mixes the effect returns, folds the tail onto the loop start (or keeps it for a one-shot), masters and returns
     *  interleaved stereo 16-bit PCM. */
    public short[] render() {
        resolveClashes();
        for (float[] e : events) play(e);
        events.clear();
        float[] dl = new float[len], dr = new float[len];
        pingpong(dly, dl, dr);
        for (int i = 0; i < len; i++) { L[i] += dl[i]; R[i] += dr[i]; rev[i] += (dl[i] + dr[i]) * 0.25f; }
        // pre-delay and a low cut on the reverb send keep the mix clear
        float[] rin = new float[len];
        int pre = (int) (0.018f * RATE);
        float hpS = 0, prevX = 0;
        for (int i = 0; i < len; i++) {
            float x = i >= pre ? rev[i - pre] : 0f;
            hpS = 0.985f * (hpS + x - prevX); prevX = x;
            rin[i] = hpS;
        }
        float[] wl = new float[len], wr = new float[len];
        freeverb(rin, wl, wr, revSize, revDamp, revWet);
        int n = oneShot ? len : loopLen;
        float[] l = new float[n], r = new float[n];
        for (int i = 0; i < len; i++) {
            int j = i < n ? i : i - loopLen;   // everything ringing past the loop end rings into its start
            l[j] += L[i] + wl[i];
            r[j] += R[i] + wr[i];
        }
        master(l, r);
        if (oneShot) {   // fade the very end so it never clicks
            int f = Math.min(n, RATE / 4);
            for (int i = 0; i < f; i++) { float g = i / (float) f; l[n - 1 - i] *= g; r[n - 1 - i] *= g; }
        }
        short[] out = new short[n * 2];
        for (int i = 0; i < n; i++) {
            out[2 * i] = (short) Math.round(clamp(l[i], -1f, 1f) * 32767f);
            out[2 * i + 1] = (short) Math.round(clamp(r[i], -1f, 1f) * 32767f);
        }
        return out;
    }

    private void master(float[] l, float[] r) {
        int n = l.length;
        // DC / rumble cut
        float hl = 0, hr = 0, pl = 0, pr = 0;
        for (int pass = 0; pass < 2; pass++)
            for (int i = 0; i < n; i++) {
                hl = 0.9935f * (hl + l[i] - pl); pl = l[i];
                hr = 0.9935f * (hr + r[i] - pr); pr = r[i];
                if (pass == 1) { l[i] = hl; r[i] = hr; }
            }
        // loudness normalise to the RMS target, so every theme sits at the same level
        double ss = 0;
        for (int i = 0; i < n; i++) ss += l[i] * l[i] + r[i] * r[i];
        float rms = (float) Math.sqrt(ss / (2.0 * n));
        float g = rms > 1e-6f ? masterTarget / rms : 1f;
        // gentle glue compressor + soft limiter (envelope primed with one silent lap so the loop start matches)
        float env = 0, atk = (float) Math.exp(-1.0 / (0.005 * RATE)), relc = (float) Math.exp(-1.0 / (0.15 * RATE));
        float thr = 0.35f, ratio = 3f;
        for (int pass = 0; pass < 2; pass++)
            for (int i = 0; i < n; i++) {
                float a = Math.max(Math.abs(l[i]), Math.abs(r[i])) * g;
                env = a > env ? atk * env + (1 - atk) * a : relc * env + (1 - relc) * a;
                float gr = env > thr ? (thr + (env - thr) / ratio) / env : 1f;
                if (pass == 1) {
                    l[i] = soft(l[i] * g * gr);
                    r[i] = soft(r[i] * g * gr);
                }
            }
    }

    private static float soft(float x) {
        float a = Math.abs(x);
        if (a < 0.8f) return x;
        float y = 0.8f + 0.2f * (float) Math.tanh((a - 0.8f) / 0.2f);
        return x < 0 ? -y : y;
    }

    // ------------------------------------------------------------------ music helpers (pitch spelling, chords)

    /** "C#5" -> 73. */
    public static int pitch(String s) {
        int i = 0;
        int pc = "C D EF G A B".indexOf(Character.toUpperCase(s.charAt(i++)));
        if (pc < 0) throw new IllegalArgumentException(s);
        while (i < s.length() && (s.charAt(i) == '#' || s.charAt(i) == 'b')) { pc += s.charAt(i) == '#' ? 1 : -1; i++; }
        int oct = Integer.parseInt(s.substring(i));
        return 12 * (oct + 1) + pc;
    }

    /** Chord symbol -> pitch classes, root first (e.g. "C#m7", "AM7", "B7sus4", "F#m9", "E/G#"). index 0 is the bass. */
    public static int[] chord(String sym) {
        String bassName = null;
        int sl = sym.indexOf('/');
        if (sl > 0) { bassName = sym.substring(sl + 1); sym = sym.substring(0, sl); }
        int i = 0;
        int root = "C D EF G A B".indexOf(sym.charAt(i++));
        while (i < sym.length() && (sym.charAt(i) == '#' || sym.charAt(i) == 'b')) { root += sym.charAt(i) == '#' ? 1 : -1; i++; }
        String q = sym.substring(i);
        int[] iv;
        switch (q) {
            case "": iv = new int[]{0, 4, 7}; break;
            case "m": iv = new int[]{0, 3, 7}; break;
            case "7": iv = new int[]{0, 4, 7, 10}; break;
            case "M7": iv = new int[]{0, 4, 7, 11}; break;
            case "m7": iv = new int[]{0, 3, 7, 10}; break;
            case "m7b5": iv = new int[]{0, 3, 6, 10}; break;
            case "dim": iv = new int[]{0, 3, 6, 9}; break;
            case "aug": iv = new int[]{0, 4, 8}; break;
            case "sus4": iv = new int[]{0, 5, 7}; break;
            case "sus2": iv = new int[]{0, 2, 7}; break;
            case "7sus4": iv = new int[]{0, 5, 7, 10}; break;
            case "add9": iv = new int[]{0, 4, 7, 14}; break;
            case "madd9": iv = new int[]{0, 3, 7, 14}; break;
            case "6": iv = new int[]{0, 4, 7, 9}; break;
            case "m6": iv = new int[]{0, 3, 7, 9}; break;
            case "M9": iv = new int[]{0, 4, 7, 11, 14}; break;
            case "m9": iv = new int[]{0, 3, 7, 10, 14}; break;
            case "9": iv = new int[]{0, 4, 7, 10, 14}; break;
            case "5": iv = new int[]{0, 7}; break;
            default: throw new IllegalArgumentException("chord " + sym);
        }
        int[] out = new int[iv.length + 1];
        int bass = root;
        if (bassName != null) {
            bass = "C D EF G A B".indexOf(bassName.charAt(0));
            for (int k = 1; k < bassName.length(); k++) bass += bassName.charAt(k) == '#' ? 1 : -1;
        }
        out[0] = ((bass % 12) + 12) % 12;
        for (int k = 0; k < iv.length; k++) out[k + 1] = ((root + iv[k]) % 12 + 12) % 12 + (iv[k] >= 12 ? 12 : 0);
        return out;
    }

    /** Close voicing of a chord's upper notes (no bass) placed nearest to `center` (MIDI). */
    public static int[] voice(String sym, int center) {
        int[] c = chord(sym);
        if (c.length > 5) {   // ninth chords: the bass has the root, the voicing leaves it out
            int[] d = new int[c.length - 1];
            d[0] = c[0];
            System.arraycopy(c, 2, d, 1, c.length - 2);
            c = d;
        }
        int k = c.length - 1;
        int[] best = null;
        int bestCost = Integer.MAX_VALUE;
        for (int inv = 0; inv < k; inv++) {
            for (int base = center - 14; base <= center + 2; base++) {
                int[] v = new int[k];
                int prev = base - 1;
                boolean ok = true;
                for (int j = 0; j < k; j++) {
                    int pc = c[1 + (inv + j) % k] % 12;
                    int n = prev + 1;
                    while (((n % 12) + 12) % 12 != pc) n++;
                    v[j] = n; prev = n;
                }
                if (v[0] != base) continue;
                int mid = (v[0] + v[k - 1]) / 2;
                int cost = Math.abs(mid - center) * 2 + (v[k - 1] - v[0]);
                for (int j = 1; j < k; j++) if (v[j] - v[j - 1] == 1) cost += 100;   // no semitone clusters
                if (ok && cost < bestCost) { bestCost = cost; best = v; }
            }
        }
        return best;
    }

    /** Bass pitch of a chord in the octave starting at `low`. */
    public static int bassOf(String sym, int low) {
        int pc = chord(sym)[0];
        int n = low;
        while (((n % 12) + 12) % 12 != pc) n++;
        return n;
    }

    /**
     * Melody notation: space separated "pitch/beats" tokens, e.g. "E5/.5 F#5/.5 r/1 A4+C#5/2". "r" is a rest, "+" makes
     * a chord, a missing "/beats" repeats the previous length, "_" before a pitch accents it, "~" after the length
     * ties it to the next token. Returns the beat after the last note.
     */
    public float mel(int inst, float beat, String notes, float vel, float pan, float revSend, float dlySend, int transpose) {
        float lenB = 1f;
        String[] tok = notes.trim().split("\\s+");
        float tieStart = -1; String tiePitch = null; float tieLen = 0;
        for (String t : tok) {
            if (t.isEmpty()) continue;
            float v = vel;
            if (t.charAt(0) == '_') { v = Math.min(1.2f, vel * 1.25f); t = t.substring(1); }
            boolean tie = t.endsWith("~");
            if (tie) t = t.substring(0, t.length() - 1);
            int sl = t.indexOf('/');
            String p = sl >= 0 ? t.substring(0, sl) : t;
            if (sl >= 0) lenB = Float.parseFloat(t.substring(sl + 1));
            if (tiePitch != null && p.equals(tiePitch)) {
                tieLen += lenB;
                if (!tie) { playChord(inst, tieStart, tieLen, tiePitch, v, pan, revSend, dlySend, transpose); tiePitch = null; }
            } else if (tie && !p.equals("r")) {
                tieStart = beat; tiePitch = p; tieLen = lenB;
            } else if (!p.equals("r")) {
                playChord(inst, beat, lenB, p, v, pan, revSend, dlySend, transpose);
            }
            beat += lenB;
        }
        return beat;
    }

    private void playChord(int inst, float beat, float len, String p, float v, float pan, float rv, float dl, int tr) {
        String[] ps = p.split("\\+");
        for (int k = 0; k < ps.length; k++) {
            float lg = inst == FLUTE || inst == SHAKU || inst == LEAD || inst == STRINGS || inst == CHOIR || inst == BRASS ? 0.97f : 0.92f;
            int old = role;
            if (role == FREE) role = MELODY;
            note(inst, beat + k * 0.012f * (ps.length > 2 ? 1 : 0), len * lg, pitch(ps[k]) + tr, v, pan, rv, dl);
            role = old;
        }
    }

    /**
     * Drum grid: one char per step ('x' accent, 'o' normal, '.' ghost, '-' rest); `step` beats per char.
     */
    public void grid(int inst, float beat, String g, float step, float vel, float pan, float rv, float midi) {
        for (int i = 0; i < g.length(); i++) {
            char c = g.charAt(i);
            float v = c == 'x' ? vel : c == 'o' ? vel * 0.72f : c == '.' ? vel * 0.38f : 0f;
            if (v > 0) note(inst, beat + i * step, step, midi, v, pan, rv);
        }
    }
}
