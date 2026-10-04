package com.endlessrush.core;

import java.util.Random;

/**
 * Sound effects for the vehicle rides, synthesised in code like the rest of the game's audio.
 * Every ride event has its own sound (ids from BASE up, so they never collide with Game.SND_*), and four looping
 * ambient beds follow the ride state (Ride.loopVol / loopPitch): cart rumble, river rush, sky wind, canopy flutter.
 * Event sounds are fired by Ride at the moment the thing happens (the paddle's catch, a rail joint, the croc's jaws
 * closing, the canopy filling), so they stay in sync with the animation.
 */
public final class RideSfx {
    public static final int BASE = 64;
    public static final int STOW = BASE, BOARD_BACK = BASE + 1, BOARD_CART = BASE + 2, CART_LAND = BASE + 3,
            CART_LAND_SOFT = BASE + 4, CART_BUMP = BASE + 5, TRACK_SWITCH = BASE + 6, RAIL_CLACK = BASE + 7,
            CROUCH = BASE + 8, DUCK_WHOOSH = BASE + 9, BATS = BASE + 10, ROCK_RUMBLE = BASE + 11, ROCKFALL = BASE + 12,
            ORE_BELL = BASE + 13, FORK_BELL = BASE + 14, CART_CRASH = BASE + 15, BUFFER_CRASH = BASE + 16,
            BOAT_LAND = BASE + 17, PADDLE_R = BASE + 18, PADDLE_L = BASE + 19, RUDDER = BASE + 20, BOAT_BUMP = BASE + 21,
            CROC_SURFACE = BASE + 22, CROC_SNAP = BASE + 23, LOG_KNOCK = BASE + 24, WHIRL = BASE + 25, BOAT_CRASH = BASE + 26,
            WATERFALL = BASE + 27, CANOPY_OPEN = BASE + 28, CAW = BASE + 29, FLOCK = BASE + 30, STORM_RUMBLE = BASE + 31,
            CHIMES = BASE + 32, GUST = BASE + 33, THERMAL = BASE + 34, GLIDER_CRASH = BASE + 35, TOUCHDOWN = BASE + 36,
            HOP_OFF = BASE + 37;
    public static final int COUNT = 38;
    public static final String[] NAMES = {"stow", "board_back", "board_cart", "cart_land", "cart_land_soft", "cart_bump",
            "track_switch", "rail_clack", "crouch", "duck_whoosh", "bats", "rock_rumble", "rockfall", "ore_bell", "fork_bell",
            "cart_crash", "buffer_crash", "boat_land", "paddle_r", "paddle_l", "rudder", "boat_bump", "croc_surface",
            "croc_snap", "log_knock", "whirl", "boat_crash", "waterfall", "canopy_open", "caw", "flock", "storm_rumble",
            "chimes", "gust", "thermal", "glider_crash", "touchdown", "hop_off"};

    public static final int LOOP_CART = 0, LOOP_RIVER = 1, LOOP_WIND = 2, LOOP_CANOPY = 3, LOOP_COUNT = 4;
    public static final String[] LOOP_NAMES = {"loop_cart", "loop_river", "loop_wind", "loop_canopy"};

    private final int rate;
    private final Random r = new Random(11);

    public RideSfx(int rate) { this.rate = rate; }

    public static boolean isRide(int id) { return id >= BASE && id < BASE + COUNT; }

    // ---------------------------------------------------------------- building blocks

    private float[] buf(float sec) { return new float[(int) (sec * rate)]; }

    public static short[] pcm(float[] f, float vol) {
        short[] s = new short[f.length];
        for (int i = 0; i < f.length; i++) s[i] = (short) Math.max(-32767, Math.min(32767, f[i] * vol * 32767));
        return s;
    }

    /** Sine/square/saw/organ tone with a pitch glide and exponential decay. */
    private void tone(float[] b, float start, float dur, float f0, float f1, float amp, int wave, float decay) {
        int s0 = (int) (start * rate), n = (int) (dur * rate);
        double ph = 0;
        for (int i = 0; i < n && s0 + i < b.length; i++) {
            float t = i / (float) n;
            float f = f0 * (float) Math.pow(f1 / f0, t);
            ph += 2 * Math.PI * f / rate;
            float v;
            switch (wave) {
                case 1: v = Math.sin(ph) > 0 ? 0.6f : -0.6f; break;
                case 2: v = (float) (2 * ((ph / (2 * Math.PI)) % 1.0) - 1) * 0.7f; break;
                case 3: v = (float) (Math.sin(ph) + 0.35 * Math.sin(ph * 2) + 0.2 * Math.sin(ph * 3)); break;
                default: v = (float) Math.sin(ph);
            }
            float env = (float) Math.exp(-t * decay) * Math.min(1, i / (rate * 0.003f));
            b[s0 + i] += v * amp * env;
        }
    }

