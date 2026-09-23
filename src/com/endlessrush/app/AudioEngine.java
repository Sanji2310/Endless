package com.endlessrush.app;

import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;

import com.endlessrush.core.Game;

import java.util.ArrayList;
import java.util.Random;

/** Software mixer: procedurally synthesised sound effects plus a looping soundtrack. */
public final class AudioEngine implements Runnable {
    private static final int RATE = 22050;
    private static final int BUF = 1024;

    private final short[][] sfx = new short[Game.SOUND_COUNT][];
    private short[] music;
    private int musicPos;
    private final ArrayList<int[]> voices = new ArrayList<int[]>(); // {sound, pos}
    private volatile boolean running, paused;
    public volatile boolean soundOn = true, musicOn = true;
    private Thread thread;
    private AudioTrack track;
    private final Object lock = new Object();

    public void start() {
        if (running) return;
        running = true;
        thread = new Thread(this, "audio");
        thread.start();
    }

    public void stop() {
        running = false;
        synchronized (lock) { lock.notifyAll(); }
    }

    public void setPaused(boolean p) {
        paused = p;
        synchronized (lock) { lock.notifyAll(); }
    }

    public void play(int id) {
        if (!soundOn || id < 0 || id >= sfx.length) return;
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
        int min = AudioTrack.getMinBufferSize(RATE, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT);
        try {
            track = new AudioTrack(AudioManager.STREAM_MUSIC, RATE, AudioFormat.CHANNEL_OUT_MONO,
                    AudioFormat.ENCODING_PCM_16BIT, Math.max(min, BUF * 4), AudioTrack.MODE_STREAM);
            track.play();
        } catch (Exception e) {
            running = false;
            return;
        }
        short[] out = new short[BUF];
        float[] mix = new float[BUF];
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
            for (int i = 0; i < BUF; i++) mix[i] = 0;
            if (musicOn && music != null) {
                for (int i = 0; i < BUF; i++) {
                    mix[i] += music[musicPos] * 0.55f;
                    if (++musicPos >= music.length) musicPos = 0;
                }
            }
            synchronized (voices) {
                for (int v = voices.size() - 1; v >= 0; v--) {
                    int[] vc = voices.get(v);
                    short[] s = sfx[vc[0]];
                    int n = Math.min(BUF, s.length - vc[1]);
                    for (int i = 0; i < n; i++) mix[i] += s[vc[1] + i];
                    vc[1] += n;
                    if (vc[1] >= s.length) voices.remove(v);
                }
            }
            for (int i = 0; i < BUF; i++) {
                float x = mix[i] / 32768f;
                x = x / (1 + Math.abs(x) * 0.6f); // soft clip
                out[i] = (short) (x * 32000);
            }
            track.write(out, 0, BUF);
        }
        try { track.stop(); track.release(); } catch (Exception ignored) { }
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
        music = makeMusic();
    }

    /** 8-bar hip-hop-ish loop: kick, snare, hats, bass line and a plucked lead. */
    private static short[] makeMusic() {
        float bpm = 112;
        float beat = 60f / bpm;
        int bars = 8;
        float[] b = buf(bars * 4 * beat);
        float[][] chords = {{220, 261.6f, 329.6f}, {174.6f, 220, 261.6f}, {130.8f, 164.8f, 196}, {196, 246.9f, 293.7f}};
        float[] bassRoots = {110, 87.3f, 130.8f, 98};
        int[] bassPat = {1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0};
        int[] leadPat = {0, 2, 1, 2, 0, 2, 1, 2, 0, 1, 2, 1, 2, 1, 0, 2};
        for (int bar = 0; bar < bars; bar++) {
            float bs = bar * 4 * beat;
            int ci = bar % 4;
            for (int st = 0; st < 16; st++) {
                float ts = bs + st * beat / 4;
                if (st % 8 == 0 || st == 10) { tone(b, ts, 0.25f, 150, 45, 0.9f, 0, 7); }
                if (st == 4 || st == 12) { noise(b, ts, 0.2f, 0.55f, 9, 0.7f, 0.5f); tone(b, ts, 0.1f, 220, 180, 0.2f, 0, 10); }
                if (st % 2 == 0) noise(b, ts, 0.04f, st % 4 == 2 ? 0.16f : 0.09f, 12, 0.95f, 0.95f);
                if (bassPat[st] == 1) tone(b, ts, beat * 0.45f, bassRoots[ci], bassRoots[ci], 0.45f, 3, 3);
                if (bar >= 2 && st % 2 == 0) {
                    float f = chords[ci][leadPat[st]] * 2;
                    tone(b, ts, beat * 0.4f, f, f, 0.09f, 1, 7);
                }
            }
            for (int k = 0; k < 3; k++) tone(b, bs, 4 * beat, chords[ci][k], chords[ci][k], 0.035f, 2, 0.8f);
        }
        return pcm(b, 0.5f);
    }
}
