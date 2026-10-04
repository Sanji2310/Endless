package com.pongo.core;

/**
 * The game's music (docs/PONGO_DESIGN.md §7), composed in code and rendered by MusicSynth at load. One looping theme
 * for the menu and one per zone, plus one-shot stingers for zone entries and game over. Every theme is rendered at the
 * same loudness so MusicPlayer can crossfade between them.
 *
 *   MENU      "Hanami Platform"  D major, 86 BPM. Piano, music box, flute and strings: a quiet morning on the platform.
 *   SAKURA    "Hanami Express"   E major, 132 BPM. Anime-opening pop: royal road chorus (IV-V-iii-vi), e-piano, synth
 *                                lead doubled by glockenspiel, four-on-the-floor drums, octave synth bass.
 *   CAVERN    "Hotaru Lamp"      D minor, 104 BPM. Celesta and glockenspiel crystals over a choir pad; woodblock
 *                                "da-dum" rail clacks once the ore cart is rolling. Sits under the cave ambience.
 *   RIVER     "Sasabune"         D yonanuki (pentatonic), 96 BPM. Shakuhachi over flowing koto, taiko, shamisen.
 *   SKY       "Kaze no Michi"    F major / Lydian waltz, 168 BPM in 3/4. Harp, flute, soaring strings, choir.
 *   ROOFTOPS  "Rooftop Rush"     B minor, 160 BPM. J-rock finale: overdriven guitars, synth lead hook, driving drums.
 *
 * Stingers: ST_SAKURA .. ST_ROOFTOPS play with each zone's title card and hand over to that zone's theme at
 * handoff(id) seconds; ST_GAMEOVER plays when the run ends.
 */
public final class Soundtrack {
    public static final int MENU = 0, SAKURA = 1, CAVERN = 2, RIVER = 3, SKY = 4, ROOFTOPS = 5,
            ST_SAKURA = 6, ST_CAVERN = 7, ST_RIVER = 8, ST_SKY = 9, ST_ROOFTOPS = 10, ST_GAMEOVER = 11, COUNT = 12;
    public static final String[] NAME = {"menu_hanami_platform", "sakura_hanami_express", "cavern_hotaru_lamp",
            "river_sasabune", "sky_kaze_no_michi", "rooftops_rooftop_rush", "sting_sakura", "sting_cavern",
            "sting_river", "sting_sky", "sting_rooftops", "sting_gameover"};
    public static final String[] TITLE = {"Hanami Platform", "Hanami Express", "Hotaru Lamp", "Sasabune",
            "Kaze no Michi", "Rooftop Rush", "Sakura Line sting", "Crystal Cavern sting", "Bamboo River sting",
            "Sky Glide sting", "Express Rooftops sting", "Game over"};

    public static boolean isLoop(int id) { return id < ST_SAKURA; }

    /** Theme for a Zones zone. */
    public static int themeFor(int zone) {
        switch (zone) {
            case Zones.CAVERN: return CAVERN;
            case Zones.RIVER: return RIVER;
            case Zones.SKY: return SKY;
            case Zones.ROOFTOPS: return ROOFTOPS;
            default: return SAKURA;
        }
    }

    /** Stinger that announces a zone. */
    public static int stingerFor(int zone) { return ST_SAKURA + themeFor(zone) - SAKURA; }

    /** The synth of the last render (tools read its per-instrument energy). */
    public static MusicSynth lastSynth;

    private static final float[] HANDOFF = new float[COUNT];

    /** Seconds into a stinger where the next theme comes in (the end of its musical phrase; the rest is reverb). */
    public static float handoff(int id) { return HANDOFF[id]; }

    /** Renders one piece to interleaved stereo 16-bit PCM at MusicSynth.RATE. Seconds of CPU; call off the UI thread. */
    public static short[] render(int id) {
        MusicSynth s;
        switch (id) {
            case MENU: s = menu(); break;
            case SAKURA: s = sakura(); break;
            case CAVERN: s = cavern(); break;
            case RIVER: s = river(); break;
            case SKY: s = sky(); break;
            case ROOFTOPS: s = rooftops(); break;
            case ST_SAKURA: s = stSakura(); break;
            case ST_CAVERN: s = stCavern(); break;
            case ST_RIVER: s = stRiver(); break;
            case ST_SKY: s = stSky(); break;
            case ST_ROOFTOPS: s = stRooftops(); break;
            default: s = stGameOver(); break;
        }
        HANDOFF[id] = s.handoffBeats > 0 ? s.handoffBeats * 60f / s.bpm : s.loopLen / (float) MusicSynth.RATE;
        lastSynth = s;
        return s.render();
    }

    // ================================================================== arranging helpers

    private static final int P = MusicSynth.PIANO, EP = MusicSynth.EPIANO, GL = MusicSynth.GLOCK,
            MB = MusicSynth.MUSICBOX, HP = MusicSynth.HARP, KO = MusicSynth.KOTO, SH = MusicSynth.SHAMISEN,
            PAD = MusicSynth.PAD, STR = MusicSynth.STRINGS, FL = MusicSynth.FLUTE, SK = MusicSynth.SHAKU,
            LD = MusicSynth.LEAD, SAW = MusicSynth.SUPERSAW, BS = MusicSynth.BASS, SUB = MusicSynth.SUBBASS,
            SB = MusicSynth.SYNBASS, GT = MusicSynth.GUITAR, CH = MusicSynth.CHOIR, CE = MusicSynth.CELESTA,
            KICK = MusicSynth.KICK, SNR = MusicSynth.SNARE, CLAP = MusicSynth.CLAP, HAT = MusicSynth.HAT,
            OHAT = MusicSynth.OHAT, SHK = MusicSynth.SHAKER, RIDE = MusicSynth.RIDE, CRASH = MusicSynth.CRASH,
            TAIKO = MusicSynth.TAIKO, TOM = MusicSynth.TOM, WOOD = MusicSynth.WOOD, RIM = MusicSynth.RIM,
            CHIME = MusicSynth.CHIMES, TRI = MusicSynth.TRIANGLE, SNAP = MusicSynth.SNAP, KAKKO = MusicSynth.KAKKO,
            REV = MusicSynth.REVCYM, SWELL = MusicSynth.SWELL;

