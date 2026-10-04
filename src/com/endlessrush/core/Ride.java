package com.endlessrush.core;

import java.util.ArrayList;
import java.util.Random;

/**
 * Vehicle segments: Pongo riding the ore cart (Crystal Cavern), the bamboo canoe (Bamboo River) and the
 * paraglider (Sky Glide), plus the boarding and vehicle-to-vehicle set pieces between them.
 *
 * Controls (docs/PONGO_DESIGN.md section 8):
 *   cart    tilt the phone left/right to hop to the next track, swipe down to crouch (logs, beams, bats)
 *   boat    tilt only: the canoe steers continuously; at a Y fork tilt toward the branch you want
 *   glider  tilt in every direction: left/right banks and turns, toward you climbs, away from you dives
 * Swipes and arrow keys give a short "virtual tilt" so the rides also work without a motion sensor.
 *
 * Power-ups: the Maneki Magnet and Fever Star keep working; a running Hayate Rocket or Tobi Boots wind down before
 * boarding; the Kaze Board is stowed with its time frozen and comes back when she is on her feet again; rockets,
 * boots and boards never spawn on a ride and double-tap does nothing.
 *
 * Pure simulation (no GL / Android): Game delegates to it while a ride is active, RideScene draws it,
 * RideSfx gives every event its sound.
 */
public final class Ride {
    // vehicles
    public static final int NONE = 0, CART = 1, BOAT = 2, GLIDER = 3;
    public static final String[] VEHICLE_NAMES = {"run", "cart", "boat", "glider"};

    // set pieces (clip names match blender/assets/ride_transitions.py)
    public static final int TR_NONE = 0, TR_BOARD_CART = 1, TR_CART_TO_BOAT = 2, TR_BOAT_TO_GLIDER = 3, TR_GLIDE_LAND = 4,
            TR_HOP_OUT = 5;
    public static final String[] TR_CLIP = {null, "board_cart", "cart_to_boat", "boat_to_glider", "glide_land", "jump"};
    public static final float[] TR_DUR = {0f, 0.9f, 1.2f, 1.4f, 1.0f, 0.7f};

    // hazards
    public static final int H_BEAM = 0, H_LOG = 1, H_BATS = 2, H_BOULDER = 3, H_ROCKFALL = 4, H_ORE_TRAIN = 5, H_PILLAR = 6,
            H_STONE = 10, H_CROC = 11, H_DRIFTLOG = 12, H_WHIRL = 13, H_ISLAND = 14,
            H_CROW = 20, H_FLOCK = 21, H_KITE = 22, H_LANTERN = 23, H_CABLE = 24, H_SPIRE = 25, H_GUST = 26, H_THERMAL = 27;

    /** World scale: Pongo and her vehicles are modelled in metres and drawn 1.2x (PongoScene.HERO_SCALE). */
    public static final float K = 1.2f;
    public static final float TRACK_W = Game.LANE_W;
    // Pongo rides at 1.2x her model (vehicles.py PONGO_SCALE): head top 1.96 standing, 1.14 ducked (+ hair)
    public static final float PONGO_SCALE = 1.2f;
    public static final float CART_FLOOR = 0.45f * K, CART_TOP_STAND = 2.0f * K, CART_TOP_CROUCH = 1.19f * K;
    public static final float SWITCH_TIME = 0.3f, CROUCH_HOLD = 0.85f;
    public static final float RIVER_HALF = 4.6f, BOAT_HALF = 0.62f, BOAT_LAT = 8.5f;
    public static final float GL_LAT = 9f, GL_VERT = 5.5f, GL_SINK = 0.5f, ALT_MIN = 3f, ALT_MAX = 12f, ALT_START = 7f;
    public static final float SKY_HALF = 6.0f;

    public static final class Hazard {
        public int type, seed, state;
        public float x, y, s, len, w, h;     // centre x, base height, start s, length along s, half width, height
        public float vx, vy, vs, t, x0, y0, s0, phase;
        public boolean passed, warned, hit, active;
    }

    /** A Y fork: the way splits around an island (river) or a crystal pillar (cave) between s0 and s1. */
    public static final class Fork {
        public float s0, s1, half;   // island half width
        public int choice;           // -1 left, +1 right, 0 undecided
        public int calm;             // the branch with more coins and fewer hazards (-1 / +1)
        public boolean announced, resolved;
    }

    public interface Zones {
        /** Vehicle for the zone that contains run distance s (NONE for running zones). */
        int vehicleAt(float s);
        /** Start of the next zone after s. */
        float nextZoneStart(float s);
    }

    /** Default schedule (docs/PONGO_DESIGN.md section 4): Sakura Line, Cavern, River, Sky, Rooftops, repeat. */
    public static final class Schedule implements Zones {
        public float zoneLen = 1400f, offset = 0f;
        private static final int[] ORDER = {NONE, CART, BOAT, GLIDER, NONE};

        public int vehicleAt(float s) {
            float u = (s + offset) / zoneLen;
            if (u < 0) return NONE;
            return ORDER[((int) u) % ORDER.length];
        }

        public float nextZoneStart(float s) {
            return ((float) Math.floor((s + offset) / zoneLen) + 1) * zoneLen - offset;
        }
    }

    private final Game g;
    private final Random rng = new Random();
    public Zones zones = new Schedule();

    public final ArrayList<Hazard> hazards = new ArrayList<Hazard>();
    public final ArrayList<Fork> forks = new ArrayList<Fork>();

    // state
    public int vehicle = NONE, from = NONE, pending = -1;
    public int transition = TR_NONE;
    public float transT, transS0, transX;
    public float x, vx, alt, valt, yaw, roll, pitch, bob;
    public int track, trackFrom;
    public float switchT = 1f, crouchT, crouch, hop;
    public float rowPhase, rowRate = 0.8f, cycle;
    public float tiltX, tiltY, rawX, rawY, virtX, virtY, virtT;
    public boolean sensor;
    public float wobble, gustX, thermal, speedScale = 1f, wake;
    public float boardHold;
    private boolean tiltArmed = true;
    private float tiltHold, lastClackS, genS, nextPowerS, nextForkS, lastMystery;
    public Fork fork;
    public float rideTime;
    public final float[] loopVol = new float[RideSfx.LOOP_COUNT], loopPitch = new float[RideSfx.LOOP_COUNT];

    Ride(Game g) { this.g = g; }

    // ------------------------------------------------------------------ queries

    public boolean active() { return vehicle != NONE || transition != TR_NONE; }

    public boolean riding() { return vehicle != NONE && transition == TR_NONE; }

    public boolean inTransition() { return transition != TR_NONE; }

