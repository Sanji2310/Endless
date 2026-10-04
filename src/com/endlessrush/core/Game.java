package com.endlessrush.core;

import com.pongo.core.CaveSounds;
import com.pongo.core.Zones;

import java.util.ArrayList;
import java.util.Random;

/** Pure game simulation: no Android or GL dependencies. */
public final class Game {
    public interface Listener {
        void onSound(int id);
        void onMessage(String text);
        void onStateChanged(int state);
    }

    // sounds
    public static final int SND_COIN = 0, SND_JUMP = 1, SND_ROLL = 2, SND_SWIPE = 3, SND_STUMBLE = 4, SND_CRASH = 5,
            SND_POWER = 6, SND_BOARD = 7, SND_BREAK = 8, SND_KEY = 9, SND_MISSION = 10, SND_LAND = 11, SND_JET = 12,
            SND_CAUGHT = 13;
    public static final int SOUND_COUNT = 14;
    /** Zone sounds: SND_ZONE + a CaveSounds id, plus SND_ENTER_TUNNEL (whoosh, sting and lamp in one). */
    public static final int SND_ZONE = 100, SND_ENTER_TUNNEL = SND_ZONE + CaveSounds.COUNT;

    // states
    public static final int MENU = 0, RUNNING = 1, PAUSED = 2, DYING = 3, SAVE_ME = 4, GAME_OVER = 5;

    // obstacle types
    public static final int TRAIN = 0, RAMP = 1, LOW = 2, HIGH = 3, BLOCK = 4;
    // pickup types
    public static final int COIN = 0, MAGNET = 1, JETPACK = 2, SNEAKERS = 3, X2 = 4, MYSTERY = 5, KEY = 6;

    public static final float LANE_W = Models.LANE_W, TRAIN_H = Models.TRAIN_H;
    public static final float GRAVITY = 58f, JUMP_V = 16.5f, SNEAK_V = 24f, LAT_SPEED = 15f;
    public static final float BASE_SPEED = 17f, MAX_SPEED = 31f, TRAIN_SPEED = 12f;
    public static final float JET_Y = 8.5f, ROLL_TIME = 0.65f, BOARD_TIME = 30f;
    public static final float SAVE_ME_TIME = 4.5f;

    public static final class Obstacle {
        public int type, lane, variant, cars;
        public float s0, len, prevS0, x;
        public boolean moving, activated, dodged;
    }

    public static final class Pickup {
        public int type;
        public float x, y, s, phase;
        public boolean taken, pulled;
    }

    public final Profile profile;
    private final Listener listener;
    private final Random rng = new Random();

    public int state = MENU;
    public final ArrayList<Obstacle> obstacles = new ArrayList<Obstacle>();
    public final ArrayList<Pickup> pickups = new ArrayList<Pickup>();

    // player
    public int lane, prevLane;
    public float s, x, y, vy, speed, speedFactor = 1;
    public boolean grounded = true, rolling, rollQueued;
    public float rollT, airT, runTime, animPhase, landT;
    private float prevS, prevX, prevY;

    // timers
    public float chaseT, guardGap = 14, boardT, invulnT, jetT, jetMax, magT, magMax, sneakT, sneakMax, x2T, x2Max;
    public float deathT, saveMeT, shake;
    public int deathKind; // 0 crash, 1 caught
    public int revives;

    // run stats
    public float scoreF;
    public int coinsRun, keysRun, jumpsRun, rollsRun;
    private float stumbleFree;

    // generation
    private float genS, nextPowerS, lastMystery;

    /** Vehicle segments (cart, canoe, glider) and the set pieces between them. */
    public final Ride ride = new Ride(this);
    // zones: the run cycles Sakura Line -> Crystal Cavern -> ... (com.pongo.core.Zones); the set pieces between them
    // are obstacle-free and harmless, and the cave plays its own ambience and one-shots
    public final Zones zones = new Zones();
    /** EV_* bits crossed since the last call to takeZoneEvents() (the vehicle side reads EV_BOARD / EV_LEAVE). */
    private int zoneEvents;
    private float caveSoundT;
    private final Random ambRng = new Random(11);
    /** Set by the renderer when it draws the zone scenery (pongo.bin has the zone pieces). Without it the run looks
     *  like the Sakura Line all the way, so the zone sounds stay off too. */
    public boolean zoneScenery;

