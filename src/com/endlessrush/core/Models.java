package com.endlessrush.core;

/** Every 3D model in the game, generated procedurally at startup. */
public final class Models {
    public static final float LANE_W = 2.4f;
    public static final float TRAIN_H = 3.3f;
    public static final float TRAIN_W = 2.2f;
    public static final float CAR_LEN = 12f;
    public static final float SEG_LEN = 12f;
    public static final float RAMP_LEN = 8f;

    public static Mesh track, lamp, tree, bridge, shadow, sky, cloud, sun;
    public static Mesh[] buildings = new Mesh[6];
    public static Mesh[] trainFront = new Mesh[4], trainMid = new Mesh[4];
    public static Mesh ramp, barrierLow, barrierHigh, block;
    public static Mesh coin, magnet, jetpack, sneaker, x2, mystery, key;
    public static Mesh hoverboard, jetBack, flame, speedLine;
    public static Mesh[][] runner; // [character][part]
    public static final int P_TORSO = 0, P_HEAD = 1, P_ARM = 2, P_LEG = 3;
    public static Mesh gTorso, gHead, gArm, gLeg, dogBody, dogLeg, dogHead;

    private static boolean built;

    public static synchronized void build() {
        if (built) return;
        MeshBuilder b = new MeshBuilder();
        track = buildTrack(b);
        for (int i = 0; i < buildings.length; i++) buildings[i] = buildBuilding(b, i);
        lamp = buildLamp(b);
        tree = buildTree(b);
        bridge = buildBridge(b);
        int[][] schemes = {
                {0xD8342C, 0xF2F2F2, 0x7A1612}, {0x2F6FD6, 0xF7D23E, 0x163A7A},
                {0x2AA65A, 0xF2F2F2, 0x13552C}, {0xF0A020, 0x333333, 0x8A5A0A}};
        for (int i = 0; i < 4; i++) {
            trainFront[i] = buildTrain(b, schemes[i], true);
            trainMid[i] = buildTrain(b, schemes[i], false);
        }
        ramp = buildRamp(b);
        barrierLow = buildBarrierLow(b);
        barrierHigh = buildBarrierHigh(b);
        block = buildBlock(b);
        coin = buildCoin(b);
        magnet = buildMagnet(b);
        jetpack = buildJetpack(b, true);
        jetBack = buildJetpack(b, false);
        sneaker = buildSneaker(b);
        x2 = buildX2(b);
        mystery = buildMystery(b);
        key = buildKey(b);
        hoverboard = buildBoard(b);
        flame = b.color(0xFFB02E).frustum(0, -0.35f, 0, 0.13f, 0.0f, 0.7f, 8, true, false)
                .color(0xFFF3A0).frustum(0, -0.2f, 0, 0.08f, 0.0f, 0.4f, 6, true, false).build();
        speedLine = b.color(0xFFFFFF).alpha(0.35f).box(0, 0, 0, 0.04f, 0.04f, 3f).build();
        shadow = b.color(0x000000).alpha(0.35f).disc(0, 0, 0, 0.6f, 16).build();
        sky = buildSky(b);
        cloud = b.color(0xFFFFFF).sphere(0, 0, 0, 14, 5, 8, 4, 8).sphere(10, -1, 2, 10, 4, 7, 4, 8)
                .sphere(-11, -1, 1, 9, 3.5f, 6, 4, 8).build();
        sun = b.color(0xFFF6C8).disc(0, 0, 0, 22, 20).build();

        runner = new Mesh[CharacterDef.ALL.length][];
        for (int i = 0; i < runner.length; i++) runner[i] = buildRunner(b, CharacterDef.ALL[i]);
        buildGuard(b);
        buildDog(b);
        built = true;
    }

    // ---------------------------------------------------------------- environment

