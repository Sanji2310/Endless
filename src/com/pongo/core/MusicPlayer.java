package com.pongo.core;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;

/**
 * Plays the Soundtrack: renders pieces on a background thread (cached to disk so later launches load instantly),
 * crossfades between themes, plays stingers that hand over to the next theme on the beat they end, and ducks the
 * music under sound effects. Pure Java: the app's mixer calls mix() from its audio thread; the game calls the cue
 * methods from any thread.
 *
 *   theme(MENU)                      crossfade to a theme (about 1.5 s)
 *   stinger(ST_RIVER, RIVER)         stinger now, current theme fades out under it, RIVER starts at the stinger's
 *                                    handoff point
 *   setLevel(0.4f)                   overall music level (pause, save-me), eased
 *   prefetch(SKY)                    make sure a theme is rendered / loaded before it is needed
 */
public final class MusicPlayer {
    public static final int RATE = MusicSynth.RATE;
    /** Bump when the music changes so stale disk caches are re-rendered. */
    public static final int VERSION = 2;
    private static final int MAX_LOOPS_IN_RAM = 3;

    private final File cacheDir;
    private final short[][] pcm = new short[Soundtrack.COUNT][];
    private final float[] handoff = new float[Soundtrack.COUNT];
    private final long[] lastUse = new long[Soundtrack.COUNT];
    private final boolean[] wanted = new boolean[Soundtrack.COUNT];
    private final Object jobs = new Object();
    private volatile boolean running = true;
    private Thread worker;

    // ---- commands (any thread) -> audio thread
    private int cmdTheme = -1, cmdStinger = -1, cmdSerial;
    private float cmdLevel = 1f;

    // ---- audio thread state
    private int serialSeen;
    private int curId = -1, nextId = -1, stId = -1, waitId = -1;
    private int curPos, nextPos, stPos;
    private float curGain, curFade, nextGain, nextFade;     // fade = gain change per sample
    private float waitAt = -1f;                              // stinger sample position where waitId starts
    private float level = 1f, duck = 1f;

    public MusicPlayer(File cacheDir) {
        this.cacheDir = cacheDir;
    }

    /** Starts the render / load worker: the menu first, then the first zone and the stingers, then the rest. */
    public void start() {
        if (worker != null) return;
        int[] order = {Soundtrack.MENU, Soundtrack.ST_SAKURA, Soundtrack.SAKURA, Soundtrack.ST_GAMEOVER,
                Soundtrack.ST_CAVERN, Soundtrack.CAVERN, Soundtrack.ST_RIVER, Soundtrack.ST_SKY, Soundtrack.ST_ROOFTOPS,
                Soundtrack.RIVER, Soundtrack.SKY, Soundtrack.ROOFTOPS};
        for (int id : order) wanted[id] = true;
        worker = new Thread(new Runnable() {
            @Override public void run() { work(); }
        }, "music");
        worker.setPriority(Thread.MIN_PRIORITY);
        worker.start();
    }

    public void stop() {
        running = false;
        synchronized (jobs) { jobs.notifyAll(); }
    }

    // ------------------------------------------------------------------ cues

    public void theme(int id) {
        synchronized (this) {
            if (cmdTheme == id && cmdStinger < 0) return;
            cmdTheme = id; cmdStinger = -1; cmdSerial++;
        }
        prefetch(id);
    }

    public void stinger(int stinger, int then) {
        synchronized (this) { cmdTheme = then; cmdStinger = stinger; cmdSerial++; }
        prefetch(then);
    }

    public void setLevel(float l) { cmdLevel = l; }

    /** True once a piece is in memory (playable without a gap). */
    public boolean ready(int id) { return pcm[id] != null; }

    public void prefetch(int id) {
        if (id < 0) return;
        lastUse[id] = System.nanoTime();
        if (pcm[id] != null) return;
        synchronized (jobs) { wanted[id] = true; jobs.notifyAll(); }
    }