    public float transU() { return transition == TR_NONE ? 1f : Math.min(1f, transT / TR_DUR[transition]); }

    /** Vehicle shown under her right now (the destination during a set piece, except when hopping off). */
    public int shownVehicle() {
        if (transition == TR_GLIDE_LAND) return GLIDER;
        if (transition == TR_HOP_OUT) return from;
        return vehicle;
    }

    /** Height of her character origin above the ground plane (what Game.y reports while riding). */
    public float originY() {
        switch (vehicle) {
            case CART: return CART_FLOOR + hop;
            case BOAT: return 0.06f * K + bob;
            case GLIDER: return alt;
            default: return 0f;
        }
    }

    // ------------------------------------------------------------------ lifecycle

    void reset() {
        hazards.clear();
        forks.clear();
        vehicle = from = NONE;
        pending = -1;
        transition = TR_NONE;
        x = vx = alt = valt = yaw = roll = pitch = bob = 0;
        track = trackFrom = 0;
        switchT = 1;
        crouchT = crouch = hop = 0;
        rowPhase = 0;
        tiltX = tiltY = rawX = rawY = virtX = virtY = virtT = 0;
        wobble = gustX = thermal = wake = 0;
        speedScale = 1;
        boardHold = 0;
        tiltArmed = true;
        fork = null;
        rideTime = 0;
        lastClackS = 0;
        genS = 0;
        nextPowerS = 0;
        nextForkS = 0;
        for (int i = 0; i < loopVol.length; i++) { loopVol[i] = 0; loopPitch[i] = 1; }
    }

    /** Distance where Game's own generator must stop (start of the next zone, if it is a ride). */
    float runGenLimit(float s) {
        float z = zones.nextZoneStart(s - 1f);
        return zones.vehicleAt(z + 1f) != NONE || vehicle != NONE ? z : Float.MAX_VALUE;
    }

    // ------------------------------------------------------------------ input

    /** Device tilt from the accelerometer, already normalised to -1..1 (x right, y toward the player = climb). */
    public void setTilt(float x, float y) {
        sensor = true;
        rawX = clamp(x, -1, 1);
        rawY = clamp(y, -1, 1);
    }

    /** Returns true when the ride consumed the swipe. dir: 0 left, 1 right, 2 up, 3 down. */
    boolean swipe(int dir) {
        if (!active()) return false;
        if (transition != TR_NONE) return true;
        switch (dir) {
            case 0: case 1:
                virtX = dir == 0 ? -1 : 1;
                virtT = vehicle == CART ? 0.18f : 0.42f;
                if (vehicle == CART) { tiltArmed = true; trySwitch(dir == 0 ? -1 : 1); }
                break;
            case 2:
                if (vehicle == GLIDER) { virtY = 1; virtT = 0.45f; }
                break;
            default:
                if (vehicle == CART) {
                    if (crouchT <= 0) sfx(RideSfx.CROUCH);
                    crouchT = CROUCH_HOLD;
                } else if (vehicle == GLIDER) { virtY = -1; virtT = 0.45f; }
                break;
        }
        return true;
    }

    // ------------------------------------------------------------------ update

    /** Called by Game.step after s has advanced. Returns true while the ride controls the player. */
    boolean step(float dt) {
        int want = zones.vehicleAt(g.s + 2f);
        if (want != vehicle && transition == TR_NONE) {
            if (canBegin()) begin(want);
            else prepare();
        }
        if (!active()) {
            loops(dt, 0);
            return false;
        }
        rideTime += dt;
        filterTilt(dt);
        if (transition != TR_NONE) {
            stepTransition(dt);
        } else {
            switch (vehicle) {
                case CART: stepCart(dt); break;
                case BOAT: stepBoat(dt); break;
                default: stepGlider(dt); break;
            }
        }
        stepHazards(dt);
        if (transition == TR_NONE && g.invulnT <= 0) collide();
        generate();
        cleanup();
        loops(dt, 1);
        // keep Game's player fields in step for pickups, camera, score and the old renderer
        g.x = x;
        g.y = originY();
        g.vy = vehicle == GLIDER ? valt : 0;
        g.lane = Math.round(clamp(x / Game.LANE_W, -1, 1));
        g.grounded = vehicle != GLIDER;
        g.rolling = false;
        return true;
    }

    private boolean canBegin() { return g.jetT <= 0 && (g.grounded || vehicle != NONE) && !g.rolling; }

    /** A ride zone is coming but she is mid-air or on the rocket: wind the rocket and boots down. */
    private void prepare() {
        if (g.jetT > 0.6f) g.jetT = 0.6f;
        if (g.sneakT > 0) g.sneakT = 0;
    }

    private void begin(int want) {
        from = vehicle;
        if (from == NONE && want == CART) transition = TR_BOARD_CART;
        else if (from == CART && want == BOAT) transition = TR_CART_TO_BOAT;
        else if (from == BOAT && want == GLIDER) transition = TR_BOAT_TO_GLIDER;
        else if (from == GLIDER && want == NONE) transition = TR_GLIDE_LAND;
        else if (want == NONE) transition = TR_HOP_OUT;
        else transition = from == NONE ? TR_BOARD_CART : TR_CART_TO_BOAT;  // unusual orders: closest set piece
        // the ride (or running again) takes the vehicle of the zone, whatever the set piece shows
        vehicle = want;
        transT = 0;
        transS0 = g.s;
        transX = x = vehicle == NONE ? g.x : g.x;
        if (from == NONE) {
            // power-ups: the board is stowed with its time frozen, boots and rocket end
            boardHold = g.boardT;
            g.boardT = 0;
            g.sneakT = 0;
            g.jetT = 0;
            if (boardHold > 0) sfx(RideSfx.STOW);
            x = g.lane * Game.LANE_W;
            track = trackFrom = g.lane;
        }
        g.invulnT = Math.max(g.invulnT, TR_DUR[transition] + 0.6f);
        sfx(new int[]{0, RideSfx.BOARD_CART, RideSfx.BUFFER_CRASH, RideSfx.WATERFALL, RideSfx.TOUCHDOWN, RideSfx.HOP_OFF}[transition]);
        if (vehicle == GLIDER) { alt = ALT_START; valt = 0; }
        if (vehicle == BOAT) { vx = 0; rowPhase = 0; }
        if (vehicle == CART) { track = Math.round(clamp(x / TRACK_W, -1, 1)); trackFrom = track; switchT = 1; }
        // the old zone's hazards stop here; the new zone starts generating after the set piece
        for (int i = hazards.size() - 1; i >= 0; i--) if (hazards.get(i).s > g.s) hazards.remove(i);
        forks.clear();
        fork = null;
        genS = g.s + TR_DUR[transition] * g.speed + 45f;
        nextPowerS = genS + 120f;
        nextForkS = genS + 160f + rng.nextFloat() * 120f;
        // Game's pickups ahead belong to the old zone
        for (int i = g.pickups.size() - 1; i >= 0; i--) {
            Game.Pickup p = g.pickups.get(i);
            if (p.s > g.s + 4f) g.pickups.remove(i);
        }
    }

