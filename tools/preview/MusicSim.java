import com.pongo.core.MusicSynth;
import com.pongo.core.Soundtrack;

import java.io.DataOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;

/**
 * Renders the soundtrack to WAV files for listening outside the game.
 *   java MusicSim <outDir> [id ...]      (ids: Soundtrack ids or names; default all; "loop2" plays loops twice)
 */
public final class MusicSim {
    public static void main(String[] a) throws IOException {
        String dir = a.length > 0 ? a[0] : "build/music";
        new java.io.File(dir).mkdirs();
        MusicSynth.logNotes = true;
        boolean twice = false;
        java.util.List<Integer> ids = new java.util.ArrayList<>();
        for (int i = 1; i < a.length; i++) {
            if (a[i].equals("loop2")) { twice = true; continue; }
            if (a[i].startsWith("solo=")) { MusicSynth.solo = Integer.parseInt(a[i].substring(5)); continue; }
            int id = -1;
            for (int k = 0; k < Soundtrack.COUNT; k++) if (Soundtrack.NAME[k].startsWith(a[i])) id = k;
            if (id < 0) id = Integer.parseInt(a[i]);
            ids.add(id);
        }
        if (ids.isEmpty()) for (int k = 0; k < Soundtrack.COUNT; k++) ids.add(k);
        for (int id : ids) {
            long t0 = System.nanoTime();
            short[] pcm = Soundtrack.render(id);
            long ms = (System.nanoTime() - t0) / 1000000;
            int frames = pcm.length / 2;
            int peak = 0; double ss = 0;
            for (short v : pcm) { peak = Math.max(peak, Math.abs(v)); ss += v * (double) v; }
            System.out.printf("%-24s %6.1f s  rendered in %5d ms  peak %5.1f dBFS  rms %5.1f dBFS  handoff %.2f s%n",
                    Soundtrack.NAME[id], frames / (float) MusicSynth.RATE, ms, 20 * Math.log10(peak / 32768.0),
                    10 * Math.log10(ss / pcm.length / (32768.0 * 32768.0)), Soundtrack.handoff(id));
            MusicSynth sy = Soundtrack.lastSynth;
            double tot = 0;
            for (double e : sy.energy) tot += e;
            StringBuilder sb = new StringBuilder("    stems dB:");
            for (int k = 0; k < 64; k++) if (sy.energy[k] > 0) sb.append(String.format(" %d:%.1f", k, 10 * Math.log10(sy.energy[k] / tot)));
            System.out.println(sb);
            int clicks = 0;
            for (int i = 2; i < pcm.length; i += 2) if (Math.abs(pcm[i] - pcm[i - 2]) > 12000) clicks++;
            if (Soundtrack.isLoop(id)) {
                int n = pcm.length;
                System.out.printf("    seam jump L %d R %d   clicks %d%n", Math.abs(pcm[0] - pcm[n - 2]), Math.abs(pcm[1] - pcm[n - 1]), clicks);
            }
            clashes(sy);
            quality(pcm);
            short[] out = pcm;
            if (twice && Soundtrack.isLoop(id)) {
                out = new short[pcm.length * 2];
                System.arraycopy(pcm, 0, out, 0, pcm.length);
                System.arraycopy(pcm, 0, out, pcm.length, pcm.length);
            }
            wav(dir + "/" + Soundtrack.NAME[id] + ".wav", out, 2);
        }
    }

    /** Pitched instruments only (drums are >= 40). Flags sustained minor-2nd / major-7th-against-root clashes. */
    static void clashes(MusicSynth sy) {
        java.util.List<float[]> ns = new java.util.ArrayList<>();
        for (float[] n : sy.log) if (n[0] < 40 && n[3] >= 50) ns.add(n);
        int total = 0;
        StringBuilder sb = new StringBuilder();
        float end = sy.loopLen / sy.spb;
        for (float t = 0; t < end; t += 0.25f) {
            java.util.List<float[]> on = new java.util.ArrayList<>();
            for (float[] n : ns) if (n[1] <= t + 1e-3f && n[1] + n[2] > t + 0.12f) on.add(n);
            for (int i = 0; i < on.size(); i++)
                for (int j = i + 1; j < on.size(); j++) {
                    float[] a = on.get(i), b = on.get(j);
                    int d = Math.abs(Math.round(a[3]) - Math.round(b[3]));
                    // a semitone (or a 9th = semitone + octave) between two notes that have both been sounding a while
                    boolean old = a[1] < t - 0.01f && b[1] < t - 0.01f;
                    if (d % 12 == 1) {
                        boolean fresh = Math.abs(a[1] - t) < 1e-3f || Math.abs(b[1] - t) < 1e-3f;
                        if (!fresh || old) continue;
                        float shorter = Math.min(a[1] + a[2], b[1] + b[2]) - t;
                        if (shorter < 0.4f) continue;   // passing tone
                        total++;
                        if (total <= 14) sb.append(String.format("      bar %.0f beat %.2f: inst %d %s vs inst %d %s%n",
                                Math.floor(t / sy.beatsPerBar) + 1, t % sy.beatsPerBar, (int) a[0], name(a[3]), (int) b[0], name(b[3])));
                    }
                }
        }
        System.out.println("    semitone/minor-9th clashes held >= 0.4 beat: " + total);
        System.out.print(sb);
    }

    static String name(float m) {
        String[] n = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
        int k = Math.round(m);
        return n[k % 12] + (k / 12 - 1);
    }

    /** Clipping, brightness (share of energy above 4.5 kHz), and the loudest transient compared to its neighbourhood. */
    static void quality(short[] pcm) {
        int clip = 0;
        double hi = 0, all = 0;
        float lp = 0;
        for (int i = 0; i < pcm.length; i += 2) {
            float x = (pcm[i] + pcm[i + 1]) / 65536f;
            if (Math.abs(pcm[i]) > 32000 || Math.abs(pcm[i + 1]) > 32000) clip++;
            lp += (x - lp) * 0.72f;   // ~4.5 kHz one-pole
            float h = x - lp;
            hi += h * h; all += x * x;
        }
        System.out.printf("    clipped samples %d   bright share %.1f%%%n", clip, 100 * hi / all);
    }

    static void wav(String path, short[] pcm, int ch) throws IOException {
        try (DataOutputStream o = new DataOutputStream(new FileOutputStream(path))) {
            int rate = MusicSynth.RATE, bytes = pcm.length * 2;
            o.writeBytes("RIFF"); le32(o, 36 + bytes); o.writeBytes("WAVEfmt ");
            le32(o, 16); le16(o, 1); le16(o, ch); le32(o, rate); le32(o, rate * ch * 2); le16(o, ch * 2); le16(o, 16);
            o.writeBytes("data"); le32(o, bytes);
            byte[] b = new byte[bytes];
            for (int i = 0; i < pcm.length; i++) { b[2 * i] = (byte) pcm[i]; b[2 * i + 1] = (byte) (pcm[i] >> 8); }
            o.write(b);
        }
    }

    static void le32(DataOutputStream o, int v) throws IOException { o.write(v); o.write(v >> 8); o.write(v >> 16); o.write(v >> 24); }
    static void le16(DataOutputStream o, int v) throws IOException { o.write(v); o.write(v >> 8); }
}
