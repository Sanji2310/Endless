package com.endlessrush.app;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.LayerDrawable;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.view.animation.AccelerateDecelerateInterpolator;
import android.view.animation.OvershootInterpolator;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import com.endlessrush.core.CharacterDef;
import com.endlessrush.core.Game;
import com.endlessrush.core.Missions;
import com.endlessrush.core.Profile;
import com.endlessrush.core.Scene;

import java.util.Locale;
import java.util.Random;

import javax.microedition.khronos.egl.EGL10;
import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.egl.EGLDisplay;

public final class MainActivity extends Activity implements Game.Listener, GameRenderer.Hud {
    // Sakura Line palette: cream paper and violet ink with pastel accents (each screen keeps the same style)
    static final int INK = 0xFF2E2440, PAPER = 0xFFFFF8EE, PAPER_LOW = 0xFFFBE7DA, SOFT_TEXT = 0xFF76698E,
            SAKURA = 0xFFF27BA8, LEAF = 0xFF5DBE6A, SKY = 0xFF4EAEF0, SUNSET = 0xFFFF9A3D, LILAC = 0xFF9D7FE8,
            MON = 0xFFFFC93C, MON_DARK = 0xFFD9951E, ROCKET_RED = 0xFFF2645A, OMAMORI_RED = 0xFFE5484D,
            MUTED = 0xFF9C94B8, WHITE = 0xFFFFFFFF;
    // power-ups in Profile's upgrade order, then the board (the HUD bars and the shop rows)
    private static final String[] POWER_NAME = {"HAYATE ROCKET", "TOBI BOOTS", "MANEKI MAGNET", "FEVER STAR 2X", "KAZE BOARD"};
    private static final String[] UPGRADE_NAME = {"Hayate Rocket", "Tobi Boots", "Maneki Magnet", "Fever Star"};
    private static final String[] POWER_GLYPH = {"翔", "跳", "招", "倍", "風"};
    private static final int[] POWER_COL = {ROCKET_RED, LEAF, MON, LILAC, SKY};

    private Profile profile;
    private Game game;
    private Scene scene;
    private GameRenderer renderer;
    private GLSurfaceView glView;
    private final AudioEngine audio = new AudioEngine();
    private final Handler ui = new Handler(Looper.getMainLooper());
    private Typeface heavy;

    private FrameLayout root, hudLayer, menuLayer, pauseLayer, saveMeLayer, overLayer, shopLayer, heroesLayer, missionsLayer;
    private TextView scoreText, coinText, multText, boardHint, banner, countdown;
    private TextView menuCoins, menuKeys, menuBoards, menuBest, menuMult, playButton, soundBtn, musicBtn;
    private TextView saveMeBtn, saveMeTitle;
    private View saveMeBar;
    private LinearLayout powerBars, shopList, missionsList, overMissions, pauseMissions;
    private TextView overTitle, overScore, overCoins, overBest, overNew, shopCoins;
    private TextView heroName, heroTag, heroBtn;
    private int heroIdx;
    private final View[] barFill = new View[5];
    private final LinearLayout[] barRow = new LinearLayout[5];

    // HUD snapshot written on the GL thread
    private volatile int hScore, hCoins, hMult, hBoards;
    private volatile float hJet, hMag, hSneak, hX2, hBoard, hSave;
    private volatile boolean hudPending;
    private int lastScore = -1, lastCoins = -1, lastMult = -1, lastBoards = -1;
    private long lastHud;

    // touch
    private float tx0, ty0;
    private boolean swiped;
    private long lastTap;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        try {
            heavy = Typeface.createFromAsset(getAssets(), "fonts/Outfit-Bold.ttf");
        } catch (RuntimeException e) {
            heavy = Typeface.create("sans-serif-black", Typeface.BOLD);
        }

        final SharedPreferences prefs = getSharedPreferences("endless_rush", Context.MODE_PRIVATE);
        profile = new Profile(new Profile.Store() {
            private SharedPreferences.Editor ed;
            public int getInt(String k, int d) { return prefs.getInt(k, d); }
            public void putInt(String k, int v) { if (ed == null) ed = prefs.edit(); ed.putInt(k, v); }
            public void commit() { if (ed != null) { ed.apply(); ed = null; } }
        });
        audio.soundOn = profile.soundOn == 1;
        audio.musicOn = profile.musicOn == 1;
        game = new Game(profile, this);
        scene = new Scene();
        renderer = new GameRenderer(game, scene, this, getAssets());

        root = new FrameLayout(this);
        glView = new GLSurfaceView(this);
        glView.setEGLContextClientVersion(2);
        glView.setEGLConfigChooser(new GLSurfaceView.EGLConfigChooser() {
            public EGLConfig chooseConfig(EGL10 egl, EGLDisplay d) {
                int rt = 0x3040, es2 = 4;
                int[][] tries = {
                        {EGL10.EGL_RED_SIZE, 8, EGL10.EGL_GREEN_SIZE, 8, EGL10.EGL_BLUE_SIZE, 8, EGL10.EGL_DEPTH_SIZE, 16,
                                rt, es2, EGL10.EGL_SAMPLE_BUFFERS, 1, EGL10.EGL_SAMPLES, 4, EGL10.EGL_NONE},
                        {EGL10.EGL_RED_SIZE, 8, EGL10.EGL_GREEN_SIZE, 8, EGL10.EGL_BLUE_SIZE, 8, EGL10.EGL_DEPTH_SIZE, 16, rt, es2, EGL10.EGL_NONE},
                        {EGL10.EGL_RED_SIZE, 5, EGL10.EGL_GREEN_SIZE, 6, EGL10.EGL_BLUE_SIZE, 5, EGL10.EGL_DEPTH_SIZE, 16, rt, es2, EGL10.EGL_NONE},
                        {EGL10.EGL_DEPTH_SIZE, 16, rt, es2, EGL10.EGL_NONE}};
                EGLConfig[] cfg = new EGLConfig[1];
                int[] num = new int[1];
                for (int[] a : tries) {
                    if (egl.eglChooseConfig(d, a, cfg, 1, num) && num[0] > 0) return cfg[0];
                }
                throw new IllegalArgumentException("No suitable EGL config");
            }
        });
        glView.setRenderer(renderer);
        glView.setRenderMode(GLSurfaceView.RENDERMODE_CONTINUOUSLY);
        glView.setOnTouchListener(new View.OnTouchListener() {
            public boolean onTouch(View v, MotionEvent e) { return touch(e); }
        });
        root.addView(glView, match());

        buildHud();
        buildMenu();
        buildPause();
        buildSaveMe();
        buildGameOver();
        buildShop();
        buildHeroes();
        buildMissions();

        banner = label("", 22, INK);
        banner.setGravity(Gravity.CENTER);
        banner.setVisibility(View.GONE);
        FrameLayout.LayoutParams bl = new FrameLayout.LayoutParams(-2, -2, Gravity.CENTER_HORIZONTAL | Gravity.TOP);
        bl.topMargin = dp(150);
        root.addView(banner, bl);