    /** Band-passed noise (state-variable filter) whose centre glides f0 -> f1; attack a, decay. */
    private void band(float[] b, float start, float dur, float f0, float f1, float q, float amp, float attack, float decay) {
        int s0 = (int) (start * rate), n = (int) (dur * rate);
        float low = 0, bp = 0;
        for (int i = 0; i < n && s0 + i < b.length; i++) {
            float t = i / (float) n;
            float fc = f0 * (float) Math.pow(f1 / f0, t);
            float f = 2f * (float) Math.sin(Math.PI * Math.min(0.45f, fc / rate));
            float in = r.nextFloat() * 2 - 1;
            low += f * bp;
            float high = in - low - bp / q;
            bp += f * high;
            float env = Math.min(1f, t * dur / Math.max(attack, 1e-4f)) * (float) Math.exp(-t * decay);
            b[s0 + i] += bp * amp * env;
        }
    }

    /** FM bell: carrier c, modulator ratio m, index decaying with the note. */
    private void bell(float[] b, float start, float dur, float c, float ratio, float index, float amp, float decay) {
        int s0 = (int) (start * rate), n = (int) (dur * rate);
        for (int i = 0; i < n && s0 + i < b.length; i++) {
            float t = i / (float) n;
            double tt = i / (double) rate;
            float env = (float) Math.exp(-t * decay) * Math.min(1, i / (rate * 0.002f));
            double mod = Math.sin(2 * Math.PI * c * ratio * tt) * index * env;
            b[s0 + i] += (float) Math.sin(2 * Math.PI * c * tt + mod) * amp * env;
        }
    }

    /** A drop of water: a short sine chirp rising fast (the classic "plip"). */
    private void drop(float[] b, float start, float f0, float amp) {
        tone(b, start, 0.05f, f0, f0 * 2.6f, amp, 0, 4);
    }

    /** Splash: broadband burst, a bubbly mid layer and a few droplets. */
    private void splash(float[] b, float start, float size, float amp) {
        band(b, start, 0.12f + 0.3f * size, 2600, 900, 0.7f, amp, 0.004f, 5);
        band(b, start + 0.01f, 0.2f + 0.4f * size, 700, 300, 1.2f, amp * 0.6f, 0.01f, 4);
        for (int k = 0; k < 3 + (int) (size * 5); k++) drop(b, start + 0.04f + r.nextFloat() * (0.12f + 0.3f * size), 500 + r.nextFloat() * 900, amp * 0.18f);
    }

    /** Thump: a low sine drop with a click. */
    private void thump(float[] b, float start, float f0, float amp) {
        tone(b, start, 0.18f, f0, f0 * 0.45f, amp, 0, 6);
        band(b, start, 0.03f, 3000, 1500, 0.8f, amp * 0.4f, 0.001f, 6);
    }

    private void wing(float[] b, float start, float amp) {
        band(b, start, 0.07f, 900, 400, 0.9f, amp, 0.01f, 5);
    }

    // ---------------------------------------------------------------- one-shots