    public Game(Profile profile, Listener listener) {
        this.profile = profile;
        this.listener = listener;
        resetWorld();
    }

    public int score() { return (int) scoreF; }

    public int multiplier() { return profile.missions.multiplier * (x2T > 0 ? 2 : 1); }

    public int saveMeCost() { return 1 << Math.min(revives, 5); }

    private void setState(int st) {
        state = st;
        if (listener != null) listener.onStateChanged(st);
    }

    void sound(int id) { if (listener != null) listener.onSound(id); }

    private void message(String m) { if (listener != null) listener.onMessage(m); }

    private void resetWorld() {
        obstacles.clear();
        pickups.clear();
        lane = prevLane = 0;
        s = x = y = vy = 0;
        prevS = prevX = prevY = 0;
        speed = BASE_SPEED;
        speedFactor = 1;
        grounded = true;
        rolling = rollQueued = false;
        chaseT = 0; guardGap = 3; boardT = invulnT = jetT = magT = sneakT = x2T = 0;
        deathT = saveMeT = shake = 0;
        revives = 0;
        scoreF = 0; coinsRun = keysRun = jumpsRun = rollsRun = 0; stumbleFree = 0;
        runTime = 0;
        genS = 45;
        nextPowerS = 260;
        lastMystery = 0;
        ride.reset();
        coinLine(0, 18, 8, 3f);
        zones.reset();
        zoneEvents = 0;
        caveSoundT = 2f;
    }

    /** Back to the attract screen. */
    public void toMenu() {
        resetWorld();
        setState(MENU);
    }

    public void start() {
        resetWorld();
        profile.missions.startRun();
        chaseT = 2.2f;
        guardGap = 2.4f;
        setState(RUNNING);
        generate();
    }

    public void pause() { if (state == RUNNING) setState(PAUSED); }

    public void resume() { if (state == PAUSED) setState(RUNNING); }

    // ------------------------------------------------------------------ input

    public void left() { if (state == RUNNING && ride.swipe(0)) return; changeLane(-1); }

    public void right() { if (state == RUNNING && ride.swipe(1)) return; changeLane(1); }

    /** Phone tilt, normalised to -1..1 (x: right, y: toward the player). Used by the vehicle rides. */
    public void tilt(float tx, float ty) { ride.setTilt(tx, ty); }

    private void changeLane(int d) {
        if (state != RUNNING) return;
        int nl = lane + d;
        if (nl < -1 || nl > 1) {
            // pushing into the wall
            if (jetT <= 0) { shake = 0.15f; sound(SND_STUMBLE); }
            return;
        }
        prevLane = lane;
        lane = nl;
        sound(SND_SWIPE);
    }

    public void jump() {
        if (state == RUNNING && ride.swipe(2)) return;
        if (state != RUNNING || jetT > 0) return;
        if (grounded || airT < 0.12f) {
            vy = sneakT > 0 ? SNEAK_V : JUMP_V;
            grounded = false;
            airT = 1;
            rolling = false;
            rollQueued = false;
            jumpsRun++;
            mission(Missions.JUMPS, 1);
            sound(SND_JUMP);
        }
    }

    public void roll() {
        if (state == RUNNING && ride.swipe(3)) return;
        if (state != RUNNING || jetT > 0) return;
        if (!grounded) {
            vy = Math.min(vy, -38f);
            rollQueued = true;
        } else {
            startRoll();
        }
    }

    private void startRoll() {
        rolling = true;
        rollT = ROLL_TIME;
        rollsRun++;
        mission(Missions.ROLLS, 1);
        sound(SND_ROLL);
    }