    private static String[] bars(String s) { return s.trim().split("\\s+"); }

    /** Chord sounding at `beat` within bar `b` ("G#m7,C#m7" splits the bar evenly). */
    private static String chordAt(String[] prog, int b, float beat, int bpb) {
        String[] c = prog[b].split(",");
        int k = Math.min(c.length - 1, (int) (beat / (bpb / (float) c.length)));
        return c[k];
    }

    /** Held chords, one voicing per chord change. */
    private static void hold(MusicSynth s, int inst, int bar0, String[] prog, int center, float vel, float pan, float rv) {
        s.role = MusicSynth.PADS;
        int bpb = s.beatsPerBar;
        for (int b = 0; b < prog.length; b++) {
            String[] c = prog[b].split(",");
            float len = bpb / (float) c.length;
            for (int k = 0; k < c.length; k++) {
                int[] v = MusicSynth.voice(c[k], center);
                for (int n : v) s.note(inst, (bar0 + b) * bpb + k * len, len, n, vel, pan, rv);
            }
        }
    }

    /**
     * Arpeggio: pattern chars '0'-'9' index the chord voicing extended upward by octaves, 'b' the bass note (octave
     * from `low`), '-' rest; one char per `step` beats, repeated through every bar.
     */
    private static void arp(MusicSynth s, int inst, int bar0, String[] prog, int center, int low, String pat, float step,
                            float vel, float pan, float rv, float dl) {
        s.role = MusicSynth.ACCOMP;
        int bpb = s.beatsPerBar;
        int steps = Math.round(bpb / step);
        for (int b = 0; b < prog.length; b++) {
            for (int i = 0; i < steps; i++) {
                char ch = pat.charAt(i % pat.length());
                if (ch == '-') continue;
                float beat = i * step;
                String c = chordAt(prog, b, beat, bpb);
                int n;
                if (ch == 'b') n = MusicSynth.bassOf(c, low);
                else {
                    int[] v = MusicSynth.voice(c, center);
                    int k = ch - '0';
                    n = v[k % v.length] + 12 * (k / v.length);
                }
                float p = pan == 2f ? (i % 2 == 0 ? -0.35f : 0.35f) : pan;
                s.note(inst, (bar0 + b) * bpb + beat, step * (step >= 1f ? 1.05f : 1.6f), n, vel * (i % 4 == 0 ? 1f : 0.82f), p, rv, dl);
            }
        }
    }

    /**
     * Bass / comping rhythm on a 16th grid (per bar): 'r' root, 'f' fifth, 'o' octave, 'c' the whole chord (voiced at
     * center), '-' rest. Each note lasts until the next event (times `legato`).
     */
    private static void line(MusicSynth s, int inst, int bar0, String[] prog, int low, int center, String pat, float vel,
                             float pan, float rv, float legato) {
        s.role = MusicSynth.ACCOMP;
        int bpb = s.beatsPerBar;
        int steps = bpb * 4;
        for (int b = 0; b < prog.length; b++) {
            for (int i = 0; i < steps; i++) {
                char ch = pat.charAt(i % pat.length());
                if (ch == '-') continue;
                int j = i + 1;
                while (j < steps && pat.charAt(j % pat.length()) == '-') j++;
                float beat = i * 0.25f, len = (j - i) * 0.25f * legato;
                String c = chordAt(prog, b, beat, bpb);
                int parts = prog[b].split(",").length;
                if (parts > 1) {   // never let a note hang over the chord change
                    float seg = bpb / (float) parts, edge = ((int) (beat / seg) + 1) * seg;
                    len = Math.min(len, edge - beat);
                }
                int root = MusicSynth.bassOf(c, low);
                float v = vel * (i % 4 == 0 ? 1f : 0.85f);
                float at = (bar0 + b) * bpb + beat;
                if (ch == 'r') s.note(inst, at, len, root, v, pan, rv);
                else if (ch == 'f') s.note(inst, at, len, root + 7, v, pan, rv);
                else if (ch == 'o') s.note(inst, at, len, root + 12, v, pan, rv);
                else if (ch == 'c') {
                    s.role = MusicSynth.PADS;
                    for (int n : MusicSynth.voice(c, center)) s.note(inst, at, len, n, v, pan, rv);
                    s.role = MusicSynth.ACCOMP;
                }
            }
        }
    }

    /** Drum grid repeated for `n` bars (16ths unless `step` says otherwise). */
    private static void drums(MusicSynth s, int inst, int bar0, int n, String g, float vel, float pan, float rv, float midi) {
        s.role = MusicSynth.FREE;
        int bpb = s.beatsPerBar;
        float step = bpb / (float) g.length();
        for (int b = 0; b < n; b++) s.grid(inst, (bar0 + b) * bpb, g, step, vel, pan, rv, midi);
    }

    private static void mel(MusicSynth s, int inst, int bar0, String notes, float vel, float pan, float rv, float dl, int tr) {
        s.role = MusicSynth.FREE;
        s.mel(inst, bar0 * s.beatsPerBar, notes.replace("|", " "), vel, pan, rv, dl, tr);
    }

    // ================================================================== MENU: "Hanami Platform"

