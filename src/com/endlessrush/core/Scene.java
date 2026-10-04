package com.endlessrush.core;

/** Turns the game state into a camera + draw list. World: x right, y up, z = -distance. */
public final class Scene {
    private float camX, camY = 5.5f, camZOff = 6.6f, menuT;
    private int menuChar = -1;
    private float charSpin;

    /**
     * Set by the renderer when the toon layer (PongoScene) draws the heroine and the Mon coins on top of this
     * scene: the body of hero 0 and the coins are then left out here (her blob shadow, board and gear stay).
     */
    public boolean toonHero, toonCoins;
    /** Set when ZoneWorld draws the set pieces and the cavern: city segments are then left out where it owns the
     *  world (com.pongo.core.Zones.cityWorldAt / cityTrackAt). */
    public boolean toonWorld;

    /** Character shown on the menu / shop (overrides profile selection when >= 0). */
    public void setPreviewCharacter(int idx) { menuChar = idx; }

    /** Hero currently on screen. */
    public int heroIndex(Game g) { return menuChar >= 0 ? menuChar : g.profile.selected; }

    public void build(Game g, DrawList dl, float aspect, float dt) {
        dl.clear();
        menuT += dt;
        charSpin += dt;
        float ps = g.s, pz = -ps;
        boolean menu = g.state == Game.MENU;

        // ---------------- camera
        float jet = g.jetT > 0 ? 1 : 0;
        float targetCamY = 4.7f + g.y * 0.6f + jet * 1.2f;
        camX += (g.x * 0.85f - camX) * Math.min(1, dt * 8);
        camY += (targetCamY - camY) * Math.min(1, dt * 4);
        float sh = g.shake > 0 ? g.shake * 0.6f : 0;
        float shx = sh * (float) Math.sin(menuT * 70), shy = sh * (float) Math.cos(menuT * 53);
        float ex, ey, ez, cx, cy, cz;
        if (menu) {
            float a = (float) Math.sin(menuT * 0.4f) * 0.35f;
            // camera in front of the runner, looking back at them
            ex = (float) Math.sin(a) * 6.5f + 0.4f;
            ey = 2.2f;
            ez = pz - 6.5f * (float) Math.cos(a);
            cx = 0; cy = 1.05f; cz = pz;
        } else {
            ex = camX + shx;
            ey = camY + shy;
            ez = pz + camZOff;
            cx = camX * 0.95f;
            cy = camY - 3.4f + g.y * 0.1f;
            cz = pz - 8f;
        }
        Mat4.lookAt(dl.view, ex, ey, ez, cx, cy, cz, 0, 1, 0);
        float depth = 6.6f;
        float fov = (float) Math.toDegrees(2 * Math.atan((3.4 / depth) / aspect));
        if (fov > 84) fov = 84;
        if (fov < 55) fov = 55;
        if (menu) fov = aspect < 1 ? 62 : 45;
        Mat4.perspective(dl.proj, fov, aspect, 0.3f, 420f);
        Mat4.mul(dl.viewProj, dl.proj, dl.view);
        dl.camPos[0] = ex; dl.camPos[1] = ey; dl.camPos[2] = ez;

        // ---------------- sky
        float[] m = dl.add(Models.sky, 1, 1, 1, 1, 0, DrawList.F_NOFOG | DrawList.F_NODEPTH | DrawList.F_UNLIT);
        Mat4.translate(m, ex, 0, ez);
        m = dl.add(Models.sun, 1, 1, 1, 1, 0, DrawList.F_NOFOG | DrawList.F_NODEPTH | DrawList.F_UNLIT);
        Mat4.translate(m, ex + 120, 150, ez - 300);
        Mat4.rotX(m, 60);
        for (int i = 0; i < 6; i++) {
            float cxp = ex + (i * 97 % 360) - 180 + (float) Math.sin(i) * 20;
            float czp = ez - 260 - (i % 3) * 30;
            m = dl.add(Models.cloud, 1, 1, 1, 1, 0.9f, DrawList.F_NOFOG | DrawList.F_NODEPTH);
            Mat4.translate(m, cxp, 70 + (i % 3) * 22, czp);
        }

        // ---------------- environment segments
        float segLen = Models.SEG_LEN;
        int k0 = (int) Math.floor((ps - (menu ? 160 : 14)) / segLen), k1 = (int) Math.floor((ps + 185) / segLen);
        for (int k = k0; k <= k1; k++) {
            float z = -k * segLen;
            if (toonWorld && !com.pongo.core.Zones.cityTrackAt(k * segLen)) continue;
            m = dl.add(Models.track);
            Mat4.translate(m, 0, 0, z);
            if (toonWorld && !com.pongo.core.Zones.cityWorldAt(k * segLen)) continue;
            int h = hash(k);
            float bx = Models.LANE_W * 1.5f + 6.2f;
            m = dl.add(Models.buildings[h % Models.buildings.length]);
            Mat4.translate(m, bx, 0, z);
            m = dl.add(Models.buildings[(h >> 4) % Models.buildings.length]);
            Mat4.translate(m, -bx, 0, z - segLen);
            Mat4.rotY(m, 180);
            if (k % 2 == 0) {
                m = dl.add(Models.lamp);
                Mat4.translate(m, bx - 1.6f, 0, z - 3);
                m = dl.add(Models.lamp);
                Mat4.translate(m, -bx + 1.6f, 0, z - 9);
                Mat4.rotY(m, 180);
            }
            if ((h >> 8) % 5 == 0) {
                m = dl.add(Models.tree);
                Mat4.translate(m, -bx + 2.2f, 0, z - 6);
            }
            if (k % 25 == 7) {
                m = dl.add(Models.bridge);
                Mat4.translate(m, 0, 0, z - 6);
            }
        }

        // ---------------- obstacles
        for (int i = 0; i < g.obstacles.size(); i++) {
            Game.Obstacle o = g.obstacles.get(i);
            if (o.s0 > ps + 190 || o.s0 + o.len < ps - 12) continue;
            float oz = -o.s0;
            switch (o.type) {
                case Game.TRAIN:
                    for (int c = 0; c < o.cars; c++) {
                        Mesh mesh = c == 0 ? Models.trainFront[o.variant] : Models.trainMid[o.variant];
                        m = dl.add(mesh, 1, 1, 1, 1, 0, 0);
                        Mat4.translate(m, o.x, 0, oz - c * Models.CAR_LEN);
                        if (o.moving && c == 0) {
                            // headlights glow on oncoming trains
                            float[] l = dl.add(Models.shadow, 1f, 0.95f, 0.6f, 0.5f, 3f, DrawList.F_BLEND);
                            Mat4.translate(l, o.x, 0.05f, oz + 3);
                            Mat4.scale(l, 1.6f, 1, 4f);
                        }
                    }
                    break;
                case Game.RAMP:
                    m = dl.add(Models.ramp);
                    Mat4.translate(m, o.x, 0, oz);
                    break;
                case Game.LOW:
                    m = dl.add(Models.barrierLow);
                    Mat4.translate(m, o.x, 0, oz);
                    break;
                case Game.HIGH:
                    m = dl.add(Models.barrierHigh);
                    Mat4.translate(m, o.x, 0, oz);
                    break;
                default:
                    m = dl.add(Models.block);
                    Mat4.translate(m, o.x, 0, oz);
                    break;
            }
        }

        // ---------------- pickups
        for (int i = 0; i < g.pickups.size(); i++) {
            Game.Pickup p = g.pickups.get(i);
            if (p.taken || p.s > ps + 170 || p.s < ps - 10) continue;
            if (toonCoins && p.type == Game.COIN) continue;
            float spin = (menuT * 180 + p.s * 7) % 360;
            float bob = p.type == Game.COIN ? 0 : (float) Math.sin(menuT * 3 + p.s) * 0.15f;
            Mesh mesh;
            float sc = 1, emis = 0.15f;
            switch (p.type) {
                case Game.COIN: mesh = Models.coin; emis = 0.35f; break;
                case Game.MAGNET: mesh = Models.magnet; sc = 1.4f; emis = 0.4f; break;
                case Game.JETPACK: mesh = Models.jetpack; sc = 1.3f; emis = 0.4f; break;
                case Game.SNEAKERS: mesh = Models.sneaker; sc = 1.4f; emis = 0.4f; break;
                case Game.X2: mesh = Models.x2; sc = 1.2f; emis = 0.45f; spin = (float) Math.sin(menuT * 2) * 35; break;
                case Game.MYSTERY: mesh = Models.mystery; sc = 1.1f; emis = 0.3f; break;
                default: mesh = Models.key; sc = 1.6f; emis = 0.6f; break;
            }
            m = dl.add(mesh, 1, 1, 1, 1, emis, 0);
            Mat4.translate(m, p.x, p.y + bob, -p.s);
            Mat4.rotY(m, spin);
            if (sc != 1) Mat4.scale(m, sc, sc, sc);
        }

        // ---------------- player
        drawPlayer(g, dl, pz, menu);

        // ---------------- guard & dog
        if (!menu && g.guardGap < 12 && g.state != Game.GAME_OVER && g.state != Game.SAVE_ME) {
            drawGuard(g, dl, pz + g.guardGap + 0.2f, g.x * 0.6f - 0.6f, g.state == Game.DYING && g.deathKind == 1);
        }

        // speed lines when fast / on a jetpack
        if (!menu && g.state == Game.RUNNING && (g.speed > 26 || g.jetT > 0)) {
            for (int i = 0; i < 10; i++) {
                float lx = g.x + ((hash(i * 31 + (int) (menuT * 6)) % 100) / 100f - 0.5f) * 9;
                float ly = g.y + 0.5f + (hash(i * 17 + (int) (menuT * 6)) % 100) / 100f * 4;
                float lz = pz - ((menuT * 60 + i * 7) % 18);
                m = dl.add(Models.speedLine, 1, 1, 1, 1, 1, DrawList.F_BLEND | DrawList.F_NOFOG);
                Mat4.translate(m, lx, ly, lz);
            }
        }
    }