    private void stepTransition(float dt) {
        transT += dt;
        float u = transU();
        // vertical: the clip carries her root motion; Game.y follows the destination mount
        if (transition == TR_BOAT_TO_GLIDER) { alt = ALT_START; }
        if (transition == TR_BOAT_TO_GLIDER && transT - dt < TR_DUR[transition] * 0.3f && transT >= TR_DUR[transition] * 0.3f)
            sfx(RideSfx.CANOPY_OPEN);
        if (transition == TR_CART_TO_BOAT && transT - dt < TR_DUR[transition] * 0.72f && transT >= TR_DUR[transition] * 0.72f)
            sfx(RideSfx.BOAT_LAND);
        if (transition == TR_BOARD_CART && transT - dt < TR_DUR[transition] * 0.72f && transT >= TR_DUR[transition] * 0.72f)
            sfx(RideSfx.CART_LAND);
        if (u >= 1f) {
            int t = transition;
            transition = TR_NONE;
            if (vehicle == NONE) finish(t);
        }
    }

    /** On her feet again: give the board back, hand control to Game. */
    private void finish(int t) {
        if (boardHold > 0) {
            g.boardT = boardHold;
            boardHold = 0;
            sfx(RideSfx.BOARD_BACK);
        }
        g.lane = Math.round(clamp(x / Game.LANE_W, -1, 1));
        g.x = x;
        g.y = 0;
        g.vy = 0;
        g.grounded = true;
        hazards.clear();
        forks.clear();
        from = NONE;
    }

    private void filterTilt(float dt) {
        if (virtT > 0) {
            virtT -= dt;
            if (virtT <= 0) { virtX = 0; virtY = 0; }
        }
        float tx = Math.abs(virtX) > Math.abs(rawX) ? virtX : rawX;
        float ty = Math.abs(virtY) > Math.abs(rawY) ? virtY : rawY;
        // dead zone, then a smooth response
        tx = dead(tx, 0.08f);
        ty = dead(ty, 0.1f);
        float k = Math.min(1f, dt * 12f);
        tiltX += (tx - tiltX) * k;
        tiltY += (ty - tiltY) * k;
    }

    // ------------------------------------------------------------------ cart

    private void trySwitch(int d) {
        if (switchT < 1f) return;
        int nt = track + d;
        if (nt < -1 || nt > 1 || trackBlocked(nt)) {
            wobble = 0.25f;
            sfx(RideSfx.CART_BUMP);
            return;
        }
        trackFrom = track;
        track = nt;
        switchT = 0;
        tiltArmed = false;
        sfx(RideSfx.TRACK_SWITCH);
    }

    /** The centre track is closed along a fork's crystal pillar. */
    private boolean trackBlocked(int t) {
        if (t != 0) return false;
        for (int i = 0; i < forks.size(); i++) {
            Fork f = forks.get(i);
            if (g.s > f.s0 - 2f && g.s < f.s1) return true;
        }
        return false;
    }

    private void stepCart(float dt) {
        speedScale = 1f;
        // tilt past the threshold hops to the next track; hold it to keep going, centre it to re-arm
        float a = Math.abs(tiltX);
        if (a < 0.28f) { tiltArmed = true; tiltHold = 0; }
        if (a > 0.45f) {
            tiltHold += dt;
            if (tiltArmed || tiltHold > 0.5f) {
                tiltHold = 0;
                trySwitch(tiltX < 0 ? -1 : 1);
            }
        }
        // Y fork: the centre track splits around the pillar; she goes the way she leans (default: the calm side)
        Fork f = nextFork(60f);
        if (f != null) {
            if (!f.announced && f.s0 - g.s < 55f) { f.announced = true; sfx(RideSfx.FORK_BELL); }
            if (track == 0 && !f.resolved && f.s0 - g.s < 5f) {
                f.resolved = true;
                int d = Math.abs(tiltX) > 0.15f ? (tiltX < 0 ? -1 : 1) : f.calm;
                f.choice = d;
                trackFrom = 0;
                track = d;
                switchT = 0;
                sfx(RideSfx.TRACK_SWITCH);
            }
        }
        if (switchT < 1f) {
            switchT = Math.min(1f, switchT + dt / SWITCH_TIME);
            float u = smooth(switchT);
            x = (trackFrom + (track - trackFrom) * u) * TRACK_W;
            hop = 0.32f * (float) Math.sin(Math.PI * switchT);
            if (switchT >= 1f) sfx(RideSfx.CART_LAND_SOFT);
        } else {
            x = track * TRACK_W;
            hop = 0;
        }
        roll = (track - trackFrom) * 10f * (float) Math.sin(Math.PI * Math.min(1f, switchT)) + tiltX * 4f;
        if (crouchT > 0) crouchT -= dt;
        crouch += ((crouchT > 0 ? 1f : 0f) - crouch) * Math.min(1f, dt * 14f);
        cycle += dt / 0.8f;
        // rail joints every 6 m: a clack in time with the cart's rattle
        if (g.s - lastClackS > 6f) {
            lastClackS = g.s;
            sfx(RideSfx.RAIL_CLACK);
        }
        if (wobble > 0) wobble = Math.max(0, wobble - dt);
    }

    // ------------------------------------------------------------------ boat