    public boolean hoverboard() {
        if (state != RUNNING || boardT > 0 || profile.boards <= 0 || ride.active()) return false;
        profile.boards--;
        boardT = BOARD_TIME;
        mission(Missions.BOARDS, 1);
        sound(SND_BOARD);
        return true;
    }

    public boolean saveMe() {
        if (state != SAVE_ME) return false;
        int cost = saveMeCost();
        if (profile.keys < cost) return false;
        profile.keys -= cost;
        revives++;
        revive();
        return true;
    }

    public void declineSaveMe() {
        if (state == SAVE_ME) finishRun();
    }

    private void revive() {
        for (int i = obstacles.size() - 1; i >= 0; i--) {
            Obstacle o = obstacles.get(i);
            if (o.s0 < s + 55 && o.s0 + o.len > s - 4) obstacles.remove(i);
        }
        y = 0; vy = 0; grounded = true; rolling = false;
        x = lane * LANE_W;
        prevX = x; prevS = s; prevY = y;
        invulnT = 3f;
        chaseT = 0;
        speedFactor = 1;
        ride.onRevive();
        setState(RUNNING);
    }

    // ------------------------------------------------------------------ update

    public void update(float dt) {
        if (dt > 0.05f) dt = 0.05f;
        animPhase += dt;
        if (shake > 0) shake = Math.max(0, shake - dt);
        switch (state) {
            case RUNNING:
                step(dt);
                break;
            case DYING:
                deathT += dt;
                if (deathKind == 1) guardGap += (0.9f - guardGap) * Math.min(1, dt * 6);
                else guardGap += (2.0f - guardGap) * Math.min(1, dt * 1.5f);
                if (deathT > 1.4f) {
                    if (profile.keys >= saveMeCost() && revives < 6) {
                        saveMeT = SAVE_ME_TIME;
                        setState(SAVE_ME);
                    } else {
                        finishRun();
                    }
                }
                break;
            case SAVE_ME:
                saveMeT -= dt;
                if (saveMeT <= 0) finishRun();
                break;
            default:
                break;
        }
    }

    private void step(float dt) {
        runTime += dt;
        prevS = s; prevX = x; prevY = y;
        for (int i = 0; i < obstacles.size(); i++) obstacles.get(i).prevS0 = obstacles.get(i).s0;

        speedFactor = Math.min(1, speedFactor + dt * 0.35f);
        float target = Math.min(MAX_SPEED, BASE_SPEED + s * 0.0028f);
        speed = target * speedFactor * (ride.riding() ? ride.speedScale : 1f);
        s += speed * dt;

        // on a vehicle (or boarding one) the ride moves her; otherwise the runner rules below
        boolean riding = ride.step(dt);
        if (riding) chaseT = 0;

        // lateral
        if (!riding) {
            float tx = lane * LANE_W;
            float dx = tx - x;
            float mv = LAT_SPEED * dt;
            x = Math.abs(dx) <= mv ? tx : x + Math.signum(dx) * mv;
        }

        // timers
        if (boardT > 0) boardT = Math.max(0, boardT - dt);
        if (invulnT > 0) invulnT = Math.max(0, invulnT - dt);
        if (magT > 0) magT = Math.max(0, magT - dt);
        if (sneakT > 0) sneakT = Math.max(0, sneakT - dt);
        if (x2T > 0) x2T = Math.max(0, x2T - dt);
        if (chaseT > 0) chaseT = Math.max(0, chaseT - dt);
        guardGap += ((chaseT > 0 ? 2.4f : 16f) - guardGap) * Math.min(1, dt * (chaseT > 0 ? 3f : 0.6f));
        if (landT > 0) landT = Math.max(0, landT - dt);

        // moving trains
        for (int i = 0; i < obstacles.size(); i++) {
            Obstacle o = obstacles.get(i);
            if (!o.moving) continue;
            if (!o.activated && o.s0 - s < 175) o.activated = true;
            if (o.activated) o.s0 -= TRAIN_SPEED * dt;
            if (!o.dodged && o.s0 + o.len < s - 1) {
                o.dodged = true;
                mission(Missions.DODGE, 1);
            }
        }

        stepZones(dt);

        // vertical
        boolean lenient = invulnT > 0 || jetT > 0 || zones.invulnerable;
        if (riding) {
            airT = 0;
        } else if (jetT > 0) {
            jetT = Math.max(0, jetT - dt);
            y += (JET_Y - y) * Math.min(1, dt * 3f);
            vy = 0;
            grounded = false;
            rolling = false;
            if (jetT <= 0) invulnT = Math.max(invulnT, 1.8f);
        } else {
            vy -= GRAVITY * dt;
            y += vy * dt;
            float ground = surfaceAt(x, s, Math.max(prevY, y), lenient);
            if (y <= ground) {
                if (!grounded && vy < -8f) { landT = 0.18f; sound(SND_LAND); }
                y = ground;
                vy = 0;
                if (!grounded) {
                    grounded = true;
                    if (rollQueued) { rollQueued = false; startRoll(); }
                }
                airT = 0;
            } else {
                if (grounded && y - ground > 0.3f) grounded = false;
                if (grounded) { y = ground; vy = 0; } // stick to descending ramps
                else airT += dt;
            }
        }
        if (rolling) {
            rollT -= dt;
            if (rollT <= 0) rolling = false;
        }

        if (!lenient && !riding) collide();
        if (state != RUNNING) return;

        collectPickups(dt);

        float ds = s - prevS;
        scoreF += ds * multiplier() * 0.5f;
        stumbleFree += ds;
        mission2(profile.missions.setMax(Missions.STUMBLE_FREE, (int) stumbleFree));
        mission2(profile.missions.setMax(Missions.SCORE_RUN, score()));

        generate();
        cleanup();
    }