    private static Mesh buildTrack(MeshBuilder b) {
        float L = SEG_LEN, zc = -L / 2;
        float halfTrack = LANE_W * 1.5f + 0.9f;
        // ground under everything
        b.color(0x6E6259).box(0, -0.15f, zc, halfTrack * 2, 0.3f, L);
        for (int lane = -1; lane <= 1; lane++) {
            float x = lane * LANE_W;
            b.color(0x857767).taperBox(x, 0.02f, zc, 2.1f, 0.14f, L, 0.9f, 1f);
            for (int i = 0; i < 12; i++) {
                b.color(i % 2 == 0 ? 0x5B3F2B : 0x654632).box(x, 0.13f, -0.5f - i, 1.9f, 0.1f, 0.34f);
            }
            for (int s = -1; s <= 1; s += 2) {
                b.color(0x4A4A52).box(x + s * 0.62f, 0.22f, zc, 0.14f, 0.12f, L);
                b.color(0xC9CDD6).box(x + s * 0.62f, 0.3f, zc, 0.12f, 0.05f, L);
            }
        }
        // walls & sidewalks
        for (int s = -1; s <= 1; s += 2) {
            float wx = s * (halfTrack + 0.3f);
            b.color(0x9C9C9C).box(wx, 0.6f, zc, 0.6f, 1.2f, L);
            b.color(0xB5B5B5).box(wx, 1.25f, zc, 0.75f, 0.12f, L);
            b.color(0x7E858C).box(s * (halfTrack + 3.2f), 0.2f, zc, 5.2f, 0.4f, L);
            b.color(0x646B72).box(s * (halfTrack + 0.9f), 0.42f, zc, 0.3f, 0.06f, L);
            // graffiti panels on the wall
            int[] g = {0xFF4E8A, 0x39D1FF, 0xFFD23A, 0x7CFF6B};
            b.color(g[(s + 1) / 2]).box(wx - s * 0.31f, 0.65f, zc - 2.5f, 0.02f, 0.6f, 3.2f);
            b.color(g[2 + (s + 1) / 2]).box(wx - s * 0.31f, 0.55f, zc + 3.1f, 0.02f, 0.4f, 1.8f);
        }
        return b.build();
    }

    private static final int[] WALLS = {0xB5553C, 0xD9B48F, 0x6F8FAF, 0xE3D8C3, 0x8C6D9E, 0xC98E4A};
    private static final int[] WINDOWS = {0x2C3E57, 0x3A4E6E, 0x9BD1F2, 0x33415C, 0x283248, 0x324A63};

    /** Building facade facing -X (placed on the right side of the track). */
    private static Mesh buildBuilding(MeshBuilder b, int v) {
        float L = SEG_LEN - 0.6f, zc = -SEG_LEN / 2;
        float h = new float[]{11, 8, 18, 7, 14, 9}[v];
        float depth = 8;
        int wall = WALLS[v], win = WINDOWS[v];
        b.color(wall).box(depth / 2, h / 2, zc, depth, h, L);
        b.color(darken(wall, 0.75f)).box(depth / 2, h + 0.2f, zc, depth + 0.3f, 0.4f, L + 0.3f);
        if (v == 2) { // glassy tower: vertical bands
            for (int i = 0; i < 5; i++) b.color(win).box(-0.03f, h / 2 + 0.5f, zc - L / 2 + 1.2f + i * 2.2f, 0.1f, h - 2.5f, 1.4f);
        } else {
            int floors = (int) ((h - 2.5f) / 2.6f);
            for (int f = 0; f < floors; f++) {
                float y = 3.6f + f * 2.6f;
                for (int i = 0; i < 4; i++) {
                    float z = zc - L / 2 + 1.6f + i * 2.7f;
                    b.color(0xEDE6D8).box(-0.04f, y, z, 0.1f, 1.5f, 1.3f);
                    b.color(((f + i + v) % 5 == 0) ? 0xFFE7A0 : win).box(-0.1f, y, z, 0.1f, 1.3f, 1.1f);
                }
            }
        }
        // ground floor shop with awning
        int aw = new int[]{0xE94B3C, 0x2BA3E0, 0xF2B233, 0x3DBE6C, 0xE85FA8, 0x7A5AE0}[v];
        b.color(0x2A2F3A).box(-0.05f, 1.3f, zc, 0.12f, 2.2f, L - 3);
        b.color(0x9FD6F5).box(-0.1f, 1.4f, zc, 0.06f, 1.6f, L - 4);
        b.push().translate(-0.9f, 2.7f, zc).rotZ(-18).color(aw).box(0, 0, 0, 1.9f, 0.12f, L - 2.6f).pop();
        for (int i = 0; i < 5; i++) b.color(0xFFFFFF).box(-1.3f, 2.4f, zc - L / 2 + 2 + i * 2.1f, 0.4f, 0.1f, 0.9f);
        if (v % 2 == 0) { // rooftop water tank / AC units
            b.color(0x7B5A3C).cylinder(depth / 2, h + 1.6f, zc, 1.1f, 2.4f, 10);
            b.color(0x55412C).frustum(depth / 2, h + 3.1f, zc, 1.2f, 0, 0.8f, 10, true, false);
        } else {
            b.color(0xA7ADB5).box(depth / 2, h + 0.8f, zc - 2, 1.6f, 1.0f, 1.6f);
            b.color(0xA7ADB5).box(depth / 2 + 1, h + 0.8f, zc + 2, 1.2f, 1.0f, 1.2f);
        }
        return b.build();
    }

