package com.pongo.core;

import java.util.Random;

/**
 * Synthesized sounds for the Crystal Cavern and the tunnel transition (docs/PONGO_DESIGN.md §7). Pure Java, no
 * Android: every sound is built once as 16-bit mono PCM at RATE and handed to whatever mixer plays it.
 * Loops (LOOP[id]) are made seamless by folding their echo tails back onto the start.
 *
 * When each one plays (see Zones for the transition events):
 *   AMBIENCE        loop, from Zones.EV_MOUTH while in the cave: low rumble, air, distant drips, timber creaks
 *   TUNNEL_WHOOSH   Zones.EV_PORTAL: the air pressure change entering the tunnel
 *   STING           Zones.EV_PORTAL with the title card: crystal arpeggio
 *   LAMP_ON         Zones.EV_PORTAL (+0.4 s): Hotaru Lamp click and warm hum
 *   CART_BOARD      Zones.EV_BOARD: Pongo lands in the ore cart
 *   CART_RUMBLE     loop while riding, pitch/volume with speed; CART_CLACK every rail joint (every 6 m)
 *   CART_TILT       tilt input: cart leans on its springs, flange squeal
 *   CART_DUCK       crouch input: cloth swish and a creak
 *   DRIP            ambient, on drip particles near the camera
 *   BAT_SQUEAK      ambient bats and ob_bat_swarm on approach; BAT_FLUTTER loop while a swarm is near;
 *   BAT_SWARM       the swarm passing over a crouched rider
 *   CRYSTAL_CHIME   ambient near big clusters, and as the pickup sound for crystal coins
 *   CRYSTAL_SHATTER grazing a crystal (ob_crystal_rock, crystal clusters)
 *   ROCKFALL        ob_rockpile ahead: rubble trickle and a thud, and the crash when you hit it
 *   LOG_THUD        hitting ob_timber_beam / ob_fallen_log
 *   ORE_TRAIN       ob_ore_train approaching: bell and rumble
 */
public final class CaveSounds {
    public static final int RATE = 22050;

    public static final int AMBIENCE = 0, TUNNEL_WHOOSH = 1, STING = 2, LAMP_ON = 3, CART_BOARD = 4, CART_RUMBLE = 5,
            CART_CLACK = 6, CART_TILT = 7, CART_DUCK = 8, DRIP = 9, BAT_SQUEAK = 10, BAT_FLUTTER = 11, BAT_SWARM = 12,
            CRYSTAL_CHIME = 13, CRYSTAL_SHATTER = 14, ROCKFALL = 15, LOG_THUD = 16, ORE_TRAIN = 17, COUNT = 18;
    public static final String[] NAME = {"cave_ambience", "tunnel_whoosh", "sting_cavern", "lamp_on", "cart_board",
            "cart_rumble", "cart_clack", "cart_tilt", "cart_duck", "drip", "bat_squeak", "bat_flutter", "bat_swarm",
            "crystal_chime", "crystal_shatter", "rockfall", "log_thud", "ore_train"};
    public static final boolean[] LOOP = new boolean[COUNT];

    static {
        LOOP[AMBIENCE] = LOOP[CART_RUMBLE] = LOOP[BAT_FLUTTER] = true;
    }

    /** Builds every sound (about 1 s of CPU on a phone; do it at load). */
    public static short[][] buildAll() {
        short[][] s = new short[COUNT][];
        for (int i = 0; i < COUNT; i++) s[i] = build(i);
        return s;
    }

    public static short[] build(int id) {
        Random r = new Random(1000 + id);
        switch (id) {
            case AMBIENCE: return pcm(ambience(r), 0.7f);
            case TUNNEL_WHOOSH: return pcm(whoosh(r), 0.9f);
            case STING: return pcm(sting(), 0.8f);
            case LAMP_ON: return pcm(lampOn(r), 0.7f);
            case CART_BOARD: return pcm(cartBoard(r), 0.9f);
            case CART_RUMBLE: return pcm(cartRumble(r), 0.75f);
            case CART_CLACK: return pcm(clack(r, buf(0.35f), 0f, 1f), 0.8f);
            case CART_TILT: return pcm(cartTilt(r), 0.7f);
            case CART_DUCK: return pcm(cartDuck(r), 0.7f);
            case DRIP: return pcm(cave(drip(buf(1.2f), 0f, 1f, 1900f), 0.35f), 0.7f);
            case BAT_SQUEAK: return pcm(batSqueak(r, buf(0.5f), 0f, 1f), 0.6f);
            case BAT_FLUTTER: return pcm(batFlutter(r, 1f), 0.6f);
            case BAT_SWARM: return pcm(batSwarm(r), 0.85f);
            case CRYSTAL_CHIME: return pcm(cave(chime(buf(2.2f), 0f, 1320f, 1f, 1.1f), 0.3f), 0.7f);
            case CRYSTAL_SHATTER: return pcm(shatter(r), 0.85f);
            case ROCKFALL: return pcm(rockfall(r), 0.9f);
            case LOG_THUD: return pcm(logThud(r), 0.95f);
            case ORE_TRAIN: return pcm(oreTrain(r), 0.85f);
            default: throw new IllegalArgumentException("sound " + id);
        }
    }