    public short[] make(int id) {
        float[] b;
        switch (id) {
            case STOW:          // the Kaze Board folds onto her back: whir down and a latch click
                b = buf(0.45f); tone(b, 0, 0.35f, 900, 240, 0.25f, 2, 2); tone(b, 0.33f, 0.05f, 2400, 2000, 0.3f, 1, 8);
                return pcm(b, 0.6f);
            case BOARD_BACK:    // board unfolds: latch, whir up
                b = buf(0.5f); tone(b, 0, 0.05f, 2000, 2400, 0.3f, 1, 8); tone(b, 0.05f, 0.4f, 240, 1000, 0.25f, 2, 1.5f);
                return pcm(b, 0.6f);
            case BOARD_CART:    // jump into the cart: whoosh up
                b = buf(0.4f); band(b, 0, 0.4f, 400, 2000, 0.8f, 0.6f, 0.15f, 2); tone(b, 0, 0.25f, 300, 700, 0.2f, 0, 3);
                return pcm(b, 0.6f);
            case CART_LAND:     // she lands in the cart: wooden thud and iron rattle
                b = buf(0.6f); thump(b, 0, 120, 0.8f); band(b, 0, 0.5f, 1800, 900, 6f, 0.5f, 0.002f, 5);
                band(b, 0.02f, 0.4f, 3200, 2600, 10f, 0.25f, 0.002f, 6);
                return pcm(b, 0.7f);
            case CART_LAND_SOFT:
                b = buf(0.25f); thump(b, 0, 150, 0.4f); band(b, 0, 0.2f, 2000, 1400, 8f, 0.2f, 0.002f, 7);
                return pcm(b, 0.6f);
            case CART_BUMP:     // cart shoved against the buffer of an edge track
                b = buf(0.3f); thump(b, 0, 90, 0.7f); band(b, 0, 0.25f, 1400, 800, 4f, 0.3f, 0.002f, 6);
                return pcm(b, 0.7f);
            case TRACK_SWITCH:  // switch points clack, wheels skip onto the next rails, a spray of sparks
                b = buf(0.5f);
                band(b, 0, 0.04f, 3500, 2500, 3f, 0.7f, 0.001f, 4); band(b, 0.09f, 0.04f, 3200, 2400, 3f, 0.6f, 0.001f, 4);
                band(b, 0.02f, 0.4f, 6000, 4500, 2f, 0.25f, 0.005f, 4);
                band(b, 0.26f, 0.05f, 3000, 2200, 3f, 0.6f, 0.001f, 5); thump(b, 0.26f, 140, 0.35f);
                return pcm(b, 0.6f);
            case RAIL_CLACK:    // wheels over a rail joint: two quick clacks (front and back axle)
                b = buf(0.22f); band(b, 0, 0.03f, 2600, 1900, 4f, 0.5f, 0.001f, 6); thump(b, 0, 180, 0.15f);
                band(b, 0.12f, 0.03f, 2500, 1800, 4f, 0.45f, 0.001f, 6); thump(b, 0.12f, 170, 0.13f);
                return pcm(b, 0.45f);
            case CROUCH:        // cloth swish as she ducks into the cart
                b = buf(0.25f); band(b, 0, 0.25f, 1200, 500, 0.7f, 0.6f, 0.03f, 4);
                return pcm(b, 0.5f);
            case DUCK_WHOOSH:   // a beam or log rushing over her head
                b = buf(0.45f); band(b, 0, 0.45f, 300, 1500, 1.2f, 0.8f, 0.2f, 1.5f); band(b, 0.15f, 0.3f, 1500, 400, 1.2f, 0.5f, 0.01f, 3);
                return pcm(b, 0.6f);
            case BATS:          // the swarm takes off: fluttering wings and high squeaks
                b = buf(1.3f);
                for (int k = 0; k < 26; k++) wing(b, k * 0.045f + r.nextFloat() * 0.02f, 0.35f);
                for (int k = 0; k < 9; k++) {
                    float f = 3800 + r.nextFloat() * 2400, st = r.nextFloat() * 1.1f;
                    tone(b, st, 0.07f, f, f * 1.25f, 0.12f, 0, 3);
                }
                return pcm(b, 0.65f);
            case ROCK_RUMBLE:   // the roof groans and dust trickles (warning)
                b = buf(0.7f); band(b, 0, 0.7f, 60, 90, 1.5f, 1.0f, 0.15f, 1.5f); band(b, 0.1f, 0.6f, 3000, 2000, 0.8f, 0.15f, 0.1f, 2);
                return pcm(b, 0.8f);
            case ROCKFALL:      // rocks crash onto the track
                b = buf(0.9f);
                for (int k = 0; k < 7; k++) thump(b, k * 0.07f + r.nextFloat() * 0.05f, 70 + r.nextFloat() * 90, 0.55f);
                band(b, 0, 0.9f, 1500, 300, 0.6f, 0.4f, 0.005f, 3);
                return pcm(b, 0.8f);
            case ORE_BELL:      // the ore train's brass bell, ringing twice in the cavern's echo
                b = buf(1.6f);
                for (int k = 0; k < 2; k++) { bell(b, k * 0.3f, 1.2f, 880, 2.76f, 2.5f, 0.35f, 4); bell(b, k * 0.3f + 0.12f, 1.0f, 880, 2.76f, 2.0f, 0.12f, 5); }
                return pcm(b, 0.6f);
            case FORK_BELL:     // a fork is coming: a two-note signal (high, low) telling her to choose
                b = buf(0.8f); bell(b, 0, 0.5f, 1318, 3.5f, 1.2f, 0.3f, 5); bell(b, 0.2f, 0.6f, 988, 3.5f, 1.2f, 0.3f, 5);
                return pcm(b, 0.55f);
            case CART_CRASH:
                b = buf(1.0f); thump(b, 0, 80, 1.0f); band(b, 0, 0.9f, 2000, 300, 0.7f, 0.9f, 0.002f, 4);
                band(b, 0.03f, 0.8f, 3000, 2500, 8f, 0.4f, 0.002f, 5); for (int k = 0; k < 4; k++) thump(b, 0.15f + k * 0.1f, 140, 0.3f);
                return pcm(b, 0.85f);
            case BUFFER_CRASH:  // the cart hits the buffer stop at the dock: iron bang, then she is airborne
                b = buf(1.0f); thump(b, 0, 70, 1.0f); bell(b, 0, 0.8f, 220, 1.41f, 4f, 0.35f, 4);
                band(b, 0, 0.5f, 2500, 600, 0.8f, 0.6f, 0.002f, 5); band(b, 0.2f, 0.5f, 400, 1800, 0.9f, 0.4f, 0.2f, 2);
                return pcm(b, 0.8f);
            case BOAT_LAND:     // lands kneeling in the canoe: hollow bamboo knock and a splash
                b = buf(0.8f); tone(b, 0, 0.25f, 260, 200, 0.6f, 3, 6); tone(b, 0.01f, 0.2f, 520, 420, 0.25f, 0, 8);
                splash(b, 0.02f, 0.8f, 0.6f);
                return pcm(b, 0.7f);
            case PADDLE_R: case PADDLE_L:   // the blade catches the water: a short "chuck" and drips as it pulls
                b = buf(0.55f); band(b, 0, 0.12f, 1100, 500, 1.4f, 0.8f, 0.004f, 5);
                band(b, 0.03f, 0.25f, 600, 280, 2f, 0.4f, 0.02f, 4);
                for (int k = 0; k < 3; k++) drop(b, 0.18f + k * 0.08f + r.nextFloat() * 0.04f, (id == PADDLE_R ? 700 : 620) + r.nextFloat() * 400, 0.12f);
                return pcm(b, 0.5f);
            case RUDDER:        // paddle held as a rudder: water hissing along the blade
                b = buf(0.6f); band(b, 0, 0.6f, 1800, 1500, 1.0f, 0.4f, 0.1f, 2);
                return pcm(b, 0.4f);
            case BOAT_BUMP:     // the hull scrapes a bank or the island's nose
                b = buf(0.5f); tone(b, 0, 0.2f, 180, 120, 0.6f, 3, 6); band(b, 0, 0.45f, 900, 500, 1.5f, 0.5f, 0.01f, 4);
                return pcm(b, 0.7f);
            case CROC_SURFACE:  // the crocodile surfaces: bubbles and a deep growl
                b = buf(1.1f);
                for (int k = 0; k < 10; k++) drop(b, k * 0.06f + r.nextFloat() * 0.03f, 200 + r.nextFloat() * 300, 0.25f);
                tone(b, 0.25f, 0.8f, 70, 55, 0.6f, 2, 2.5f); band(b, 0.25f, 0.8f, 180, 120, 3f, 0.4f, 0.1f, 2.5f);
                return pcm(b, 0.75f);
            case CROC_SNAP:     // jaws slam shut with a splash
                b = buf(0.6f); thump(b, 0, 200, 0.6f); band(b, 0, 0.03f, 2500, 2000, 2f, 0.9f, 0.0005f, 3);
                splash(b, 0.03f, 0.6f, 0.55f);
                return pcm(b, 0.8f);
            case LOG_KNOCK:     // a drifting log knocking on stones
                b = buf(0.6f); tone(b, 0, 0.15f, 210, 180, 0.6f, 3, 8); tone(b, 0.22f, 0.15f, 190, 170, 0.45f, 3, 8);
                band(b, 0, 0.5f, 600, 400, 1.5f, 0.15f, 0.05f, 3);
                return pcm(b, 0.6f);
            case WHIRL:         // whirlpool: a swirling gurgle
                b = buf(1.2f);
                for (int i = 0; i < b.length; i++) {
                    float t = i / (float) rate;
                    b[i] = (float) Math.sin(2 * Math.PI * (90 + 40 * Math.sin(t * 9)) * t) * 0.15f * (float) Math.sin(Math.PI * t / 1.2f);
                }
                band(b, 0, 1.2f, 500, 300, 2f, 0.4f, 0.3f, 1);
                for (int k = 0; k < 8; k++) drop(b, r.nextFloat() * 1.1f, 250 + r.nextFloat() * 250, 0.15f);
                return pcm(b, 0.6f);
            case BOAT_CRASH:
                b = buf(1.0f); tone(b, 0, 0.4f, 160, 70, 0.8f, 3, 5); band(b, 0, 0.7f, 1200, 300, 1f, 0.6f, 0.002f, 4);
                splash(b, 0.05f, 1.0f, 0.8f);
                return pcm(b, 0.85f);
            case WATERFALL:     // over the lip: the roar swells as the canoe tips
                b = buf(1.6f); band(b, 0, 1.6f, 300, 900, 0.5f, 1.0f, 0.6f, 1.2f); band(b, 0.3f, 1.2f, 2500, 1500, 0.5f, 0.4f, 0.3f, 2);
                return pcm(b, 0.75f);
            case CANOPY_OPEN:   // the glider bursts open: rustle, then a deep "whump" as the cells fill
                b = buf(0.9f); band(b, 0, 0.35f, 1500, 3000, 0.6f, 0.5f, 0.05f, 2); thump(b, 0.32f, 75, 1.0f);
                band(b, 0.32f, 0.5f, 400, 200, 1f, 0.5f, 0.003f, 4);
                return pcm(b, 0.8f);
            case CAW: {         // a crow: two harsh caws
                b = buf(0.8f);
                for (int k = 0; k < 2; k++) {
                    float st = k * 0.32f;
                    tone(b, st, 0.22f, 820, 640, 0.35f, 2, 2); tone(b, st, 0.22f, 1240, 980, 0.18f, 1, 2);
                    band(b, st, 0.22f, 1600, 1200, 1.5f, 0.4f, 0.02f, 2);
                }
                return pcm(b, 0.6f);
            }
            case FLOCK:         // a flock: many wings and overlapping caws
                b = buf(1.6f);
                for (int k = 0; k < 30; k++) wing(b, k * 0.05f + r.nextFloat() * 0.03f, 0.3f);
                for (int k = 0; k < 5; k++) {
                    float st = r.nextFloat() * 1.2f, f = 700 + r.nextFloat() * 300;
                    tone(b, st, 0.2f, f, f * 0.8f, 0.18f, 2, 2);
                }
                return pcm(b, 0.6f);
            case STORM_RUMBLE:  // a small thundercloud: a soft crackle, then a low rolling rumble
                b = buf(2.0f);
                for (int k = 0; k < 4; k++) band(b, k * 0.05f, 0.05f, 2600, 1800, 0.8f, 0.5f, 0.002f, 6);
                band(b, 0.12f, 1.8f, 90, 60, 0.7f, 0.9f, 0.25f, 2);
                band(b, 0.3f, 1.4f, 160, 80, 0.8f, 0.5f, 0.3f, 2);
                return pcm(b, 0.65f);
            case CHIMES:        // wind chimes strung on the cable ring as she nears it
                b = buf(1.8f);
                float[] notes = {1568, 1760, 2093, 2349, 2637};
                for (int k = 0; k < 7; k++) bell(b, k * 0.16f + r.nextFloat() * 0.05f, 1.0f, notes[r.nextInt(notes.length)], 2.0f, 1.0f, 0.18f, 4);
                return pcm(b, 0.6f);
            case GUST:          // a side gust: whoosh with a canopy shudder
                b = buf(1.0f); band(b, 0, 1.0f, 300, 1200, 0.6f, 0.9f, 0.3f, 2);
                for (int k = 0; k < 6; k++) band(b, 0.3f + k * 0.06f, 0.04f, 900, 600, 1f, 0.25f, 0.002f, 6);
                return pcm(b, 0.6f);
            case THERMAL:       // rising air: an airy upward sweep and a soft chime
                b = buf(1.1f); band(b, 0, 1.0f, 300, 2400, 1.2f, 0.6f, 0.4f, 1.5f); bell(b, 0.2f, 0.8f, 1046, 2f, 0.6f, 0.15f, 4);
                bell(b, 0.35f, 0.7f, 1568, 2f, 0.6f, 0.12f, 4);
                return pcm(b, 0.55f);
            case GLIDER_CRASH:  // canopy collapses: fabric rip and tumbling wind
                b = buf(1.1f); band(b, 0, 0.4f, 3500, 1500, 0.5f, 0.8f, 0.002f, 3); band(b, 0.1f, 1.0f, 900, 200, 0.6f, 0.6f, 0.05f, 2);
                thump(b, 0.05f, 110, 0.5f);
                return pcm(b, 0.8f);
            case TOUCHDOWN:     // feet on the train roof: double step on steel, glider lines release
                b = buf(0.7f); thump(b, 0, 130, 0.6f); band(b, 0, 0.3f, 2200, 1800, 6f, 0.3f, 0.001f, 6);
                thump(b, 0.14f, 120, 0.5f); band(b, 0.3f, 0.3f, 1200, 2400, 0.8f, 0.3f, 0.02f, 3);
                return pcm(b, 0.7f);
            case HOP_OFF:
                b = buf(0.4f); band(b, 0, 0.3f, 500, 1500, 0.8f, 0.5f, 0.1f, 2); thump(b, 0.3f, 140, 0.4f);
                return pcm(b, 0.6f);
            default:
                return new short[1];
        }
    }