    // ------------------------------------------------------------------ worker

    private void work() {
        while (running) {
            int id = -1;
            synchronized (jobs) {
                // most recently asked for first, then the start-up order
                long best = -1;
                for (int k = 0; k < Soundtrack.COUNT; k++)
                    if (wanted[k] && pcm[k] == null && lastUse[k] > best) { best = lastUse[k]; id = k; }
                if (id < 0) {
                    for (int k = 0; k < Soundtrack.COUNT; k++) if (wanted[k]) { wanted[k] = false; }
                    try { jobs.wait(500); } catch (InterruptedException e) { return; }
                    continue;
                }
                wanted[id] = false;
            }
            short[] p = load(id);
            if (p == null) {
                p = Soundtrack.render(id);
                handoff[id] = Soundtrack.handoff(id);
                save(id, p);
            }
            pcm[id] = p;
            evict();
        }
    }

    /** Keeps at most MAX_LOOPS_IN_RAM loops (never the ones playing); stingers are small and stay. */
    private void evict() {
        int n = 0;
        for (int k = 0; k < Soundtrack.ST_SAKURA; k++) if (pcm[k] != null) n++;
        while (n > MAX_LOOPS_IN_RAM) {
            int old = -1;
            for (int k = 0; k < Soundtrack.ST_SAKURA; k++) {
                if (pcm[k] == null || k == curId || k == nextId || k == waitId || k == cmdTheme) continue;
                if (old < 0 || lastUse[k] < lastUse[old]) old = k;
            }
            if (old < 0 || cacheDir == null) return;   // without a disk cache, keep everything
            pcm[old] = null;
            n--;
        }
    }

    private File file(int id) { return new File(cacheDir, "music_v" + VERSION + "_" + Soundtrack.NAME[id] + ".pcm"); }

    private short[] load(int id) {
        if (cacheDir == null) return null;
        File f = file(id);
        if (!f.isFile() || f.length() < 8) return null;
        try (FileInputStream in = new FileInputStream(f); FileChannel ch = in.getChannel()) {
            ByteBuffer b = ByteBuffer.allocate((int) f.length()).order(ByteOrder.LITTLE_ENDIAN);
            while (b.hasRemaining() && ch.read(b) >= 0) { }
            b.flip();
            handoff[id] = b.getFloat();
            b.getInt();
            short[] s = new short[b.remaining() / 2];
            b.asShortBuffer().get(s);
            return s;
        } catch (Exception e) {
            return null;
        }
    }

    private void save(int id, short[] p) {
        if (cacheDir == null) return;
        File f = file(id), tmp = new File(cacheDir, f.getName() + ".tmp");
        try (FileOutputStream out = new FileOutputStream(tmp); FileChannel ch = out.getChannel()) {
            ByteBuffer b = ByteBuffer.allocate(8 + p.length * 2).order(ByteOrder.LITTLE_ENDIAN);
            b.putFloat(handoff[id]).putInt(p.length);
            b.asShortBuffer().put(p);
            b.position(b.capacity());
            b.flip();
            while (b.hasRemaining()) ch.write(b);
        } catch (Exception e) {
            tmp.delete();
            return;
        }
        if (!tmp.renameTo(f)) tmp.delete();
    }

    // ------------------------------------------------------------------ mixing (audio thread)