    /** Height of the walkable surface under the player. */
    public float surfaceAt(float px, float ps, float py, boolean lenient) {
        float g = 0;
        for (int i = 0; i < obstacles.size(); i++) {
            Obstacle o = obstacles.get(i);
            if (Math.abs(px - o.x) > 1.2f) continue;
            if (o.type == TRAIN) {
                if (ps >= o.s0 - 0.3f && ps <= o.s0 + o.len && (lenient || py >= TRAIN_H - 0.8f)) g = Math.max(g, TRAIN_H);
            } else if (o.type == RAMP) {
                if (ps >= o.s0 && ps <= o.s0 + o.len) {
                    float h = TRAIN_H * (ps - o.s0) / o.len;
                    if (lenient || py >= h - 1.0f) g = Math.max(g, h);
                }
            }
        }
        return g;
    }

    private void collide() {
        float ph = rolling ? 0.9f : 1.8f;
        for (int i = 0; i < obstacles.size(); i++) {
            Obstacle o = obstacles.get(i);
            float half = (o.type == TRAIN ? 1.1f : 1.0f) + 0.3f;
            if (Math.abs(x - o.x) >= half) continue;
            float far = o.s0 + o.len;
            if (s + 0.3f < o.s0 || s - 0.3f > far) continue;
            boolean hit;
            switch (o.type) {
                case TRAIN: hit = y < TRAIN_H - 0.8f; break;
                case RAMP: hit = y < TRAIN_H * (s - o.s0) / o.len - 1.0f; break;
                case LOW: hit = y < 0.95f; break;
                case HIGH: hit = y + ph > 1.5f && y < 2.4f; break;
                default: hit = y < 3.0f; break;
            }
            if (!hit) continue;
            boolean wasInS = prevS + 0.3f >= o.prevS0 && prevS - 0.3f <= o.prevS0 + o.len;
            boolean wasInX = Math.abs(prevX - o.x) < half;
            if (wasInS && !wasInX) {
                // clipped the side while changing lanes
                lane = prevLane;
                x = prevX;
                stumble();
                return;
            }
            crash(o);
            return;
        }
    }

    private void stumble() {
        shake = 0.3f;
        stumbleFree = 0;
        speedFactor = 0.8f;
        if (chaseT > 0) {
            if (boardT > 0) {
                breakBoard();
                return;
            }
            die(1);
            return;
        }
        chaseT = 4.5f;
        sound(SND_STUMBLE);
    }

