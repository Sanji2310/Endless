package com.endlessrush.core;

/**
 * The camera, sun and fog for the current game state (world: x right, y up, z = -distance). Everything on screen
 * is drawn by the toon layers (PongoScene, ZoneWorld, SakuraWorld), which take their view from here.
 */
public final class Scene {
    private float camX, camY = 5.5f, camZOff = 6.6f, menuT;
    private int menuChar = -1;

    /** Set by the toon layers when they attach: PongoScene draws the heroine and the Mon coins, ZoneWorld the tunnel
     *  and the Crystal Cavern. */
    public boolean toonHero, toonCoins, toonWorld;

    /** Character shown on the menu / shop (overrides profile selection when >= 0). */
    public void setPreviewCharacter(int idx) { menuChar = idx; }

    /** Hero currently on screen. */
    public int heroIndex(Game g) { return menuChar >= 0 ? menuChar : g.profile.selected; }

    public void build(Game g, DrawList dl, float aspect, float dt) {
        dl.clear();
        menuT += dt;
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
    }
}