    private static Mesh buildLamp(MeshBuilder b) {
        b.color(0x3C4450).cylinder(0, 3, 0, 0.1f, 6, 8);
        b.color(0x3C4450).box(-0.7f, 6, 0, 1.5f, 0.12f, 0.12f);
        b.color(0xFFF1B0).box(-1.35f, 5.85f, 0, 0.45f, 0.18f, 0.3f);
        b.color(0x2B3038).cylinder(0, 0.2f, 0, 0.22f, 0.4f, 8);
        return b.build();
    }

    private static Mesh buildTree(MeshBuilder b) {
        b.color(0x6B4A2F).cylinder(0, 1.2f, 0, 0.22f, 2.4f, 7);
        b.color(0x3E9D46).sphere(0, 3.4f, 0, 1.6f, 1.4f, 1.6f, 5, 8);
        b.color(0x57B85A).sphere(0.5f, 4.3f, 0.3f, 1.0f, 0.9f, 1.0f, 4, 7);
        return b.build();
    }

    private static Mesh buildBridge(MeshBuilder b) {
        float span = 30;
        float by = 17f;
        b.color(0x8A8F99).box(0, by, 0, span, 1.4f, 5);
        b.color(0x6C717A).box(0, by + 1, -2.3f, span, 0.6f, 0.3f);
        b.color(0x6C717A).box(0, by + 1, 2.3f, span, 0.6f, 0.3f);
        for (int i = -7; i <= 7; i++) b.color(0x5A5E66).box(i * 2, by + 0.6f, 2.3f, 0.15f, 0.8f, 0.2f);
        for (int s = -1; s <= 1; s += 2) {
            b.color(0x9D8E7A).box(s * 7.8f, by / 2, 0, 1.6f, by, 3.6f);
            b.color(0xB5A590).box(s * 7.8f, 0.4f, 0, 2.2f, 0.8f, 4.2f);
        }
        b.color(0xFF4E8A).box(0, by - 0.2f, 2.52f, 6, 0.8f, 0.05f);
        b.color(0xFFD23A).box(-7, by - 0.2f, 2.52f, 3, 0.6f, 0.05f);
        return b.build();
    }

    private static Mesh buildSky(MeshBuilder b) {
        int lon = 16, lat = 8;
        float R = 380;
        for (int i = 0; i < lat; i++) {
            double t0 = Math.PI / 2 * i / lat, t1 = Math.PI / 2 * (i + 1) / lat;
            for (int j = 0; j < lon; j++) {
                double f0 = Math.PI * 2 * j / lon, f1 = Math.PI * 2 * (j + 1) / lon;
                int c = lerpColor(0xB9E4FF, 0x3A8EE6, (float) i / lat);
                b.color(c);
                float[] p = skyP(R, t0, f0), q = skyP(R, t0, f1), r = skyP(R, t1, f1), s = skyP(R, t1, f0);
                b.quad(p, s, r, q);
            }
        }
        // ground skirt below horizon
        for (int j = 0; j < lon; j++) {
            double f0 = Math.PI * 2 * j / lon, f1 = Math.PI * 2 * (j + 1) / lon;
            b.color(0xB9E4FF);
            float[] p = skyP(R, 0, f0), q = skyP(R, 0, f1);
            float[] r = {q[0], -R * 0.3f, q[2]}, s = {p[0], -R * 0.3f, p[2]};
            b.quad(s, p, q, r);
        }
        return b.build();
    }

    private static float[] skyP(float R, double t, double f) {
        return new float[]{R * (float) (Math.cos(t) * Math.sin(f)), R * (float) Math.sin(t), R * (float) (Math.cos(t) * Math.cos(f))};
    }

    // ---------------------------------------------------------------- obstacles