    private void crash(Obstacle o) {
        if (boardT > 0) {
            obstacles.remove(o);
            breakBoard();
            return;
        }
        die(0);
    }

    private void breakBoard() {
        boardT = 0;
        invulnT = 2f;
        shake = 0.35f;
        sound(SND_BREAK);
    }

    void die(int kind) {
        deathKind = kind;
        deathT = 0;
        shake = 0.5f;
        rolling = false;
        sound(kind == 1 ? SND_CAUGHT : SND_CRASH);
        if (kind == 1) guardGap = Math.min(guardGap, 3f);
        setState(DYING);
    }

    private void finishRun() {
        profile.coins += coinsRun;
        if (score() > profile.highScore) profile.highScore = score();
        profile.totalRuns++;
        profile.save();
        setState(GAME_OVER);
    }

    private void collectPickups(float dt) {
        float cy = y + (rolling ? 0.5f : 0.9f);
        for (int i = 0; i < pickups.size(); i++) {
            Pickup p = pickups.get(i);
            if (p.taken) continue;
            p.phase += dt;
            if (p.type == COIN && magT > 0 && !p.pulled && p.s - s < 22 && p.s > s - 1 && Math.abs(p.x - x) < 6) p.pulled = true;
            if (p.pulled) {
                float k = Math.min(1, dt * 12);
                p.x += (x - p.x) * k;
                p.y += (cy - p.y) * k;
                p.s += (s + 0.5f - p.s) * k + speed * dt * 0.5f;
            }
            boolean inS = p.s >= prevS - 0.9f && p.s <= s + 0.9f;
            if (inS && Math.abs(p.x - x) < 1.0f && Math.abs(p.y - cy) < 1.5f) {
                p.taken = true;
                take(p);
            }
        }
    }

    private void take(Pickup p) {
        switch (p.type) {
            case COIN:
                coinsRun++;
                sound(SND_COIN);
                mission(Missions.COINS_TOTAL, 1);
                mission2(profile.missions.setMax(Missions.COINS_RUN, coinsRun));
                return;
            case KEY:
                keysRun++;
                profile.keys++;
                sound(SND_KEY);
                message("+1 KEY");
                mission(Missions.KEYS, 1);
                return;
            case MYSTERY:
                openMystery();
                return;
            default:
                break;
        }
        sound(SND_POWER);
        mission(Missions.POWERUPS, 1);
        switch (p.type) {
            case MAGNET: magT = magMax = profile.powerDuration(Profile.UP_MAGNET); message("COIN MAGNET"); break;
            case SNEAKERS: sneakT = sneakMax = profile.powerDuration(Profile.UP_SNEAK); message("SUPER SNEAKERS"); break;
            case X2: x2T = x2Max = profile.powerDuration(Profile.UP_X2); message("2X MULTIPLIER"); break;
            case JETPACK: startJet(); break;
            default: break;
        }
    }

    private void openMystery() {
        sound(SND_POWER);
        float r = rng.nextFloat();
        if (r < 0.12f) {
            profile.keys++;
            message("MYSTERY BOX: +1 KEY");
        } else if (r < 0.35f) {
            profile.boards++;
            message("MYSTERY BOX: +1 HOVERBOARD");
        } else {
            int c = r < 0.45f ? 1000 : r < 0.7f ? 350 : 150;
            profile.coins += c;
            message("MYSTERY BOX: +" + c + " COINS");
        }
    }

    private void startJet() {
        jetT = jetMax = profile.powerDuration(Profile.UP_JET);
        rolling = false;
        rollQueued = false;
        sound(SND_JET);
        message("JETPACK");
        // trail of sky coins
        float dist = jetT * speed * 1.05f;
        int ln = lane;
        for (float d = 18; d < dist - 10; d += 3.2f) {
            if (((int) (d / 40)) % 2 == 1 && ((int) ((d - 3.2f) / 40)) % 2 == 0) {
                ln = ln == 0 ? (rng.nextBoolean() ? 1 : -1) : 0;
            }
            Pickup p = new Pickup();
            p.type = COIN;
            p.x = ln * LANE_W;
            p.y = JET_Y + 0.9f;
            p.s = s + d;
            pickups.add(p);
        }
    }