        countdown = label("", 96, WHITE);
        countdown.setVisibility(View.GONE);
        root.addView(countdown, new FrameLayout.LayoutParams(-2, -2, Gravity.CENTER));

        setContentView(root);
        showFor(Game.MENU);
        audio.start();
    }

    // ------------------------------------------------------------------ lifecycle

    @Override
    protected void onResume() {
        super.onResume();
        glView.onResume();
        audio.setPaused(false);
        hideSystemUi();
    }

    @Override
    protected void onPause() {
        renderer.post(new Runnable() { public void run() { game.pause(); } });
        glView.onPause();
        audio.setPaused(true);
        profile.save();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        audio.stop();
        super.onDestroy();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemUi();
    }

    @SuppressWarnings("deprecation")
    private void hideSystemUi() {
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
    }

    @Override
    public void onBackPressed() {
        if (shopLayer.getVisibility() == View.VISIBLE || heroesLayer.getVisibility() == View.VISIBLE
                || missionsLayer.getVisibility() == View.VISIBLE) {
            backToMenu();
            return;
        }
        int st = game.state;
        if (st == Game.RUNNING) { gl(new Runnable() { public void run() { game.pause(); } }); return; }
        if (st == Game.PAUSED) { resumeWithCountdown(); return; }
        if (st == Game.SAVE_ME) { gl(new Runnable() { public void run() { game.declineSaveMe(); } }); return; }
        if (st == Game.GAME_OVER) { gl(new Runnable() { public void run() { game.toMenu(); } }); return; }
        if (st == Game.DYING) return;
        super.onBackPressed();
    }

    // ------------------------------------------------------------------ input

    private void gl(Runnable r) { renderer.post(r); }

    private boolean touch(MotionEvent e) {
        float th = dp(22);
        switch (e.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                tx0 = e.getX(); ty0 = e.getY(); swiped = false;
                return true;
            case MotionEvent.ACTION_MOVE:
                if (!swiped) {
                    float dx = e.getX() - tx0, dy = e.getY() - ty0;
                    if (Math.max(Math.abs(dx), Math.abs(dy)) > th) { swipe(dx, dy); swiped = true; }
                }
                return true;
            case MotionEvent.ACTION_UP:
                if (!swiped) {
                    float dx = e.getX() - tx0, dy = e.getY() - ty0;
                    if (Math.max(Math.abs(dx), Math.abs(dy)) > th * 0.5f) swipe(dx, dy);
                    else tap();
                }
                return true;
            default:
                return true;
        }
    }

    private void swipe(float dx, float dy) {
        final int dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 1 : 0) : (dy < 0 ? 2 : 3);
        gl(new Runnable() {
            public void run() {
                switch (dir) {
                    case 0: game.left(); break;
                    case 1: game.right(); break;
                    case 2: game.jump(); break;
                    default: game.roll(); break;
                }
            }
        });
    }

    private void tap() {
        long now = SystemClock.uptimeMillis();
        if (now - lastTap < 320) {
            lastTap = 0;
            useBoard();
        } else {
            lastTap = now;
        }
    }

    private void useBoard() {
        gl(new Runnable() {
            public void run() {
                if (game.state == Game.RUNNING && game.boardT <= 0 && profile.boards <= 0) onMessage("NO HOVERBOARDS LEFT");
                else game.hoverboard();
            }
        });
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent e) {
        if (e.getAction() == KeyEvent.ACTION_DOWN && game.state == Game.RUNNING) {
            switch (e.getKeyCode()) {
                case KeyEvent.KEYCODE_DPAD_LEFT: case KeyEvent.KEYCODE_A: swipe(-1, 0); return true;
                case KeyEvent.KEYCODE_DPAD_RIGHT: case KeyEvent.KEYCODE_D: swipe(1, 0); return true;
                case KeyEvent.KEYCODE_DPAD_UP: case KeyEvent.KEYCODE_W: case KeyEvent.KEYCODE_SPACE: swipe(0, -1); return true;
                case KeyEvent.KEYCODE_DPAD_DOWN: case KeyEvent.KEYCODE_S: swipe(0, 1); return true;
                case KeyEvent.KEYCODE_B: case KeyEvent.KEYCODE_ENTER: useBoard(); return true;
                default: break;
            }
        }
        return super.dispatchKeyEvent(e);
    }

    // ------------------------------------------------------------------ game callbacks (any thread)

    @Override
    public void onSound(int id) { audio.play(id); }

    @Override
    public void onMessage(final String text) {
        ui.post(new Runnable() { public void run() { showBanner(display(text)); } });
    }

    @Override
    public void onStateChanged(final int state) {
        ui.post(new Runnable() { public void run() { showFor(state); } });
    }

    /** GL thread, every frame. */
    @Override
    public void onFrame(Game g) {
        audio.ambience = g.caveAmbience();
        hScore = g.score();
        hCoins = g.coinsRun;
        hMult = g.multiplier();
        hBoards = profile.boards;
        hJet = g.jetT > 0 ? g.jetT / g.jetMax : 0;
        hMag = g.magT > 0 ? g.magT / g.magMax : 0;
        hSneak = g.sneakT > 0 ? g.sneakT / g.sneakMax : 0;
        hX2 = g.x2T > 0 ? g.x2T / g.x2Max : 0;
        hBoard = g.boardT / Game.BOARD_TIME;
        hSave = g.state == Game.SAVE_ME ? g.saveMeT / Game.SAVE_ME_TIME : 0;
        long now = SystemClock.uptimeMillis();
        if (!hudPending && now - lastHud > 50) {
            lastHud = now;
            hudPending = true;
            ui.post(hudUpdate);
        }
    }

    private final Runnable hudUpdate = new Runnable() {
        public void run() {
            hudPending = false;
            if (hScore != lastScore) { lastScore = hScore; scoreText.setText(fmt(hScore)); }
            if (hCoins != lastCoins) { lastCoins = hCoins; coinText.setText(fmt(hCoins)); }
            if (hMult != lastMult) {
                lastMult = hMult;
                multText.setText("x" + hMult);
                multText.setBackground(chip(hX2 > 0 ? LILAC : SAKURA));
                pop(multText);
            }
            if (hBoards != lastBoards) {
                lastBoards = hBoards;
                boardHint.setText("DOUBLE-TAP FOR KAZE BOARD  (" + hBoards + ")");
            }
            float[] vals = {hJet, hSneak, hMag, hX2, hBoard};
            for (int i = 0; i < 5; i++) {
                boolean on = vals[i] > 0;
                barRow[i].setVisibility(on ? View.VISIBLE : View.GONE);
                if (on) barFill[i].setScaleX(vals[i]);
            }
            boardHint.setVisibility(hBoard > 0 || game.state != Game.RUNNING ? View.GONE : View.VISIBLE);
            if (saveMeLayer.getVisibility() == View.VISIBLE) saveMeBar.setScaleX(Math.max(0, hSave));
        }
    };

    // ------------------------------------------------------------------ screens

    private void hideAll() {
        View[] all = {hudLayer, menuLayer, pauseLayer, saveMeLayer, overLayer, shopLayer, heroesLayer, missionsLayer};
        for (View v : all) v.setVisibility(View.GONE);
    }

    private void showFor(int state) {
        hideAll();
        switch (state) {
            case Game.MENU:
                refreshMenu();
                fadeIn(menuLayer);
                gl(new Runnable() { public void run() { scene.setPreviewCharacter(-1); } });
                break;
            case Game.RUNNING:
            case Game.DYING:
                hudLayer.setVisibility(View.VISIBLE);
                break;
            case Game.PAUSED:
                hudLayer.setVisibility(View.VISIBLE);
                fillMissions(pauseMissions, false);
                fadeIn(pauseLayer);
                break;
            case Game.SAVE_ME:
                hudLayer.setVisibility(View.VISIBLE);
                int cost = game.saveMeCost();
                saveMeBtn.setText("USE " + cost + " OMAMORI   (YOU HAVE " + profile.keys + ")");
                fadeIn(saveMeLayer);
                pop(saveMeTitle);
                break;
            case Game.GAME_OVER:
                showGameOver();
                break;
            default:
                break;
        }
    }

    private void buildHud() {
        hudLayer = new FrameLayout(this);
        TextView pause = circleButton("II", PAPER);
        pause.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { gl(new Runnable() { public void run() { game.pause(); } }); }
        });
        FrameLayout.LayoutParams pl = new FrameLayout.LayoutParams(dp(50), dp(50), Gravity.TOP | Gravity.LEFT);
        pl.setMargins(dp(14), dp(18), 0, 0);
        hudLayer.addView(pause, pl);

        LinearLayout right = new LinearLayout(this);
        right.setOrientation(LinearLayout.VERTICAL);
        right.setGravity(Gravity.RIGHT);
        LinearLayout top = hrow();
        top.setGravity(Gravity.CENTER_VERTICAL);
        multText = label("x1", 17, WHITE);
        multText.setPadding(dp(10), dp(2), dp(10), dp(3));
        multText.setBackground(chip(SAKURA));
        top.addView(multText);
        scoreText = label("0", 38, WHITE);
        scoreText.setPadding(dp(10), 0, 0, 0);
        top.addView(scoreText);
        right.addView(top);
        LinearLayout cr = hrow();
        cr.setGravity(Gravity.CENTER_VERTICAL);
        cr.addView(coinIcon(24));
        coinText = label("0", 26, MON);
        coinText.setPadding(dp(6), 0, 0, 0);
        cr.addView(coinText);
        right.addView(cr);
        FrameLayout.LayoutParams rl = new FrameLayout.LayoutParams(-2, -2, Gravity.TOP | Gravity.RIGHT);
        rl.setMargins(0, dp(14), dp(16), 0);
        hudLayer.addView(right, rl);

        // power-up timers: a cream tag per power-up with its kanji badge and a draining bar
        powerBars = new LinearLayout(this);
        powerBars.setOrientation(LinearLayout.VERTICAL);
        for (int i = 0; i < 5; i++) {
            LinearLayout row = hrow();
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(6), dp(5), dp(12), dp(9));
            row.setBackground(paper(dp(14), false));
            row.addView(badge(POWER_GLYPH[i], POWER_COL[i], 30), new LinearLayout.LayoutParams(dp(30), dp(30)));
            LinearLayout txt = new LinearLayout(this);
            txt.setOrientation(LinearLayout.VERTICAL);
            txt.setPadding(dp(8), 0, 0, 0);
            TextView n = label(POWER_NAME[i], 11, INK);
            n.setGravity(Gravity.LEFT);
            txt.addView(n);
            FrameLayout track = new FrameLayout(this);
            track.setBackground(rounded(0x262E2440, dp(5)));
            View fill = new View(this);
            GradientDrawable fd = rounded(POWER_COL[i], dp(5));
            fd.setStroke(dp(1.5f), INK);
            fill.setBackground(fd);
            fill.setPivotX(0);
            track.addView(fill, new FrameLayout.LayoutParams(dp(96), dp(9)));
            LinearLayout.LayoutParams tl = new LinearLayout.LayoutParams(dp(96), dp(9));
            tl.topMargin = dp(2);
            txt.addView(track, tl);
            row.addView(txt);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, -2);
            lp.bottomMargin = dp(4);
            powerBars.addView(row, lp);
            row.setVisibility(View.GONE);
            barRow[i] = row;
            barFill[i] = fill;
        }
        FrameLayout.LayoutParams bl = new FrameLayout.LayoutParams(-2, -2, Gravity.LEFT | Gravity.TOP);
        bl.setMargins(dp(10), dp(80), 0, 0);
        hudLayer.addView(powerBars, bl);

        boardHint = label("DOUBLE-TAP FOR KAZE BOARD", 12, INK);
        boardHint.setPadding(dp(14), dp(6), dp(16), dp(10));
        boardHint.setBackground(paper(dp(18), false));
        boardHint.setAlpha(0.92f);
        FrameLayout.LayoutParams hl = new FrameLayout.LayoutParams(-2, -2, Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        hl.bottomMargin = dp(18);
        hudLayer.addView(boardHint, hl);
        root.addView(hudLayer, match());
    }

    private void buildMenu() {
        menuLayer = new FrameLayout(this);
        menuLayer.setClickable(true);
        menuLayer.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { startRun(); }
        });
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setGravity(Gravity.CENTER_HORIZONTAL);
        col.setPadding(dp(16), dp(16), dp(16), dp(20));

        LinearLayout stats = hrow();
        stats.setGravity(Gravity.CENTER);
        menuCoins = statPill(new MonCoin());
        menuKeys = statPill(new Glyph("守", OMAMORI_RED));
        menuBoards = statPill(new Glyph("風", SKY));
        stats.addView(menuCoins);
        stats.addView(menuKeys);
        stats.addView(menuBoards);
        col.addView(stats);

        // logo: the name in sakura pink with an ink outline, on a sky ribbon
        TextView t1 = label("PONGO", 70, SAKURA);
        t1.setRotation(-4);
        LinearLayout.LayoutParams tl = new LinearLayout.LayoutParams(-2, -2);
        tl.topMargin = dp(22);
        col.addView(t1, tl);
        TextView t2 = label("SAKURA LINE DASH", 16, WHITE);
        t2.setPadding(dp(16), dp(4), dp(16), dp(8));
        t2.setBackground(chip(SKY));
        t2.setRotation(-4);
        LinearLayout.LayoutParams t2l = new LinearLayout.LayoutParams(-2, -2);
        t2l.topMargin = -dp(12);
        col.addView(t2, t2l);

        LinearLayout info = hrow();
        info.setGravity(Gravity.CENTER);
        info.setPadding(0, dp(14), 0, 0);
        menuBest = label("BEST 0", 14, INK);
        menuBest.setPadding(dp(14), dp(5), dp(16), dp(9));
        menuBest.setBackground(paper(dp(18), false));
        menuMult = label("x1", 14, WHITE);
        menuMult.setPadding(dp(14), dp(5), dp(14), dp(9));
        menuMult.setBackground(chip(LEAF));
        info.addView(menuBest);
        info.addView(space(dp(8)));
        info.addView(menuMult);
        col.addView(info);

        col.addView(new View(this), new LinearLayout.LayoutParams(1, 0, 1f));

        playButton = gameButton("TAP TO RUN", LEAF, 30);
        playButton.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { startRun(); } });
        col.addView(playButton, new LinearLayout.LayoutParams(-1, dp(76)));
        pulse(playButton);

        LinearLayout row = hrow();
        row.setPadding(0, dp(10), 0, 0);
        TextView shop = gameButton("SHOP", SUNSET, 16);
        TextView heroes = gameButton("HEROES", SKY, 16);
        TextView missions = gameButton("MISSIONS", LILAC, 16);
        shop.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { openShop(); } });
        heroes.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { openHeroes(); } });
        missions.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { openMissions(); } });
        row.addView(shop, weight());
        row.addView(space(dp(8)));
        row.addView(heroes, weight());
        row.addView(space(dp(8)));
        row.addView(missions, weight());
        col.addView(row, new LinearLayout.LayoutParams(-1, dp(64)));

        LinearLayout row2 = hrow();
        row2.setPadding(0, dp(8), 0, 0);
        soundBtn = gameButton("", MUTED, 13);
        musicBtn = gameButton("", MUTED, 13);
        soundBtn.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                profile.soundOn = 1 - profile.soundOn;
                audio.soundOn = profile.soundOn == 1;
                profile.save();
                refreshMenu();
            }
        });
        musicBtn.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                profile.musicOn = 1 - profile.musicOn;
                audio.musicOn = profile.musicOn == 1;
                profile.save();
                refreshMenu();
            }
        });
        row2.addView(soundBtn, weight());
        row2.addView(space(dp(8)));
        row2.addView(musicBtn, weight());
        col.addView(row2, new LinearLayout.LayoutParams(-1, dp(50)));

        TextView help = label("Swipe ← → to switch lanes  •  ↑ jump  •  ↓ roll", 12, WHITE);
        help.setPadding(0, dp(10), 0, 0);
        col.addView(help);
        menuLayer.addView(col, match());
        root.addView(menuLayer, match());
    }

    private void refreshMenu() {
        menuCoins.setText(fmt(profile.coins));
        menuKeys.setText(String.valueOf(profile.keys));
        menuBoards.setText(String.valueOf(profile.boards));
        menuBest.setText("BEST  " + fmt(profile.highScore));
        menuMult.setText("MULTIPLIER x" + profile.missions.multiplier);
        soundBtn.setText("SOUND  " + (profile.soundOn == 1 ? "ON" : "OFF"));
        musicBtn.setText("MUSIC  " + (profile.musicOn == 1 ? "ON" : "OFF"));
    }

    private void startRun() {
        hideAll();
        hudLayer.setVisibility(View.VISIBLE);
        lastScore = lastCoins = lastMult = lastBoards = -1;
        gl(new Runnable() {
            public void run() {
                scene.setPreviewCharacter(-1);
                game.start();
            }
        });
    }

    private void buildPause() {
        pauseLayer = dimLayer();
        LinearLayout p = panel();
        p.addView(label("PAUSED", 38, INK));
        pauseMissions = new LinearLayout(this);
        pauseMissions.setOrientation(LinearLayout.VERTICAL);
        pauseMissions.setPadding(0, dp(10), 0, dp(14));
        p.addView(pauseMissions, new LinearLayout.LayoutParams(-1, -2));
        TextView resume = gameButton("RESUME", LEAF, 22);
        resume.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { resumeWithCountdown(); } });
        p.addView(resume, new LinearLayout.LayoutParams(-1, dp(64)));
        TextView menu = gameButton("MAIN MENU", SAKURA, 18);
        menu.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                gl(new Runnable() {
                    public void run() {
                        // coins picked up so far are kept
                        profile.coins += game.coinsRun;
                        game.coinsRun = 0;
                        profile.save();
                        game.toMenu();
                    }
                });
            }
        });
        LinearLayout.LayoutParams ml = new LinearLayout.LayoutParams(-1, dp(56));
        ml.topMargin = dp(10);
        p.addView(menu, ml);
        pauseLayer.addView(p, centered(dp(330)));
        root.addView(pauseLayer, match());
    }

    private void resumeWithCountdown() {
        pauseLayer.setVisibility(View.GONE);
        countdown.setVisibility(View.VISIBLE);
        for (int i = 3; i >= 1; i--) {
            final int n = i;
            ui.postDelayed(new Runnable() {
                public void run() { countdown.setText(String.valueOf(n)); pop(countdown); }
            }, (3 - i) * 600L);
        }
        ui.postDelayed(new Runnable() {
            public void run() {
                countdown.setVisibility(View.GONE);
                gl(new Runnable() { public void run() { game.resume(); } });
            }
        }, 1800);
    }

    private void buildSaveMe() {
        saveMeLayer = dimLayer();
        saveMeLayer.setClickable(true);
        saveMeLayer.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { gl(new Runnable() { public void run() { game.declineSaveMe(); } }); }
        });
        LinearLayout p = panel();
        p.addView(badge("守", OMAMORI_RED, 56), new LinearLayout.LayoutParams(dp(56), dp(56)));
        saveMeTitle = label("KEEP RUNNING?", 34, SAKURA);
        saveMeTitle.setPadding(0, dp(6), 0, 0);
        p.addView(saveMeTitle);
        TextView sub = label("An omamori charm shakes off the crash", 14, SOFT_TEXT);
        sub.setPadding(0, 0, 0, dp(14));
        p.addView(sub);
        saveMeBtn = gameButton("USE 1 OMAMORI", OMAMORI_RED, 17);
        saveMeBtn.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { gl(new Runnable() { public void run() { game.saveMe(); } }); }
        });
        p.addView(saveMeBtn, new LinearLayout.LayoutParams(-1, dp(66)));
        FrameLayout bar = new FrameLayout(this);
        GradientDrawable bt = rounded(0x262E2440, dp(6));
        bt.setStroke(dp(2), INK);
        bar.setBackground(bt);
        saveMeBar = new View(this);
        saveMeBar.setBackground(rounded(MON, dp(6)));
        saveMeBar.setPivotX(0);
        bar.addView(saveMeBar, new FrameLayout.LayoutParams(-1, dp(12)));
        LinearLayout.LayoutParams bl = new LinearLayout.LayoutParams(-1, dp(12));
        bl.topMargin = dp(14);
        p.addView(bar, bl);
        TextView skip = label("tap anywhere to skip", 12, SOFT_TEXT);
        skip.setPadding(0, dp(10), 0, 0);
        p.addView(skip);
        p.setClickable(true);
        saveMeLayer.addView(p, centered(dp(330)));
        root.addView(saveMeLayer, match());
    }

    private void buildGameOver() {
        overLayer = dimLayer();
        LinearLayout p = panel();
        overTitle = label("CRASHED!", 36, ROCKET_RED);
        p.addView(overTitle);
        overNew = label("NEW HIGH SCORE!", 15, WHITE);
        overNew.setPadding(dp(14), dp(3), dp(14), dp(7));
        overNew.setBackground(chip(SAKURA));
        LinearLayout.LayoutParams nl = new LinearLayout.LayoutParams(-2, -2);
        nl.topMargin = dp(4);
        p.addView(overNew, nl);
        TextView sl = label("SCORE", 13, SOFT_TEXT);
        sl.setPadding(0, dp(8), 0, 0);
        p.addView(sl);
        overScore = label("0", 52, INK);
        p.addView(overScore);
        LinearLayout r = hrow();
        r.setGravity(Gravity.CENTER);
        r.addView(coinIcon(22));
        overCoins = label("0", 22, MON);
        overCoins.setPadding(dp(6), 0, dp(20), 0);
        r.addView(overCoins);
        overBest = label("BEST 0", 15, SOFT_TEXT);
        r.addView(overBest);
        p.addView(r);
        overMissions = new LinearLayout(this);
        overMissions.setOrientation(LinearLayout.VERTICAL);
        overMissions.setPadding(0, dp(10), 0, dp(14));
        p.addView(overMissions, new LinearLayout.LayoutParams(-1, -2));
        TextView again = gameButton("RUN AGAIN", LEAF, 22);
        again.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { startRun(); } });
        p.addView(again, new LinearLayout.LayoutParams(-1, dp(64)));
        LinearLayout row = hrow();
        row.setPadding(0, dp(10), 0, 0);
        TextView menu = gameButton("MENU", MUTED, 16);
        menu.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { gl(new Runnable() { public void run() { game.toMenu(); } }); }
        });
        TextView shop = gameButton("SHOP", SUNSET, 16);
        shop.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                gl(new Runnable() { public void run() { game.toMenu(); } });
                ui.postDelayed(new Runnable() { public void run() { openShop(); } }, 120);
            }
        });
        row.addView(menu, weight());
        row.addView(space(dp(8)));
        row.addView(shop, weight());
        p.addView(row, new LinearLayout.LayoutParams(-1, dp(64)));
        overLayer.addView(p, centered(dp(340)));
        root.addView(overLayer, match());
    }

    private void showGameOver() {
        overTitle.setText(game.deathKind == 1 ? "CAUGHT!" : "CRASHED!");
        overScore.setText(fmt(game.score()));
        overCoins.setText("+" + fmt(game.coinsRun));
        overBest.setText("BEST " + fmt(profile.highScore));
        overNew.setVisibility(game.score() >= profile.highScore && game.score() > 0 ? View.VISIBLE : View.GONE);
        fillMissions(overMissions, false);
        fadeIn(overLayer);
        pop(overScore);
    }

    private void fillMissions(LinearLayout into, boolean big) {
        into.removeAllViews();
        Missions m = profile.missions;
        TextView h = flat(label("MISSIONS  •  MULTIPLIER x" + m.multiplier, big ? 15 : 12, LILAC));
        h.setGravity(Gravity.LEFT);
        into.addView(h);
        for (int i = 0; i < 3; i++) {
            LinearLayout row = hrow();
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(8), dp(7), dp(10), dp(7));
            GradientDrawable bg = rounded(m.done[i] ? 0x405DBE6A : 0x142E2440, dp(12));
            bg.setStroke(dp(1.5f), m.done[i] ? LEAF : 0x332E2440);
            row.setBackground(bg);
            int sz = big ? 30 : 26;
            row.addView(badge(m.done[i] ? "✔" : String.valueOf(i + 1), m.done[i] ? LEAF : LILAC, sz),
                    new LinearLayout.LayoutParams(dp(sz), dp(sz)));
            LinearLayout txt = new LinearLayout(this);
            txt.setOrientation(LinearLayout.VERTICAL);
            txt.setPadding(dp(10), 0, 0, 0);
            TextView d = label(m.describe(i), big ? 15 : 13, INK);
            d.setGravity(Gravity.LEFT);
            txt.addView(d);
            TextView pr = label(fmt(m.progress[i]) + " / " + fmt(m.target[i]), 11, SOFT_TEXT);
            pr.setGravity(Gravity.LEFT);
            txt.addView(pr);
            row.addView(txt, weight());
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
            lp.topMargin = dp(6);
            into.addView(row, lp);
        }
    }

    // ------------------------------------------------------------------ shop

    private void buildShop() {
        shopLayer = dimLayer();
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setPadding(dp(16), dp(20), dp(16), dp(16));
        LinearLayout head = hrow();
        head.setGravity(Gravity.CENTER_VERTICAL);
        TextView title = label("SHOP", 38, WHITE);
        title.setGravity(Gravity.LEFT);
        head.addView(title, weight());
        shopCoins = statPill(new MonCoin());
        head.addView(shopCoins);
        col.addView(head);
        ScrollView sv = new ScrollView(this);
        shopList = new LinearLayout(this);
        shopList.setOrientation(LinearLayout.VERTICAL);
        shopList.setPadding(0, 0, 0, dp(8));
        sv.addView(shopList);
        col.addView(sv, new LinearLayout.LayoutParams(-1, 0, 1f));
        TextView back = gameButton("BACK", MUTED, 18);
        back.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { backToMenu(); } });
        LinearLayout.LayoutParams bk = new LinearLayout.LayoutParams(-1, dp(58));
        bk.topMargin = dp(8);
        col.addView(back, bk);
        shopLayer.addView(col, match());
        root.addView(shopLayer, match());
    }

    private void openShop() {
        hideAll();
        refreshShop();
        fadeIn(shopLayer);
    }

    private void refreshShop() {
        shopCoins.setText(fmt(profile.coins));
        shopList.removeAllViews();
        String[] desc = {"Blast up over the trains and grab the sky coins.", "Spring so high you land on train roofs.",
                "The golden lucky cat pulls every nearby coin to you.", "Every point counts double while it shines."};
        // shop order follows Profile's upgrades (rocket, boots, magnet, star); the HUD bars use the same entries
        for (int i = 0; i < 4; i++) {
            final int up = i;
            int cost = profile.upgradeCost(i);
            StringBuilder pips = new StringBuilder();
            for (int k = 0; k < Profile.MAX_UP; k++) pips.append(k < profile.upgrades[i] ? "● " : "○ ");
            shopRow(POWER_GLYPH[i], POWER_COL[i], UPGRADE_NAME[i],
                    desc[i] + "\nLasts " + (int) profile.powerDuration(i) + "s   " + pips,
                    cost < 0 ? "MAX" : fmt(cost), cost >= 0 && profile.coins >= cost, new Runnable() {
                        public void run() {
                            int c = profile.upgradeCost(up);
                            if (c < 0 || profile.coins < c) return;
                            profile.coins -= c;
                            profile.upgrades[up]++;
                            done("UPGRADED!");
                        }
                    });
        }
        shopRow("風", SKY, "Kaze Board", "Double-tap while running. Rides out one crash.\nOwned: " + profile.boards,
                fmt(Profile.BOARD_COST), profile.coins >= Profile.BOARD_COST, new Runnable() {
                    public void run() {
                        if (profile.coins < Profile.BOARD_COST) return;
                        profile.coins -= Profile.BOARD_COST;
                        profile.boards++;
                        done("+1 KAZE BOARD");
                    }
                });
        shopRow("守", OMAMORI_RED, "Omamori", "A lucky charm that keeps your run going after a crash.\nOwned: " + profile.keys,
                fmt(Profile.KEY_COST), profile.coins >= Profile.KEY_COST, new Runnable() {
                    public void run() {
                        if (profile.coins < Profile.KEY_COST) return;
                        profile.coins -= Profile.KEY_COST;
                        profile.keys++;
                        done("+1 OMAMORI");
                    }
                });
        shopRow("福", SAKURA, "Gacha Capsule", "Coins, Kaze Boards or even an omamori inside!",
                fmt(Profile.BOX_COST), profile.coins >= Profile.BOX_COST, new Runnable() {
                    public void run() {
                        if (profile.coins < Profile.BOX_COST) return;
                        profile.coins -= Profile.BOX_COST;
                        Random r = new Random();
                        float x = r.nextFloat();
                        String msg;
                        if (x < 0.1f) { profile.keys++; msg = "JACKPOT! +1 OMAMORI"; }
                        else if (x < 0.4f) { profile.boards += 2; msg = "+2 KAZE BOARDS"; }
                        else if (x < 0.5f) { profile.coins += 2000; msg = "+2000 COINS!"; }
                        else { int c = 200 + r.nextInt(5) * 100; profile.coins += c; msg = "+" + c + " COINS"; }
                        done(msg);
                    }
                });
    }

    private void done(String msg) {
        profile.save();
        audio.play(Game.SND_POWER);
        showBanner(msg);
        refreshShop();
    }

    private void shopRow(String glyph, int color, String name, String desc, String price, boolean enabled, final Runnable buy) {
        LinearLayout row = hrow();
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(12), dp(12), dp(15), dp(17));
        row.setBackground(paper(dp(18), true));
        row.addView(badge(glyph, color, 48), new LinearLayout.LayoutParams(dp(48), dp(48)));
        LinearLayout txt = new LinearLayout(this);
        txt.setOrientation(LinearLayout.VERTICAL);
        txt.setPadding(dp(12), 0, dp(8), 0);
        TextView n = label(name, 17, INK);
        n.setGravity(Gravity.LEFT);
        txt.addView(n);
        TextView d = new TextView(this);
        d.setText(desc);
        d.setTextSize(12);
        d.setTextColor(SOFT_TEXT);
        txt.addView(d);
        row.addView(txt, weight());
        TextView b = gameButton(price, enabled ? LEAF : MUTED, 15);
        b.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { buy.run(); }
        });
        row.addView(b, new LinearLayout.LayoutParams(dp(92), dp(50)));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.topMargin = dp(10);
        shopList.addView(row, lp);
    }

    // ------------------------------------------------------------------ heroes

    private void buildHeroes() {
        heroesLayer = new FrameLayout(this);
        LinearLayout p = panel();
        LinearLayout row = hrow();
        row.setGravity(Gravity.CENTER_VERTICAL);
        TextView prev = circleButton("◀", SKY);
        TextView next = circleButton("▶", SKY);
        prev.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { showHero(heroIdx - 1); } });
        next.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { showHero(heroIdx + 1); } });
        LinearLayout mid = new LinearLayout(this);
        mid.setOrientation(LinearLayout.VERTICAL);
        mid.setGravity(Gravity.CENTER);
        heroName = label("", 30, INK);
        heroTag = label("", 13, SOFT_TEXT);
        mid.addView(heroName);
        mid.addView(heroTag);
        row.addView(prev, new LinearLayout.LayoutParams(dp(50), dp(50)));
        row.addView(mid, weight());
        row.addView(next, new LinearLayout.LayoutParams(dp(50), dp(50)));
        p.addView(row, new LinearLayout.LayoutParams(-1, -2));
        heroBtn = gameButton("", LEAF, 20);
        heroBtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { heroAction(); } });
        LinearLayout.LayoutParams hb = new LinearLayout.LayoutParams(-1, dp(62));
        hb.topMargin = dp(12);
        p.addView(heroBtn, hb);
        TextView back = gameButton("BACK", MUTED, 16);
        back.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { backToMenu(); } });
        LinearLayout.LayoutParams bl = new LinearLayout.LayoutParams(-1, dp(52));
        bl.topMargin = dp(8);
        p.addView(back, bl);
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(-1, -2, Gravity.BOTTOM);
        lp.setMargins(dp(12), 0, dp(12), dp(16));
        heroesLayer.addView(p, lp);
        root.addView(heroesLayer, match());
    }

    private void openHeroes() {
        hideAll();
        showHero(profile.selected);
        fadeIn(heroesLayer);
    }

    private void showHero(int idx) {
        int n = CharacterDef.ALL.length;
        heroIdx = (idx + n) % n;
        final int h = heroIdx;
        gl(new Runnable() { public void run() { scene.setPreviewCharacter(h); } });
        CharacterDef d = CharacterDef.ALL[heroIdx];
        heroName.setText(d.name.toUpperCase(Locale.US));
        heroTag.setText(d.tagline);
        if (profile.selected == heroIdx) {
            heroBtn.setText("SELECTED");
            heroBtn.setBackground(buttonBg(MUTED));
        } else if (profile.owned[heroIdx]) {
            heroBtn.setText("SELECT");
            heroBtn.setBackground(buttonBg(LEAF));
        } else {
            heroBtn.setText("UNLOCK  " + fmt(d.price));
            heroBtn.setBackground(buttonBg(profile.coins >= d.price ? SUNSET : MUTED));
        }
    }

    private void heroAction() {
        CharacterDef d = CharacterDef.ALL[heroIdx];
        if (!profile.owned[heroIdx]) {
            if (profile.coins < d.price) { showBanner("NOT ENOUGH COINS"); return; }
            profile.coins -= d.price;
            profile.owned[heroIdx] = true;
            audio.play(Game.SND_MISSION);
            showBanner(d.name.toUpperCase(Locale.US) + " UNLOCKED!");
        }
        profile.selected = heroIdx;
        profile.save();
        showHero(heroIdx);
    }

    // ------------------------------------------------------------------ missions

    private void buildMissions() {
        missionsLayer = dimLayer();
        LinearLayout p = panel();
        p.addView(label("MISSIONS", 36, INK));
        TextView sub = label("Finish all three to raise your score multiplier!", 13, SOFT_TEXT);
        sub.setPadding(0, 0, 0, dp(10));
        p.addView(sub);
        missionsList = new LinearLayout(this);
        missionsList.setOrientation(LinearLayout.VERTICAL);
        p.addView(missionsList, new LinearLayout.LayoutParams(-1, -2));
        TextView back = gameButton("BACK", MUTED, 18);
        back.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { backToMenu(); } });
        LinearLayout.LayoutParams bl = new LinearLayout.LayoutParams(-1, dp(56));
        bl.topMargin = dp(16);
        p.addView(back, bl);
        missionsLayer.addView(p, centered(dp(350)));
        root.addView(missionsLayer, match());
    }

    private void openMissions() {
        hideAll();
        fillMissions(missionsList, true);
        fadeIn(missionsLayer);
    }

    private void backToMenu() {
        hideAll();
        refreshMenu();
        fadeIn(menuLayer);
        gl(new Runnable() { public void run() { scene.setPreviewCharacter(-1); } });
    }

    // ------------------------------------------------------------------ view helpers

    /** The game's messages use the old item names; the screens show the Pongo names. */
    private static String display(String msg) {
        return msg.replace("SUPER SNEAKERS", "TOBI BOOTS").replace("COIN MAGNET", "MANEKI MAGNET")
                .replace("2X MULTIPLIER", "FEVER STAR  2X").replace("JETPACK", "HAYATE ROCKET")
                .replace("MYSTERY BOX", "GACHA").replace("HOVERBOARDS", "KAZE BOARDS").replace("HOVERBOARD", "KAZE BOARD")
                .replace("KEYS", "OMAMORI").replace("KEY", "OMAMORI");
    }

    private void showBanner(String text) {
        banner.setText(text);
        banner.setVisibility(View.VISIBLE);
        banner.setBackground(paper(dp(20), false));
        banner.setPadding(dp(20), dp(10), dp(22), dp(16));
        banner.setTextSize(text.length() > 22 ? 17 : 22);
        banner.animate().cancel();
        banner.setAlpha(1);
        banner.setScaleX(0.6f);
        banner.setScaleY(0.6f);
        banner.animate().scaleX(1).scaleY(1).setDuration(250).setInterpolator(new OvershootInterpolator()).start();
        ui.removeCallbacks(hideBanner);
        ui.postDelayed(hideBanner, 1800);
    }

    private final Runnable hideBanner = new Runnable() {
        public void run() {
            banner.animate().alpha(0).setDuration(300).withEndAction(new Runnable() {
                public void run() { banner.setVisibility(View.GONE); }
            }).start();
        }
    };

    private static String fmt(int n) { return String.format(Locale.US, "%,d", n); }

    private int dp(float v) { return (int) (v * getResources().getDisplayMetrics().density + 0.5f); }

    private static FrameLayout.LayoutParams match() { return new FrameLayout.LayoutParams(-1, -1); }

    private static FrameLayout.LayoutParams centered(int w) { return new FrameLayout.LayoutParams(w, -2, Gravity.CENTER); }

    private static LinearLayout.LayoutParams weight() { return new LinearLayout.LayoutParams(0, -1, 1f); }

    private View space(int w) {
        View v = new View(this);
        v.setLayoutParams(new LinearLayout.LayoutParams(w, 1));
        return v;
    }

    private LinearLayout hrow() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.HORIZONTAL);
        return l;
    }

    /** Text in the heavy face. Ink text sits on paper as it is; any other colour gets a violet ink outline and a
     *  little drop below it, so it reads over the 3D scene and on the pastel buttons. */
    private TextView label(String s, float sp, int color) {
        InkText t = new InkText(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(color);
        t.setTypeface(heavy);
        t.setGravity(Gravity.CENTER);
        if (color != INK && color != SOFT_TEXT) {
            float px = sp * getResources().getDisplayMetrics().scaledDensity;
            t.stroke = Math.max(dp(1.8f), px * 0.16f);
            t.drop = Math.max(dp(1f), px * 0.06f);
        }
        return t;
    }

    /** A coloured label printed straight on the paper, without the ink outline. */
    private static TextView flat(TextView t) {
        if (t instanceof InkText) ((InkText) t).stroke = 0;
        return t;
    }

    private GradientDrawable rounded(int color, float r) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(r);
        return g;
    }

    /** A pastel chip with an ink rim (multiplier, ribbons, tags). */
    private GradientDrawable chip(int color) {
        GradientDrawable g = rounded(color, dp(40));
        g.setStroke(dp(2.5f), INK);
        return g;
    }

    /** Cream paper card with an ink rim and a violet drop shadow; framed cards add a thin sakura line inside. */
    private LayerDrawable paper(float r, boolean framed) {
        int sh = dp(4);
        GradientDrawable shadow = rounded(0x552E2440, r);
        GradientDrawable face = new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM, new int[]{PAPER, PAPER_LOW});
        face.setCornerRadius(r);
        face.setStroke(dp(2.5f), INK);
        Drawable[] layers;
        if (framed) {
            GradientDrawable line = new GradientDrawable();
            line.setColor(0);
            line.setCornerRadius(Math.max(dp(4), r - dp(5)));
            line.setStroke(dp(1.5f), 0xAAF5A9C6);
            layers = new Drawable[]{shadow, face, line};
        } else {
            layers = new Drawable[]{shadow, face};
        }
        LayerDrawable ld = new LayerDrawable(layers);
        ld.setLayerInset(0, sh / 2, sh, 0, 0);
        ld.setLayerInset(1, 0, 0, sh / 2, sh);
        if (framed) ld.setLayerInset(2, dp(6), dp(6), sh / 2 + dp(6), sh + dp(6));
        return ld;
    }

    /** Raised pastel button: ink-rimmed face over a darker lip, lit from the top. */
    private LayerDrawable buttonBg(int color) {
        GradientDrawable lip = rounded(darken(color), dp(18));
        lip.setStroke(dp(3), INK);
        GradientDrawable face = new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{lighten(lighten(color)), lighten(color), color});
        face.setCornerRadius(dp(18));
        face.setStroke(dp(3), INK);
        LayerDrawable ld = new LayerDrawable(new Drawable[]{lip, face});
        ld.setLayerInset(1, 0, 0, 0, dp(6));
        return ld;
    }

    private TextView gameButton(String s, int color, float sp) {
        final TextView t = label(s, sp, WHITE);
        t.setBackground(buttonBg(color));
        t.setPadding(dp(8), 0, dp(8), dp(6));
        t.setClickable(true);
        t.setOnTouchListener(new View.OnTouchListener() {
            public boolean onTouch(View v, MotionEvent e) {
                if (e.getAction() == MotionEvent.ACTION_DOWN) v.animate().scaleX(0.94f).scaleY(0.94f).setDuration(60).start();
                else if (e.getAction() == MotionEvent.ACTION_UP || e.getAction() == MotionEvent.ACTION_CANCEL)
                    v.animate().scaleX(1).scaleY(1).setDuration(90).start();
                return false;
            }
        });
        return t;
    }

    private TextView circleButton(String s, int color) {
        TextView t = label(s, 18, color == PAPER ? INK : WHITE);
        GradientDrawable g = new GradientDrawable();
        g.setShape(GradientDrawable.OVAL);
        g.setColor(color);
        g.setStroke(dp(3), INK);
        t.setBackground(g);
        t.setClickable(true);
        return t;
    }

    /** A rounded square badge with a glyph (power-up kanji, mission number). */
    private TextView badge(String glyph, int color, int sizeDp) {
        TextView t = label(glyph, sizeDp * 0.46f, WHITE);
        GradientDrawable g = rounded(color, dp(sizeDp * 0.3f));
        g.setStroke(dp(2.5f), INK);
        t.setBackground(g);
        t.setPadding(0, 0, 0, dp(1));
        return t;
    }

    private TextView statPill(Drawable icon) {
        TextView t = label("", 15, INK);
        t.setPadding(dp(8), dp(5), dp(15), dp(9));
        t.setBackground(paper(dp(18), false));
        icon.setBounds(0, 0, dp(22), dp(22));
        t.setCompoundDrawables(icon, null, null, null);
        t.setCompoundDrawablePadding(dp(6));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, -2);
        lp.setMargins(dp(4), 0, dp(4), 0);
        t.setLayoutParams(lp);
        return t;
    }

    private View coinIcon(int size) {
        View v = new View(this);
        v.setBackground(new MonCoin());
        v.setLayoutParams(new LinearLayout.LayoutParams(dp(size), dp(size)));
        return v;
    }

    private FrameLayout dimLayer() {
        FrameLayout f = new FrameLayout(this);
        f.setBackgroundColor(0x802E2440);
        f.setClickable(true);
        return f;
    }

    private LinearLayout panel() {
        LinearLayout p = new LinearLayout(this);
        p.setOrientation(LinearLayout.VERTICAL);
        p.setGravity(Gravity.CENTER_HORIZONTAL);
        p.setPadding(dp(20), dp(18), dp(22), dp(24));
        p.setBackground(paper(dp(26), true));
        return p;
    }

    private static int darken(int c) {
        int r = (int) (((c >> 16) & 255) * 0.72f), g = (int) (((c >> 8) & 255) * 0.68f), b = (int) ((c & 255) * 0.78f);
        return Color.argb(255, r, g, b);
    }

    private static int lighten(int c) {
        int r = ((c >> 16) & 255), g = ((c >> 8) & 255), b = (c & 255);
        return Color.argb(255, r + (255 - r) / 4, g + (255 - g) / 4, b + (255 - b) / 4);
    }

    private void fadeIn(View v) {
        v.setVisibility(View.VISIBLE);
        v.setAlpha(0);
        v.animate().alpha(1).setDuration(200).start();
    }

    private void pop(View v) {
        v.setScaleX(1.4f);
        v.setScaleY(1.4f);
        v.animate().scaleX(1).scaleY(1).setDuration(260).setInterpolator(new OvershootInterpolator()).start();
    }

    private void pulse(final View v) {
        v.animate().scaleX(1.05f).scaleY(1.05f).setDuration(600).setInterpolator(new AccelerateDecelerateInterpolator())
                .withEndAction(new Runnable() {
                    public void run() {
                        v.animate().scaleX(1f).scaleY(1f).setDuration(600).withEndAction(new Runnable() {
                            public void run() { pulse(v); }
                        }).start();
                    }
                }).start();
    }

    /** TextView that draws its text twice: an ink stroke (with a small drop) under the coloured fill. */
    static final class InkText extends TextView {
        float stroke, drop;
        private boolean inDraw;

        InkText(Context c) { super(c); }

        @Override
        protected void onDraw(Canvas c) {
            if (stroke <= 0) { super.onDraw(c); return; }
            inDraw = true;
            ColorStateList fill = getTextColors();
            Paint p = getPaint();
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeJoin(Paint.Join.ROUND);
            p.setStrokeWidth(stroke);
            p.setShadowLayer(0.5f, 0, drop, INK);
            setTextColor(INK);
            super.onDraw(c);
            p.setStyle(Paint.Style.FILL);
            p.clearShadowLayer();
            setTextColor(fill);
            super.onDraw(c);
            inDraw = false;
        }

        @Override
        public void invalidate() { if (!inDraw) super.invalidate(); }
    }

    /** A gold Mon coin: ink rim, raised inner ring and the square hole. */
    static final class MonCoin extends Drawable {
        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);

        @Override
        public void draw(Canvas c) {
            Rect b = getBounds();
            float cx = b.exactCenterX(), cy = b.exactCenterY(), r = Math.min(b.width(), b.height()) / 2f;
            float w = Math.max(1.5f, r * 0.16f);
            p.setStyle(Paint.Style.FILL);
            p.setColor(INK);
            c.drawCircle(cx, cy, r, p);
            p.setColor(MON);
            c.drawCircle(cx, cy, r - w, p);
            p.setColor(0xFFFFE08A);
            c.drawCircle(cx - r * 0.12f, cy - r * 0.12f, r * 0.52f, p);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(w * 0.6f);
            p.setColor(MON_DARK);
            c.drawCircle(cx, cy, r * 0.6f, p);
            p.setStyle(Paint.Style.FILL);
            float h = r * 0.24f;
            p.setColor(INK);
            c.drawRoundRect(new RectF(cx - h - w * 0.5f, cy - h - w * 0.5f, cx + h + w * 0.5f, cy + h + w * 0.5f), w, w, p);
            p.setColor(MON_DARK);
            c.drawRect(cx - h + w * 0.3f, cy - h + w * 0.3f, cx + h - w * 0.3f, cy + h - w * 0.3f, p);
        }

        @Override public void setAlpha(int a) { p.setAlpha(a); }
        @Override public void setColorFilter(ColorFilter f) { p.setColorFilter(f); }
        @Override public int getOpacity() { return PixelFormat.TRANSLUCENT; }
    }

    /** A small round icon with a kanji on it (for the stat pills). */
    final class Glyph extends Drawable {
        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final String s;
        private final int col;

        Glyph(String s, int col) { this.s = s; this.col = col; }

        @Override
        public void draw(Canvas c) {
            Rect b = getBounds();
            float cx = b.exactCenterX(), cy = b.exactCenterY(), r = Math.min(b.width(), b.height()) / 2f;
            float w = Math.max(1.5f, r * 0.16f);
            p.setStyle(Paint.Style.FILL);
            p.setColor(INK);
            c.drawCircle(cx, cy, r, p);
            p.setColor(col);
            c.drawCircle(cx, cy, r - w, p);
            p.setColor(WHITE);
            p.setTypeface(heavy);
            p.setTextAlign(Paint.Align.CENTER);
            p.setTextSize(r * 1.1f);
            Paint.FontMetrics fm = p.getFontMetrics();
            c.drawText(s, cx, cy - (fm.ascent + fm.descent) / 2, p);
        }

        @Override public void setAlpha(int a) { p.setAlpha(a); }
        @Override public void setColorFilter(ColorFilter f) { p.setColorFilter(f); }
        @Override public int getOpacity() { return PixelFormat.TRANSLUCENT; }
    }
}