    private static MusicSynth menu() {
        MusicSynth s = new MusicSynth(86, 4, 16, 101);
        s.revSize = 0.86f; s.revWet = 1.0f; s.humanize = 0.009f;
        String[] A = bars("DM7 A/C# Bm7 F#m7 GM7 D/F# Em7 A7sus4,A7");
        String[] B = bars("GM7 A F#m7 Bm7 Em7 A/C# D,G/D D");
        String mA = "F#5/1.5 E5/.5 F#5/1 A5/1 | E5/2 r/.5 C#5/.5 D5/.5 E5/.5 | D5/1.5 C#5/.5 D5/1 F#5/1 | C#5/3 r/1 |"
                + " B4/.5 D5/.5 G5/1.5 F#5/.5 E5/.5 D5/.5 | F#5/1.5 E5/.5 D5/1 A4/1 | G5/1 F#5/.5 E5/.5 D5/1 E5/1 |"
                + " E5/2.5 r/.5 A4/.5 C#5/.5";
        String mB = "D6/1.5 C#6/.5 D6/1 B5/1 | C#6/1.5 B5/.5 A5/2 | A5/1.5 G5/.5 F#5/1 E5/1 | F#5/3 D5/.5 E5/.5 |"
                + " G5/1.5 F#5/.5 E5/1 G5/1 | A5/1.5 B5/.5 C#6/1 E6/1 | D6/2 C#6/.5 B5/.5 A5/1 | F#5/2 D5/2";
        // piano: low bass then a rising broken chord, the classic film-score left hand
        arp(s, P, 0, A, 62, 38, "b0123210", 0.5f, 0.42f, -0.15f, 0.35f, 0f);
        arp(s, P, 8, B, 62, 38, "b0123210", 0.5f, 0.46f, -0.15f, 0.35f, 0f);
        // A: music box melody an octave up, a soft string bed
        mel(s, MB, 0, mA, 0.75f, 0.25f, 0.5f, 0.12f, 12);
        hold(s, STR, 0, A, 57, 0.18f, 0f, 0.5f);
        // B: flute sings it, celesta shadows an octave up, strings fuller, a low cello line
        mel(s, FL, 8, mB, 0.62f, 0.15f, 0.45f, 0.1f, 0);
        mel(s, CE, 8, mB, 0.22f, 0.4f, 0.5f, 0f, 12);
        hold(s, STR, 8, B, 62, 0.26f, -0.1f, 0.5f);
        line(s, STR, 8, B, 38, 0, "r---------------", 0.3f, 0f, 0.4f, 1f);
        drums(s, SHK, 8, 8, "-o-o-o-o", 0.35f, 0.4f, 0.3f, 60);
        drums(s, TRI, 8, 1, "x-------", 0.4f, -0.4f, 0.6f, 100);
        drums(s, TRI, 12, 1, "x-------", 0.35f, -0.4f, 0.6f, 100);
        s.note(CHIME, 0, 3, 90, 0.35f, 0.3f, 0.7f);
        s.note(SWELL, 6 * 4 + 2, 6, 60, 0.25f, 0f, 0.6f);
        return s;
    }

    // ================================================================== SAKURA LINE: "Hanami Express"

    private static MusicSynth sakura() {
        MusicSynth s = new MusicSynth(132, 4, 28, 202);
        s.revSize = 0.78f; s.dlyBeats = 0.75f; s.dlyFb = 0.3f;
        String[] intro = bars("AM7 B G#m7 C#m7");
        String[] verse = bars("EM7 G#m7 AM7 B EM7 G#m7,C#m7 F#m7 B7sus4,B7");
        String[] chorus = bars("AM7 B G#m7 C#m7 F#m7 G#m7 A B AM7 B G#m7 C#m7 F#m7 B7 E E");
        int I = 0, V = 4, C = 12;
        String mV = "r/.5 B4/.5 E5/.5 F#5/.5 G#5/1 F#5/.5 E5/.5 | D#5/1.5 E5/.5 F#5/1 B4/1 |"
                + " r/.5 C#5/.5 E5/.5 F#5/.5 G#5/1 A5/.5 G#5/.5 | F#5/3 r/1 |"
                + " r/.5 B4/.5 E5/.5 F#5/.5 G#5/1 B5/.5 A5/.5 | G#5/1.5 F#5/.5 E5/1 G#5/1 |"
                + " A5/1.5 G#5/.5 F#5/1 E5/1 | F#5/1 E5/1 D#5/2";
        String c1 = "E5/.5 F#5/.5 G#5/.5 _C#6/1 B5/.5 G#5/1 | F#5/.5 G#5/.5 A5/.5 _B5/1 A5/.5 F#5/1 |"
                + " F#5/.5 G#5/.5 B5/.5 _D#6/1 C#6/.5 B5/1 | C#6/1.5 B5/.5 G#5/1 E5/1 |";
        String mC = c1
                + " A5/.5 G#5/.5 A5/.5 _C#6/1 B5/.5 A5/1 | G#5/.5 F#5/.5 G#5/.5 _B5/1 F#5/.5 G#5/1 |"
                + " E5/.5 F#5/.5 A5/.5 _C#6/1 E6/1 C#6/.5 | _D#6/2 B5/.5 C#6/.5 D#6/1 |"
                + c1
                + " A5/.5 G#5/.5 A5/.5 _C#6/1 B5/.5 A5/1 | G#5/.5 A5/.5 B5/.5 _D#6/1 C#6/.5 B5/1 |"
                + " B5/.5 C#6/.5 _E6/3 | r/4";
        // --- intro: glockenspiel hook over e-piano, drums build
        arp(s, GL, I, intro, 76, 40, "0123212301232123", 0.25f, 0.32f, 2f, 0.35f, 0.25f);
        line(s, EP, I, intro, 40, 64, "c-----c-----c---", 0.42f, -0.2f, 0.3f, 0.95f);
        line(s, SB, I + 2, bars("G#m7 C#m7"), 28, 0, "r-o-r-o-r-o-r-o-", 0.6f, 0f, 0f, 0.6f);
        drums(s, HAT, I, 4, "x-o-x-o-x-o-x-o-", 0.5f, 0.25f, 0.1f, 0);
        drums(s, KICK, I + 2, 1, "x---x---x---x---", 0.9f, 0f, 0f, 0);
        drums(s, KICK, I + 3, 1, "x---x---x-------", 0.9f, 0f, 0f, 0);
        drums(s, SNR, I + 3, 1, "--------..oooxxx", 0.7f, 0f, 0.2f, 0);
        s.note(SWELL, (I + 2) * 4, 8, 60, 0.35f, 0f, 0.3f);
        // --- verse
        mel(s, LD, V, mV, 0.5f, 0f, 0.3f, 0.18f, 0);
        line(s, EP, V, verse, 40, 64, "c-----c---c-----", 0.45f, -0.2f, 0.3f, 0.9f);
        hold(s, STR, V, verse, 60, 0.16f, 0.2f, 0.5f);
        line(s, BS, V, verse, 28, 0, "r-----r-r-----o-", 0.75f, 0f, 0f, 0.8f);
        drums(s, KICK, V, 7, "x-----x-x-------", 0.95f, 0f, 0f, 0);
        drums(s, SNAP, V, 7, "----x-------x---", 0.55f, 0.1f, 0.35f, 0);
        drums(s, SHK, V, 8, "xo.oxo.oxo.oxo.o", 0.45f, -0.3f, 0.15f, 0);
        drums(s, KICK, V + 7, 1, "x-----x---------", 0.95f, 0f, 0f, 0);
        drums(s, SNR, V + 7, 1, "----x---x-x-xxxx", 0.7f, 0f, 0.2f, 0);
        // --- chorus
        mel(s, LD, C, mC, 0.72f, 0f, 0.3f, 0.22f, 0);
        mel(s, GL, C, mC, 0.3f, 0.3f, 0.35f, 0.1f, 12);
        hold(s, SAW, C, chorus, 64, 0.32f, 0f, 0.35f);
        line(s, EP, C, chorus, 40, 62, "--c--c----c--c--", 0.42f, -0.3f, 0.25f, 0.8f);
        line(s, SB, C, chorus, 28, 0, "r-o-r-o-r-o-r-o-", 0.7f, 0f, 0f, 0.55f);
        drums(s, KICK, C, 15, "x---x---x---x---", 1f, 0f, 0f, 0);
        drums(s, CLAP, C, 15, "----x-------x---", 0.7f, 0f, 0.3f, 0);
        drums(s, HAT, C, 16, "x.o.x.o.x.o.x.o.", 0.42f, 0.25f, 0.1f, 0);
        drums(s, OHAT, C, 16, "--x---x---x---x-", 0.35f, -0.25f, 0.1f, 0);
        drums(s, KICK, C + 15, 1, "x-----x---------", 1f, 0f, 0f, 0);
        drums(s, SNR, C + 15, 1, "--------x-x-xxxx", 0.75f, 0f, 0.2f, 0);
        s.note(CRASH, C * 4, 4, 60, 0.8f, -0.3f, 0.3f);
        s.note(CRASH, (C + 8) * 4, 4, 60, 0.7f, 0.3f, 0.3f);
        s.note(CHIME, (C + 15) * 4, 2, 90, 0.3f, 0.3f, 0.5f);
        return s;
    }

