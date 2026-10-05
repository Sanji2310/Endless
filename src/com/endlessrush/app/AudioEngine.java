package com.endlessrush.app;

import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;

import com.endlessrush.core.Game;
import com.pongo.core.CaveSounds;
import com.pongo.core.MusicPlayer;
import com.pongo.core.Soundtrack;
import com.pongo.core.Zones;

import java.io.File;

import java.util.ArrayList;
import java.util.Random;

/** Software stereo mixer: procedurally synthesised sound effects, the zone sounds (com.pongo.core.CaveSounds:
 *  one-shots as Game.SND_ZONE + id, and the cave ambience loop at `ambience`) and the soundtrack
 *  (com.pongo.core.MusicPlayer, cued from the game state by cue()). */
public final class AudioEngine implements Runnable {
    private static final int RATE = 22050;
    private static final int BUF = 1024;

    private final short[][] sfx = new short[Game.SOUND_COUNT][];
    /** Music sits this far under full scale so the sound effects stay on top. */
    private static final float MUSIC_GAIN = 0.5f;
    private MusicPlayer music;
    private File cacheDir;
    private int lastState = -1, lastZone = -1;
    private short[][] zone;
    private short[] enterTunnel, caveLoop;
    private int caveLoopPos;
    private float ambGain;
    /** Cave ambience volume 0..1 (Game.caveAmbience(), set every frame); the music dips under it. */
    public volatile float ambience;
    private final ArrayList<int[]> voices = new ArrayList<int[]>(); // {sound, pos}
    private volatile boolean running, paused;
    public volatile boolean soundOn = true, musicOn = true;
    private Thread thread;
    private AudioTrack track;
    private final Object lock = new Object();

    /** Where rendered music is cached (Context.getCacheDir()); call before start(). */
    public void setCacheDir(File dir) { cacheDir = dir; }

    public void start() {
        if (running) return;
        if (music == null) { music = new MusicPlayer(cacheDir); music.start(); }
        running = true;
        thread = new Thread(this, "audio");
        thread.start();
    }

    public void stop() {
        running = false;
        if (music != null) { music.stop(); music = null; }
        synchronized (lock) { lock.notifyAll(); }
    }

    public void setPaused(boolean p) {
        paused = p;
        synchronized (lock) { lock.notifyAll(); }
    }

    public void play(int id) {
        if (!soundOn || id < 0 || (id >= sfx.length && (id < Game.SND_ZONE || id > Game.SND_ENTER_TUNNEL))) return;
        synchronized (voices) {
            if (id == Game.SND_COIN) {
                // don't stack too many coin chimes
                int n = 0;
                for (int[] v : voices) if (v[0] == id) n++;
                if (n >= 3) return;
            }
            if (voices.size() < 12) voices.add(new int[]{id, 0});
        }
    }

    @Override
    public void run() {
        synth();
        int min = AudioTrack.getMinBufferSize(RATE, AudioFormat.CHANNEL_OUT_STEREO, AudioFormat.ENCODING_PCM_16BIT);
        try {
            track = new AudioTrack(AudioManager.STREAM_MUSIC, RATE, AudioFormat.CHANNEL_OUT_STEREO,
                    AudioFormat.ENCODING_PCM_16BIT, Math.max(min, BUF * 8), AudioTrack.MODE_STREAM);
            track.play();
        } catch (Exception e) {
            running = false;
            return;
        }
        short[] out = new short[BUF * 2];
        float[] mix = new float[BUF], ml = new float[BUF], mr = new float[BUF];
        boolean trackPaused = false;
        while (running) {
            if (paused) {
                if (!trackPaused) { track.pause(); trackPaused = true; }
                synchronized (lock) {
                    try { lock.wait(200); } catch (InterruptedException ignored) { }
                }
                continue;
            }
            if (trackPaused) { track.play(); trackPaused = false; }
            for (int i = 0; i < BUF; i++) { mix[i] = 0; ml[i] = 0; mr[i] = 0; }
            float a0 = ambGain, a1 = ambGain + (ambience - ambGain) * 0.08f;   // eased per buffer, no clicks
            ambGain = a1;
            if (soundOn && caveLoop != null && (a0 > 0.001f || a1 > 0.001f)) {
                for (int i = 0; i < BUF; i++) {
                    mix[i] += caveLoop[caveLoopPos] * 0.6f * (a0 + (a1 - a0) * i / BUF);
                    if (++caveLoopPos >= caveLoop.length) caveLoopPos = 0;
                }
            }
            double sfxEnergy = 0;
            synchronized (voices) {
                for (int v = voices.size() - 1; v >= 0; v--) {
                    int[] vc = voices.get(v);
                    short[] s = sound(vc[0]);
                    int n = Math.min(BUF, s.length - vc[1]);
                    for (int i = 0; i < n; i++) { float x = s[vc[1] + i]; mix[i] += x; sfxEnergy += x * x; }
                    vc[1] += n;
                    if (vc[1] >= s.length) voices.remove(v);
                }
            }
            MusicPlayer mp = music;
            if (musicOn && mp != null) {
                // the music dips under the sound effects and under the cave ambience
                float sfx = (float) Math.sqrt(sfxEnergy / BUF) / 32768f * 5f;
                mp.mix(ml, mr, BUF, sfx);
                for (int i = 0; i < BUF; i++) {
                    float g = MUSIC_GAIN * (1f - 0.45f * (a0 + (a1 - a0) * i / BUF));
                    ml[i] *= g; mr[i] *= g;
                }
            }
            for (int i = 0; i < BUF; i++) {
                out[2 * i] = clip(mix[i] + ml[i]);
                out[2 * i + 1] = clip(mix[i] + mr[i]);
            }
            track.write(out, 0, BUF * 2);
        }
        try { track.stop(); track.release(); } catch (Exception ignored) { }
    }

