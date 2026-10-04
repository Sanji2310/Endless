import com.pongo.core.*;

import java.io.*;

/**
 * Zone transition harness (no device needed).
 *   java ZoneSim test                         -> runs through Sakura Line -> Crystal Cavern and checks the schedule
 *   java ZoneSim sfx <dir>                    -> writes every CaveSounds sound as <dir>/<name>.wav
 *   java ZoneSim track <out.wav> <d0> <speed> <seconds>
 *                                             -> the soundtrack of a run from distance d0 at a constant speed, mixed
 *                                                from the Zones events exactly as the game would trigger them
 */
public class ZoneSim {
    public static void main(String[] a) throws Exception {
        switch (a.length > 0 ? a[0] : "test") {
            case "sfx": sfx(new File(a[1])); break;
            case "track": track(new File(a[1]), Float.parseFloat(a[2]), Float.parseFloat(a[3]), Float.parseFloat(a[4])); break;
            default: test();
        }
    }

    static void check(boolean ok, String what) {
        if (!ok) throw new AssertionError(what);
        System.out.println("ok   " + what);
    }

    static void test() {
        Zones z = new Zones();
        float b = Zones.ZONE_LEN;              // Sakura Line -> Crystal Cavern boundary (the tunnel mouth)
        float dt = 1f / 60f, speed = 16f;
        int seen = 0;
        float portalT = -1, cardEnd = -1, lastBlend = 0;
        boolean monotonic = true, invulInTunnel = true, invulBefore = false;
        RenderFrame f = new RenderFrame();
        for (float d = b - 200f, t = 0; d < b + 100f; d += speed * dt, t += dt) {
            int ev = z.update(d, dt);
            seen |= ev;
            if ((ev & Zones.EV_PORTAL) != 0) portalT = t;
            if (portalT >= 0 && cardEnd < 0 && z.cardTime < 0) cardEnd = t;
            if (d < b && z.blend + 1e-4f < lastBlend) monotonic = false;
            lastBlend = d < b ? z.blend : lastBlend;
            if (d > Zones.portalAt(b) && d < b && !z.invulnerable) invulInTunnel = false;
            if (d < Zones.portalAt(b) - 2f && z.invulnerable) invulBefore = true;
            if (Math.abs(d - (b - 1f)) < speed * dt) {
                RenderFrame g = new RenderFrame();
                z.apply(g, 0, 1.5f, -d);
                check(g.lamp[3] > 10f, "Hotaru Lamp on before the mouth (radius " + g.lamp[3] + ")");
                float[] cs = Zones.PALETTE[Zones.CAVERN].shade;
                check(Math.abs(g.shadeCol[0] - cs[0]) < 0.05f && Math.abs(g.shadeCol[2] - cs[2]) < 0.05f,
                      "cave lavender shadow band in the tunnel (" + g.shadeCol[0] + ", " + g.shadeCol[2] + ")");
            }
        }
        check((seen & Zones.EV_APPROACH) != 0, "approach event");
        check((seen & Zones.EV_PORTAL) != 0, "portal event");
        check((seen & Zones.EV_BOARD) != 0, "ore cart boarding event");
        check((seen & Zones.EV_MOUTH) != 0, "mouth event (cave starts)");
        check(z.zone == Zones.CAVERN, "zone is Crystal Cavern after the boundary");
        check(monotonic, "palette blend only rises on the way in");
        check(invulInTunnel, "invulnerable from portal to mouth");
        check(!invulBefore, "vulnerable in the approach");
        check(Math.abs(z.blend - 1f) < 1e-4f, "full cave palette inside");
        float cardDur = cardEnd - portalT;
        check(cardDur > 2.8f && cardDur < 3.2f, "title card shows for " + cardDur + " s");
        // the way out of the cavern: the same set piece turned round, back onto the Sakura Line
        float b2 = 2 * Zones.ZONE_LEN;
        check(Zones.exitAt(b2) && !Zones.exitAt(b), "the second boundary leaves the cavern");
        Zones z2 = new Zones();
        int seen2 = 0;
        float leaveD = -1, cardD = -1;
        boolean invul2 = true;
        for (float d = b2 - 200f; d < b2 + 100f; d += speed * dt) {
            int ev = z2.update(d, dt);
            seen2 |= ev;
            if ((ev & Zones.EV_LEAVE) != 0) leaveD = d;
            if (cardD < 0 && z2.cardTime >= 0) cardD = d;
            if (d > Zones.portalAt(b2) && d < b2 && !z2.invulnerable) invul2 = false;
        }
        check((seen2 & Zones.EV_BOARD) == 0, "no boarding on the way out");
        check(Math.abs(leaveD - Zones.leaveAt(b2)) < 1f, "leave the cart in the lining (" + leaveD + ")");
        check(Math.abs(cardD - b2) < 1f && z2.zone == Zones.SAKURA, "Sakura Line card coming out of the portal");
        check(invul2, "invulnerable through the lining on the way out");
        check(z2.blend < 1e-4f, "cave palette gone outside");
        check(Zones.zoneAt(3 * Zones.ZONE_LEN + 1f) == Zones.CAVERN, "the cycle comes back to the cavern");
        // the city world and track hand over to the set pieces at segment seams
        check(Zones.cityWorldAt(b - 73f) && !Zones.cityWorldAt(b - 72f), "city scenery stops at the approach");
        check(Zones.cityTrackAt(b - 25f) && !Zones.cityTrackAt(b - 24f), "city track stops at the portal");
        check(!Zones.cityTrackAt(b2 - 1f) && Zones.cityTrackAt(b2), "city track resumes at the portal out");
        check(!Zones.cityWorldAt(b2 + 47f) && Zones.cityWorldAt(b2 + 48f), "city scenery resumes after the cutting");
        check(Zones.cityWorldAt(10f), "the run starts on the Sakura Line");
        check(Zones.ZONE_LEN % Zones.SEG == 0, "zones are whole segments");
        check(Zones.skipSafe(b - 90f) == b - 90f && Zones.skipSafe(b - 50f) == Zones.safeTo(b)
                && Zones.skipSafe(b2 + 10f) == Zones.safeTo(b2), "no obstacle patterns start in the set pieces");
        int[] kit = new int[3];
        Zones.caveKit(0, kit);
        check(kit[0] == 1, "first cave segment uses shell 1 (matches the tunnel mouth seam)");
        System.out.println("all zone checks passed");
    }