    // ================================================================== CRYSTAL CAVERN: "Hotaru Lamp"

    private static MusicSynth cavern() {
        MusicSynth s = new MusicSynth(104, 4, 24, 303);
        s.revSize = 0.93f; s.revDamp = 0.25f; s.revWet = 1.25f; s.dlyBeats = 0.75f; s.dlyFb = 0.45f;
        String[] A = bars("Dm9 Dm9 BbM7 BbM7 Gm9 Gm9 A7sus4 A7");
        String[] B = bars("BbM7 C Am7 Dm9 BbM7 C A7sus4 A7");
        String mA = "A4/1.5 C5/.5 D5/1 E5/1 | F5/1.5 E5/.5 D5/1 A4/1 | D5/1.5 F5/.5 A5/1 G5/1 | F5/3 r/1 |"
                + " Bb4/1.5 D5/.5 F5/1 A5/1 | G5/1.5 F5/.5 D5/1 Bb4/1 | D5/1.5 E5/.5 G5/1 E5/1 | C#5/2 E5/1 A4/1";
        String mB = "D6/1.5 C6/.5 A5/1 F5/1 | E5/1.5 G5/.5 C6/1 G5/1 | A5/1.5 G5/.5 E5/1 C5/1 | D5/3 r/1 |"
                + " F5/1.5 A5/.5 D6/1 C6/1 | C6/1.5 Bb5/.5 G5/1 E5/1 | D5/1.5 E5/.5 A5/2 | A5/1.5 G5/.5 E5/1 C#5/1";
        // pads and low drone throughout
        hold(s, CH, 0, A, 62, 0.3f, 0f, 0.6f);
        hold(s, CH, 8, B, 62, 0.32f, 0f, 0.6f);
        hold(s, CH, 16, A, 62, 0.34f, 0f, 0.6f);
        line(s, SUB, 0, A, 26, 0, "r---------------", 0.55f, 0f, 0f, 1f);
        line(s, SUB, 8, B, 26, 0, "r---------------", 0.55f, 0f, 0f, 1f);
        line(s, SUB, 16, A, 26, 0, "r---------------", 0.55f, 0f, 0f, 1f);
        // A: celesta melody, sparse crystal arpeggio, far-off rail clacks
        mel(s, CE, 0, mA, 0.7f, 0.1f, 0.55f, 0.2f, 12);
        arp(s, GL, 0, A, 74, 38, "0-2-1-3-", 0.5f, 0.16f, 2f, 0.6f, 0.3f);
        drums(s, WOOD, 4, 4, "x--o------------", 0.35f, -0.3f, 0.5f, 74);
        // B: the cart is rolling: da-dum clacks, a soft kick, shaker, plucked bass
        mel(s, CE, 8, mB, 0.72f, 0.1f, 0.55f, 0.2f, 0);
        mel(s, FL, 8, mB, 0.3f, -0.2f, 0.5f, 0.1f, -12);
        arp(s, GL, 8, B, 74, 38, "0-2-1-3-", 0.5f, 0.16f, 2f, 0.6f, 0.3f);
        line(s, BS, 8, B, 26, 0, "r-----r---r-----", 0.6f, 0f, 0.1f, 0.8f);
        line(s, BS, 16, A, 26, 0, "r-----r---r---f-", 0.6f, 0f, 0.1f, 0.8f);
        drums(s, KICK, 8, 16, "x-----x---x-----", 0.65f, 0f, 0.15f, 0);
        drums(s, WOOD, 8, 16, "x--o----x--o----", 0.4f, -0.3f, 0.4f, 74);
        drums(s, WOOD, 8, 16, "-------------o--", 0.3f, 0.3f, 0.4f, 79);
        drums(s, SHK, 8, 16, "-o-o-o-o", 0.32f, 0.35f, 0.3f, 0);
        drums(s, RIM, 8, 16, "------------x---", 0.4f, 0.1f, 0.5f, 0);
        // C: strings take the tune low, glockenspiel runs 16ths with echoes
        mel(s, STR, 16, mA, 0.45f, -0.1f, 0.5f, 0f, 0);
        mel(s, CE, 16, mA, 0.3f, 0.3f, 0.6f, 0.2f, 12);
        arp(s, GL, 16, A, 74, 38, "0123123423413210", 0.25f, 0.14f, 2f, 0.55f, 0.35f);
        s.note(REV, 7 * 4, 4, 60, 0.3f, 0f, 0.4f);
        s.note(CHIME, 8 * 4, 3, 90, 0.3f, -0.3f, 0.8f);
        s.note(REV, 15 * 4, 4, 60, 0.3f, 0f, 0.4f);
        s.note(TAIKO, 16 * 4, 2, 38, 0.5f, 0f, 0.6f);
        return s;
    }