    private void mission(int type, int amount) { mission2(profile.missions.add(type, amount)); }

    private void mission2(int idx) {
        if (idx < 0) return;
        Missions m = profile.missions;
        sound(SND_MISSION);
        message("MISSION COMPLETE!\n" + m.describe(idx));
        if (m.allDone()) {
            m.advance();
            message("SCORE MULTIPLIER x" + m.multiplier + "!");
        }
    }

    private void cleanup() {
        for (int i = obstacles.size() - 1; i >= 0; i--) {
            Obstacle o = obstacles.get(i);
            if (o.s0 + o.len < s - 25) obstacles.remove(i);
        }
        for (int i = pickups.size() - 1; i >= 0; i--) {
            Pickup p = pickups.get(i);
            if (p.taken || p.s < s - 12) pickups.remove(i);
        }
    }

    // ------------------------------------------------------------------ level generation

    private void generate() {
        // vehicle zones generate their own hazards (Ride); skip them and the set pieces either side
        if (ride.vehicle != Ride.NONE) {
            genS = Math.max(genS, Zones.safeTo(Zones.nextBoundary(s)));
            return;
        }
        while (genS < s + 240) {
            if (Zones.isVehicleZone(Zones.zoneAt(genS))) {
                genS = Zones.safeTo(Zones.nextBoundary(genS));
                continue;
            }
            float skip = Zones.skipSafe(genS);
            if (skip > genS) {
                // the set piece between zones: no obstacles, a line of coins down the lining
                coinLine(0, Zones.portalAt(Zones.nextBoundary(genS - 30f)) + 3f, 5, 3f);
                genS = skip;
                continue;
            }
            spawnPattern();
        }
    }

    // ------------------------------------------------------------------ zones

    private void stepZones(float dt) {
        int ev = zones.update(s, dt);
        zoneEvents |= ev;
        if (!zoneScenery) return;
        float b = Zones.nextBoundary(s), pb = b - Zones.ZONE_LEN;
        if ((ev & Zones.EV_PORTAL) != 0) sound(Zones.exitAt(b) ? SND_ZONE + CaveSounds.TUNNEL_WHOOSH : SND_ENTER_TUNNEL);
        if ((ev & Zones.EV_MOUTH) != 0 && Zones.exitAt(pb)) sound(SND_ZONE + CaveSounds.TUNNEL_WHOOSH);
        // cave one-shots over the ambience loop: drips, a crystal ringing, a bat somewhere up in the dark
        if (zones.zone == Zones.CAVERN && !zones.invulnerable) {
            caveSoundT -= dt;
            if (caveSoundT <= 0) {
                float r = ambRng.nextFloat();
                sound(SND_ZONE + (r < 0.6f ? CaveSounds.DRIP : r < 0.85f ? CaveSounds.CRYSTAL_CHIME : CaveSounds.BAT_SQUEAK));
                caveSoundT = 1.4f + ambRng.nextFloat() * 2.6f;
            }
        }
    }

    /** The EV_* bits crossed since the last call (cleared by the call). */
    public int takeZoneEvents() {
        int e = zoneEvents;
        zoneEvents = 0;
        return e;
    }

    /** Volume of the cave ambience loop (0..1): rises through the tunnel in, falls through the tunnel out. */
    public float caveAmbience() {
        return zoneScenery && state == RUNNING && zones.paletteZone == Zones.CAVERN ? zones.blend : 0f;
    }

    private float difficulty() { return Math.min(1f, genS / 5000f); }

    private float gap() { return 14f + Math.min(MAX_SPEED, BASE_SPEED + genS * 0.0028f) * 0.75f; }