    // ------------------------------------------------------------------ sounds

    static float[] ambience(Random r) {
        float len = 8f;
        float[] b = buf(len + 1.5f);
        // rumble: brown noise through two low-passes, slowly breathing
        float lp = 0, lp2 = 0, br = 0;
        for (int i = 0; i < b.length; i++) {
            float t = i / (float) RATE;
            br = br * 0.995f + (r.nextFloat() * 2 - 1) * 0.05f;
            lp += (br - lp) * 0.02f;
            lp2 += (lp - lp2) * 0.02f;
            float breathe = 0.75f + 0.25f * (float) Math.sin(2 * Math.PI * t / len * 2);
            b[i] += lp2 * 3.2f * breathe;
        }
        // air: faint band of hiss
        float h1 = 0, h2 = 0;
        for (int i = 0; i < b.length; i++) {
            float n = r.nextFloat() * 2 - 1;
            h1 += (n - h1) * 0.12f;
            h2 += (h1 - h2) * 0.12f;
            b[i] += (h1 - h2) * 0.05f;
        }
        // distant drips (different pitches) and one timber creak
        float[] at = {0.6f, 1.9f, 2.4f, 4.1f, 5.6f, 6.3f, 7.4f};
        for (float t : at) drip(b, t, 0.25f + r.nextFloat() * 0.3f, 1300f + r.nextFloat() * 1300f);
        creak(r, b, 3.2f, 0.7f, 0.12f);
        b = cave(b, 0.45f);
        return foldLoop(b, len);
    }

    static float[] whoosh(Random r) {
        float[] b = buf(1.8f);
        // band-passed noise sweeping up as the portal rushes past, then muffled and boomy inside
        float lo = 0, lo2 = 0;
        for (int i = 0; i < b.length; i++) {
            float t = i / (float) RATE;
            float k = t < 0.45f ? 0.04f + 0.3f * (t / 0.45f) : 0.34f * (float) Math.exp(-(t - 0.45f) * 5f) + 0.02f;
            float n = r.nextFloat() * 2 - 1;
            lo += (n - lo) * k;
            lo2 += (lo - lo2) * k;
            float env = t < 0.45f ? (t / 0.45f) * (t / 0.45f) : (float) Math.exp(-(t - 0.45f) * 2.2f);
            b[i] += (lo - lo2 * 0.6f) * env * 1.4f;
        }
        tone(b, 0.42f, 0.9f, 70f, 42f, 0.5f, 0, 4f);          // pressure thump
        return cave(b, 0.3f);
    }

    static float[] sting() {
        // crystal arpeggio: A minor add9 rising, each note a glassy bell, last chord rings
        float[] b = buf(3.2f);
        float[] f = {440f, 523.25f, 659.25f, 987.77f, 880f};
        for (int k = 0; k < f.length; k++) chime(b, k * 0.11f, f[k], 0.55f, 1.3f);
        chime(b, 0.62f, 1318.5f, 0.4f, 1.8f);
        tone(b, 0.0f, 2.6f, 110f, 110f, 0.18f, 0, 1.4f);       // low A pad underneath
        return cave(b, 0.4f);
    }

    static float[] lampOn(Random r) {
        float[] b = buf(1.0f);
        noise(r, b, 0f, 0.02f, 0.8f, 200f, 0.6f, 0.6f);         // switch click
        tone(b, 0.0f, 0.012f, 2400f, 1800f, 0.4f, 1, 80f);
        // warm hum swelling in (mains-like 100/200 Hz with a filament shimmer)
        for (int i = (int) (0.05f * RATE); i < b.length; i++) {
            float t = i / (float) RATE - 0.05f;
            float env = Math.min(1f, t * 4f) * (float) Math.exp(-t * 1.6f);
            b[i] += env * (0.12f * (float) Math.sin(2 * Math.PI * 100 * t) + 0.05f * (float) Math.sin(2 * Math.PI * 200 * t)
                    + 0.02f * (float) Math.sin(2 * Math.PI * 1650 * t) * (float) Math.sin(2 * Math.PI * 7 * t));
        }
        return b;
    }

