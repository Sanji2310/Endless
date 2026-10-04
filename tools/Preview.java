import com.endlessrush.core.*;

/**
 * Headless autopilot runs to sanity-check level generation, and the look-ahead bot PongoPreview drives.
 * (Everything visual goes through the toon renderer: ./preview.sh pongo / zones.)
 *
 * Usage: java Preview sim [runs]
 */
public class Preview {
    public static void main(String[] args) {
        int runs = 20;
        for (int i = 0; i < args.length; i++) if (args[i].equals("sim") && i + 1 < args.length) runs = Integer.parseInt(args[i + 1]);
        simulate(runs);
    }

    static void simulate(int runs) {
        Profile prof = new Profile(null);
        final int[] deaths = new int[2];
        double total = 0;
        for (int r = 0; r < runs; r++) {
            final Game[] ref = new Game[1];
            Game g = new Game(prof, new Game.Listener() {
                public void onSound(int id) {}
                public void onMessage(String t) {}
                public void onStateChanged(int st) {}
            });
            ref[0] = g;
            prof.keys = 0; prof.boards = 0;
            g.start();
            Autopilot ai = new Autopilot();
            int f = 0;
            while (g.state == Game.RUNNING && f < 60 * 60 * 6) {
                ai.drive(g);
                g.update(1 / 60f);
                f++;
            }
            total += g.s;
            String cause = "alive";
            if (g.state == Game.DYING) {
                deaths[g.deathKind]++;
                cause = g.deathKind == 0 ? "crash" : "caught";
                String what = "";
                for (Game.Obstacle o : g.obstacles) {
                    if (Math.abs(o.x - g.x) < 1.5f && g.s + 1 >= o.s0 && g.s - 1 <= o.s0 + o.len)
                        what += " type=" + o.type + (o.moving ? "(moving)" : "") + " lane=" + o.lane;
                }
                cause += what;
            }
            System.out.printf("run %2d: dist %6.0f  score %7d  coins %4d  t=%5.1fs  %s%n", r, g.s, g.score(), g.coinsRun, f / 60f, cause);
        }
        System.out.printf("avg dist %.0f, crashes %d, caught %d%n", total / runs, deaths[0], deaths[1]);
    }

    /** Simple look-ahead bot used for previews and generator testing. */
    static class Autopilot {
        float cooldown;

        void drive(Game g) {
            if (g.state != Game.RUNNING) return;
            cooldown -= 1 / 60f;
            float look = g.speed * 1.4f + 8;
            float[] free = new float[3];
            for (int l = -1; l <= 1; l++) free[l + 1] = danger(g, l, look);
            int cur = g.lane;
            // lane choice
            int best = cur;
            for (int l = -1; l <= 1; l++) if (free[l + 1] > free[best + 1] + 3) best = l;
            if (best != cur && cooldown <= 0 && Math.abs(g.x - cur * Game.LANE_W) < 0.2f) {
                int step = best > cur ? 1 : -1;
                if (danger(g, cur + step, 6) > 5) {
                    if (step > 0) g.right(); else g.left();
                    cooldown = 0.15f;
                }
            }
            // jump / roll for barriers in current lane
            for (Game.Obstacle o : g.obstacles) {
                if (o.lane != g.lane) continue;
                float d = o.s0 - g.s;
                if (d < 0 || d > g.speed * 0.3f) continue;
                if (o.type == Game.LOW && g.grounded) g.jump();
                if (o.type == Game.HIGH && !g.rolling) g.roll();
            }
        }

        /** Distance until something that can't be jumped/rolled in this lane. */
        float danger(Game g, int lane, float look) {
            float best = look;
            for (Game.Obstacle o : g.obstacles) {
                if (o.lane != lane) continue;
                float d = o.s0 - g.s;
                if (o.moving) d = d * g.speed / (g.speed + 12);
                if (d + o.len < -0.5f || d > look) continue;
                boolean bad = o.type == Game.BLOCK || (o.type == Game.TRAIN && g.y < Game.TRAIN_H - 0.8f && !rampBefore(g, o));
                if (o.type == Game.TRAIN && o.moving) bad = true;
                if (bad) best = Math.min(best, Math.max(d, 0));
            }
            return best;
        }

        boolean rampBefore(Game g, Game.Obstacle t) {
            for (Game.Obstacle o : g.obstacles)
                if (o.type == Game.RAMP && o.lane == t.lane && Math.abs(o.s0 + o.len - t.s0) < 0.5f && g.s <= o.s0 + 0.5f) return true;
            return false;
        }
    }
}