    // ================================================================== BAMBOO RIVER: "Sasabune"

    private static MusicSynth river() {
        MusicSynth s = new MusicSynth(96, 4, 24, 404);
        s.revSize = 0.84f; s.revWet = 1.0f; s.humanize = 0.01f;
        String[] A = bars("D Bm7 G A D Bm7 Em7 A7sus4,A");
        String[] B = bars("G A F#m7 Bm7 G A D D");
        String mA = "A4/1 D5/1 E5/1 F#5/1 | A5/3 F#5/1 | E5/1.5 F#5/.5 E5/1 D5/1 | E5/4 |"
                + " A4/1 D5/1 E5/1 F#5/1 | B5/2 A5/1 F#5/1 | A5/1.5 B5/.5 A5/1 F#5/.5 E5/.5 | E5/4";
        String mB = "B5/1.5 A5/.5 B5/1 D6/1 | E6/3 D6/.5 B5/.5 | A5/1.5 B5/.5 A5/1 F#5/1 | B5/3 A5/.5 F#5/.5 |"
                + " E5/1.5 F#5/.5 A5/1 B5/1 | A5/1.5 F#5/.5 E5/1 D5/.5 E5/.5 | D5/4 | r/4";
        // koto water: 8ths in A, 16ths from B on
        arp(s, KO, 0, A, 67, 38, "b1230123", 0.5f, 0.42f, 2f, 0.35f, 0f);
        arp(s, KO, 8, B, 67, 38, "0123432101234321", 0.25f, 0.34f, 2f, 0.35f, 0.15f);
        arp(s, KO, 16, A, 67, 38, "b123432101234321", 0.25f, 0.3f, 2f, 0.35f, 0.15f);
        hold(s, STR, 0, A, 62, 0.16f, 0f, 0.5f);
        hold(s, STR, 8, B, 62, 0.2f, 0f, 0.5f);
        hold(s, STR, 16, A, 62, 0.2f, 0f, 0.5f);
        line(s, BS, 0, A, 26, 0, "r-------f-------", 0.5f, 0f, 0.1f, 0.9f);
        line(s, BS, 8, B, 26, 0, "r-----r-f-------", 0.55f, 0f, 0.1f, 0.9f);
        line(s, BS, 16, A, 26, 0, "r-----r-f-----o-", 0.55f, 0f, 0.1f, 0.9f);
        // shakuhachi sings A and B; in C the koto takes the tune and shamisen answers
        mel(s, SK, 0, mA, 0.7f, 0.05f, 0.5f, 0.15f, 0);
        mel(s, SK, 8, mB, 0.75f, 0.05f, 0.5f, 0.15f, 0);
        mel(s, KO, 16, mA, 0.75f, -0.15f, 0.4f, 0.1f, 0);
        mel(s, SK, 16, "A5/16 | A5/8 | B5/4 | A5/4", 0.35f, 0.3f, 0.6f, 0f, 0);
        line(s, SH, 8, B, 50, 0, "-------------r-f", 0.5f, 0.3f, 0.3f, 0.5f);
        line(s, SH, 16, A, 50, 0, "----------r-f-o-", 0.5f, 0.3f, 0.3f, 0.5f);
        // percussion: taiko pulse grows; kakko ticks once the river picks up
        drums(s, TAIKO, 0, 8, "x-------", 0.45f, 0f, 0.4f, 33);
        drums(s, TAIKO, 8, 8, "x-----o-----o---", 0.5f, 0f, 0.4f, 33);
        drums(s, TAIKO, 16, 8, "x---o-o-x---o-..", 0.55f, 0f, 0.4f, 33);
        drums(s, KAKKO, 8, 16, "o-.-o-.-o-.-o-.-", 0.35f, -0.35f, 0.3f, 86);
        drums(s, SHK, 16, 8, "-o-o-o-o", 0.25f, 0.35f, 0.3f, 0);
        s.note(CHIME, 0, 3, 90, 0.35f, -0.3f, 0.7f);
        s.note(CHIME, 16 * 4, 3, 90, 0.3f, 0.3f, 0.7f);
        return s;
    }

    // ================================================================== SKY GLIDE: "Kaze no Michi" (waltz)