    /** Train car occupying local z in [-CAR_LEN, 0]; cab (if front) at z=0 facing +Z. */
    private static Mesh buildTrain(MeshBuilder b, int[] c, boolean front) {
        int body = c[0], stripe = c[1], dark = c[2];
        float L = CAR_LEN - 0.4f, zc = -CAR_LEN / 2 - 0.2f, W = TRAIN_W;
        // undercarriage & wheels
        b.color(0x2B2B30).box(0, 0.45f, zc, W * 0.8f, 0.5f, L - 0.6f);
        for (int s = -1; s <= 1; s += 2) for (int k = 0; k < 4; k++) {
            float z = zc + (k < 2 ? -L / 2 + 1.4f + k * 1.3f : L / 2 - 1.4f - (k - 2) * 1.3f);
            b.color(0x1C1C1F).cylinderX(s * 0.72f, 0.42f, z, 0.36f, 0.22f, 10);
            b.color(0x9A9AA2).cylinderX(s * 0.84f, 0.42f, z, 0.14f, 0.05f, 8);
        }
        // body
        b.color(body).box(0, 1.95f, zc, W, 2.5f, L);
        b.color(darken(body, 0.85f)).box(0, TRAIN_H - 0.12f, zc, W * 0.94f, 0.25f, L * 0.99f);
        b.color(0xBFC4CC).box(0, TRAIN_H + 0.02f, zc, W * 0.7f, 0.1f, L * 0.9f);
        b.color(0x8E949E).box(0, TRAIN_H + 0.1f, zc - L / 4, 1.0f, 0.2f, 1.6f);
        // stripe + windows on sides
        for (int s = -1; s <= 1; s += 2) {
            b.color(stripe).box(s * (W / 2 + 0.01f), 1.25f, zc, 0.03f, 0.35f, L * 0.98f);
            for (int i = 0; i < 4; i++) {
                b.color(0x1E2A3A).box(s * (W / 2 + 0.02f), 2.35f, zc - L / 2 + 1.6f + i * 2.9f, 0.04f, 0.9f, 1.7f);
                b.color(0x88B8DB).box(s * (W / 2 + 0.03f), 2.55f, zc - L / 2 + 1.3f + i * 2.9f, 0.03f, 0.25f, 0.6f);
            }
            b.color(dark).box(s * (W / 2 + 0.02f), 1.9f, zc + L / 2 - 1.2f, 0.04f, 2.0f, 1.1f);
        }
        if (front) {
            float fz = -0.2f;
            b.color(dark).box(0, 1.95f, fz + 0.06f, W * 0.96f, 2.4f, 0.12f);
            b.color(0x1E2A3A).box(0, 2.45f, fz + 0.13f, W * 0.8f, 0.95f, 0.05f);
            b.color(0x9FD0F0).box(-0.45f, 2.7f, fz + 0.16f, 0.4f, 0.25f, 0.03f);
            b.color(stripe).box(0, 1.25f, fz + 0.13f, W * 0.96f, 0.35f, 0.04f);
            b.color(0xFFF6B0).cylinderZ(-0.7f, 0.95f, fz + 0.16f, 0.17f, 0.1f, 10);
            b.color(0xFFF6B0).cylinderZ(0.7f, 0.95f, fz + 0.16f, 0.17f, 0.1f, 10);
            b.color(0xFF3B30).box(0, 3.05f, fz + 0.14f, 0.7f, 0.18f, 0.05f);
            b.color(0x333338).box(0, 0.35f, fz + 0.2f, W * 0.9f, 0.3f, 0.3f);
        } else {
            b.color(0x2B2B30).box(0, 0.7f, -0.1f, 0.4f, 0.3f, 0.4f);
            b.color(dark).box(0, 1.9f, -0.18f, 1.2f, 2.2f, 0.1f);
        }
        b.color(0x2B2B30).box(0, 0.7f, -CAR_LEN + 0.1f, 0.4f, 0.3f, 0.4f);
        return b.build();
    }

    /** Ramp occupying z in [-RAMP_LEN, 0], rising to TRAIN_H at the far end. */
    private static Mesh buildRamp(MeshBuilder b) {
        float L = RAMP_LEN, H = TRAIN_H, w = 1.1f;
        b.color(0xE8C23A);
        b.tri(-w, 0.05f, 0, w, 0.05f, 0, w, H, -L);
        b.tri(-w, 0.05f, 0, w, H, -L, -w, H, -L);
        // stripes on the slope
        for (int i = 1; i < 8; i += 2) {
            float t0 = i / 8f, t1 = (i + 0.5f) / 8f;
            b.color(0x222222);
            float y0 = 0.07f + H * t0, y1 = 0.07f + H * t1;
            b.tri(-w, y0, -L * t0, w, y0, -L * t0, w, y1, -L * t1);
            b.tri(-w, y0, -L * t0, w, y1, -L * t1, -w, y1, -L * t1);
        }
        b.color(0x7A7F88);
        for (int s = -1; s <= 1; s += 2) {
            float x = s * w;
            if (s > 0) b.tri(x, 0, 0, x, 0, -L, x, H, -L);
            else b.tri(x, 0, 0, x, H, -L, x, 0, -L);
        }
        b.color(0x5E636B).box(0, H / 2, -L + 0.1f, 2 * w, H, 0.2f);
        for (int k = 1; k <= 3; k++) {
            float z = -L * k / 4, h = H * k / 4;
            b.color(0x4E535B).box(-w + 0.15f, h / 2, z, 0.2f, h, 0.2f);
            b.color(0x4E535B).box(w - 0.15f, h / 2, z, 0.2f, h, 0.2f);
        }
        return b.build();
    }