    private void spawnPattern() {
        float d = difficulty();
        boolean power = genS >= nextPowerS;
        if (power) {
            nextPowerS = genS + 320 + rng.nextFloat() * 260;
            patternPower();
            return;
        }
        float r = rng.nextFloat();
        if (r < 0.10f - d * 0.05f) patternCoins();
        else if (r < 0.40f) patternBarriers();
        else if (r < 0.52f + d * 0.12f) patternMoving();
        else patternTrains();
    }

    private Obstacle add(int type, int lane, float s0, float len) {
        Obstacle o = new Obstacle();
        o.type = type;
        o.lane = lane;
        o.x = lane * LANE_W;
        o.s0 = o.prevS0 = s0;
        o.len = len;
        o.variant = rng.nextInt(4);
        obstacles.add(o);
        return o;
    }

    private Obstacle addTrain(int lane, float s0, int cars) {
        Obstacle o = add(TRAIN, lane, s0, cars * Models.CAR_LEN);
        o.cars = cars;
        return o;
    }

    private Pickup addPickup(int type, int lane, float ps, float py) {
        Pickup p = new Pickup();
        p.type = type;
        p.x = lane * LANE_W;
        p.s = ps;
        p.y = py;
        p.phase = rng.nextFloat() * 6;
        pickups.add(p);
        return p;
    }

    private float staticSurface(int lane, float ps) {
        float g = 0;
        for (int i = 0; i < obstacles.size(); i++) {
            Obstacle o = obstacles.get(i);
            if (o.lane != lane || o.moving) continue;
            if (o.type == TRAIN && ps >= o.s0 - 0.3f && ps <= o.s0 + o.len) g = Math.max(g, TRAIN_H);
            if (o.type == RAMP && ps >= o.s0 && ps <= o.s0 + o.len) g = Math.max(g, TRAIN_H * (ps - o.s0) / o.len);
        }
        return g;
    }

    private void coinLine(int lane, float s0, int n, float spacing) {
        for (int i = 0; i < n; i++) {
            float ps = s0 + i * spacing;
            addPickup(COIN, lane, ps, staticSurface(lane, ps) + 1.0f);
        }
    }

    private void coinArc(int lane, float centre) {
        for (int i = -3; i <= 3; i++) {
            float ps = centre + i * 2.2f;
            float t = i / 3.6f;
            addPickup(COIN, lane, ps, 1.0f + 2.3f * (1 - t * t));
        }
    }

    private int randLane() { return rng.nextInt(3) - 1; }

    private void maybeExtra(int lane, float ps, float py) {
        if (genS > 400 && rng.nextFloat() < 0.035f) addPickup(KEY, lane, ps, py);
        else if (genS - lastMystery > 700 && rng.nextFloat() < 0.08f) {
            lastMystery = genS;
            addPickup(MYSTERY, lane, ps, py);
        }
    }

    private void patternCoins() {
        int l = randLane();
        coinLine(l, genS, 10, 3f);
        maybeExtra(l, genS + 33, 1.0f);
        genS += 30 + gap() * 0.4f;
    }

    private void patternPower() {
        int l = randLane();
        coinLine(l, genS, 5, 3f);
        int[] types = {MAGNET, MAGNET, JETPACK, SNEAKERS, SNEAKERS, X2, X2};
        addPickup(types[rng.nextInt(types.length)], l, genS + 17, 1.1f);
        coinLine(l, genS + 21, 4, 3f);
        genS += 34 + gap() * 0.4f;
    }