    /**
     * Adds n stereo frames of music into l / r (scaled to the 16-bit range like the mixer's other sources).
     * sfx: how busy the sound effects are right now (0..1); the music ducks under them.
     */
    public void mix(float[] l, float[] r, int n, float sfx) {
        takeCommands();
        // level and ducking are eased per buffer and interpolated per sample (no zipper noise)
        float lv0 = level, d0 = duck;
        level += (cmdLevel - level) * 0.12f;
        float dTarget = 1f - 0.4f * Math.min(1f, sfx);
        duck += (dTarget - duck) * (dTarget < duck ? 0.6f : 0.08f);
        // a theme waiting on a stinger starts at the handoff point (or as soon as it exists)
        if (waitId >= 0 && pcm[waitId] != null && (stId < 0 || stPos >= waitAt)) {
            startNext(waitId, 0.12f);
            waitId = -1;
        }
        for (int i = 0; i < n; i++) {
            float t = i / (float) n;
            float g = (lv0 + (level - lv0) * t) * (d0 + (duck - d0) * t);
            float sl = 0, sr = 0;
            if (curId >= 0) {
                short[] p = pcm[curId];
                if (p != null) {
                    sl += p[curPos] * curGain; sr += p[curPos + 1] * curGain;
                    curPos += 2; if (curPos >= p.length) curPos = 0;
                }
                curGain += curFade;
                if (curGain <= 0f) { curGain = 0f; curId = -1; }
                else if (curGain > 1f) { curGain = 1f; curFade = 0f; }
            }
            if (nextId >= 0) {
                short[] p = pcm[nextId];
                if (p != null) {
                    sl += p[nextPos] * nextGain; sr += p[nextPos + 1] * nextGain;
                    nextPos += 2; if (nextPos >= p.length) nextPos = 0;
                }
                nextGain = Math.min(1f, nextGain + nextFade);
            }
            if (stId >= 0) {
                short[] p = pcm[stId];
                if (p != null && stPos < p.length) {
                    sl += p[stPos] * 0.95f; sr += p[stPos + 1] * 0.95f;
                    stPos += 2;
                } else stId = -1;
            }
            l[i] += sl * g;
            r[i] += sr * g;
        }
        // the incoming deck becomes the current one once it is fully in and the old one is gone
        if (nextId >= 0 && nextGain >= 1f && curId < 0) {
            curId = nextId; curPos = nextPos; curGain = 1f; curFade = 0f;
            nextId = -1;
        }
    }

    private void takeCommands() {
        int theme, sting, serial;
        synchronized (this) { theme = cmdTheme; sting = cmdStinger; serial = cmdSerial; }
        if (serial == serialSeen) return;
        serialSeen = serial;
        if (sting >= 0) {
            lastUse[sting] = System.nanoTime();
            if (pcm[sting] != null) {
                stId = sting; stPos = 0;
                waitAt = handoff[sting] * RATE * 2;
                fadeOutAll(0.7f);
                waitId = theme;
                return;
            }
            // stinger not ready yet: just crossfade
        }
        if (theme == playingTheme()) return;
        fadeOutAll(1.5f);
        waitId = theme;
        stId = -1;
        waitAt = -1f;
    }

    private int playingTheme() {
        if (waitId >= 0) return waitId;
        if (nextId >= 0) return nextId;
        return curFade < 0f ? -1 : curId;
    }

    /** Fades whatever is playing out over `sec` seconds; the incoming deck (if any) becomes the outgoing one. */
    private void fadeOutAll(float sec) {
        if (nextId >= 0) {
            if (curId < 0 || nextGain >= curGain) { curId = nextId; curPos = nextPos; curGain = nextGain; }
            nextId = -1;
        }
        if (curId >= 0) curFade = -Math.max(curGain, 0.01f) / (sec * RATE);
    }

    private void startNext(int id, float fadeSec) {
        lastUse[id] = System.nanoTime();
        if (curId < 0 || curFade < 0f) {
            if (curId < 0) {   // nothing to cross: straight in
                curId = id; curPos = 0; curGain = 0f; curFade = 1f / (fadeSec * RATE);
                return;
            }
            nextId = id; nextPos = 0; nextGain = 0f; nextFade = 1f / (fadeSec * RATE);
            return;
        }
        curFade = -1f / (1.5f * RATE);
        nextId = id; nextPos = 0; nextGain = 0f; nextFade = 1f / (Math.max(fadeSec, 1.2f) * RATE);
    }
}