    static float[] cartBoard(Random r) {
        float[] b = buf(1.2f);
        tone(b, 0f, 0.35f, 90f, 55f, 0.8f, 0, 10f);             // landing thud in the cart
        noise(r, b, 0f, 0.15f, 0.5f, 18f, 0.08f, 0.04f);         // wood knock
        clack(r, b, 0.05f, 0.7f);                              // iron rattle
        creak(r, b, 0.18f, 0.5f, 0.35f);                        // springs settle
        return cave(b, 0.25f);
    }

    static float[] cartRumble(Random r) {
        float len = 2f;
        float[] b = buf(len + 1f);
        float lp = 0, lp2 = 0;
        for (int i = 0; i < b.length; i++) {
            float t = i / (float) RATE;
            float n = r.nextFloat() * 2 - 1;
            lp += (n - lp) * 0.035f;
            lp2 += (lp - lp2) * 0.035f;
            // wheels: low roll with a wobble per wheel turn (0.4 m wheel at ~14 m/s)
            float wob = 0.8f + 0.2f * (float) Math.sin(2 * Math.PI * 5.5 * t);
            b[i] += lp2 * 2.6f * wob + 0.08f * (float) Math.sin(2 * Math.PI * 48 * t) * wob;
        }
        // two wheel sets crossing a joint every half second
        for (float t = 0.1f; t < len; t += 0.5f) {
            clack(r, b, t, 0.45f);
            clack(r, b, t + 0.09f, 0.35f);
        }
        // faint flange singing
        tone(b, 0f, len + 1f, 1730f, 1760f, 0.012f, 0, 0f);
        return foldLoop(cave(b, 0.2f), len);
    }

    static float[] clack(Random r, float[] b, float at, float amp) {
        noise(r, b, at, 0.04f, amp, 60f, 0.5f, 0.25f);
        tone(b, at, 0.12f, 420f, 380f, amp * 0.35f, 2, 30f);
        tone(b, at, 0.2f, 1210f, 1190f, amp * 0.12f, 0, 22f);   // metallic ring
        return b;
    }

    static float[] cartTilt(Random r) {
        float[] b = buf(0.8f);
        creak(r, b, 0f, 0.45f, 0.55f);
        tone(b, 0.05f, 0.45f, 2100f, 2600f, 0.06f, 0, 5f);      // flange squeal
        noise(r, b, 0.0f, 0.3f, 0.12f, 6f, 0.3f, 0.2f);
        return cave(b, 0.2f);
    }

    static float[] cartDuck(Random r) {
        float[] b = buf(0.7f);
        // cloth swish down
        float lo = 0, lo2 = 0;
        for (int i = 0; i < (int) (0.3f * RATE); i++) {
            float t = i / (float) RATE;
            float n = r.nextFloat() * 2 - 1;
            float k = 0.35f - t;
            lo += (n - lo) * k;
            lo2 += (lo - lo2) * k;
            b[i] += (lo - lo2) * (float) Math.sin(Math.PI * t / 0.3f) * 0.8f;
        }
        creak(r, b, 0.2f, 0.3f, 0.3f);
        tone(b, 0.22f, 0.2f, 120f, 80f, 0.3f, 0, 18f);
        return b;
    }

    static float[] drip(float[] b, float at, float amp, float f0) {
        // water drop: a fast upward-then-down pitch "plip" with a short resonant tail
        int s = (int) (at * RATE);
        for (int i = 0; i < (int) (0.25f * RATE) && s + i < b.length; i++) {
            float t = i / (float) RATE;
            float f = f0 * (1f + 0.6f * (float) Math.exp(-t * 90f)) * (1f - 0.25f * Math.min(1f, t * 12f));
            float env = (float) Math.exp(-t * 26f) * Math.min(1f, t * 2000f);
            b[s + i] += amp * env * (float) Math.sin(2 * Math.PI * f * t);
        }
        return b;
    }

    static float[] batSqueak(Random r, float[] b, float at, float amp) {
        for (int k = 0; k < 3; k++) {
            float t0 = at + k * 0.075f + r.nextFloat() * 0.02f;
            float f0 = 4200f + r.nextFloat() * 1600f;
            tone(b, t0, 0.045f, f0, f0 * 0.62f, amp * (1f - k * 0.2f), 0, 35f);
            tone(b, t0, 0.045f, f0 * 1.5f, f0 * 0.95f, amp * 0.25f, 0, 40f);
        }
        return b;
    }