    private static short clip(float v) {
        float x = v / 32768f;
        x = x / (1 + Math.abs(x) * 0.6f); // soft clip
        return (short) (x * 32000);
    }

    /**
     * Picks the music for the game's state; call every frame (any thread). Menu theme on the menu; on a run, each
     * zone's stinger as its title card shows (or as the zone starts, for zones without a card) handing over to the
     * zone's theme; the game-over stinger at the end of a run, then the menu theme; quieter while paused or dying.
     */
    public void cue(Game g) {
        MusicPlayer mp = music;
        if (mp == null) return;
        int st = g.state;
        if (st == Game.MENU) {
            mp.theme(Soundtrack.MENU);
            mp.setLevel(1f);
            lastZone = -1;
        } else if (st == Game.GAME_OVER) {
            if (lastState != Game.GAME_OVER) mp.stinger(Soundtrack.ST_GAMEOVER, Soundtrack.MENU);
            mp.setLevel(0.8f);
            lastZone = -1;
        } else {
            Zones z = g.zones;
            int zone = z.cardZone >= 0 ? z.cardZone : z.zone;
            if (zone != lastZone) {
                mp.stinger(Soundtrack.stingerFor(zone), Soundtrack.themeFor(zone));
                lastZone = zone;
            }
            // load the next zone's theme well before its tunnel
            mp.prefetch(Soundtrack.themeFor(Zones.zoneAt(Zones.nextBoundary(g.s))));
            mp.setLevel(st == Game.PAUSED ? 0.45f : st == Game.DYING || st == Game.SAVE_ME ? 0.35f : 1f);
        }
        lastState = st;
    }

    private short[] sound(int id) {
        if (id < Game.SND_ZONE) return sfx[id];
        return id == Game.SND_ENTER_TUNNEL ? enterTunnel : zone[id - Game.SND_ZONE];
    }

    // ---------------------------------------------------------------- synthesis

    private static final Random R = new Random(7);

    private static float[] buf(float sec) { return new float[(int) (sec * RATE)]; }

    private static short[] pcm(float[] f, float vol) {
        short[] s = new short[f.length];
        for (int i = 0; i < f.length; i++) s[i] = (short) Math.max(-32767, Math.min(32767, f[i] * vol * 32767));
        return s;
    }

    private static void tone(float[] b, float start, float dur, float f0, float f1, float amp, int wave, float decay) {
        int s0 = (int) (start * RATE), n = (int) (dur * RATE);
        double ph = 0;
        for (int i = 0; i < n && s0 + i < b.length; i++) {
            float t = i / (float) n;
            float f = f0 + (f1 - f0) * t;
            ph += 2 * Math.PI * f / RATE;
            float v;
            switch (wave) {
                case 1: v = Math.sin(ph) > 0 ? 0.6f : -0.6f; break;             // square
                case 2: v = (float) (2 * ((ph / (2 * Math.PI)) % 1.0) - 1) * 0.7f; break; // saw
                case 3: v = (float) (Math.sin(ph) + 0.35 * Math.sin(ph * 2) + 0.2 * Math.sin(ph * 3)); break;
                default: v = (float) Math.sin(ph);
            }
            float env = (float) Math.exp(-t * decay) * Math.min(1, i / (RATE * 0.004f));
            b[s0 + i] += v * amp * env;
        }
    }

    private static void noise(float[] b, float start, float dur, float amp, float decay, float lp0, float lp1) {
        int s0 = (int) (start * RATE), n = (int) (dur * RATE);
        float y = 0;
        for (int i = 0; i < n && s0 + i < b.length; i++) {
            float t = i / (float) n;
            float a = lp0 + (lp1 - lp0) * t;
            y += (R.nextFloat() * 2 - 1 - y) * a;
            float env = (float) Math.exp(-t * decay) * Math.min(1, i / (RATE * 0.01f));
            b[s0 + i] += y * amp * env;
        }
    }