    private void drawPlayer(Game g, DrawList dl, float pz, boolean menu) {
        int ci = heroIndex(g);
        Mesh[] parts = Models.runner[ci];
        boolean toon = toonHero && ci == 0;
        float t = g.animPhase;
        boolean blink = g.invulnT > 0 && ((int) (g.invulnT * 12)) % 2 == 0;
        float alpha = 1;
        float emis = blink ? 0.6f : 0;

        float px = g.x, py = g.y;
        float ground = g.state == Game.MENU ? 0 : Math.max(0, g.surfaceAt(g.x, g.s, g.y + 0.1f, false));
        // blob shadow
        float sh = Math.max(0.3f, 1 - (py - ground) * 0.12f);
        float[] m = dl.add(Models.shadow, 1, 1, 1, 0.9f * sh, 0, DrawList.F_BLEND);
        Mat4.translate(m, px, ground + 0.03f, pz);
        Mat4.scale(m, sh, 1, sh);

        float[] root = new float[16];
        Mat4.setIdentity(root);
        Mat4.translate(root, px, py, pz);

        boolean board = g.boardT > 0;
        boolean dying = g.state == Game.DYING || g.state == Game.SAVE_ME || g.state == Game.GAME_OVER;
        float lean = 0;
        if (!menu && !dying) lean = (g.lane * Game.LANE_W - g.x) * -6f;
        Mat4.rotZ(root, lean);

        if (board && !menu) {
            float[] bm = dl.add(Models.hoverboard, 1, 1, 1, 1, 0.3f + 0.2f * (float) Math.sin(t * 8), 0);
            Mat4.copy(bm, root);
            Mat4.translate(bm, 0, 0.32f + (float) Math.sin(t * 5) * 0.05f, 0);
            Mat4.translate(root, 0, 0.4f, 0);
        }

        // pose
        float legL = 0, legR = 0, armL = 0, armR = 0, torsoPitch = 0, bob = 0, headPitch = 0;
        float armSpreadL = 0, armSpreadR = 0;
        float rollAngle = 0;
        if (menu) {
            float br = (float) Math.sin(t * 2);
            armL = 8 + br * 3; armR = -8 - br * 3;
            armSpreadL = 12; armSpreadR = -12;
            bob = br * 0.02f;
            headPitch = br * 3;
        } else if (dying) {
            float k = Math.min(1, g.deathT * 3);
            if (g.deathKind == 0) {
                // knocked backwards off the obstacle
                Mat4.translate(root, 0, 0, 0.8f * k);
                Mat4.rotX(root, 70 * k);
                armL = armR = -150 * k;
                legL = 20; legR = -10;
            } else {
                armL = -60; armR = -60; armSpreadL = 30; armSpreadR = -30;
                legL = 10; legR = -10; headPitch = -15;
            }
        } else if (g.jetT > 0) {
            legL = 15; legR = 25; armL = armR = 30; armSpreadL = 25; armSpreadR = -25;
            torsoPitch = -15;
        } else if (g.rolling) {
            rollAngle = (1 - g.rollT / Game.ROLL_TIME) * -720;
        } else if (!g.grounded) {
            float up = g.vy > 0 ? 1 : 0;
            legL = -60 * up - 20; legR = 35; armL = 120 * up + 20; armR = -60;
            armSpreadL = 15; armSpreadR = -15;
            torsoPitch = -8;
        } else if (board) {
            legL = -10; legR = 15; armL = -20; armR = 30; armSpreadL = 45; armSpreadR = -45;
            bob = (float) Math.sin(t * 5) * 0.03f;
            torsoPitch = -5;
        } else {
            float f = t * g.speed * 0.55f;
            float sw = (float) Math.sin(f);
            legL = sw * 55; legR = -sw * 55;
            armL = -sw * 60; armR = sw * 60;
            armSpreadL = 6; armSpreadR = -6;
            bob = Math.abs((float) Math.cos(f)) * 0.12f;
            torsoPitch = -10;
            if (g.landT > 0) bob -= g.landT * 0.8f;
        }

        float[] body = root.clone();
        Mat4.translate(body, 0, bob, 0);
        if (rollAngle != 0) {
            // tuck into a ball and tumble
            Mat4.translate(body, 0, 0.55f, 0);
            Mat4.rotX(body, rollAngle);
            Mat4.scale(body, 0.6f, 0.6f, 0.6f);
            Mat4.translate(body, 0, -0.95f, 0);
            legL = legR = -110; armL = armR = -90;
            torsoPitch = -40; headPitch = -20;
        }
        float hipY = 0.95f;
        float[] torso = body.clone();
        Mat4.translate(torso, 0, hipY, 0);
        Mat4.rotX(torso, torsoPitch);
        if (!toon) {
            // legs
            part(dl, parts[Models.P_LEG], body, -0.13f, hipY, 0, legL, 0, alpha, emis);
            part(dl, parts[Models.P_LEG], body, 0.13f, hipY, 0, legR, 0, alpha, emis);
            // torso
            float[] tm = dl.add(parts[Models.P_TORSO], 1, 1, 1, alpha, emis, 0);
            Mat4.copy(tm, torso);
            // head
            float[] hm = dl.add(parts[Models.P_HEAD], 1, 1, 1, alpha, emis, 0);
            Mat4.copy(hm, torso);
            Mat4.translate(hm, 0, 0.6f, 0);
            Mat4.rotX(hm, headPitch);
            if (menu) Mat4.rotY(hm, (float) Math.sin(t * 0.7f) * 12);
            // arms
            part(dl, parts[Models.P_ARM], torso, -0.34f, 0.52f, 0, armL, armSpreadL, alpha, emis);
            part(dl, parts[Models.P_ARM], torso, 0.34f, 0.52f, 0, armR, armSpreadR, alpha, emis);
        }
        // jetpack
        if (g.jetT > 0 && !menu) {
            float[] jm = dl.add(Models.jetBack, 1, 1, 1, 1, 0.1f, 0);
            Mat4.copy(jm, torso);
            Mat4.translate(jm, 0, 0.3f, 0.36f);
            for (int s = -1; s <= 1; s += 2) {
                float fl = 0.8f + 0.4f * (float) Math.abs(Math.sin(t * 40 + s));
                float[] fm = dl.add(Models.flame, 1, 1, 1, 1, 1.2f, DrawList.F_NOFOG);
                Mat4.copy(fm, torso);
                Mat4.translate(fm, s * 0.16f, -0.1f, 0.36f);
                Mat4.scale(fm, 1, fl, 1);
            }
        }
        if (g.sneakT > 0 && !menu) {
            // glowing feet trail
            float[] sm = dl.add(Models.shadow, 0.2f, 1f, 0.5f, 0.5f, 2f, DrawList.F_BLEND);
            Mat4.translate(sm, px, py + 0.05f, pz + 0.6f);
            Mat4.scale(sm, 0.5f, 1, 1.4f);
        }
        if (g.magT > 0 && !menu) {
            float[] mm = dl.add(Models.magnet, 1, 1, 1, 1, 0.3f, 0);
            Mat4.copy(mm, torso);
            Mat4.translate(mm, 0.5f, 0.2f, -0.3f);
            Mat4.scale(mm, 0.5f, 0.5f, 0.5f);
        }
    }