    static float[] batFlutter(Random r, float len) {
        float[] b = buf(len + 0.3f);
        // soft leathery wing beats: band-limited noise gated at ~13 Hz with jitter
        float lo = 0, lo2 = 0;
        for (int i = 0; i < b.length; i++) {
            float t = i / (float) RATE;
            float n = r.nextFloat() * 2 - 1;
            lo += (n - lo) * 0.25f;
            lo2 += (lo - lo2) * 0.25f;
            float ph = (float) ((t * 13.0 + 0.15 * Math.sin(2 * Math.PI * 1.7 * t)) % 1.0);
            float gate = (float) Math.exp(-ph * 9f);
            b[i] += (lo - lo2) * gate * 0.9f;
        }
        return foldLoop(b, len);
    }

    static float[] batSwarm(Random r) {
        float[] b = buf(2.0f);
        float[] fl = batFlutter(r, 2.0f);
        for (int i = 0; i < b.length && i < fl.length; i++) {
            float t = i / (float) RATE;
            float env = (float) Math.exp(-((t - 0.8f) * (t - 0.8f)) / 0.12f);   // swells as it passes overhead
            b[i] += fl[i] * env * 1.4f;
        }
        for (int k = 0; k < 9; k++) batSqueak(r, b, 0.2f + k * 0.13f + r.nextFloat() * 0.05f, 0.35f + 0.3f * r.nextFloat());
        return cave(b, 0.25f);
    }

    static float[] chime(float[] b, float at, float f, float amp, float decay) {
        // glass/quartz bell: inharmonic partials, higher ones die faster
        float[] ratio = {1f, 2.76f, 5.40f, 8.93f};
        float[] gain = {1f, 0.45f, 0.25f, 0.12f};
        for (int p = 0; p < ratio.length; p++) {
            float ff = f * ratio[p];
            if (ff > RATE * 0.45f) continue;
            tone(b, at, Math.min(4f, decay * 4f / (1f + p)), ff, ff, amp * gain[p], 0, 1f / decay * (1f + p));
        }
        return b;
    }

    static float[] shatter(Random r) {
        float[] b = buf(1.6f);
        noise(r, b, 0f, 0.08f, 0.9f, 25f, 0.9f, 0.7f);          // crack
        for (int k = 0; k < 10; k++)
            chime(b, 0.01f + k * 0.035f + r.nextFloat() * 0.03f, 1500f + r.nextFloat() * 2600f, 0.22f, 0.25f + 0.2f * r.nextFloat());
        return cave(b, 0.3f);
    }

    static float[] rockfall(Random r) {
        float[] b = buf(2.2f);
        for (int k = 0; k < 26; k++) {                          // pebbles trickling, getting bigger
            float t = 0.05f + k * 0.04f + r.nextFloat() * 0.05f;
            float a = 0.15f + 0.35f * k / 26f;
            noise(r, b, t, 0.03f, a, 70f, 0.4f + 0.3f * r.nextFloat(), 0.2f);
            tone(b, t, 0.05f, 300f + r.nextFloat() * 500f, 200f, a * 0.3f, 2, 50f);
        }
        tone(b, 1.05f, 0.9f, 75f, 38f, 0.9f, 0, 4f);            // the big one lands
        noise(r, b, 1.05f, 0.6f, 0.6f, 5f, 0.06f, 0.03f);
        return cave(b, 0.45f);
    }

    static float[] logThud(Random r) {
        float[] b = buf(1.4f);
        tone(b, 0f, 0.5f, 140f, 70f, 1f, 0, 9f);                // hollow wooden clonk
        tone(b, 0f, 0.3f, 330f, 260f, 0.4f, 2, 14f);
        noise(r, b, 0f, 0.12f, 0.7f, 20f, 0.25f, 0.1f);
        creak(r, b, 0.15f, 0.6f, 0.3f);
        return cave(b, 0.4f);
    }

    static float[] oreTrain(Random r) {
        float[] b = buf(3.0f);
        // mine loco bell (ding-ding) over an approaching rumble
        for (int k = 0; k < 2; k++) chime(b, 0.1f + k * 0.42f, 988f, 0.5f, 0.9f);
        float lp = 0, lp2 = 0;
        for (int i = 0; i < b.length; i++) {
            float t = i / (float) RATE;
            float n = r.nextFloat() * 2 - 1;
            lp += (n - lp) * 0.03f;
            lp2 += (lp - lp2) * 0.03f;
            float env = Math.min(1f, t / 2.2f);
            b[i] += lp2 * 3f * env * env;
        }
        for (float t = 0.6f; t < 3f; t += 0.32f - t * 0.04f) clack(r, b, t, 0.25f * Math.min(1f, t / 2f));
        return cave(b, 0.35f);
    }

