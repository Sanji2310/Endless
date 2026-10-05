import com.endlessrush.core.*;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.ArrayList;

/**
 * Power-ups across the vehicle rides, headless (no device needed).
 *   java PowerSim [out.png]
 * Runs the game with the bots through run -> ore cart -> canoe -> glider -> run (Ride.Schedule, 700 m zones) once per
 * power-up, starting it 30 m before every hand-over and again in the middle of every ride, then checks the rules
 * (docs/PONGO_DESIGN.md section 8) and draws a timeline of every power-up's timer against the zones.
 */
public class PowerSim {
    static final float ZONE = 700f;
    static final String[] NAMES = {"Maneki Magnet", "Fever Star 2x", "Hayate Rocket", "Tobi Boots", "Kaze Board"};
    static final int[] TYPES = {Game.MAGNET, Game.X2, Game.JETPACK, Game.SNEAKERS, -1};
    static int fails;

    public static void main(String[] a) throws Exception {
        ArrayList<float[]>[] tl = new ArrayList[NAMES.length];
        for (int k = 0; k < NAMES.length; k++) tl[k] = run(k);
        draw(tl, new File(a.length > 0 ? a[0] : "preview/power_timeline.png"));
        System.out.println(fails == 0 ? "ALL POWER-UP CHECKS PASSED" : fails + " CHECK(S) FAILED");
        if (fails > 0) System.exit(1);
    }

    static void check(boolean ok, String what) {
        System.out.println((ok ? "ok   " : "FAIL ") + what);
        if (!ok) fails++;
    }

    /** One run with power-up k; returns samples {s, timer 0..1, vehicle, transition?1:0}. */
    static ArrayList<float[]> run(int k) {
        System.out.println("== " + NAMES[k]);
        Profile prof = new Profile(null);
        prof.keys = 99;
        prof.boards = 20;
        Game g = new Game(prof, new Game.Listener() {
            public void onSound(int id) {}
            public void onMessage(String t) {}
            public void onStateChanged(int st) {}
        });
        Ride.Schedule sch = new Ride.Schedule();
        sch.zoneLen = ZONE;
        g.ride.zones = sch;
        g.start();
        Preview.Autopilot bot = new Preview.Autopilot();
        float[] fire = {ZONE - 30, ZONE + 350, 2 * ZONE - 30, 2 * ZONE + 350, 3 * ZONE - 30, 3 * ZONE + 350, 4 * ZONE - 30};
        int next = 0;
        ArrayList<float[]> out = new ArrayList<float[]>();
        float boardAtBoarding = -1, boardHeld = -1;
        boolean ridePickupBad = false, magPulledOnRide = false, x2OnRide = true, x2Seen = false, boardOnRideRefused = true;
        boolean jetOnRide = false, sneakOnRide = false;
        int coinsStart = 0, lastVeh = Ride.NONE;
        java.util.Set<Game.Pickup> injected = java.util.Collections.newSetFromMap(new java.util.IdentityHashMap<Game.Pickup, Boolean>());
        java.util.Set<Game.Pickup> seen = java.util.Collections.newSetFromMap(new java.util.IdentityHashMap<Game.Pickup, Boolean>());
        int[] perZone = new int[8];
        for (int f = 0; f < 60 * 60 * 8 && g.s < 4 * ZONE + 120; f++) {
            if (g.state == Game.SAVE_ME) g.saveMe();
            if (g.state != Game.RUNNING) { g.update(1 / 60f); continue; }
            if (next < fire.length && g.s >= fire[next]) {
                boolean riding = g.ride.active();
                if (TYPES[k] >= 0) {
                    Game.Pickup p = new Game.Pickup();
                    p.type = TYPES[k];
                    p.x = g.x;
                    p.y = g.y + 0.6f;
                    p.s = g.s + 0.6f;
                    g.pickups.add(p);
                    injected.add(p);
                } else {
                    boolean ok = g.hoverboard();
                    if (riding && ok) boardOnRideRefused = false;
                }
                next++;
            }
            if (g.ride.riding()) g.ride.autopilot(); else bot.drive(g);
            g.update(1 / 60f);
            Ride r = g.ride;
            // hand-overs: what each power-up looks like just after she is aboard
            if (r.vehicle != lastVeh && !r.inTransition()) {
                if (lastVeh == Ride.NONE && r.vehicle != Ride.NONE) boardHeld = r.boardHold;
                lastVeh = r.vehicle;
            }
            if (r.active()) {
                if (g.jetT > 0 && r.riding()) jetOnRide = true;
                if (g.sneakT > 0 && r.riding()) sneakOnRide = true;
                if (g.boardT > 0) boardOnRideRefused = false;
                if (g.magT > 0) for (Game.Pickup p : g.pickups) if (p.pulled) magPulledOnRide = true;
                if (g.x2T > 0) { x2Seen = true; if (g.multiplier() % 2 != 0) x2OnRide = false; }
            }
            for (Game.Pickup p : g.pickups)
                if (!injected.contains(p) && seen.add(p) && p.type != Game.KEY && p.type != Game.COIN)
                    perZone[Math.min(7, (int) (p.s / ZONE))]++;
            for (Game.Pickup p : g.pickups)
                if ((p.type == Game.JETPACK || p.type == Game.SNEAKERS) && sch.vehicleAt(p.s) != Ride.NONE && TYPES[k] != p.type)
                    ridePickupBad = true;
            float tm;
            switch (k) {
                case 0: tm = g.magMax > 0 ? g.magT / g.magMax : 0; break;
                case 1: tm = g.x2Max > 0 ? g.x2T / g.x2Max : 0; break;
                case 2: tm = g.jetMax > 0 ? g.jetT / g.jetMax : 0; break;
                case 3: tm = g.sneakMax > 0 ? g.sneakT / g.sneakMax : 0; break;
                default: tm = Math.max(g.boardT, r.boardHold) / Game.BOARD_TIME * (r.boardHold > 0 ? -1 : 1); break;
            }
            if (f % 6 == 0) out.add(new float[]{g.s, tm, r.vehicle, r.inTransition() ? 1 : 0});
        }
        check(g.s >= 4 * ZONE, NAMES[k] + ": the run gets through cart, canoe, glider and back to running (" + (int) g.s + " m)");
        int most = 0;
        for (int z = 1; z < 4; z++) most = Math.max(most, perZone[z]);
        check(most <= 4, NAMES[k] + ": rides place four or fewer power-ups per zone (cart " + perZone[1] + ", canoe "
                + perZone[2] + ", glider " + perZone[3] + ")");
        check(!ridePickupBad, NAMES[k] + ": no Rocket or Boots pickup is ever placed inside a ride");
        switch (k) {
            case 0: check(magPulledOnRide, "Magnet keeps pulling coins while riding"); break;
            case 1: check(x2Seen && x2OnRide, "2x multiplier holds while riding"); break;
            case 2: check(!jetOnRide, "Rocket never flies on a ride (winds down before boarding, refused aboard)"); break;
            case 3: check(!sneakOnRide, "Boots never run on a ride (end before boarding, refused aboard)"); break;
            default:
                check(boardOnRideRefused, "Kaze Board can't be used on a ride");
                check(boardHeld > 0, "Kaze Board is stowed with its time when she boards (" + boardHeld + " s held)");
                boolean restored = false;
                for (float[] smp : out) if (smp[0] > 4 * ZONE && smp[0] < 4 * ZONE + 40 && smp[1] > 0) restored = true;
                check(restored, "Kaze Board comes back when she is on her feet after the glider");
        }
        return out;
    }

