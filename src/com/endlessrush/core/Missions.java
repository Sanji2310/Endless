package com.endlessrush.core;

/** Three active missions; clearing a set raises the permanent score multiplier. */
public final class Missions {
    public static final int COINS_TOTAL = 0, COINS_RUN = 1, JUMPS = 2, ROLLS = 3, SCORE_RUN = 4,
            POWERUPS = 5, BOARDS = 6, DODGE = 7, STUMBLE_FREE = 8, KEYS = 9;
    private static final int TYPES = 10;

    public int multiplier = 1;
    public int set = 0;
    public final int[] type = new int[3], target = new int[3], progress = new int[3];
    public final boolean[] done = new boolean[3];

    public Missions() { newSet(); }

    public void newSet() {
        java.util.Random r = new java.util.Random(set * 7919L + 17);
        for (int i = 0; i < 3; i++) {
            int t;
            boolean dup;
            do {
                t = r.nextInt(TYPES);
                dup = false;
                for (int j = 0; j < i; j++) if (type[j] == t) dup = true;
            } while (dup);
            type[i] = t;
            target[i] = targetFor(t, set);
            progress[i] = 0;
            done[i] = false;
        }
    }

    private static int targetFor(int t, int lvl) {
        switch (t) {
            case COINS_TOTAL: return 300 + lvl * 250;
            case COINS_RUN: return 100 + lvl * 60;
            case JUMPS: return 20 + lvl * 10;
            case ROLLS: return 15 + lvl * 8;
            case SCORE_RUN: return 5000 + lvl * 4000;
            case POWERUPS: return 3 + lvl;
            case BOARDS: return 1 + lvl / 3;
            case DODGE: return 5 + lvl * 3;
            case STUMBLE_FREE: return 300 + lvl * 150;
            default: return 1 + lvl / 4;
        }
    }

    public String describe(int i) {
        int n = target[i];
        switch (type[i]) {
            case COINS_TOTAL: return "Collect " + n + " coins";
            case COINS_RUN: return "Collect " + n + " coins in one run";
            case JUMPS: return "Jump " + n + " times";
            case ROLLS: return "Roll " + n + " times";
            case SCORE_RUN: return "Score " + n + " points in one run";
            case POWERUPS: return "Pick up " + n + " power-ups";
            case BOARDS: return "Use " + n + " hoverboard" + (n > 1 ? "s" : "");
            case DODGE: return "Dodge " + n + " oncoming trains";
            case STUMBLE_FREE: return "Run " + n + "m without stumbling";
            default: return "Find " + n + " key" + (n > 1 ? "s" : "");
        }
    }

    /** Run-scoped missions reset their progress when a new run starts. */
    public static boolean perRun(int t) { return t == COINS_RUN || t == SCORE_RUN || t == STUMBLE_FREE; }

    public void startRun() {
        for (int i = 0; i < 3; i++) if (!done[i] && perRun(type[i])) progress[i] = 0;
    }

    /** Adds progress; returns index of a mission just completed or -1. */
    public int add(int t, int amount) {
        for (int i = 0; i < 3; i++) {
            if (done[i] || type[i] != t) continue;
            progress[i] += amount;
            if (progress[i] >= target[i]) { progress[i] = target[i]; done[i] = true; return i; }
        }
        return -1;
    }

    /** For "best in run" style missions. */
    public int setMax(int t, int value) {
        for (int i = 0; i < 3; i++) {
            if (done[i] || type[i] != t) continue;
            if (value > progress[i]) progress[i] = value;
            if (progress[i] >= target[i]) { progress[i] = target[i]; done[i] = true; return i; }
        }
        return -1;
    }

    public boolean allDone() { return done[0] && done[1] && done[2]; }

    /** Call when all done: bumps multiplier and rolls a fresh set. */
    public void advance() {
        if (multiplier < 30) multiplier++;
        set++;
        newSet();
    }

    void load(Profile.Store s) {
        multiplier = s.getInt("m_mult", 1);
        set = s.getInt("m_set", 0);
        newSet();
        for (int i = 0; i < 3; i++) {
            progress[i] = s.getInt("m_p" + i, 0);
            done[i] = s.getInt("m_d" + i, 0) == 1;
        }
    }

    void save(Profile.Store s) {
        s.putInt("m_mult", multiplier);
        s.putInt("m_set", set);
        for (int i = 0; i < 3; i++) {
            s.putInt("m_p" + i, progress[i]);
            s.putInt("m_d" + i, done[i] ? 1 : 0);
        }
    }
}