    static void sfx(File dir) throws IOException {
        dir.mkdirs();
        for (int i = 0; i < CaveSounds.COUNT; i++) {
            short[] s = CaveSounds.build(i);
            writeWav(new File(dir, CaveSounds.NAME[i] + ".wav"), s);
            System.out.printf("%-16s %5.2f s%s%n", CaveSounds.NAME[i], s.length / (float) CaveSounds.RATE, CaveSounds.LOOP[i] ? " loop" : "");
        }
    }

    /** Mixes the soundtrack of a run segment the way the game would: loops by zone and riding state, one-shots on events. */
    static void track(File out, float d0, float speed, float seconds) throws IOException {
        short[][] snd = CaveSounds.buildAll();
        int R = CaveSounds.RATE, n = (int) (seconds * R);
        float[] mix = new float[n];
        Zones z = new Zones();
        float dt = 1f / 60f;
        float riding = 0f, nextJoint = -1f;
        float[] ambGain = new float[n];
        // city bed: a soft wind so the change into the tunnel is audible (the Sakura Line ambience is not in this kit)
        java.util.Random r = new java.util.Random(3);
        float lp = 0;
        float[] wind = new float[n];
        for (int i = 0; i < n; i++) { lp += ((r.nextFloat() * 2 - 1) - lp) * 0.05f; wind[i] = lp * 0.5f; }
        z.update(d0, dt);
        for (float t = 0; t < seconds; t += dt) {
            float d = d0 + speed * t;
            int ev = z.update(d, dt);
            int i0 = (int) (t * R);
            if ((ev & Zones.EV_PORTAL) != 0) {
                add(mix, snd[CaveSounds.TUNNEL_WHOOSH], i0, 0.9f);
                add(mix, snd[CaveSounds.STING], i0 + (int) (0.15f * R), 0.6f);
                add(mix, snd[CaveSounds.LAMP_ON], i0 + (int) (0.4f * R), 0.5f);
            }
            if ((ev & Zones.EV_BOARD) != 0) { add(mix, snd[CaveSounds.CART_BOARD], i0, 0.9f); riding = t; nextJoint = d + 6f; }
            if (riding > 0 && nextJoint > 0 && d >= nextJoint) { add(mix, snd[CaveSounds.CART_CLACK], i0, 0.35f); nextJoint += 6f; }
            for (int i = i0; i < Math.min(n, (int) ((t + dt) * R)); i++) ambGain[i] = z.blend;
        }
        // loops: wind fades out, cave ambience fades in with the palette blend, cart rumble from boarding
        short[] amb = snd[CaveSounds.AMBIENCE], rum = snd[CaveSounds.CART_RUMBLE];
        for (int i = 0; i < n; i++) {
            float g = ambGain[i];
            mix[i] += wind[i] * (1 - g) * 0.8f + amb[i % amb.length] / 32768f * g * 0.55f;
            if (riding > 0 && i >= riding * R) mix[i] += rum[i % rum.length] / 32768f * 0.45f * Math.min(1f, (i - riding * R) / (0.3f * R));
        }
        // a few cave details once inside
        for (float t : new float[]{3.6f, 4.9f, 5.7f}) if (t < seconds) add(mix, snd[CaveSounds.DRIP], (int) (t * R), 0.4f);
        if (seconds > 4.4f) add(mix, snd[CaveSounds.CRYSTAL_CHIME], (int) (4.4f * R), 0.3f);
        if (seconds > 5.2f) add(mix, snd[CaveSounds.BAT_SQUEAK], (int) (5.2f * R), 0.35f);
        float peak = 1e-6f;
        for (float v : mix) peak = Math.max(peak, Math.abs(v));
        short[] s = new short[n];
        for (int i = 0; i < n; i++) s[i] = (short) (mix[i] / Math.max(1f, peak) * 30000f);
        writeWav(out, s);
        System.out.println("wrote " + out + " (" + seconds + " s from d=" + d0 + " at " + speed + " m/s)");
    }

    static void add(float[] mix, short[] s, int at, float g) {
        for (int i = 0; i < s.length && at + i < mix.length; i++) if (at + i >= 0) mix[at + i] += s[i] / 32768f * g;
    }

    static void writeWav(File f, short[] s) throws IOException {
        int R = CaveSounds.RATE;
        try (DataOutputStream o = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(f)))) {
            o.writeBytes("RIFF"); o.writeInt(Integer.reverseBytes(36 + s.length * 2)); o.writeBytes("WAVEfmt ");
            o.writeInt(Integer.reverseBytes(16)); o.writeShort(Short.reverseBytes((short) 1)); o.writeShort(Short.reverseBytes((short) 1));
            o.writeInt(Integer.reverseBytes(R)); o.writeInt(Integer.reverseBytes(R * 2));
            o.writeShort(Short.reverseBytes((short) 2)); o.writeShort(Short.reverseBytes((short) 16));
            o.writeBytes("data"); o.writeInt(Integer.reverseBytes(s.length * 2));
            for (short v : s) o.writeShort(Short.reverseBytes(v));
        }
    }
}