    private void patternBarriers() {
        float d = difficulty();
        int[] t = new int[3];
        int blocks = 0, empties = 0;
        for (int l = 0; l < 3; l++) {
            float r = rng.nextFloat();
            if (r < 0.28f - d * 0.12f) t[l] = -1;
            else if (r < 0.58f) t[l] = LOW;
            else if (r < 0.84f) t[l] = HIGH;
            else t[l] = BLOCK;
            if (t[l] == BLOCK) blocks++;
            if (t[l] == -1) empties++;
        }
        if (blocks == 3) t[rng.nextInt(3)] = rng.nextBoolean() ? LOW : HIGH;
        if (empties == 3) t[rng.nextInt(3)] = LOW;
        float at = genS;
        for (int l = 0; l < 3; l++) {
            if (t[l] == -1) continue;
            add(t[l], l - 1, at, t[l] == BLOCK ? 1.0f : 0.4f);
        }
        // coins through a passable lane
        int cl = randLane();
        for (int k = 0; k < 3 && t[cl + 1] == BLOCK; k++) cl = randLane();
        if (t[cl + 1] == LOW) coinArc(cl, at + 0.2f);
        else if (t[cl + 1] == BLOCK) { /* none */ }
        else coinLine(cl, at - 9, 7, 3f);
        maybeExtra(cl, at + 12, 1.0f);
        genS = at + gap();
    }

    private void patternTrains() {
        float d = difficulty();
        float r = rng.nextFloat();
        int k = r < 0.25f + d * 0.4f ? 3 : r < 0.7f ? 2 : 1;
        int[] lanes = {-1, 0, 1};
        shuffle(lanes);
        int rampIdx = k == 3 || rng.nextFloat() < 0.45f ? rng.nextInt(k) : -1;
        float maxEnd = genS;
        int coinLaneDone = 0;
        for (int i = 0; i < k; i++) {
            int l = lanes[i];
            int cars = 1 + rng.nextInt(i == rampIdx ? 3 : 2);
            float start = genS + rng.nextFloat() * (i == rampIdx ? 4 : 12);
            if (i == rampIdx) {
                add(RAMP, l, start, Models.RAMP_LEN);
                start += Models.RAMP_LEN;
            }
            Obstacle o = addTrain(l, start, cars);
            maxEnd = Math.max(maxEnd, o.s0 + o.len);
            if (i == rampIdx) {
                coinLine(l, start - Models.RAMP_LEN + 1, (int) ((Models.RAMP_LEN + o.len - 2) / 3f), 3f);
                coinLaneDone = 1;
                if (rng.nextFloat() < 0.5f) maybeExtra(l, o.s0 + o.len - 3, TRAIN_H + 1.1f);
            }
        }
        if (k < 3) {
            int free = lanes[k];
            if (coinLaneDone == 0) coinLine(free, genS, 8, 3f);
            if (rng.nextFloat() < 0.3f + d * 0.4f) {
                int bt = rng.nextBoolean() ? LOW : HIGH;
                float bs = genS + 26;
                add(bt, free, bs, 0.4f);
            }
        }
        genS = maxEnd + gap() * 0.7f;
    }

    private void patternMoving() {
        int ml = randLane();
        float corridor = 95;
        int cars = 1 + rng.nextInt(2);
        Obstacle m = addTrain(ml, genS + corridor, cars);
        m.moving = true;
        m.variant = rng.nextInt(4);
        // bait coins in front of the oncoming train
        coinLine(ml, genS + 10, 8, 3f);
        // the other two lanes get something to deal with
        int a = ml == -1 ? 0 : -1, b = ml == 1 ? 0 : 1;
        if (rng.nextBoolean()) { int t = a; a = b; b = t; }
        float r = rng.nextFloat();
        if (r < 0.5f) {
            boolean ramp = rng.nextBoolean();
            float st = genS + 20;
            if (ramp) { add(RAMP, a, st, Models.RAMP_LEN); st += Models.RAMP_LEN; }
            addTrain(a, st, 2 + rng.nextInt(2));
            if (ramp) coinLine(a, genS + 21, 10, 3f);
        } else {
            add(rng.nextBoolean() ? LOW : HIGH, a, genS + 30, 0.4f);
        }
        if (rng.nextFloat() < 0.5f) add(rng.nextBoolean() ? LOW : HIGH, b, genS + 60, 0.4f);
        genS = m.s0 + m.len + gap() * 0.5f;
    }

    private void shuffle(int[] a) {
        for (int i = a.length - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            int t = a[i]; a[i] = a[j]; a[j] = t;
        }
    }
}