    private void synth() {
        float[] b;
        b = buf(0.22f); tone(b, 0, 0.06f, 1568, 1568, 0.35f, 3, 2); tone(b, 0.05f, 0.17f, 2093, 2093, 0.35f, 3, 5);
        sfx[Game.SND_COIN] = pcm(b, 0.55f);
        b = buf(0.25f); tone(b, 0, 0.22f, 280, 760, 0.4f, 0, 3); noise(b, 0, 0.2f, 0.4f, 4, 0.05f, 0.4f);
        sfx[Game.SND_JUMP] = pcm(b, 0.6f);
        b = buf(0.3f); noise(b, 0, 0.3f, 0.8f, 3, 0.5f, 0.04f); tone(b, 0, 0.25f, 500, 160, 0.25f, 0, 4);
        sfx[Game.SND_ROLL] = pcm(b, 0.6f);
        b = buf(0.14f); noise(b, 0, 0.14f, 0.7f, 3, 0.1f, 0.5f);
        sfx[Game.SND_SWIPE] = pcm(b, 0.45f);
        b = buf(0.3f); tone(b, 0, 0.25f, 120, 60, 0.9f, 0, 6); noise(b, 0, 0.15f, 0.6f, 8, 0.2f, 0.05f);
        tone(b, 0.02f, 0.2f, 420, 300, 0.2f, 1, 6);
        sfx[Game.SND_STUMBLE] = pcm(b, 0.8f);
        b = buf(0.8f); noise(b, 0, 0.8f, 1.0f, 5, 0.6f, 0.03f); tone(b, 0, 0.6f, 90, 35, 1.0f, 0, 5);
        sfx[Game.SND_CRASH] = pcm(b, 0.9f);
        b = buf(0.45f);
        float[] arp = {523, 659, 784, 1047, 1319};
        for (int i = 0; i < arp.length; i++) tone(b, i * 0.06f, 0.16f, arp[i], arp[i], 0.3f, 1, 5);
        sfx[Game.SND_POWER] = pcm(b, 0.6f);
        b = buf(0.5f); tone(b, 0, 0.5f, 200, 1100, 0.35f, 2, 2); noise(b, 0, 0.5f, 0.2f, 2, 0.02f, 0.3f);
        sfx[Game.SND_BOARD] = pcm(b, 0.6f);
        b = buf(0.6f); noise(b, 0, 0.5f, 0.9f, 6, 0.8f, 0.2f); tone(b, 0, 0.5f, 900, 120, 0.35f, 1, 3);
        sfx[Game.SND_BREAK] = pcm(b, 0.7f);
        b = buf(0.6f); tone(b, 0, 0.5f, 1760, 1760, 0.3f, 0, 5); tone(b, 0.08f, 0.5f, 2637, 2637, 0.3f, 0, 5);
        tone(b, 0.16f, 0.4f, 3520, 3520, 0.2f, 0, 5);
        sfx[Game.SND_KEY] = pcm(b, 0.6f);
        b = buf(0.9f);
        float[] fan = {523, 659, 784, 659, 1047};
        float[] fd = {0.1f, 0.1f, 0.1f, 0.1f, 0.45f};
        float t = 0;
        for (int i = 0; i < fan.length; i++) { tone(b, t, fd[i] + 0.05f, fan[i], fan[i], 0.3f, 1, 3); tone(b, t, fd[i] + 0.05f, fan[i] / 2, fan[i] / 2, 0.2f, 3, 3); t += fd[i]; }
        sfx[Game.SND_MISSION] = pcm(b, 0.6f);
        b = buf(0.1f); tone(b, 0, 0.1f, 140, 70, 0.6f, 0, 8); noise(b, 0, 0.06f, 0.3f, 8, 0.3f, 0.1f);
        sfx[Game.SND_LAND] = pcm(b, 0.5f);
        b = buf(0.9f); noise(b, 0, 0.9f, 0.9f, 2, 0.08f, 0.3f); tone(b, 0, 0.8f, 80, 160, 0.4f, 2, 2);
        sfx[Game.SND_JET] = pcm(b, 0.6f);
        b = buf(1.0f); tone(b, 0, 0.3f, 392, 370, 0.3f, 1, 1); tone(b, 0.3f, 0.3f, 370, 349, 0.3f, 1, 1);
        tone(b, 0.6f, 0.4f, 349, 300, 0.3f, 1, 2);
        sfx[Game.SND_CAUGHT] = pcm(b, 0.6f);
        zone = CaveSounds.buildAll();
        enterTunnel = CaveSounds.enterTunnel(zone);
        caveLoop = zone[CaveSounds.AMBIENCE];
    }
}