    private void stepBoat(float dt) {
        speedScale = 0.82f;
        float lo = -RIVER_HALF + BOAT_HALF, hi = RIVER_HALF - BOAT_HALF;
        Fork f = nextFork(80f);
        float pull = 0f;
        if (f != null) {
            if (!f.announced && f.s0 - g.s < 70f) { f.announced = true; sfx(RideSfx.FORK_BELL); }
            boolean inside = g.s > f.s0 - 1f && g.s < f.s1;
            if (!f.resolved && f.s0 - g.s < 3f) {
                // past the island's nose: she is in the branch she steered to (a bump nudges her off the nose)
                f.resolved = true;
                f.choice = Math.abs(x) > 0.3f ? (x < 0 ? -1 : 1) : (Math.abs(tiltX) > 0.1f ? (tiltX < 0 ? -1 : 1) : f.calm);
                if (Math.abs(x) < f.half + BOAT_HALF) {
                    wobble = 0.5f;
                    g.shake = 0.25f;
                    sfx(RideSfx.BOAT_BUMP);
                }
            }
            if (inside && f.resolved) {
                if (f.choice < 0) hi = -f.half - BOAT_HALF;
                else lo = f.half + BOAT_HALF;
            } else if (f.s0 - g.s < 25f && !f.resolved && Math.abs(tiltX) < 0.1f) {
                // drift gently toward the calm branch when she does not choose
                pull = f.calm * 0.8f;
            }
        }
        float target = tiltX * BOAT_LAT + gustX + pull;
        vx += (target - vx) * Math.min(1f, dt * 4.5f);
        x += vx * dt;
        if (x < lo) { x = lo; if (vx < -2f) bankBump(); vx = Math.max(vx, 0); }
        if (x > hi) { x = hi; if (vx > 2f) bankBump(); vx = Math.min(vx, 0); }
        yaw = (float) Math.toDegrees(Math.atan2(vx, Math.max(4f, g.speed))) * 0.9f;
        roll = -tiltX * 9f + wobbleRoll();
        // the canoe rocks on the current; rowing rate follows the speed
        bob = 0.03f * (float) Math.sin(rideTime * 2.1f) + 0.015f * (float) Math.sin(rideTime * 3.7f);
        float prev = rowPhase;
        rowRate = 0.65f + 0.35f * (g.speed / Game.BASE_SPEED - 1f) + 0.2f;
        rowPhase = (rowPhase + dt * rowRate) % 1f;
        // paddle splashes at each catch (phase 0 right, 0.5 left), skipped while ruddering
        if (Math.abs(tiltX) < 0.6f && crossed(prev, rowPhase, 0.02f)) sfx(RideSfx.PADDLE_R);
        if (Math.abs(tiltX) < 0.6f && crossed(prev, rowPhase, 0.52f)) sfx(RideSfx.PADDLE_L);
        if (Math.abs(tiltX) >= 0.6f && crossed(prev, rowPhase, 0.25f)) sfx(RideSfx.RUDDER);
        wake = Math.min(1f, Math.abs(vx) / BOAT_LAT + 0.3f);
        cycle = rowPhase;
        if (gustX != 0) gustX *= Math.max(0, 1 - dt * 2f);
        if (wobble > 0) wobble = Math.max(0, wobble - dt);
    }

    private void bankBump() {
        wobble = 0.3f;
        sfx(RideSfx.BOAT_BUMP);
    }

    // ------------------------------------------------------------------ glider

    private void stepGlider(float dt) {
        float climb = Math.max(0, tiltY), dive = Math.max(0, -tiltY);
        speedScale = 0.92f + 0.28f * dive - 0.14f * climb;
        float tvx = tiltX * GL_LAT + gustX;
        vx += (tvx - vx) * Math.min(1f, dt * 3f);
        x += vx * dt;
        float tva = tiltY * GL_VERT - GL_SINK + thermal;
        valt += (tva - valt) * Math.min(1f, dt * 2.5f);
        alt += valt * dt;
        if (x < -SKY_HALF) { x = -SKY_HALF; vx = Math.max(0, vx); }
        if (x > SKY_HALF) { x = SKY_HALF; vx = Math.min(0, vx); }
        if (alt < ALT_MIN) { alt = ALT_MIN; valt = Math.max(0, valt); }
        if (alt > ALT_MAX) { alt = ALT_MAX; valt = Math.min(0, valt); }
        roll = -tiltX * 24f + wobbleRoll();
        pitch = tiltY * 10f;
        yaw = (float) Math.toDegrees(Math.atan2(vx, Math.max(6f, g.speed))) * 0.7f;
        cycle = (cycle + dt / 1.4f) % 1f;
        if (thermal > 0) thermal = Math.max(0, thermal - dt * 2.5f);
        if (gustX != 0) gustX *= Math.max(0, 1 - dt * 1.5f);
        if (wobble > 0) wobble = Math.max(0, wobble - dt);
    }

    private float wobbleRoll() { return wobble > 0 ? 14f * wobble * (float) Math.sin(rideTime * 40f) : 0f; }

    // ------------------------------------------------------------------ hazards

    private Fork nextFork(float ahead) {
        Fork best = null;
        for (int i = 0; i < forks.size(); i++) {
            Fork f = forks.get(i);
            if (f.s1 < g.s || f.s0 - g.s > ahead) continue;
            if (best == null || f.s0 < best.s0) best = f;
        }
        fork = best;
        return best;
    }

