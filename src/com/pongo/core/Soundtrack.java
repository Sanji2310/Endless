package com.pongo.core;

/**
 * The game's music (docs/PONGO_DESIGN.md §7), composed in code and rendered by MusicSynth at load. One looping theme
 * for the menu and one per zone, plus one-shot stingers for zone entries and game over. Every theme is rendered at the
 * same loudness so MusicPlayer can crossfade between them.
 *
 *   MENU      "Hanami Platform"  G major, 124 BPM. City-pop turnaround on clean guitar, synth bass and lead.
 *   SAKURA    "Hanami Express"   E major, 172 BPM. Anime-opening rock: royal road chorus, power chords, lead + glockenspiel.
 *   CAVERN    "Hotaru Lamp"      D minor, 150 BPM. Darker driving rock, celesta and ringing glockenspiel crystals.
 *   RIVER     "Sasabune"         B minor / yo scale, 156 BPM. Wagakki rock: the band plus shamisen riff, koto and taiko.
 *   SKY       "Kaze no Michi"    D major, 176 BPM. Soaring rock with a supersaw sky and harp arpeggios.
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

    // ================================================================== the band (Rooftop Rush's sound, shared)

    /**
     * One section of the Rooftop Rush band: double-tracked power-chord guitars, synth bass and drums.
     * style: INTRO (driving 8ths), VERSE (chugs), CHORUS (open hits, ride, offbeat hats), SOFT (menu: clean guitar
     * arpeggios, lighter drums). A tom fill closes the section unless fill is false.
     */
    private static final int INTRO = 0, VERSE = 1, CHORUS = 2, SOFT = 3;

    private static void band(MusicSynth s, int bar0, String[] prog, int style, float gtVel, boolean fill) {
        int n = prog.length, last = fill ? n - 1 : n;
        switch (style) {
            case INTRO:
                powerChords(s, bar0, prog, "x-o-o-x-o-o-x-o-", gtVel);
                line(s, SB, bar0, prog, 35, 0, "r-r-r-r-r-r-r-r-", 0.7f, 0f, 0f, 0.7f);
                drums(s, KICK, bar0, n, "x-----x-x-------", 1f, 0f, 0f, 0);
                drums(s, SNR, bar0, last, "----x-------x---", 0.8f, 0f, 0.2f, 0);
                drums(s, HAT, bar0, n, "x-o-x-o-x-o-x-o-", 0.45f, 0.25f, 0.1f, 0);
                break;
            case VERSE:
                powerChords(s, bar0, prog, "x-o-o-o-x-o-o-o-", gtVel);
                line(s, SB, bar0, prog, 35, 0, "r-r-r-r-r-r-r-r-", 0.7f, 0f, 0f, 0.7f);
                drums(s, KICK, bar0, n, "x-----x-x-----x-", 1f, 0f, 0f, 0);
                drums(s, SNR, bar0, last, "----x-------x---", 0.8f, 0f, 0.2f, 0);
                drums(s, HAT, bar0, n, "x.o.x.o.x.o.x.o.", 0.42f, 0.25f, 0.1f, 0);
                break;
            case CHORUS:
                powerChords(s, bar0, prog, "x-----o-x-o-x-o-", gtVel);
                line(s, SB, bar0, prog, 35, 0, "r-r-o-r-r-r-o-r-", 0.75f, 0f, 0f, 0.7f);
                drums(s, KICK, bar0, n, "x-----x-x-x---x-", 1f, 0f, 0f, 0);
                drums(s, SNR, bar0, last, "----x-------x---", 0.85f, 0f, 0.2f, 0);
                drums(s, RIDE, bar0, n, "x-o-x-o-x-o-x-o-", 0.38f, -0.25f, 0.2f, 0);
                drums(s, OHAT, bar0, n, "--x---x---x---x-", 0.3f, 0.25f, 0.1f, 0);
                break;
            default:
                arp(s, MusicSynth.CLEANGTR, bar0, prog, 62, 40, "b0120312", 0.5f, gtVel, 2f, 0.3f, 0.15f);
                line(s, SB, bar0, prog, 35, 0, "r--r--o-r-r---o-", 0.6f, 0f, 0f, 0.6f);
                drums(s, KICK, bar0, n, "x-----x-x-------", 0.85f, 0f, 0f, 0);
                drums(s, CLAP, bar0, last, "----x-------x---", 0.55f, 0f, 0.3f, 0);
                drums(s, HAT, bar0, n, "x.o.x.o.x.o.x.o.", 0.35f, 0.25f, 0.1f, 0);
                break;
        }
        if (fill) fill(s, bar0 + n - 1);
    }

    private static void crashes(MusicSynth s, int bars, int... strong) {
        for (int b = 0; b < bars; b += 4) s.note(CRASH, b * 4, 4, 60, 0.6f, b % 8 == 0 ? -0.3f : 0.3f, 0.25f);
        for (int b : strong) s.note(CRASH, b * 4, 4, 60, 0.85f, 0.3f, 0.25f);
    }

    // ================================================================== MENU: "Hanami Platform"

    private static MusicSynth menu() {
        MusicSynth s = new MusicSynth(124, 4, 20, 101);
        s.revSize = 0.75f; s.revWet = 0.8f; s.dlyBeats = 0.75f; s.dlyFb = 0.3f;
        // city pop turnaround (the "Just the Two of Us" family) in G
        String[] prog = bars("GM7 F#m7,B7 Em7 Dm7,G7 CM7 B7 Em7,A7 D7");
        String[] intro = bars("GM7 F#m7,B7 Em7 Dm7,G7");
        String m = "B5/.5 A5/.5 B5/.5 D6/.5 _F#6/1 E6/.5 D6/.5 | E6/1 C#6/.5 A5/.5 _D#6/1 B5/1 |"
                + " B5/1.5 G5/.5 B5/1 D6/1 | C6/1 A5/.5 F5/.5 B5/1 G5/1 |"
                + " E6/1.5 D6/.5 E6/1 G6/1 | _F#6/1.5 E6/.5 D#6/1 B5/1 | G6/1 F#6/.5 E6/.5 C#6/1 A5/1 | _D6/3 r/1";
        band(s, 0, intro, SOFT, 0.7f, true);
        band(s, 4, prog, SOFT, 0.7f, true);
        band(s, 12, prog, SOFT, 0.75f, true);
        hold(s, SAW, 0, intro, 64, 0.16f, 0f, 0.35f);
        hold(s, SAW, 4, prog, 64, 0.18f, 0f, 0.35f);
        hold(s, SAW, 12, prog, 64, 0.22f, 0f, 0.35f);
        mel(s, LD, 4, m, 0.55f, 0f, 0.3f, 0.2f, -12);
        mel(s, LD, 12, m, 0.65f, 0f, 0.3f, 0.2f, 0);
        mel(s, GL, 12, m, 0.22f, 0.3f, 0.3f, 0.1f, 0);
        s.note(CRASH, 4 * 4, 4, 60, 0.45f, -0.3f, 0.25f);
        s.note(CRASH, 12 * 4, 4, 60, 0.55f, 0.3f, 0.25f);
        return s;
    }

    // ================================================================== SAKURA LINE: "Hanami Express"

    private static MusicSynth sakura() {
        MusicSynth s = new MusicSynth(172, 4, 28, 202);
        s.revSize = 0.7f; s.revWet = 0.7f; s.dlyBeats = 0.75f; s.dlyFb = 0.3f;
        String[] intro = bars("A B G#m C#m");
        String[] verse = bars("E B/D# C#m A E B/D# A B");
        String[] chorus = bars("A B G#m C#m A B E E A B G#m C#m F#m B E E");
        int I = 0, V = 4, C = 12;
        String hook = "E5/.5 F#5/.5 G#5/.5 B5/.5 _C#6/1 B5/.5 G#5/.5 | F#5/.5 G#5/.5 B5/.5 _D#6/1.5 C#6/.5 B5/.5 |"
                + " G#5/.5 B5/.5 D#6/.5 _F#6/1 E6/.5 D#6/.5 B5/.5 | _C#6/2 B5/.5 G#5/.5 E5/1";
        String mV = "G#5/.5 G#5/.5 G#5/.5 F#5/.5 E5/1 B4/1 | D#5/.5 D#5/.5 E5/.5 F#5/.5 D#5/2 |"
                + " E5/.5 E5/.5 G#5/.5 E5/.5 C#5/1 B4/1 | C#5/3 r/1 |"
                + " G#5/.5 G#5/.5 G#5/.5 F#5/.5 E5/1 G#5/1 | F#5/.5 F#5/.5 F#5/.5 E5/.5 D#5/1 B4/1 |"
                + " C#5/1 E5/1 A5/1 G#5/1 | F#5/1.5 G#5/.5 A5/1 B5/1";
        String k1 = "_C#6/1.5 B5/.5 C#6/1 E6/1 | D#6/1.5 C#6/.5 B5/1 F#5/1 | B5/1.5 G#5/.5 B5/1 D#6/1 |"
                + " _E6/2 D#6/.5 C#6/.5 B5/1 |";
        String mC = k1 + " A5/1.5 B5/.5 C#6/1 E6/1 | _F#6/1.5 E6/.5 D#6/1 B5/1 | G#5/1.5 F#5/.5 E5/1 B5/1 | _E6/3 r/1 |"
                + k1 + " A5/1 C#6/1 F#6/1 E6/1 | D#6/1.5 E6/.5 F#6/2 | _G#6/2 F#6/1 E6/1 | B5/2 r/2";
        band(s, I, intro, INTRO, 0.65f, true);
        band(s, V, verse, VERSE, 0.58f, true);
        band(s, C, chorus, CHORUS, 0.72f, true);
        mel(s, LD, I, hook, 0.7f, 0f, 0.25f, 0.2f, 0);
        mel(s, GL, I, hook, 0.22f, 0.3f, 0.3f, 0.1f, 12);
        mel(s, LD, V, mV, 0.6f, 0f, 0.25f, 0.18f, 0);
        mel(s, LD, C, mC, 0.75f, 0f, 0.25f, 0.2f, 0);
        mel(s, GL, C, mC, 0.25f, 0.3f, 0.3f, 0.1f, 12);
        hold(s, SAW, C, chorus, 66, 0.28f, 0f, 0.3f);
        hold(s, STR, V, verse, 62, 0.15f, 0f, 0.4f);
        crashes(s, 28, C, C + 8);
        s.note(CHIME, C * 4, 2, 90, 0.3f, 0.3f, 0.5f);
        return s;
    }

    // ================================================================== CRYSTAL CAVERN: "Hotaru Lamp"

    private static MusicSynth cavern() {
        MusicSynth s = new MusicSynth(150, 4, 28, 303);
        s.revSize = 0.85f; s.revWet = 0.9f; s.dlyBeats = 0.75f; s.dlyFb = 0.38f;
        String[] intro = bars("Dm Bb C A");
        String[] verse = bars("Dm Bb F C Dm Bb Gm A");
        String[] chorus = bars("Bb C Am Dm Gm Am Bb C Bb C Am Dm Gm C Dm A");
        int I = 0, V = 4, C = 12;
        String hook = "D5/.5 A5/.5 D6/.5 E6/.5 _F6/1 E6/.5 D6/.5 | D6/.5 Bb5/.5 F5/.5 G5/.5 _A5/1 G5/.5 F5/.5 |"
                + " E5/.5 G5/.5 C6/.5 D6/.5 _E6/1 D6/.5 C6/.5 | _C#6/1 E6/1 A5/1 C#6/.5 E6/.5";
        String mV = "A5/.5 A5/.5 A5/.5 G5/.5 F5/1 D5/1 | F5/.5 F5/.5 F5/.5 G5/.5 D5/2 |"
                + " A5/.5 A5/.5 C6/.5 A5/.5 G5/1 F5/1 | G5/3 r/1 |"
                + " A5/.5 A5/.5 A5/.5 G5/.5 F5/1 A5/1 | Bb5/.5 Bb5/.5 Bb5/.5 A5/.5 F5/1 D5/1 |"
                + " Bb5/1 A5/1 G5/1 F5/1 | E5/1.5 G5/.5 A5/2";
        String k1 = "_D6/1.5 C6/.5 D6/1 F6/1 | E6/1.5 D6/.5 C6/1 G5/1 | A5/1.5 C6/.5 E6/1 G6/1 | _F6/2 E6/.5 D6/.5 A5/1 |";
        String mC = k1 + " Bb5/1.5 A5/.5 G5/1 D6/1 | C6/1.5 A5/.5 E5/1 E6/1 | F6/1.5 E6/.5 D6/1 C6/1 | _E6/3 r/1 |"
                + k1 + " Bb5/1 D6/1 G6/1 F6/1 | E6/1.5 F6/.5 G6/2 | _A6/2 G6/1 F6/1 | E6/2 C#6/1 E6/1";
        band(s, I, intro, INTRO, 0.62f, true);
        band(s, V, verse, VERSE, 0.58f, true);
        band(s, C, chorus, CHORUS, 0.7f, true);
        mel(s, LD, I, hook, 0.7f, 0f, 0.28f, 0.22f, 0);
        mel(s, CE, I, hook, 0.25f, 0.3f, 0.4f, 0.15f, 12);
        mel(s, LD, V, mV, 0.6f, 0f, 0.28f, 0.2f, 0);
        mel(s, CE, V, mV, 0.2f, -0.3f, 0.4f, 0.15f, 12);
        mel(s, LD, C, mC, 0.75f, 0f, 0.28f, 0.22f, 0);
        mel(s, GL, C, mC, 0.22f, 0.3f, 0.35f, 0.1f, 12);
        // crystals: glockenspiel 16ths ringing through the chorus with echoes
        arp(s, GL, C, chorus, 74, 38, "0123123423413210", 0.25f, 0.13f, 2f, 0.45f, 0.3f);
        hold(s, SAW, C, chorus, 64, 0.24f, 0f, 0.35f);
        hold(s, STR, V, verse, 60, 0.15f, 0f, 0.45f);
        crashes(s, 28, C, C + 8);
        return s;
    }

    // ================================================================== BAMBOO RIVER: "Sasabune"

    private static MusicSynth river() {
        MusicSynth s = new MusicSynth(156, 4, 28, 404);
        s.revSize = 0.75f; s.revWet = 0.75f; s.dlyBeats = 0.75f; s.dlyFb = 0.3f;
        // wagakki rock: the band plus shamisen and koto, melodies in the Japanese yo scale (B D E F# A)
        String[] intro = bars("Bm G A Bm");
        String[] verse = bars("Bm G A Bm Bm G Em F#");
        String[] chorus = bars("G A F#m Bm G A Bm Bm G A F#m Bm Em F# Bm Bm");
        int I = 0, V = 4, C = 12;
        String riff = "B4/.25 D5/.25 E5/.25 F#5/.25 A5/.5 F#5/.5 E5/.5 D5/.5 B4/1 |"
                + " D5/.25 E5/.25 F#5/.25 A5/.25 B5/.5 A5/.5 F#5/.5 E5/.5 D5/1 |"
                + " E5/.25 F#5/.25 A5/.25 B5/.25 D6/.5 B5/.5 A5/.5 F#5/.5 E5/1 | F#5/.5 E5/.5 D5/.5 E5/.5 B4/2";
        String mV = "F#5/.5 F#5/.5 E5/.5 D5/.5 E5/1 B4/1 | D5/.5 D5/.5 E5/.5 F#5/.5 B4/2 |"
                + " E5/.5 E5/.5 F#5/.5 A5/.5 E5/1 A4/1 | B4/3 r/1 |"
                + " F#5/.5 F#5/.5 A5/.5 B5/.5 A5/1 F#5/1 | D5/.5 E5/.5 D5/.5 B4/.5 D5/2 |"
                + " E5/1 G5/1 B5/1 A5/1 | F#5/1.5 E5/.5 C#5/1 F#5/1";
        String k1 = "_B5/1.5 A5/.5 B5/1 D6/1 | E6/1.5 D6/.5 B5/1 A5/1 | A5/1.5 F#5/.5 A5/1 C#6/1 | _B5/3 A5/.5 F#5/.5 |";
        String mC = k1 + " D6/1.5 B5/.5 D6/1 E6/1 | E6/1.5 D6/.5 C#6/1 A5/1 | B5/1.5 A5/.5 F#5/1 E5/1 | _F#5/3 r/1 |"
                + k1 + " G5/1 B5/1 E6/1 D6/1 | C#6/1.5 A#5/.5 C#6/1 E6/1 | _F#6/2 E6/1 D6/1 | B5/2 r/2";
        band(s, I, intro, INTRO, 0.6f, true);
        band(s, V, verse, VERSE, 0.55f, true);
        band(s, C, chorus, CHORUS, 0.68f, true);
        // the riff on shamisen and lead together; shamisen answers in the verse; koto runs through the chorus
        mel(s, SH, I, riff, 1.1f, -0.35f, 0.25f, 0f, 0);
        mel(s, LD, I, riff, 0.55f, 0.1f, 0.25f, 0.15f, 0);
        mel(s, LD, V, mV, 0.6f, 0f, 0.25f, 0.18f, 0);
        line(s, SH, V, verse, 59, 0, "--------------r-", 0.9f, -0.35f, 0.2f, 0.5f);
        mel(s, LD, C, mC, 0.75f, 0f, 0.25f, 0.2f, 0);
        mel(s, SH, C, mC, 0.55f, -0.35f, 0.25f, 0f, 0);
        arp(s, KO, C, chorus, 71, 38, "0123432101234321", 0.25f, 0.4f, 2f, 0.35f, 0.1f);
        hold(s, SAW, C, chorus, 66, 0.25f, 0f, 0.3f);
        hold(s, STR, V, verse, 62, 0.15f, 0f, 0.4f);
        crashes(s, 28, C, C + 8);
        s.note(TAIKO, C * 4, 2, 33, 0.8f, 0f, 0.3f);
        s.note(TAIKO, (C + 8) * 4, 2, 33, 0.75f, 0f, 0.3f);
        s.note(TAIKO, 0, 2, 33, 0.7f, 0f, 0.3f);
        return s;
    }

    // ================================================================== SKY GLIDE: "Kaze no Michi"

    private static MusicSynth sky() {
        MusicSynth s = new MusicSynth(176, 4, 28, 505);
        s.revSize = 0.8f; s.revWet = 0.85f; s.dlyBeats = 0.75f; s.dlyFb = 0.35f;
        String[] intro = bars("D A/C# Bm G");
        String[] verse = bars("D A/C# Bm F#m G D/F# Em A");
        String[] chorus = bars("D A Bm F#m G D G A D A Bm F#m Em A D D");
        int I = 0, V = 4, C = 12;
        String hook = "A5/.5 D6/.5 E6/.5 F#6/.5 _A6/1 F#6/.5 E6/.5 | E6/.5 C#6/.5 A5/.5 B5/.5 _C#6/1 B5/.5 A5/.5 |"
                + " F#5/.5 B5/.5 D6/.5 E6/.5 _F#6/1 E6/.5 D6/.5 | _B5/1 D6/1 G5/1 A5/.5 B5/.5";
        String mV = "F#5/.5 F#5/.5 F#5/.5 E5/.5 D5/1 A4/1 | C#5/.5 C#5/.5 D5/.5 E5/.5 A4/2 |"
                + " D5/.5 D5/.5 F#5/.5 D5/.5 B4/1 A4/1 | C#5/3 r/1 |"
                + " B4/.5 D5/.5 G5/.5 F#5/.5 D5/1 B4/1 | A4/.5 D5/.5 F#5/.5 A5/.5 F#5/2 |"
                + " G5/1 F#5/1 E5/1 D5/1 | C#5/1.5 E5/.5 A5/2";
        String k1 = "_F#6/1.5 E6/.5 D6/1 A5/1 | C#6/1.5 B5/.5 A5/1 E5/1 | D6/1.5 C#6/.5 B5/1 F#5/1 | A5/1.5 F#5/.5 C#6/2 |";
        String mC = k1 + " B5/1.5 A5/.5 G5/1 D6/1 | _F#6/1.5 E6/.5 D6/1 A5/1 | G5/1 B5/1 D6/1 E6/1 | _E6/3 r/1 |"
                + k1 + " G5/1 B5/1 E6/1 D6/1 | C#6/1.5 D6/.5 E6/2 | _F#6/2 E6/1 D6/1 | D6/2 r/2";
        band(s, I, intro, INTRO, 0.6f, true);
        band(s, V, verse, VERSE, 0.55f, true);
        band(s, C, chorus, CHORUS, 0.7f, true);
        mel(s, LD, I, hook, 0.7f, 0f, 0.3f, 0.22f, 0);
        mel(s, GL, I, hook, 0.22f, 0.3f, 0.35f, 0.1f, 12);
        mel(s, LD, V, mV, 0.6f, 0f, 0.3f, 0.2f, 0);
        mel(s, LD, C, mC, 0.75f, 0f, 0.3f, 0.22f, 0);
        mel(s, GL, C, mC, 0.25f, 0.3f, 0.35f, 0.1f, 12);
        // open sky: supersaw bed everywhere, harp-like clean arpeggios in the verse
        hold(s, SAW, I, intro, 66, 0.2f, 0f, 0.35f);
        hold(s, SAW, V, verse, 64, 0.18f, 0f, 0.35f);
        hold(s, SAW, C, chorus, 66, 0.3f, 0f, 0.35f);
        arp(s, HP, V, verse, 71, 38, "01230123", 0.5f, 0.22f, 2f, 0.35f, 0.15f);
        crashes(s, 28, C, C + 8);
        s.note(CHIME, C * 4, 2, 90, 0.3f, -0.3f, 0.5f);
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
                if (c.indexOf('/') > 0) c = c.substring(0, c.indexOf('/'));   // power chords sit on the chord root
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

    /**
     * Band stinger in the Rooftop Rush mould: a tom pickup, three power-chord hits (the last one held) with kick and
     * synth bass, a crash, and the lead ringing out. root: the power chord's MIDI root (E2..D3).
     */
    private static MusicSynth bandSting(float bpm, long seed, int root, String lead, float hand) {
        MusicSynth s = sting(bpm, 8, seed);
        s.masterTarget = 0.13f;
        s.handoffBeats = hand;
        float[] tp = {50, 45, 41, 38};
        for (int i = 0; i < 4; i++) s.note(TOM, i * 0.25f, 0.25f, tp[i], 0.7f, (i - 1.5f) * 0.2f, 0.2f);
        float[] at = {1f, 1.75f, 2.5f};
        for (float a : at)
            for (int side = -1; side <= 1; side += 2) {
                float len = a == 2.5f ? 3f : 0.6f;
                s.note(GT, a, len, root, 0.8f, side * 0.7f, 0.15f);
                s.note(GT, a, len, root + 7, 0.65f, side * 0.7f, 0.15f);
                s.note(GT, a, len, root + 12, 0.5f, side * 0.7f, 0.15f);
            }
        int b = root - 12;
        while (b < 28) b += 12;
        for (float a : at) { s.note(KICK, a, 1, 0, 1f, 0f, 0f); s.note(SB, a, a == 2.5f ? 2f : 0.5f, b, 0.8f, 0f, 0f); }
        s.note(SNR, 2.5f, 1, 0, 0.9f, 0f, 0.2f);
        s.note(CRASH, 2.5f, 4, 60, 0.9f, 0.2f, 0.3f);
        s.mel(LD, 1f, lead, 0.7f, 0f, 0.25f, 0.25f, 0);
        return s;
    }

    private static MusicSynth stSakura() {
        MusicSynth s = bandSting(172, 1, 40, "B5/.5 C#6/.25 E6/.75 _G#6/3", 5f);
        s.mel(GL, 1f, "B5/.5 C#6/.25 E6/.75 G#6/3", 0.25f, 0.3f, 0.3f, 0.1f, 12);
        s.note(CHIME, 2.5f, 2, 90, 0.3f, 0.3f, 0.5f);
        return s;
    }

    private static MusicSynth stCavern() {
        MusicSynth s = bandSting(150, 2, 50, "A5/.5 C6/.25 D6/.75 _F6/3", 5f);
        s.mel(CE, 2.5f, "D6/.25 F6/.25 A6/.25 C7/.25 E7/2", 0.4f, 0.3f, 0.5f, 0.3f, 0);
        return s;
    }

    private static MusicSynth stRiver() {
        MusicSynth s = bandSting(156, 3, 47, "F#5/.5 A5/.25 B5/.75 _D6/1.5 B5/1.5", 5f);
        s.mel(SH, 1f, "F#5/.5 A5/.25 B5/.75 D6/1.5 B5/1.5", 0.6f, -0.35f, 0.25f, 0f, 0);
        s.note(TAIKO, 2.5f, 2, 33, 0.8f, 0f, 0.3f);
        return s;
    }

    private static MusicSynth stSky() {
        MusicSynth s = bandSting(176, 4, 50, "A5/.5 D6/.25 E6/.75 _F#6/3", 5f);
        s.mel(SAW, 2.5f, "D4+A4+E5+F#5/3", 0.35f, 0f, 0.35f, 0f, 0);
        s.mel(GL, 1f, "A5/.5 D6/.25 E6/.75 F#6/3", 0.22f, 0.3f, 0.35f, 0.1f, 12);
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

    /** Game over: the band slows to a halt, C - D - E minor, the lead falling to the root. */
    private static MusicSynth stGameOver() {
        MusicSynth s = sting(100, 8, 6);
        s.masterTarget = 0.13f;
        s.handoffBeats = 7f;
        int[] roots = {48, 50, 40};
        float[] at = {0f, 1.5f, 3f}, len = {1.4f, 1.4f, 4f};
        for (int k = 0; k < 3; k++) {
            for (int side = -1; side <= 1; side += 2) {
                s.note(GT, at[k], len[k], roots[k], 0.75f, side * 0.7f, 0.2f);
                s.note(GT, at[k], len[k], roots[k] + 7, 0.6f, side * 0.7f, 0.2f);
                s.note(GT, at[k], len[k], roots[k] + 12, 0.45f, side * 0.7f, 0.2f);
            }
            s.note(KICK, at[k], 1, 0, 0.95f, 0f, 0f);
            s.note(SNR, at[k], 1, 0, 0.7f, 0f, 0.25f);
            s.note(SB, at[k], len[k], roots[k] - 12 < 28 ? roots[k] : roots[k] - 12, 0.75f, 0f, 0f);
        }
        s.note(CRASH, 3f, 4, 60, 0.75f, 0.2f, 0.3f);
        s.mel(LD, 0f, "G5/1.5 F#5/1.5 _E5/4", 0.65f, 0f, 0.3f, 0.25f, 0);
        s.mel(SAW, 3f, "E4+G4+B4/4", 0.25f, 0f, 0.35f, 0f, 0);
        return s;
    }
}