    private static MusicSynth sky() {
        MusicSynth s = new MusicSynth(168, 3, 40, 505);
        s.revSize = 0.88f; s.revWet = 1.1f; s.humanize = 0.008f;
        String[] A = bars("F F C/E C/E Dm Dm Bb C F F Am Am Bb Gm7 C7sus4 C7");
        String[] B = bars("Bb C Am7 Dm Gm7 C F F/A Bb C/Bb Am7 Dm7 Gm7 Bb/C F F");
        String[] A2 = bars("F F Am Am Bb Gm7 C7sus4 C7");
        String mA = "A4/1 C5/1 F5/1 | A5/2 G5/1 | G5/2 E5/1 | C5/3 | D5/1 F5/1 A5/1 | D6/2 C6/1 | Bb5/1 A5/1 G5/1 |"
                + " G5/1.5 A5/.5 Bb5/1 | A4/1 C5/1 F5/1 | C6/2 Bb5/1 | E5/1 A5/1 B5/1 | C6/3 | D6/1.5 C6/.5 Bb5/1 |"
                + " A5/1 G5/1 F5/1 | F5/2 G5/1 | E5/3";
        String mA2 = "A4/1 C5/1 F5/1 | C6/2 Bb5/1 | E5/1 A5/1 B5/1 | C6/3 | D6/1.5 C6/.5 Bb5/1 | A5/1 G5/1 F5/1 |"
                + " F5/2 G5/1 | E5/3";
        String mB = "F5/1 Bb5/1 D6/1 | E6/2 C6/1 | C6/1 B5/1 A5/1 | A5/2 F5/1 | G5/1 Bb5/1 D6/1 | C6/2 Bb5/1 | A5/3 |"
                + " r/1 A5/1 C6/1 | F6/1.5 E6/.5 D6/1 | E6/2 C6/1 | C6/2 A5/1 | A5/1 D6/1 F6/1 | D6/1.5 C6/.5 Bb5/1 |"
                + " G5/1 A5/1 Bb5/1 | C6/3 | A5/3";
        // oom-pah-pah: harp in A, piano and harp in B, everything in A'
        arp(s, HP, 0, A, 65, 41, "b01", 1f, 0.5f, -0.2f, 0.45f, 0f);
        arp(s, HP, 16, B, 65, 41, "b01", 1f, 0.45f, -0.25f, 0.45f, 0f);
        arp(s, P, 16, B, 62, 29, "b12", 1f, 0.35f, 0.15f, 0.4f, 0f);
        arp(s, P, 32, A2, 62, 29, "b12", 1f, 0.4f, 0.15f, 0.4f, 0f);
        arp(s, HP, 32, A2, 72, 41, "012345", 0.5f, 0.3f, 2f, 0.5f, 0f);
        // A: flute, light strings; B: strings soar in octaves, flute answers; A': choir, glockenspiel, timpani
        mel(s, FL, 0, mA, 0.68f, 0.1f, 0.45f, 0.1f, 0);
        hold(s, STR, 0, A, 60, 0.15f, 0f, 0.5f);
        mel(s, STR, 16, mB, 0.6f, 0.15f, 0.45f, 0f, 0);
        mel(s, STR, 16, mB, 0.4f, -0.2f, 0.45f, 0f, -12);
        mel(s, FL, 16, mB, 0.28f, 0.35f, 0.5f, 0f, 0);
        hold(s, CH, 16, B, 60, 0.18f, 0f, 0.5f);
        line(s, STR, 16, B, 29, 0, "r-----------", 0.28f, 0f, 0.4f, 1f);
        mel(s, STR, 32, mA2, 0.62f, 0.15f, 0.45f, 0f, 12);
        mel(s, FL, 32, mA2, 0.6f, -0.15f, 0.45f, 0.1f, 12);
        mel(s, GL, 32, mA2, 0.25f, 0.35f, 0.5f, 0.1f, 12);
        hold(s, CH, 32, A2, 64, 0.28f, 0f, 0.55f);
        line(s, STR, 32, A2, 29, 0, "r-----------", 0.35f, 0f, 0.4f, 1f);
        drums(s, TOM, 16, 1, "x--", 0.55f, 0f, 0.5f, 31);
        drums(s, TOM, 32, 1, "x-o", 0.6f, 0f, 0.5f, 31);
        drums(s, TOM, 36, 1, "x--", 0.55f, 0f, 0.5f, 31);
        drums(s, SHK, 16, 24, "-oo", 0.25f, 0.4f, 0.3f, 0);
        for (int b = 0; b < 16; b += 4) s.note(TRI, b * 3, 1, 100, 0.35f, -0.4f, 0.6f);
        s.note(REV, 14 * 3, 6, 60, 0.35f, 0f, 0.4f);
        s.note(REV, 30 * 3, 6, 60, 0.35f, 0f, 0.4f);
        s.note(CRASH, 32 * 3, 3, 60, 0.45f, 0.3f, 0.5f);
        s.note(CHIME, 0, 3, 90, 0.35f, 0.3f, 0.7f);
        s.note(CHIME, 16 * 3, 3, 90, 0.3f, -0.3f, 0.7f);
        return s;
    }

    // ================================================================== EXPRESS ROOFTOPS: "Rooftop Rush"