    private void stepHazards(float dt) {
        float ps = g.s;
        for (int i = 0; i < hazards.size(); i++) {
            Hazard h = hazards.get(i);
            float d = h.s - ps;
            h.t += dt;
            switch (h.type) {
                case H_BATS:
                    // the swarm waits under the roof, then swoops down the track at her head height
                    if (!h.active && d < 34f) { h.active = true; h.vs = -9f; sfx(RideSfx.BATS); }
                    if (h.active) {
                        h.s += h.vs * dt;
                        h.y += (1.3f * K - h.y) * Math.min(1f, dt * 2.5f);
                    }
                    break;
                case H_ROCKFALL:
                    // rocks shake loose when she is near: dust first (the warning), then the pile lands on the track
                    if (h.state == 0 && d < 42f) { h.state = 1; h.t = 0; sfx(RideSfx.ROCK_RUMBLE); }
                    if (h.state == 1 && h.t > 0.55f) { h.state = 2; sfx(RideSfx.ROCKFALL); g.shake = Math.max(g.shake, 0.12f); }
                    break;
                case H_ORE_TRAIN:
                    if (!h.active && d < 120f) { h.active = true; sfx(RideSfx.ORE_BELL); }
                    if (h.active) h.s -= 7f * dt;
                    break;
                case H_CROC:
                    // lurks (eyes only), surfaces and swims across toward her line, then the snap
                    if (h.state == 0 && d < 38f) { h.state = 1; h.t = 0; sfx(RideSfx.CROC_SURFACE); }
                    if (h.state == 1) {
                        float tx = clamp(x, h.x0 - 2.6f, h.x0 + 2.6f);
                        h.x += clamp(tx - h.x, -2.4f * dt, 2.4f * dt);
                        if (d < 9f) { h.state = 2; h.t = 0; }
                    }
                    if (h.state == 2 && h.t > 0.22f && !h.warned) { h.warned = true; sfx(RideSfx.CROC_SNAP); }
                    break;
                case H_DRIFTLOG:
                    h.x += h.vx * dt;
                    if (h.x < -RIVER_HALF + 1.2f || h.x > RIVER_HALF - 1.2f) h.vx = -h.vx;
                    h.phase += h.vx * dt * 0.8f;
                    if (!h.warned && d < 25f) { h.warned = true; sfx(RideSfx.LOG_KNOCK); }
                    break;
                case H_WHIRL:
                    if (Math.abs(d) < h.len && Math.abs(x - h.x) < h.w + 1.2f) {
                        // pulls the canoe toward its eye and spins it a little
                        gustX += (h.x - x) * 1.6f * dt * 6f;
                        if (!h.warned) { h.warned = true; sfx(RideSfx.WHIRL); }
                    }
                    break;
                case H_CROW:
                    // flies in from the side, then dives at her altitude
                    h.x += h.vx * dt;
                    h.y += (alt + 1.3f - h.y) * Math.min(1f, dt * (d < 30f ? 1.6f : 0.3f));
                    h.s += h.vs * dt;
                    if (!h.warned && d < 40f) { h.warned = true; sfx(RideSfx.CAW); }
                    break;
                case H_FLOCK:
                    h.x += h.vx * dt;
                    h.s += h.vs * dt;
                    if (!h.warned && d < 55f) { h.warned = true; sfx(RideSfx.FLOCK); }
                    break;
                case H_KITE:
                    h.phase += dt;
                    h.x = h.x0 + 0.9f * (float) Math.sin(h.phase * 1.3f + h.seed);
                    h.y = h.y0 + 0.5f * (float) Math.sin(h.phase * 0.9f + h.seed * 2);
                    if (!h.warned && d < 30f) { h.warned = true; sfx(RideSfx.KITE_FLAP); }
                    break;
                case H_LANTERN:
                    h.y += 0.7f * dt;
                    h.x += 0.25f * (float) Math.sin(h.t * 0.8f + h.seed) * dt;
                    break;
                case H_CABLE:
                    if (!h.warned && d < 35f) { h.warned = true; sfx(RideSfx.CHIMES); }
                    break;
                case H_GUST:
                    if (Math.abs(d) < h.len * 0.5f && Math.abs(alt + 1f - h.y) < h.h && !h.hit) {
                        h.hit = true;
                        gustX += h.vx;
                        wobble = 0.35f;
                        sfx(RideSfx.GUST);
                    }
                    break;
                case H_THERMAL:
                    if (Math.abs(d) < h.len * 0.5f && Math.abs(x - h.x) < h.w) {
                        thermal = 5.5f;
                        if (!h.hit) { h.hit = true; sfx(RideSfx.THERMAL); }
                    }
                    break;
                default:
                    break;
            }
            if (!h.passed && h.s + h.len < ps) {
                h.passed = true;
                if (h.type == H_BEAM || h.type == H_LOG) sfx(RideSfx.DUCK_WHOOSH);
            }
        }
    }

    /** Pongo's hit volume: x half width, bottom and top heights (game units) for the current vehicle. */
    private void collide() {
        float ps = g.s, pps = ps - g.speed * 0.02f;
        for (int i = 0; i < hazards.size(); i++) {
            Hazard h = hazards.get(i);
            if (h.hit && h.type != H_GUST) continue;
            if (ps + 0.6f < h.s || pps - 0.6f > h.s + h.len) continue;
            if (hits(h)) {
                h.hit = true;
                if (h.type == H_GUST || h.type == H_THERMAL || h.type == H_WHIRL || h.type == H_PILLAR || h.type == H_ISLAND) continue;
                crash(h);
                return;
            }
        }
    }

    boolean hits(Hazard h) {
        switch (vehicle) {
            case CART: {
                if (Math.abs(x - h.x) > h.w + 0.62f) return false;
                float bottom = CART_FLOOR + hop, top = bottom + (CART_TOP_STAND - CART_FLOOR) * (1 - crouch) +
                        (CART_TOP_CROUCH - CART_FLOOR) * crouch;
                if (h.type == H_BEAM || h.type == H_LOG || h.type == H_BATS) return top > h.y;
                if (h.type == H_ROCKFALL) return h.state == 2;
                return true;
            }
            case BOAT: {
                if (h.type == H_WHIRL || h.type == H_ISLAND) return false;
                if (h.type == H_CROC && h.state < 1) return false;
                return Math.abs(x - h.x) < h.w + BOAT_HALF;
            }
            case GLIDER: {
                float cy = alt + 1.1f;
                float dx = Math.abs(x - h.x), dy;
                switch (h.type) {
                    case H_CABLE:   // a line across the whole way: climb over or dive under (canopy counts)
                        return alt + 3.3f > h.y && alt + 0.2f < h.y;
                    case H_SPIRE:   // rock pillar from the valley floor up to h.y
                        return dx < h.w + 1.6f && alt < h.y;
                    case H_KITE:    // the kite and its string down to the ground at x0 - 2
                        if (dx < h.w + 0.9f && Math.abs(cy - h.y) < h.h + 0.9f) return true;
                        float sx = h.x - 2f + (alt + 1f) / Math.max(0.5f, h.y) * 2f;
                        return alt + 1f < h.y && Math.abs(x - sx) < 0.5f;
                    default:
                        dy = Math.abs(cy - h.y);
                        float rx = h.w + 0.8f, ry = h.h + 1.1f;
                        return (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) < 1f;
                }
            }
            default:
                return false;
        }
    }

    private void crash(Hazard h) {
        sfx(vehicle == BOAT ? RideSfx.BOAT_CRASH : vehicle == GLIDER ? RideSfx.GLIDER_CRASH : RideSfx.CART_CRASH);
        if (h.type == H_CROC) sfx(RideSfx.CROC_SNAP);
        g.die(0);
    }

    /** After a revive: clear what is right in front of her and give her a moment. */
    void onRevive() {
        for (int i = hazards.size() - 1; i >= 0; i--) {
            Hazard h = hazards.get(i);
            if (h.s < g.s + 60f && h.s + h.len > g.s - 5f) hazards.remove(i);
        }
        crouchT = crouch = 0;
        switchT = 1;
        if (vehicle == CART) x = track * TRACK_W;
        if (vehicle == GLIDER) { alt = Math.max(alt, ALT_START); valt = 0; }
        vx = 0;
        wobble = 0;
    }

    // ------------------------------------------------------------------ generation

    private float difficulty() { return Math.min(1f, g.s / 6000f); }

    private void generate() {
        if (vehicle == NONE) return;
        float zoneEnd = zones.nextZoneStart(g.s);
        float limit = Math.min(g.s + 240f, zoneEnd - 40f);
        while (genS < limit) {
            if (genS >= nextForkS && genS + 120f < zoneEnd) {
                patternFork();
                nextForkS = genS + 260f + rng.nextFloat() * 200f;
            } else if (genS >= nextPowerS) {
                patternPower();
                nextPowerS = genS + 300f + rng.nextFloat() * 240f;
            } else {
                switch (vehicle) {
                    case CART: patternCart(); break;
                    case BOAT: patternBoat(); break;
                    default: patternSky(); break;
                }
            }
        }
    }