    // ---------------------------------------------------------------- loops

    /** Seamless loop (the tail is cross-faded into the head). */
    public short[] makeLoop(int loop) {
        float sec = 2.4f;
        float[] b = buf(sec + 0.3f);
        switch (loop) {
            case LOOP_CART:     // iron wheels on rails: low rumble with a squeal now and then
                band(b, 0, sec + 0.3f, 70, 70, 1.2f, 1.2f, 0.001f, 0);
                band(b, 0, sec + 0.3f, 600, 600, 1.5f, 0.2f, 0.001f, 0);
                for (int k = 0; k < 4; k++) tone(b, k * 0.6f + 0.1f, 0.35f, 2900 + k * 60, 3100, 0.025f, 0, 2);
                break;
            case LOOP_RIVER:    // the river: broadband rush, mid gurgle, droplets
                band(b, 0, sec + 0.3f, 900, 900, 0.5f, 0.7f, 0.001f, 0);
                band(b, 0, sec + 0.3f, 300, 300, 1.2f, 0.4f, 0.001f, 0);
                for (int k = 0; k < 14; k++) drop(b, r.nextFloat() * sec, 400 + r.nextFloat() * 900, 0.08f);
                break;
            case LOOP_WIND:     // high-altitude wind
                for (int i = 0; i < b.length; i++) b[i] = 0;
                band(b, 0, sec + 0.3f, 500, 500, 0.4f, 0.9f, 0.001f, 0);
                band(b, 0, sec + 0.3f, 1400, 1400, 1.5f, 0.2f, 0.001f, 0);
                break;
            default:            // canopy flutter: the trailing edge vibrating
                for (int i = 0; i < b.length; i++) {
                    float t = i / (float) rate;
                    b[i] = (r.nextFloat() * 2 - 1) * 0.3f * (0.6f + 0.4f * (float) Math.sin(2 * Math.PI * 14 * t));
                }
                band(b, 0, sec + 0.3f, 250, 250, 1f, 0.5f, 0.001f, 0);
                break;
        }
        int n = (int) (sec * rate), x = b.length - n;
        float[] o = new float[n];
        for (int i = 0; i < n; i++) o[i] = b[i];
        for (int i = 0; i < x; i++) {
            float w = i / (float) x;
            o[i] = b[i] * w + b[n + i] * (1 - w);
        }
        return pcm(o, 0.5f);
    }
}