    // ------------------------------------------------------------------ chart

    static void draw(ArrayList<float[]>[] tl, File file) throws Exception {
        int W = 1400, row = 70, top = 70, H = top + row * tl.length + 60;
        float s1 = 4 * ZONE + 120;
        BufferedImage im = new BufferedImage(W, H, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = im.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setColor(new Color(0xFBF8F2));
        g.fillRect(0, 0, W, H);
        int x0 = 170, x1 = W - 20;
        Color[] zc = {new Color(0xF6DCE6), new Color(0xD9D2F2), new Color(0xCDEBF4), new Color(0xDDF0FF), new Color(0xF6DCE6)};
        String[] zn = {"running", "ore cart (cave)", "canoe (river)", "glider (sky)", "running"};
        for (int z = 0; z < 5; z++) {
            int a = x0 + (int) ((x1 - x0) * Math.min(1f, z * ZONE / s1)), b = x0 + (int) ((x1 - x0) * Math.min(1f, (z + 1) * ZONE / s1));
            g.setColor(zc[z]);
            g.fillRect(a, top - 30, b - a, row * tl.length + 30);
            g.setColor(new Color(0x4A4060));
            g.setFont(new Font("SansSerif", Font.BOLD, 15));
            g.drawString(zn[z], a + 8, top - 10);
        }
        g.setFont(new Font("SansSerif", Font.BOLD, 20));
        g.drawString("Power-ups across the rides: timer left (bar height) vs distance; striped = Kaze Board stowed", 20, 28);
        for (int k = 0; k < tl.length; k++) {
            int y = top + k * row;
            g.setColor(new Color(0x4A4060));
            g.setFont(new Font("SansSerif", Font.BOLD, 15));
            g.drawString(NAMES[k], 12, y + row / 2 + 5);
            g.setColor(new Color(0xE6DEEA));
            g.drawLine(x0, y + row - 6, x1, y + row - 6);
            for (float[] smp : tl[k]) {
                int px = x0 + (int) ((x1 - x0) * smp[0] / s1);
                float v = Math.abs(smp[1]);
                if (v <= 0) continue;
                int h = (int) ((row - 14) * Math.min(1f, v));
                g.setColor(smp[1] < 0 ? ((px / 4) % 2 == 0 ? new Color(0x8C7BC8) : new Color(0xC9BFF0)) :
                        new Color(new int[]{0xE0A030, 0xF06A8A, 0xE85A3A, 0x3AA0E8, 0x3AC08A}[k]));
                g.fillRect(px, y + row - 6 - h, 3, h);
            }
            if (k < tl.length) for (float[] smp : tl[k]) {
                if (smp[3] > 0) {
                    int px = x0 + (int) ((x1 - x0) * smp[0] / s1);
                    g.setColor(new Color(0x30, 0x28, 0x50, 60));
                    g.fillRect(px, y + 4, 3, row - 10);
                }
            }
        }
        g.setColor(new Color(0x4A4060));
        g.setFont(new Font("SansSerif", Font.PLAIN, 14));
        g.drawString("grey bands = boarding / hand-over set pieces. Each power-up is started 30 m before every hand-over and again mid-ride.",
                20, H - 20);
        file.getParentFile().mkdirs();
        ImageIO.write(im, "png", file);
        System.out.println("wrote " + file);
    }
}