    private float gap() { return 16f + g.speed * 0.8f; }

    private Hazard add(int type, float x, float y, float s, float len, float w, float h) {
        Hazard z = new Hazard();
        z.type = type;
        z.x = z.x0 = x;
        z.y = z.y0 = y;
        z.s = z.s0 = s;
        z.len = len;
        z.w = w;
        z.h = h;
        z.seed = rng.nextInt(1000);
        z.phase = rng.nextFloat() * 6.28f;
        hazards.add(z);
        return z;
    }

    private void coin(float px, float py, float ps) {
        Game.Pickup p = new Game.Pickup();
        p.type = Game.COIN;
        p.x = px;
        p.y = py;
        p.s = ps;
        p.phase = rng.nextFloat() * 6;
        g.pickups.add(p);
    }

    /** Coin height for the current vehicle (her chest). */
    private float coinY(float a) {
        switch (vehicle) {
            case CART: return CART_FLOOR + 0.9f;
            case BOAT: return 0.95f;
            default: return a + 1.0f;
        }
    }

    private void coinRun(float x0, float x1, float a0, float a1, float s0, int n, float spacing) {
        for (int i = 0; i < n; i++) {
            float u = n > 1 ? i / (float) (n - 1) : 0;
            coin(x0 + (x1 - x0) * u, coinY(a0 + (a1 - a0) * u), s0 + i * spacing);
        }
    }

    private void patternPower() {
        float px = vehicle == CART ? (rng.nextInt(3) - 1) * TRACK_W : (rng.nextFloat() * 2 - 1) * 2.4f;
        float pa = vehicle == GLIDER ? 4f + rng.nextFloat() * 4f : 0f;
        coinRun(px, px, pa, pa, genS, 5, 3f);
        // magnet, Fever Star (2x), gacha capsule or (rarely) an Omamori; never rocket, boots or board
        int r = rng.nextInt(10);
        int type = r < 4 ? Game.MAGNET : r < 8 ? Game.X2 : r < 9 ? Game.MYSTERY : Game.KEY;
        Game.Pickup p = new Game.Pickup();
        p.type = type;
        p.x = px;
        p.y = coinY(pa) + 0.1f;
        p.s = genS + 17f;
        g.pickups.add(p);
        genS += 34f + gap() * 0.4f;
    }

    private void patternCart() {
        float d = difficulty();
        int[] t = {-1, 0, 1};
        shuffle(t);
        float r = rng.nextFloat();
        float at = genS;
        if (r < 0.3f) {
            // a low beam or a fallen log across one or two tracks (crouch), coins under it on another
            int n = rng.nextFloat() < 0.4f + d * 0.4f ? 2 : 1;
            for (int i = 0; i < n; i++) add(rng.nextBoolean() ? H_BEAM : H_LOG, t[i] * TRACK_W, 1.25f * K, at, 0.5f, 1.1f, 0.4f);
            coinRun(t[0] * TRACK_W, t[0] * TRACK_W, 0, 0, at - 9f, 7, 3f);
        } else if (r < 0.48f) {
            // bats roosting over a track, swooping at her when she comes close
            Hazard b = add(H_BATS, t[0] * TRACK_W, 2.6f * K, at + 12f, 2.4f, 1.0f, 0.55f * K);
            if (rng.nextFloat() < d) add(H_BOULDER, t[1] * TRACK_W, 0, at + 6f, 1.6f, 0.9f, 1.4f);
            coinRun(t[2] * TRACK_W, t[2] * TRACK_W, 0, 0, at, 8, 3f);
        } else if (r < 0.68f) {
            // crystal boulders on one or two tracks (tilt around)
            int n = rng.nextFloat() < 0.5f + d * 0.3f ? 2 : 1;
            for (int i = 0; i < n; i++) add(H_BOULDER, t[i] * TRACK_W, 0, at + i * 7f, 1.6f, 0.9f, 1.4f);
            coinRun(t[2] * TRACK_W, t[2] * TRACK_W, 0, 0, at - 6f, 8, 3f);
        } else if (r < 0.84f) {
            // rockfall: dust and a rumble, then the pile drops onto the track
            add(H_ROCKFALL, t[0] * TRACK_W, 0, at + 8f, 2.2f, 1.0f, 1.2f);
            coinRun(t[1] * TRACK_W, t[1] * TRACK_W, 0, 0, at, 6, 3f);
        } else {
            // an ore train coming the other way on one track
            Hazard o = add(H_ORE_TRAIN, t[0] * TRACK_W, 0, at + 70f, 9f, 1.0f, 1.8f);
            coinRun(t[0] * TRACK_W, t[0] * TRACK_W, 0, 0, at + 4f, 6, 3f);
            if (rng.nextFloat() < 0.4f + d * 0.3f) add(H_BEAM, t[1] * TRACK_W, 1.25f * K, at + 40f, 0.5f, 1.1f, 0.4f);
        }
        genS = at + gap();
    }

    private void patternBoat() {
        float d = difficulty();
        float r = rng.nextFloat();
        float at = genS;
        float lane = (rng.nextFloat() * 2 - 1) * (RIVER_HALF - 1.4f);
        if (r < 0.32f) {
            // stones: two or three, leaving a gap the coins mark
            int n = 2 + (rng.nextFloat() < d ? 1 : 0);
            float gapX = (rng.nextFloat() * 2 - 1) * 2.6f;
            for (int i = 0; i < n; i++) {
                float sx;
                int tries = 0;
                do { sx = (rng.nextFloat() * 2 - 1) * (RIVER_HALF - 0.8f); } while (Math.abs(sx - gapX) < 2.2f && ++tries < 8);
                add(H_STONE, sx, 0, at + i * 5f, 1.4f, 0.75f + rng.nextFloat() * 0.35f, 0.8f);
            }
            coinRun(gapX, gapX, 0, 0, at - 6f, 6, 3f);
        } else if (r < 0.55f) {
            // crocodile: lurks off one side, swims toward her line and snaps
            float side = rng.nextBoolean() ? -1 : 1;
            add(H_CROC, side * (RIVER_HALF - 1.6f), 0, at + 10f, 3.2f, 0.75f, 0.6f);
            coinRun(-side * 1.6f, -side * 2.6f, 0, 0, at, 7, 3f);
        } else if (r < 0.72f) {
            // a drifting log sliding across the current
            Hazard l = add(H_DRIFTLOG, lane, 0, at + 8f, 1.0f, 1.6f, 0.5f);
            l.vx = (rng.nextBoolean() ? 1 : -1) * (1.2f + d * 1.2f);
            coinRun(-lane * 0.6f, -lane * 0.6f, 0, 0, at, 6, 3f);
        } else if (r < 0.84f) {
            // whirlpool: not lethal, it tugs the canoe toward its eye
            add(H_WHIRL, lane, 0, at + 6f, 6f, 1.6f, 0.2f);
            add(H_STONE, lane + (lane > 0 ? -1.2f : 1.2f), 0, at + 8f, 1.4f, 0.7f, 0.8f);
            coinRun(-lane, -lane, 0, 0, at, 7, 3f);
        } else {
            // a coin slalom between stones
            for (int i = 0; i < 4; i++) {
                float sx = (i % 2 == 0 ? -1 : 1) * 1.8f;
                add(H_STONE, sx, 0, at + i * 9f, 1.4f, 0.7f, 0.8f);
                coin(-sx, coinY(0), at + i * 9f);
                coin(-sx * 0.5f, coinY(0), at + i * 9f + 4.5f);
            }
        }
        genS = at + gap() * 1.05f;
    }