    private static MusicSynth rooftops() {
        MusicSynth s = new MusicSynth(160, 4, 28, 606);
        s.revSize = 0.7f; s.revWet = 0.7f; s.dlyBeats = 0.75f; s.dlyFb = 0.3f;
        String[] intro = bars("Bm G D A");
        String[] verse = bars("Bm G D A Bm G Em7 F#7");
        String[] chorus = bars("GM7 A F#m7 Bm Em7 F#m7 GM7 A GM7 A F#m7 Bm Em7 A Bm F#7");
        int I = 0, V = 4, C = 12;
        String hook = "B5/.5 F#5/.5 B5/.5 C#6/.5 _D6/1 C#6/.5 B5/.5 | D6/.5 B5/.5 G5/.5 A5/.5 _B5/1 A5/.5 G5/.5 |"
                + " F#5/.5 A5/.5 D6/.5 E6/.5 _F#6/1 E6/.5 D6/.5 | _C#6/1 E6/1 A5/1 C#6/.5 E6/.5";
        String mV = "F#5/.5 F#5/.5 F#5/.5 E5/.5 D5/1 B4/1 | D5/.5 D5/.5 D5/.5 E5/.5 B4/2 |"
                + " F#5/.5 F#5/.5 A5/.5 F#5/.5 E5/1 D5/1 | E5/3 r/1 |"
                + " F#5/.5 F#5/.5 F#5/.5 E5/.5 D5/1 F#5/1 | G5/.5 G5/.5 G5/.5 F#5/.5 D5/1 B4/1 |"
                + " G5/1 F#5/1 E5/1 D5/1 | C#5/1.5 E5/.5 F#5/2";
        String k1 = "_B5/1.5 A5/.5 B5/1 D6/1 | C#6/1.5 B5/.5 A5/1 E5/1 | F#5/1.5 A5/.5 C#6/1 E6/1 |"
                + " D6/2 C#6/.5 B5/.5 F#5/1 |";
        String mC = k1 + " G5/1.5 F#5/.5 E5/1 B5/1 | A5/1.5 G5/.5 F#5/1 C#6/1 | D6/1.5 C#6/.5 B5/1 A5/1 | _E6/3 r/1 |"
                + k1 + " G5/1 B5/1 E6/1 D6/1 | C#6/1.5 D6/.5 E6/2 | _F#6/2 E6/1 D6/1 | C#6/2 A#5/1 C#6/1";
        // guitars: chugging power chords, wide L/R double-track
        powerChords(s, I, intro, "x-o-o-x-o-o-x-o-", 0.7f);
        powerChords(s, V, verse, "x-o-o-o-x-o-o-o-", 0.6f);
        powerChords(s, C, chorus, "x-----o-x-o-x-o-", 0.75f);
        line(s, SB, I, intro, 35, 0, "r-r-r-r-r-r-r-r-", 0.7f, 0f, 0f, 0.7f);
        line(s, SB, V, verse, 35, 0, "r-r-r-r-r-r-r-r-", 0.7f, 0f, 0f, 0.7f);
        line(s, SB, C, chorus, 35, 0, "r-r-o-r-r-r-o-r-", 0.75f, 0f, 0f, 0.7f);
        // melody: hook on lead, verse on lead, chorus doubled with glockenspiel and a supersaw bed
        mel(s, LD, I, hook, 0.7f, 0f, 0.25f, 0.2f, 0);
        mel(s, LD, V, mV, 0.6f, 0f, 0.25f, 0.18f, 0);
        mel(s, LD, C, mC, 0.75f, 0f, 0.25f, 0.2f, 0);
        mel(s, GL, C, mC, 0.25f, 0.3f, 0.3f, 0.1f, 12);
        hold(s, SAW, C, chorus, 66, 0.28f, 0f, 0.3f);
        hold(s, STR, V, verse, 62, 0.15f, 0f, 0.4f);
        // drums
        drums(s, KICK, I, 4, "x-----x-x-------", 1f, 0f, 0f, 0);
        drums(s, SNR, I, 3, "----x-------x---", 0.8f, 0f, 0.2f, 0);
        drums(s, HAT, I, 4, "x-o-x-o-x-o-x-o-", 0.45f, 0.25f, 0.1f, 0);
        drums(s, KICK, V, 8, "x-----x-x-----x-", 1f, 0f, 0f, 0);
        drums(s, SNR, V, 7, "----x-------x---", 0.8f, 0f, 0.2f, 0);
        drums(s, HAT, V, 8, "x.o.x.o.x.o.x.o.", 0.42f, 0.25f, 0.1f, 0);
        drums(s, KICK, C, 16, "x-----x-x-x---x-", 1f, 0f, 0f, 0);
        drums(s, SNR, C, 15, "----x-------x---", 0.85f, 0f, 0.2f, 0);
        drums(s, RIDE, C, 16, "x-o-x-o-x-o-x-o-", 0.38f, -0.25f, 0.2f, 0);
        drums(s, OHAT, C, 16, "--x---x---x---x-", 0.3f, 0.25f, 0.1f, 0);
        fill(s, I + 3);
        fill(s, V + 7);
        fill(s, C + 15);
        for (int b = 0; b < 28; b += 4) s.note(CRASH, b * 4, 4, 60, b == C ? 0.85f : 0.6f, b % 8 == 0 ? -0.3f : 0.3f, 0.25f);
        s.note(CRASH, (C + 8) * 4, 4, 60, 0.75f, 0.3f, 0.25f);
        return s;
    }

    /** Power chords (root, fifth, octave) on a 16th grid: 'x' open hit, 'o' palm-muted chug. */
    private static void powerChords(MusicSynth s, int bar0, String[] prog, String pat, float vel) {
        s.role = MusicSynth.ACCOMP;
        int bpb = s.beatsPerBar;
        for (int b = 0; b < prog.length; b++)
            for (int i = 0; i < 16; i++) {
                char ch = pat.charAt(i);
                if (ch == '-') continue;
                int j = i + 1;
                while (j < 16 && pat.charAt(j) == '-') j++;
                float beat = i * 0.25f;
                String c = chordAt(prog, b, beat, bpb);
                int r = MusicSynth.bassOf(c, 40);
                boolean mute = ch == 'o';
                float len = mute ? 0.2f : (j - i) * 0.25f * 0.95f;
                float v = vel * (mute ? 0.7f : 1f);
                for (int side = -1; side <= 1; side += 2) {
                    float at = (bar0 + b) * bpb + beat + (side > 0 ? 0.01f : 0f);
                    s.note(GT, at, len, r, v, side * 0.7f, 0.15f);
                    s.note(GT, at, len, r + 7, v * 0.8f, side * 0.7f, 0.15f);
                    if (!mute) s.note(GT, at, len, r + 12, v * 0.6f, side * 0.7f, 0.15f);
                }
            }
    }

    private static void fill(MusicSynth s, int bar) {
        float b = bar * 4 + 2;
        float[] tp = {50, 50, 45, 45, 41, 41, 38, 38};
        for (int i = 0; i < 8; i++) s.note(TOM, b + i * 0.25f, 0.25f, tp[i], 0.6f + i * 0.04f, (i - 3.5f) * 0.12f, 0.25f);
    }

    // ================================================================== stingers

    private static MusicSynth sting(float bpm, int beats, long seed) {
        MusicSynth s = new MusicSynth(bpm, beats, 1, seed);
        s.oneShot = true;
        return s;
    }