    private static void part(DrawList dl, Mesh mesh, float[] parent, float x, float y, float z, float pitch, float roll,
                             float alpha, float emis) {
        float[] m = dl.add(mesh, 1, 1, 1, alpha, emis, 0);
        Mat4.copy(m, parent);
        Mat4.translate(m, x, y, z);
        if (pitch != 0) Mat4.rotX(m, pitch);
        if (roll != 0) Mat4.rotZ(m, roll);
    }

    private void drawGuard(Game g, DrawList dl, float gz, float gx, boolean grabbing) {
        float t = g.animPhase;
        float f = t * 11;
        float sw = grabbing ? 0 : (float) Math.sin(f);
        float[] shadowM = dl.add(Models.shadow, 1, 1, 1, 0.8f, 0, DrawList.F_BLEND);
        Mat4.translate(shadowM, gx, 0.03f, gz);
        Mat4.scale(shadowM, 1.2f, 1, 1.2f);
        float[] root = new float[16];
        Mat4.setIdentity(root);
        Mat4.translate(root, gx, Math.abs((float) Math.cos(f)) * 0.1f, gz);
        Mat4.scale(root, 1.1f, 1.1f, 1.1f);
        part(dl, Models.gLeg, root, -0.16f, 0.95f, 0, sw * 45, 0, 1, 0);
        part(dl, Models.gLeg, root, 0.16f, 0.95f, 0, -sw * 45, 0, 1, 0);
        float[] torso = root.clone();
        Mat4.translate(torso, 0, 0.95f, 0);
        Mat4.rotX(torso, -8);
        float[] tm = dl.add(Models.gTorso);
        Mat4.copy(tm, torso);
        float[] hm = dl.add(Models.gHead);
        Mat4.copy(hm, torso);
        Mat4.translate(hm, 0, 0.72f, 0);
        float armA = grabbing ? -95 : -sw * 50;
        float armB = grabbing ? -95 : sw * 50;
        if (!grabbing && g.chaseT > 0) armB = -130 + sw * 20; // shaking a fist
        part(dl, Models.gArm, torso, -0.43f, 0.62f, 0, armA, 8, 1, 0);
        part(dl, Models.gArm, torso, 0.43f, 0.62f, 0, armB, -8, 1, 0);

        // dog runs alongside
        float dx = gx + 1.0f, dz = gz - 0.6f;
        float df = t * 16;
        float[] droot = new float[16];
        Mat4.setIdentity(droot);
        Mat4.translate(droot, dx, 0.62f + Math.abs((float) Math.sin(df)) * 0.12f, dz);
        float[] db = dl.add(Models.dogBody);
        Mat4.copy(db, droot);
        float[] dh = dl.add(Models.dogHead);
        Mat4.copy(dh, droot);
        Mat4.translate(dh, 0, 0.22f, -0.45f);
        float ls = (float) Math.sin(df) * 40;
        part(dl, Models.dogLeg, droot, -0.12f, -0.1f, -0.3f, ls, 0, 1, 0);
        part(dl, Models.dogLeg, droot, 0.12f, -0.1f, -0.3f, -ls, 0, 1, 0);
        part(dl, Models.dogLeg, droot, -0.12f, -0.1f, 0.3f, -ls, 0, 1, 0);
        part(dl, Models.dogLeg, droot, 0.12f, -0.1f, 0.3f, ls, 0, 1, 0);
    }

    private static int hash(int k) {
        int h = k * 0x45d9f3b;
        h = ((h >>> 16) ^ h) * 0x45d9f3b;
        h = (h >>> 16) ^ h;
        return h & 0x7fffffff;
    }
}
