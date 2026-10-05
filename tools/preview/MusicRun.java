import com.pongo.core.MusicPlayer;
import com.pongo.core.MusicSynth;
import com.pongo.core.Soundtrack;

/**
 * Plays a scripted run through MusicPlayer the way AudioEngine.cue() drives it and writes the mix to a WAV:
 *   menu -> run starts (Sakura sting + theme) -> tunnel into the cave (cave sting + theme) -> crash, save-me dip
 *   -> game over sting -> menu.   java MusicRun <out.wav> [cacheDir]
 * Also prints the loudest step between adjacent samples around every cue (a click check for the crossfades).
 */
public final class MusicRun {
    public static void main(String[] a) throws Exception {
        java.io.File cache = new java.io.File(a.length > 1 ? a[1] : "build/music-cache");
        cache.mkdirs();
        MusicPlayer mp = new MusicPlayer(cache);
        mp.start();
        int[] need = {Soundtrack.MENU, Soundtrack.SAKURA, Soundtrack.CAVERN, Soundtrack.ST_SAKURA, Soundtrack.ST_CAVERN, Soundtrack.ST_GAMEOVER};
        for (int id : need) mp.prefetch(id);
        for (int id : need) while (!mp.ready(id)) Thread.sleep(50);
        // {time s, action, arg}: 0 theme, 1 stinger(arg -> theme arg2), 2 level
        float[][] script = {
                {0f, 0, Soundtrack.MENU, 0}, {8f, 1, Soundtrack.ST_SAKURA, Soundtrack.SAKURA},
                {40f, 1, Soundtrack.ST_CAVERN, Soundtrack.CAVERN}, {66f, 2, 0.35f, 0},
                {70f, 1, Soundtrack.ST_GAMEOVER, Soundtrack.MENU}, {70f, 2, 0.8f, 0}};
        float total = 86f;
        int buf = 1024, frames = (int) (total * MusicSynth.RATE);
        short[] out = new short[frames * 2];
        float[] l = new float[buf], r = new float[buf];
        int si = 0;
        for (int f = 0; f < frames; f += buf) {
            float t = f / (float) MusicSynth.RATE;
            while (si < script.length && script[si][0] <= t) {
                float[] c = script[si++];
                if (c[1] == 0) mp.theme((int) c[2]);
                else if (c[1] == 1) mp.stinger((int) c[2], (int) c[3]);
                else mp.setLevel(c[2]);
            }
            java.util.Arrays.fill(l, 0); java.util.Arrays.fill(r, 0);
            // a burst of sound effects at 20 s and 50 s to hear the ducking
            float sfx = (t > 20 && t < 21) || (t > 50 && t < 50.4f) ? 0.8f : 0f;
            mp.mix(l, r, buf, sfx);
            for (int i = 0; i < buf && f + i < frames; i++) {
                out[2 * (f + i)] = (short) Math.max(-32767, Math.min(32767, l[i]));
                out[2 * (f + i) + 1] = (short) Math.max(-32767, Math.min(32767, r[i]));
            }
        }
        mp.stop();
        for (float[] c : script) {
            int c0 = (int) (c[0] * MusicSynth.RATE);
            int worst = 0;
            for (int i = Math.max(1, c0 - 2205); i < Math.min(frames, c0 + 6 * MusicSynth.RATE); i++)
                worst = Math.max(worst, Math.abs(out[2 * i] - out[2 * i - 2]));
            System.out.printf("cue at %5.1f s: largest sample step in the next 6 s = %d%n", c[0], worst);
        }
        MusicSim.wav(a[0], out, 2);
    }
}