    private static Mesh buildBarrierLow(MeshBuilder b) {
        for (int s = -1; s <= 1; s += 2) {
            b.color(0x9A9EA6).box(s * 0.95f, 0.5f, 0, 0.14f, 1.0f, 0.14f);
            b.color(0x5B5F66).box(s * 0.95f, 0.05f, 0, 0.5f, 0.1f, 0.5f);
        }
        for (int i = 0; i < 6; i++) {
            b.color(i % 2 == 0 ? 0xE53935 : 0xFFFFFF).box(-0.95f + 0.19f + i * 0.316f, 0.72f, 0.02f, 0.316f, 0.42f, 0.12f);
        }
        b.color(0xFFB300).box(-0.95f, 1.06f, 0, 0.18f, 0.1f, 0.18f);
        b.color(0xFFB300).box(0.95f, 1.06f, 0, 0.18f, 0.1f, 0.18f);
        return b.build();
    }

    private static Mesh buildBarrierHigh(MeshBuilder b) {
        for (int s = -1; s <= 1; s += 2) {
            b.color(0x3B4048).box(s * 1.0f, 1.3f, 0, 0.18f, 2.6f, 0.18f);
            b.color(0x2A2E34).box(s * 1.0f, 0.06f, 0, 0.5f, 0.12f, 0.6f);
        }
        for (int i = 0; i < 7; i++) {
            b.color(i % 2 == 0 ? 0xFFD000 : 0x1A1A1A).box(-0.98f + 0.14f + i * 0.28f, 1.95f, 0.02f, 0.28f, 0.8f, 0.14f);
        }
        b.color(0xFFFFFF).box(0, 2.5f, 0, 1.0f, 0.3f, 0.1f);
        b.color(0xE53935).sphere(-0.9f, 2.72f, 0, 0.12f, 4, 6);
        b.color(0xE53935).sphere(0.9f, 2.72f, 0, 0.12f, 4, 6);
        return b.build();
    }

    /** Full-height signal block: must be dodged sideways. */
    private static Mesh buildBlock(MeshBuilder b) {
        b.color(0x464B53).box(0, 1.5f, -0.3f, 2.0f, 3.0f, 0.8f);
        b.color(0x2A2E34).box(0, 1.5f, 0.12f, 1.8f, 2.8f, 0.06f);
        b.color(0xFFFFFF).box(0, 2.35f, 0.16f, 1.5f, 0.7f, 0.04f);
        b.color(0xE53935).box(0, 2.35f, 0.19f, 1.3f, 0.5f, 0.03f);
        b.color(0x111111).cylinderZ(-0.45f, 1.2f, 0.16f, 0.3f, 0.05f, 12);
        b.color(0x111111).cylinderZ(0.45f, 1.2f, 0.16f, 0.3f, 0.05f, 12);
        b.color(0xFF3B30).cylinderZ(-0.45f, 1.2f, 0.19f, 0.22f, 0.04f, 12);
        b.color(0xFFC107).cylinderZ(0.45f, 1.2f, 0.19f, 0.22f, 0.04f, 12);
        for (int i = 0; i < 5; i++) b.color(i % 2 == 0 ? 0xFFD000 : 0x1A1A1A).box(-0.8f + i * 0.4f, 0.25f, 0.14f, 0.4f, 0.3f, 0.05f);
        return b.build();
    }

    // ---------------------------------------------------------------- pickups

    private static Mesh buildCoin(MeshBuilder b) {
        b.color(0xF5B90A).cylinderZ(0, 0, 0, 0.42f, 0.12f, 18);
        b.color(0xFFDD4A).cylinderZ(0, 0, 0, 0.3f, 0.16f, 18);
        b.color(0xF5B90A).box(0, 0, 0, 0.1f, 0.34f, 0.2f);
        return b.build();
    }

    private static Mesh buildMagnet(MeshBuilder b) {
        b.color(0xE53935);
        for (int i = 0; i < 7; i++) {
            double a0 = Math.PI * i / 7, a1 = Math.PI * (i + 1) / 7;
            double am = (a0 + a1) / 2;
            b.push().translate((float) Math.cos(am) * 0.35f, -(float) Math.sin(am) * 0.35f, 0).rotZ((float) Math.toDegrees(-am) + 90)
                    .box(0, 0, 0, 0.18f, 0.18f, 0.22f).pop();
        }
        b.color(0xE53935).box(-0.35f, 0.2f, 0, 0.2f, 0.4f, 0.22f).box(0.35f, 0.2f, 0, 0.2f, 0.4f, 0.22f);
        b.color(0xDADFE6).box(-0.35f, 0.5f, 0, 0.21f, 0.22f, 0.23f).box(0.35f, 0.5f, 0, 0.21f, 0.22f, 0.23f);
        return b.build();
    }