    private void patternSky() {
        float d = difficulty();
        float r = rng.nextFloat();
        float at = genS;
        float lx = (rng.nextFloat() * 2 - 1) * (SKY_HALF - 1.5f);
        float la = ALT_MIN + 1f + rng.nextFloat() * (ALT_MAX - ALT_MIN - 2.5f);
        if (r < 0.2f) {
            // a crow crossing and diving at her height, coins on the other side
            Hazard c = add(H_CROW, lx > 0 ? SKY_HALF + 2f : -SKY_HALF - 2f, la + 1f, at + 20f, 0.8f, 0.55f, 0.35f);
            c.vx = (lx > 0 ? -1 : 1) * (2.5f + d * 2f);
            c.vs = -3f;
            coinRun(-lx * 0.7f, -lx * 0.7f, la, la, at, 7, 3f);
        } else if (r < 0.34f) {
            // a flock of crows sweeping across in a V
            float dir = rng.nextBoolean() ? 1 : -1;
            for (int i = 0; i < 5 + (int) (d * 3); i++) {
                Hazard c = add(H_FLOCK, -dir * (SKY_HALF + 3f + Math.abs(i - 2) * 1.1f), la + Math.abs(i - 2) * 0.35f,
                        at + 30f + i * 1.3f, 0.8f, 0.45f, 0.3f);
                c.vx = dir * (3.4f + d);
                c.vs = -1.5f;
            }
            float ca = la > (ALT_MIN + ALT_MAX) * 0.5f ? la - 3.5f : la + 3.5f;
            coinRun(0, 0, ca, ca, at + 20f, 7, 3f);
        } else if (r < 0.5f) {
            // kites on long strings; go over them or around
            int n = 1 + (rng.nextFloat() < d ? 1 : 0);
            for (int i = 0; i < n; i++) {
                float kx = (rng.nextFloat() * 2 - 1) * (SKY_HALF - 1f);
                add(H_KITE, kx, la + 0.5f, at + 10f + i * 14f, 1.0f, 0.9f, 0.9f);
            }
            coinRun(-lx * 0.5f, lx * 0.2f, la + 3f, la + 3f, at + 4f, 8, 3f);
        } else if (r < 0.62f) {
            // a wind-chime cable strung across the valley: climb over or dive under
            float ca = ALT_MIN + 2.6f + rng.nextFloat() * (ALT_MAX - ALT_MIN - 4.5f);
            add(H_CABLE, 0, ca, at + 16f, 0.4f, SKY_HALF + 3f, 0.2f);
            boolean over = rng.nextBoolean();
            float pa = over ? Math.min(ALT_MAX - 0.6f, ca + 0.4f) : Math.max(ALT_MIN, ca - 4.0f);
            coinRun(lx * 0.3f, lx * 0.3f, pa, pa, at + 6f, 7, 3f);
        } else if (r < 0.74f) {
            // rock spires rising from the valley; fly between or over
            float sx = lx;
            add(H_SPIRE, sx, ALT_MIN + 3f + rng.nextFloat() * 4f, at + 12f, 4f, 1.3f, 0f);
            if (rng.nextFloat() < 0.5f + d * 0.3f)
                add(H_SPIRE, sx > 0 ? sx - 5.2f : sx + 5.2f, ALT_MIN + 2f + rng.nextFloat() * 3f, at + 26f, 4f, 1.2f, 0f);
            coinRun(sx > 0 ? sx - 2.6f : sx + 2.6f, 0, la, la, at + 8f, 8, 3f);
        } else if (r < 0.84f) {
            // sky lanterns drifting up; a gust shoves her sideways
            for (int i = 0; i < 3; i++)
                add(H_LANTERN, (rng.nextFloat() * 2 - 1) * (SKY_HALF - 1f), la - 2f + rng.nextFloat() * 3f, at + 8f + i * 7f,
                        0.6f, 0.45f, 0.55f);
            Hazard gu = add(H_GUST, 0, la + 1f, at + 30f, 6f, SKY_HALF, 3f);
            gu.vx = (rng.nextBoolean() ? 1 : -1) * (3f + d * 2f);
            coinRun(0, 0, la + 1.5f, la + 1.5f, at + 12f, 6, 3f);
        } else {
            // a thermal: a column of rising air (and coins) that lifts her
            add(H_THERMAL, lx, la, at + 10f, 14f, 1.6f, 6f);
            for (int i = 0; i < 6; i++) coin(lx, coinY(la + i * 0.7f), at + 8f + i * 2.4f);
        }
        genS = at + gap() * 1.1f;
    }

    /** Y fork: river island or the cavern's crystal pillar, with a calm branch (coins) and a busy one. */
    private void patternFork() {
        if (vehicle == GLIDER) { genS += 10f; return; }
        Fork f = new Fork();
        f.s0 = genS + 20f;
        f.s1 = f.s0 + (vehicle == BOAT ? 60f : 50f);
        f.half = vehicle == BOAT ? 1.4f : 0.9f;
        f.calm = rng.nextBoolean() ? -1 : 1;
        forks.add(f);
        if (vehicle == BOAT) {
            add(H_ISLAND, 0, 0, f.s0, f.s1 - f.s0, f.half, 2f);
            float cx = f.calm * (f.half + (RIVER_HALF - f.half) * 0.5f);
            coinRun(cx, cx, 0, 0, f.s0 + 4f, 14, 3.4f);
            float bx = -f.calm * (f.half + (RIVER_HALF - f.half) * 0.5f);
            add(H_STONE, bx - 0.8f, 0, f.s0 + 14f, 1.4f, 0.6f, 0.8f);
            add(H_CROC, -f.calm * (RIVER_HALF - 1.1f), 0, f.s0 + 34f, 3.2f, 0.7f, 0.6f);
            coinRun(bx + 0.9f, bx + 0.9f, 0, 0, f.s0 + 10f, 4, 3f);
        } else {
            add(H_PILLAR, 0, 0, f.s0, f.s1 - f.s0, f.half, 3f);
            float cx = f.calm * TRACK_W;
            coinRun(cx, cx, 0, 0, f.s0 + 2f, 13, 3.4f);
            add(H_BEAM, -f.calm * TRACK_W, 1.25f * K, f.s0 + 22f, 0.5f, 1.1f, 0.4f);
            add(H_BATS, -f.calm * TRACK_W, 2.6f * K, f.s0 + 40f, 2.4f, 1.0f, 0.55f * K);
        }
        genS = f.s1 + gap() * 0.6f;
    }

