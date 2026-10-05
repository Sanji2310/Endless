import com.pongo.core.MusicSynth;

/** Renders one note per pitched instrument and measures its pitch (autocorrelation), to catch detuned models. */
public final class TuneCheck {
    public static void main(String[] a) throws Exception {
        java.lang.reflect.Method voice = MusicSynth.class.getDeclaredMethod("voice", int.class, float.class, int.class, float.class);
        voice.setAccessible(true);
        String[] names = {"PIANO","EPIANO","GLOCK","MUSICBOX","HARP","KOTO","SHAMISEN","PAD","STRINGS","FLUTE","SHAKU","LEAD","SUPERSAW","BASS","SUBBASS","SYNBASS","GUITAR","CLEANGTR","CHOIR","BRASS","CELESTA"};
        int[] test = {45, 57, 69, 81, 88};
        for (int inst = 0; inst < names.length; inst++) {
            StringBuilder sb = new StringBuilder(String.format("%-9s", names[inst]));
            for (int m : test) {
                if ((inst == 13 || inst == 14 || inst == 15) && m > 69) continue;
                if ((inst == 2 || inst == 3 || inst == 20) && m < 57) continue;
                MusicSynth s = new MusicSynth(120, 4, 1, 1);
                float[] w = (float[]) voice.invoke(s, inst, (float) m, MusicSynth.RATE / 2, 0.8f);
                int st = Math.min(w.length / 3, (int) (0.15f * MusicSynth.RATE)), n = Math.min(4096, w.length - st);
                float f = MusicSynth.hz(m);
                // autocorrelation peak near the expected period (+-1 semitone) with parabolic refinement
                int p0 = (int) (MusicSynth.RATE / (f * 1.06f)), p1 = (int) (MusicSynth.RATE / (f / 1.06f)) + 1;
                double best = -1e9; int bp = p0;
                double[] ac = new double[p1 + 2];
                for (int p = p0 - 1; p <= p1 + 1; p++) {
                    double c = 0;
                    for (int i = 0; i + p < n; i++) c += w[st + i] * w[st + i + p];
                    ac[p] = c;
                }
                for (int p = p0; p <= p1; p++) if (ac[p] > best) { best = ac[p]; bp = p; }
                double y0 = ac[bp - 1], y1 = ac[bp], y2 = ac[bp + 1];
                double per = bp + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2);
                double cents = 1200 * Math.log((MusicSynth.RATE / per) / f) / Math.log(2);
                sb.append(String.format("  m%d %+5.0fc", m, cents));
            }
            System.out.println(sb);
        }
    }
}