    static void creak(Random r, float[] b, float at, float dur, float amp) {
        // wood under strain: a slowly gliding pulse train (stick-slip) through a resonance
        int s = (int) (at * RATE);
        float ph = 0, res = 0, vel = 0;
        for (int i = 0; i < (int) (dur * RATE) && s + i < b.length; i++) {
            float t = i / (float) RATE;
            float f = 55f + 30f * (float) Math.sin(Math.PI * t / dur) + 8f * r.nextFloat();
            ph += f / RATE;
            float pulse = 0f;
            if (ph >= 1f) { ph -= 1f; pulse = 1f; }
            // two-pole resonator at ~900 Hz
            float w = (float) (2 * Math.PI * 900 / RATE);
            vel += (pulse - res * w * w - vel * 0.08f);
            res += vel * 0.02f;
            float env = (float) Math.sin(Math.PI * t / dur);
            b[s + i] += res * env * amp * 6f;
        }
    }

    // ------------------------------------------------------------------ dsp helpers

    static float[] buf(float sec) { return new float[(int) (sec * RATE)]; }

    /** wave: 0 sine, 1 square, 2 triangle; decay: exp rate per second. */
    static void tone(float[] b, float at, float dur, float f0, float f1, float amp, int wave, float decay) {
        int s = (int) (at * RATE), n = (int) (dur * RATE);
        double ph = 0;
        for (int i = 0; i < n && s + i < b.length; i++) {
            float t = i / (float) RATE, u = i / (float) n;
            double f = f0 + (f1 - f0) * u;
            ph += f / RATE;
            float x = wave == 0 ? (float) Math.sin(2 * Math.PI * ph) : wave == 1 ? (ph % 1.0 < 0.5 ? 1f : -1f)
                    : (float) (4 * Math.abs((ph % 1.0) - 0.5) - 1);
            float env = (float) Math.exp(-t * decay) * Math.min(1f, i / 40f) * Math.min(1f, (n - i) / 60f);
            b[s + i] += x * amp * env;
        }
    }

    /** Noise burst through a one-pole low-pass (coefficient lp0 -> lp1 across the burst). */
    static void noise(Random r, float[] b, float at, float dur, float amp, float decay, float lp0, float lp1) {
        int s = (int) (at * RATE), n = (int) (dur * RATE);
        float y = 0;
        for (int i = 0; i < n && s + i < b.length; i++) {
            float u = i / (float) n;
            y += ((r.nextFloat() * 2 - 1) - y) * (lp0 + (lp1 - lp0) * u);
            float env = (float) Math.exp(-i / (float) RATE * decay) * Math.min(1f, (n - i) / 30f);
            b[s + i] += y * amp * env;
        }
    }

    /** Cave acoustics: a few early reflections plus a damped feedback tail (wet = mix of the tail). */
    static float[] cave(float[] in, float wet) {
        float[] out = in.clone();
        int[] taps = {(int) (0.047f * RATE), (int) (0.083f * RATE), (int) (0.131f * RATE)};
        float[] tg = {0.35f, 0.25f, 0.18f};
        for (int k = 0; k < taps.length; k++)
            for (int i = taps[k]; i < out.length; i++) out[i] += in[i - taps[k]] * tg[k] * wet * 2f;
        int[] d = {(int) (0.173f * RATE), (int) (0.229f * RATE), (int) (0.311f * RATE)};
        float[][] line = {new float[d[0]], new float[d[1]], new float[d[2]]};
        int[] p = new int[3];
        float[] lp = new float[3];
        for (int i = 0; i < out.length; i++) {
            float acc = 0;
            for (int k = 0; k < 3; k++) {
                float y = line[k][p[k]];
                lp[k] += (y - lp[k]) * 0.45f;                    // darker every bounce
                line[k][p[k]] = in[i] + lp[k] * 0.62f;
                p[k] = (p[k] + 1) % d[k];
                acc += y;
            }
            out[i] += acc * wet * 0.33f;
        }
        return out;
    }

    /** Folds everything after len seconds back onto the start so the loop has no seam. */
    static float[] foldLoop(float[] b, float len) {
        int n = (int) (len * RATE);
        float[] o = new float[n];
        for (int i = 0; i < b.length; i++) o[i % n] += b[i];
        return o;
    }

    static short[] pcm(float[] f, float vol) {
        float peak = 1e-6f;
        for (float v : f) peak = Math.max(peak, Math.abs(v));
        float g = vol / peak * 32000f;
        short[] s = new short[f.length];
        for (int i = 0; i < f.length; i++) s[i] = (short) Math.max(-32767, Math.min(32767, f[i] * g));
        return s;
    }
}