    private static Mesh buildJetpack(MeshBuilder b, boolean pickup) {
        float s = pickup ? 1.0f : 0.8f;
        b.push().scale(s, s, s);
        b.color(0xB0B8C4).cylinder(-0.2f, 0, 0, 0.17f, 0.7f, 10).cylinder(0.2f, 0, 0, 0.17f, 0.7f, 10);
        b.color(0xE53935).frustum(-0.2f, 0.45f, 0, 0.17f, 0.02f, 0.25f, 10, false, false)
                .frustum(0.2f, 0.45f, 0, 0.17f, 0.02f, 0.25f, 10, false, false);
        b.color(0x444A55).frustum(-0.2f, -0.42f, 0, 0.1f, 0.15f, 0.16f, 8, true, true)
                .frustum(0.2f, -0.42f, 0, 0.1f, 0.15f, 0.16f, 8, true, true);
        b.color(0x39475A).box(0, 0.05f, -0.12f, 0.35f, 0.5f, 0.12f);
        b.pop();
        return b.build();
    }

    private static Mesh buildSneaker(MeshBuilder b) {
        b.color(0x2BD17E).box(0, 0, 0, 0.36f, 0.28f, 0.7f);
        b.color(0x2BD17E).box(0, 0.22f, 0.15f, 0.34f, 0.3f, 0.36f);
        b.color(0xFFFFFF).box(0, -0.17f, 0, 0.38f, 0.1f, 0.76f);
        b.color(0xFFFFFF).box(0.19f, 0.02f, -0.05f, 0.02f, 0.08f, 0.4f);
        b.color(0xB0B8C4);
        for (int i = 0; i < 3; i++) b.box(0, -0.3f - i * 0.1f, 0, 0.24f - i * 0.03f, 0.04f, 0.24f);
        b.color(0xFFFFFF).box(0.2f, 0.3f, 0.2f, 0.02f, 0.25f, 0.1f);
        b.color(0x1FA864).box(-0.2f, 0.25f, 0.28f, 0.1f, 0.1f, 0.1f);
        return b.build();
    }

    private static Mesh buildX2(MeshBuilder b) {
        b.color(0xB53BE0).box(0, 0, -0.05f, 1.1f, 0.85f, 0.14f);
        b.color(0xFFFFFF).push().translate(0, 0, 0.06f).text("2X", 0.11f, 0.12f).pop();
        return b.build();
    }

    private static Mesh buildMystery(MeshBuilder b) {
        b.color(0x8A4CE0).box(0, 0, 0, 0.8f, 0.8f, 0.8f);
        b.color(0xFFD23A).box(0, 0, 0, 0.84f, 0.12f, 0.84f).box(0, 0, 0, 0.12f, 0.84f, 0.84f);
        b.color(0xFFFFFF).push().translate(0, 0.02f, 0.42f).text("?", 0.09f, 0.06f).pop();
        b.color(0xFFFFFF).push().translate(0, 0.02f, -0.42f).rotY(180).text("?", 0.09f, 0.06f).pop();
        return b.build();
    }

    private static Mesh buildKey(MeshBuilder b) {
        b.push().rotX(90);
        b.color(0x39B8FF).torus(0, 0.28f, 0, 0.18f, 0.06f, 12, 6);
        b.pop();
        b.color(0x39B8FF).box(0, -0.15f, 0, 0.09f, 0.55f, 0.09f);
        b.color(0x39B8FF).box(0.1f, -0.35f, 0, 0.14f, 0.07f, 0.08f);
        b.color(0x39B8FF).box(0.08f, -0.22f, 0, 0.1f, 0.07f, 0.08f);
        return b.build();
    }

    private static Mesh buildBoard(MeshBuilder b) {
        b.color(0xFF4E8A).box(0, 0, 0, 0.7f, 0.08f, 1.5f);
        b.color(0xFF4E8A).cylinder(0, 0, -0.75f, 0.35f, 0.08f, 12).cylinder(0, 0, 0.75f, 0.35f, 0.08f, 12);
        b.color(0xFFD23A).box(0, 0.045f, 0, 0.3f, 0.02f, 1.7f);
        b.color(0x39D1FF).box(0, -0.07f, -0.5f, 0.5f, 0.06f, 0.3f).box(0, -0.07f, 0.5f, 0.5f, 0.06f, 0.3f);
        b.color(0x9CF6FF).box(0, -0.1f, 0, 0.4f, 0.02f, 1.2f);
        return b.build();
    }

    // ---------------------------------------------------------------- characters