    private static MusicSynth stSakura() {
        MusicSynth s = sting(132, 8, 1);
        s.handoffBeats = 5f;
        s.mel(GL, 0, "B5/.25 E6/.25 G#6/.25 B6/.25 r/1 E6+G#6+B6/2", 0.5f, 0.3f, 0.4f, 0.2f, 0);
        s.mel(LD, 0, "r/1 B5/.5 C#6/.5 _E6/3", 0.75f, 0f, 0.3f, 0.25f, 0);
        s.mel(SAW, 0, "r/1 E4+G#4+B4+F#5/4", 0.4f, 0f, 0.35f, 0f, 0);
        s.mel(SB, 0, "r/1 E2/2", 0.8f, 0f, 0f, 0f, 0);
        s.note(KICK, 1, 1, 0, 1f, 0f, 0f);
        s.note(CLAP, 1, 1, 0, 0.5f, 0f, 0.3f);
        s.note(CRASH, 1, 4, 60, 0.6f, -0.2f, 0.3f);
        s.note(CHIME, 1.5f, 2, 90, 0.35f, 0.3f, 0.5f);
        return s;
    }

    private static MusicSynth stCavern() {
        MusicSynth s = sting(104, 8, 2);
        s.handoffBeats = 5.5f;
        s.revSize = 0.93f; s.revWet = 1.3f; s.dlyFb = 0.45f;
        s.note(REV, 0, 1, 60, 0.35f, 0f, 0.4f);
        s.mel(CE, 1, "D5/.25 F5/.25 A5/.25 C6/.25 E6/.25 F6/.25 A6/1.5", 0.7f, 0.2f, 0.6f, 0.3f, 0);
        s.mel(CH, 1, "D4+A4+C5+E5+F5/5", 0.4f, 0f, 0.6f, 0f, 0);
        s.mel(SUB, 1, "D2/5", 0.6f, 0f, 0f, 0f, 0);
        s.note(TAIKO, 1, 2, 38, 0.6f, 0f, 0.5f);
        s.note(CHIME, 2, 2, 90, 0.3f, -0.3f, 0.7f);
        return s;
    }

    private static MusicSynth stRiver() {
        MusicSynth s = sting(96, 8, 3);
        s.handoffBeats = 5.5f;
        s.mel(KO, 0, "D6/.125 B5/.125 A5/.125 F#5/.125 E5/.125 D5/.125 B4/.125 A4/.125", 0.6f, -0.2f, 0.4f, 0f, 0);
        s.note(TAIKO, 1, 1, 33, 0.8f, 0f, 0.4f);
        s.note(TAIKO, 1.75f, 1, 36, 0.5f, 0f, 0.4f);
        s.note(KAKKO, 1.5f, 1, 86, 0.4f, -0.3f, 0.3f);
        s.mel(SK, 1, "A5/1 B5/.5 _A5/3.5", 0.8f, 0.05f, 0.5f, 0.15f, 0);
        s.mel(STR, 1, "D4+A4+E5/5", 0.3f, 0f, 0.5f, 0f, 0);
        s.mel(KO, 1, "D3+A3/4", 0.5f, -0.2f, 0.4f, 0f, 0);
        return s;
    }

    private static MusicSynth stSky() {
        MusicSynth s = sting(120, 8, 4);
        s.handoffBeats = 6f;
        s.revSize = 0.88f; s.revWet = 1.1f;
        s.mel(HP, 0, "F4/.125 G4/.125 A4/.125 B4/.125 C5/.125 D5/.125 E5/.125 F5/.125 G5/.125 A5/.125 B5/.125 C6/.125"
                + " D6/.125 E6/.125 F6/.5", 0.45f, -0.2f, 0.5f, 0f, 0);
        s.mel(STR, 2, "F4+C5+G5+A5/5", 0.45f, 0f, 0.5f, 0f, 0);
        s.mel(STR, 2, "F3/5", 0.35f, 0f, 0.4f, 0f, 0);
        s.mel(FL, 2, "C6/1 G6/.5 _A6/3.5", 0.6f, 0.2f, 0.5f, 0.1f, 0);
        s.note(CHIME, 2, 3, 90, 0.4f, 0.3f, 0.7f);
        s.note(TOM, 2, 1, 31, 0.55f, 0f, 0.5f);
        return s;
    }

    private static MusicSynth stRooftops() {
        MusicSynth s = sting(160, 8, 5);
        s.masterTarget = 0.13f;
        s.handoffBeats = 5f;
        float[] tp = {50, 45, 41, 38};
        for (int i = 0; i < 4; i++) s.note(TOM, i * 0.25f, 0.25f, tp[i], 0.7f, (i - 1.5f) * 0.2f, 0.2f);
        float[] at = {1f, 1.75f, 2.5f};
        for (float a : at)
            for (int side = -1; side <= 1; side += 2) {
                float len = a == 2.5f ? 3f : 0.6f;
                s.note(GT, a, len, 47, 0.8f, side * 0.7f, 0.15f);
                s.note(GT, a, len, 54, 0.65f, side * 0.7f, 0.15f);
                s.note(GT, a, len, 59, 0.5f, side * 0.7f, 0.15f);
            }
        for (float a : at) { s.note(KICK, a, 1, 0, 1f, 0f, 0f); s.note(SB, a, a == 2.5f ? 2f : 0.5f, 35, 0.8f, 0f, 0f); }
        s.note(SNR, 2.5f, 1, 0, 0.9f, 0f, 0.2f);
        s.note(CRASH, 2.5f, 4, 60, 0.9f, 0.2f, 0.3f);
        s.mel(LD, 2.5f, "F#6/3", 0.7f, 0f, 0.25f, 0.25f, 0);
        return s;
    }

    private static MusicSynth stGameOver() {
        MusicSynth s = sting(84, 8, 6);
        s.handoffBeats = 7f;
        s.revSize = 0.86f; s.revWet = 1.0f;
        s.mel(P, 0, "A2+E3/2 A2+E3/2 E2+B2/4", 0.45f, -0.1f, 0.4f, 0f, 0);
        s.mel(P, 0, "C#4+E4+G#4/2 C4+E4+F#4/2 B3+E4+F#4+G#4/4", 0.4f, 0.05f, 0.45f, 0f, 0);
        s.mel(MB, 0, "G#6/.5 E6/.5 C#6/1 C6/.5 A5/.5 F#5/1 G#5/4", 0.6f, 0.2f, 0.55f, 0.1f, 0);
        s.mel(STR, 0, "E4+A4/2 E4+A4/2 E4+B4/4", 0.18f, 0f, 0.5f, 0f, 0);
        return s;
    }
}