    private void cleanup() {
        for (int i = hazards.size() - 1; i >= 0; i--) {
            Hazard h = hazards.get(i);
            if (h.s + h.len < g.s - 30f) hazards.remove(i);
        }
        for (int i = forks.size() - 1; i >= 0; i--) if (forks.get(i).s1 < g.s - 30f) forks.remove(i);
    }

    // ------------------------------------------------------------------ sound

    private void sfx(int id) { if (id > 0) g.sound(id); }

    /** Ambient beds: cart rumble (pitch follows speed), river rush, sky wind; faded with the ride. */
    private void loops(float dt, int on) {
        float k = Math.min(1f, dt * 3f);
        float sp = g.speed / Game.BASE_SPEED;
        boolean cart = on == 1 && vehicle == CART && transition == TR_NONE;
        boolean boat = on == 1 && (vehicle == BOAT || transition == TR_CART_TO_BOAT);
        boolean sky = on == 1 && vehicle == GLIDER;
        fade(RideSfx.LOOP_CART, cart ? 0.55f : 0f, 0.8f + 0.35f * sp, k);
        fade(RideSfx.LOOP_RIVER, boat ? 0.5f : 0f, 1f, k);
        fade(RideSfx.LOOP_WIND, sky ? 0.35f + 0.4f * Math.max(0, -tiltY) : 0f, 0.9f + 0.3f * Math.max(0, -tiltY), k);
        fade(RideSfx.LOOP_CANOPY, sky ? 0.2f + 0.3f * Math.abs(tiltX) : 0f, 1f + 0.2f * Math.abs(tiltX), k);
    }

    private void fade(int l, float v, float p, float k) {
        loopVol[l] += (v - loopVol[l]) * k;
        loopPitch[l] += (p - loopPitch[l]) * k;
    }

    // ------------------------------------------------------------------ helpers

    private static boolean crossed(float a, float b, float m) {
        return a <= b ? (a < m && b >= m) : (a < m || b >= m);
    }

    static float clamp(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

    private static float dead(float v, float z) {
        float a = Math.abs(v);
        if (a < z) return 0;
        return Math.signum(v) * (a - z) / (1 - z);
    }

    static float smooth(float t) {
        t = clamp(t, 0, 1);
        return t * t * (3 - 2 * t);
    }

    private void shuffle(int[] a) {
        for (int i = a.length - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            int t = a[i]; a[i] = a[j]; a[j] = t;
        }
    }

    // ------------------------------------------------------------------ bot (headless sims and attract mode)

    /** Simple autopilot: steers to the clearest line ahead and crouches under low things. */
    public void autopilot() {
        if (!riding()) return;
        float look = vehicle == GLIDER ? 45f : 38f;
        if (vehicle == CART) {
            float best = -1e9f;
            int bt = track;
            for (int t = -1; t <= 1; t++) {
                if (trackBlocked(t) && t != track) continue;
                float sc = -Math.abs(t - track) * 0.5f;
                for (int i = 0; i < hazards.size(); i++) {
                    Hazard h = hazards.get(i);
                    float d = h.s - g.s;
                    if (d < -1 || d > look || Math.abs(h.x - t * TRACK_W) > h.w + 0.5f) continue;
                    if (h.type == H_BEAM || h.type == H_LOG || h.type == H_BATS) sc -= 2f;
                    else if (h.type != H_PILLAR) sc -= 100f / (1f + d * 0.1f);
                }
                if (sc > best) { best = sc; bt = t; }
            }
            rawX = bt < track ? -1 : bt > track ? 1 : 0;
            for (int i = 0; i < hazards.size(); i++) {
                Hazard h = hazards.get(i);
                float d = h.s - g.s;
                if ((h.type == H_BEAM || h.type == H_LOG || h.type == H_BATS) && d > -1 && d < 9f
                        && Math.abs(h.x - x) < h.w + 0.62f && crouchT < 0.3f) swipe(3);
            }
            return;
        }
        // boat and glider: sample candidate lines, pick the one with most clearance
        float bestX = x, bestA = alt, best = -1e9f;
        int na = vehicle == GLIDER ? 5 : 1;
        for (int ix = -6; ix <= 6; ix++) {
            float cx = ix * (vehicle == BOAT ? RIVER_HALF - BOAT_HALF : SKY_HALF) / 6f;
            for (int ia = 0; ia < na; ia++) {
                float ca = vehicle == GLIDER ? ALT_MIN + 0.5f + ia * (ALT_MAX - ALT_MIN - 1f) / (na - 1) : 0f;
                float sc = -Math.abs(cx - x) * 0.25f - Math.abs(ca - alt) * 0.2f;
                for (int i = 0; i < hazards.size(); i++) {
                    Hazard h = hazards.get(i);
                    float d = h.s - g.s;
                    if (d < -2 || d > look) continue;
                    if (h.type == H_THERMAL || h.type == H_GUST) continue;
                    float dx = Math.abs(cx - h.x) - h.w;
                    if (h.type == H_CABLE) { if (ca + 3.3f > h.y && ca + 0.2f < h.y) sc -= 60f; continue; }
                    if (h.type == H_SPIRE) { if (dx < 1.8f && ca < h.y + 0.5f) sc -= 60f; continue; }
                    if (h.type == H_ISLAND) { if (dx < 1.2f) sc -= 40f; continue; }
                    float dy = vehicle == GLIDER ? Math.abs(ca + 1.1f - h.y) - h.h : 0;
                    if (dx < 1.4f && dy < 1.4f) sc -= 50f / (1f + d * 0.05f);
                }
                if (sc > best) { best = sc; bestX = cx; bestA = ca; }
            }
        }
        rawX = clamp((bestX - x) * 0.6f, -1, 1);
        rawY = vehicle == GLIDER ? clamp((bestA - alt) * 0.5f + GL_SINK / GL_VERT, -1, 1) : 0;
    }
}