    /** Parts in pivot space. Character faces -Z. */
    private static Mesh[] buildRunner(MeshBuilder b, CharacterDef d) {
        Mesh[] p = new Mesh[4];
        boolean robot = d.style == CharacterDef.HELMET;
        // torso: pivot at hips, extends up 0.62
        b.color(d.pants).box(0, 0.05f, 0, 0.5f, 0.16f, 0.3f);
        b.color(d.top).taperBox(0, 0.34f, 0, 0.52f, 0.5f, 0.3f, 1.12f, 1.05f);
        b.color(d.topAccent).box(0, 0.34f, -0.155f, 0.3f, 0.12f, 0.02f);
        b.color(d.topAccent).box(0, 0.55f, 0.02f, 0.45f, 0.07f, 0.32f);
        b.color(darken(d.top, 0.7f)).box(0, 0.32f, 0.2f, 0.38f, 0.42f, 0.14f); // backpack
        b.color(d.topAccent).box(0, 0.4f, 0.28f, 0.26f, 0.1f, 0.02f);
        p[P_TORSO] = b.build();
        // head: pivot at neck
        b.color(d.skin).box(0, 0.05f, 0, 0.14f, 0.12f, 0.14f);
        if (robot) b.color(d.skin).box(0, 0.3f, 0, 0.44f, 0.4f, 0.42f);
        else b.color(d.skin).sphere(0, 0.3f, 0, 0.23f, 0.25f, 0.23f, 6, 10);
        if (robot) {
            b.color(0x111820).box(0, 0.33f, -0.215f, 0.36f, 0.13f, 0.02f);
            b.color(d.topAccent).box(0, 0.33f, -0.225f, 0.3f, 0.05f, 0.02f);
            b.color(d.hair).cylinder(0, 0.58f, 0, 0.03f, 0.2f, 5);
            b.color(d.topAccent).sphere(0, 0.7f, 0, 0.06f, 3, 5);
        } else {
            b.color(0x1B1B1B).box(-0.08f, 0.33f, -0.215f, 0.05f, 0.07f, 0.02f).box(0.08f, 0.33f, -0.215f, 0.05f, 0.07f, 0.02f);
            b.color(darken(d.skin, 0.8f)).box(0, 0.19f, -0.22f, 0.1f, 0.03f, 0.02f);
            b.color(d.skin).box(-0.24f, 0.3f, 0, 0.05f, 0.1f, 0.08f).box(0.24f, 0.3f, 0, 0.05f, 0.1f, 0.08f);
            b.color(d.hair).sphere(0, 0.4f, 0.06f, 0.245f, 0.2f, 0.23f, 5, 10);
            if (d.style == CharacterDef.CAP) {
                b.color(d.headwear).sphere(0, 0.42f, 0.02f, 0.25f, 0.17f, 0.25f, 4, 10);
                b.color(d.headwear).box(0, 0.45f, 0.25f, 0.34f, 0.04f, 0.22f); // backwards cap brim
                b.color(0xFFFFFF).box(0, 0.5f, -0.2f, 0.1f, 0.08f, 0.04f);
            } else if (d.style == CharacterDef.BEANIE) {
                b.color(d.headwear).sphere(0, 0.44f, 0.02f, 0.26f, 0.2f, 0.26f, 4, 10);
                b.color(darken(d.headwear, 0.8f)).cylinder(0, 0.36f, 0.02f, 0.265f, 0.08f, 10);
                b.color(0xFFFFFF).sphere(0, 0.66f, 0.02f, 0.07f, 3, 6);
            } else if (d.style == CharacterDef.BUNS) {
                b.color(d.hair).sphere(-0.2f, 0.56f, 0.04f, 0.1f, 4, 6).sphere(0.2f, 0.56f, 0.04f, 0.1f, 4, 6);
                b.color(0x222222).box(0, 0.36f, -0.225f, 0.34f, 0.04f, 0.02f);
            } else {
                b.color(d.hair).box(0, 0.2f, 0.18f, 0.36f, 0.4f, 0.1f); // long hair
                b.color(d.headwear).box(0, 0.5f, 0, 0.44f, 0.05f, 0.3f); // headband
            }
        }
        p[P_HEAD] = b.build();
        // arm: pivot at shoulder, extends down
        b.color(d.top).box(0, -0.17f, 0, 0.15f, 0.36f, 0.16f);
        b.color(robot ? d.hair : d.skin).box(0, -0.43f, 0, 0.12f, 0.2f, 0.13f);
        b.color(robot ? d.topAccent : d.skin).box(0, -0.56f, 0, 0.13f, 0.1f, 0.14f);
        p[P_ARM] = b.build();
        // leg: pivot at hip, extends down to feet (0.95)
        b.color(d.pants).box(0, -0.25f, 0, 0.19f, 0.5f, 0.2f);
        b.color(d.pants).box(0, -0.66f, 0, 0.17f, 0.38f, 0.18f);
        b.color(d.shoes).box(0, -0.88f, -0.06f, 0.2f, 0.16f, 0.32f);
        b.color(0xFFFFFF).box(0, -0.945f, -0.06f, 0.21f, 0.04f, 0.33f);
        p[P_LEG] = b.build();
        return p;
    }

