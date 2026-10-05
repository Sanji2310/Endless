import com.pongo.core.MusicSynth;

/** Renders the vocal chops, shouts, whistle, 808 and scratch one after another (java VoxCheck out.wav). */
public final class VoxCheck {
    public static void main(String[] a) throws Exception {
        MusicSynth s = new MusicSynth(120, 4, 8, 7);
        s.humanize = 0;
        float b = 0;
        int[] shouts = {MusicSynth.HEY, MusicSynth.HO, MusicSynth.YEAH};
        for (int k : shouts) { s.note(k, b, 1, 0, 0.9f, 0, 0.15f); b += 2; }
        String ch = "E5/.5 G#5/.5 B5/.5 E6/.5 C#6/1 B5/1";
        s.mel(MusicSynth.VOX_AH, b, ch, 0.8f, 0, 0.2f, 0.1f, 0); b += 4;
        s.mel(MusicSynth.VOX_OO, b, ch, 0.8f, 0, 0.2f, 0.1f, 0); b += 4;
        s.mel(MusicSynth.VOX_EE, b, ch, 0.8f, 0, 0.2f, 0.1f, 0); b += 4;
        s.mel(MusicSynth.WHISTLE, b, "B5/.5 C#6/.5 E6/1 G#6/1.5 F#6/.5 E6/2", 0.8f, 0, 0.2f, 0.1f, 0); b += 6;
        for (int i = 0; i < 4; i++) s.note(MusicSynth.KICK808, b + i * 0.75f, 1, 28, 1f, 0, 0);
        b += 3;
        s.note(MusicSynth.SCRATCH, b, 0.5f, 0, 0.9f, 0, 0.1f);
        s.note(MusicSynth.SCRATCH, b + 1, 1f, 0, 0.9f, 0, 0.1f);
        short[] pcm = s.render();
        int peak = 0; for (short v : pcm) peak = Math.max(peak, Math.abs(v));
        System.out.println("peak " + 20 * Math.log10(peak / 32768.0));
        MusicSim.wav(a[0], pcm, 2);
    }
}