    private static void buildGuard(MeshBuilder b) {
        int uni = 0x2C4C8C, skin = 0xE2A983;
        b.color(0x1E2F55).box(0, 0.05f, 0, 0.62f, 0.2f, 0.42f);
        b.color(uni).taperBox(0, 0.4f, 0, 0.68f, 0.62f, 0.5f, 1.08f, 0.95f);
        b.color(0x1E2F55).box(0, 0.12f, -0.22f, 0.7f, 0.1f, 0.1f);
        b.color(0xFFD23A).box(-0.15f, 0.55f, -0.25f, 0.1f, 0.12f, 0.02f);
        gTorso = b.build();
        b.color(skin).sphere(0, 0.3f, 0, 0.27f, 0.28f, 0.27f, 6, 10);
        b.color(0x7A4A2A).box(0, 0.16f, -0.23f, 0.3f, 0.07f, 0.06f); // moustache
        b.color(0x1B1B1B).box(-0.09f, 0.33f, -0.25f, 0.05f, 0.06f, 0.02f).box(0.09f, 0.33f, -0.25f, 0.05f, 0.06f, 0.02f);
        b.color(0x1E2F55).cylinder(0, 0.52f, 0, 0.29f, 0.14f, 12);
        b.color(0x1E2F55).box(0, 0.47f, -0.28f, 0.4f, 0.04f, 0.2f);
        b.color(0xFFD23A).box(0, 0.54f, -0.29f, 0.1f, 0.08f, 0.02f);
        gHead = b.build();
        b.color(uni).box(0, -0.22f, 0, 0.19f, 0.46f, 0.2f);
        b.color(skin).box(0, -0.54f, 0, 0.16f, 0.18f, 0.16f);
        gArm = b.build();
        b.color(0x1E2F55).box(0, -0.4f, 0, 0.23f, 0.8f, 0.24f);
        b.color(0x111111).box(0, -0.88f, -0.06f, 0.25f, 0.16f, 0.36f);
        gLeg = b.build();
    }

    private static void buildDog(MeshBuilder b) {
        int fur = 0xA0683A;
        b.color(fur).box(0, 0, 0, 0.36f, 0.34f, 0.8f);
        b.color(0xE9D3B5).box(0, -0.1f, -0.1f, 0.3f, 0.16f, 0.5f);
        b.push().translate(0, 0.15f, 0.45f).rotX(-35).color(fur).box(0, 0.12f, 0, 0.08f, 0.3f, 0.08f).pop();
        b.color(0xE53935).box(0, 0.16f, -0.36f, 0.38f, 0.08f, 0.08f);
        dogBody = b.build();
        b.color(fur).box(0, 0.05f, -0.05f, 0.32f, 0.3f, 0.32f);
        b.color(0xE9D3B5).box(0, -0.02f, -0.28f, 0.2f, 0.16f, 0.22f);
        b.color(0x111111).box(0, 0.05f, -0.4f, 0.08f, 0.07f, 0.04f);
        b.color(0x111111).box(-0.09f, 0.12f, -0.21f, 0.05f, 0.05f, 0.02f).box(0.09f, 0.12f, -0.21f, 0.05f, 0.05f, 0.02f);
        b.color(0x6A4222).box(-0.15f, 0.2f, 0, 0.08f, 0.2f, 0.14f).box(0.15f, 0.2f, 0, 0.08f, 0.2f, 0.14f);
        dogHead = b.build();
        b.color(fur).box(0, -0.15f, 0, 0.1f, 0.32f, 0.1f);
        b.color(0xE9D3B5).box(0, -0.3f, -0.03f, 0.11f, 0.06f, 0.15f);
        dogLeg = b.build();
    }

    // ---------------------------------------------------------------- colour utils

    public static int darken(int c, float f) {
        int r = (int) (((c >> 16) & 255) * f), g = (int) (((c >> 8) & 255) * f), bl = (int) ((c & 255) * f);
        return (r << 16) | (g << 8) | bl;
    }

    public static int lerpColor(int a, int c, float t) {
        int r = (int) (((a >> 16) & 255) * (1 - t) + ((c >> 16) & 255) * t);
        int g = (int) (((a >> 8) & 255) * (1 - t) + ((c >> 8) & 255) * t);
        int bl = (int) ((a & 255) * (1 - t) + (c & 255) * t);
        return (r << 16) | (g << 8) | bl;
    }
}
