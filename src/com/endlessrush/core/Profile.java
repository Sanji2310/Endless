package com.endlessrush.core;

/** Persistent player progress: currencies, upgrades, characters, missions. */
public final class Profile {
    public interface Store {
        int getInt(String key, int def);
        void putInt(String key, int value);
        void commit();
    }

    public static final int UP_JET = 0, UP_SNEAK = 1, UP_MAGNET = 2, UP_X2 = 3;
    public static final String[] UP_NAMES = {"Jetpack", "Super Sneakers", "Coin Magnet", "2X Multiplier"};
    public static final int[] UP_COST = {500, 1000, 2500, 5000, 10000, 20000};
    public static final int MAX_UP = 6;
    public static final int BOARD_COST = 300, KEY_COST = 2000, BOX_COST = 500;

    public int coins, keys = 1, boards = 3, highScore, selected, soundOn = 1, musicOn = 1;
    public int[] upgrades = new int[4];
    public boolean[] owned = new boolean[CharacterDef.ALL.length];
    public final Missions missions = new Missions();
    public int totalRuns;

    private final Store store;

    public Profile(Store store) {
        this.store = store;
        owned[0] = true;
        if (store != null) load();
    }

    public float powerDuration(int up) { return 10f + upgrades[up] * 2.5f; }

    public int upgradeCost(int up) { return upgrades[up] >= MAX_UP ? -1 : UP_COST[upgrades[up]]; }

    public void load() {
        coins = store.getInt("coins", 0);
        keys = store.getInt("keys", 1);
        boards = store.getInt("boards", 3);
        highScore = store.getInt("high", 0);
        selected = store.getInt("sel", 0);
        soundOn = store.getInt("sound", 1);
        musicOn = store.getInt("music", 1);
        totalRuns = store.getInt("runs", 0);
        for (int i = 0; i < 4; i++) upgrades[i] = store.getInt("up" + i, 0);
        for (int i = 0; i < owned.length; i++) owned[i] = i == 0 || store.getInt("own" + i, 0) == 1;
        if (selected < 0 || selected >= owned.length || !owned[selected]) selected = 0;
        missions.load(store);
    }

    public void save() {
        if (store == null) return;
        store.putInt("coins", coins);
        store.putInt("keys", keys);
        store.putInt("boards", boards);
        store.putInt("high", highScore);
        store.putInt("sel", selected);
        store.putInt("sound", soundOn);
        store.putInt("music", musicOn);
        store.putInt("runs", totalRuns);
        for (int i = 0; i < 4; i++) store.putInt("up" + i, upgrades[i]);
        for (int i = 0; i < owned.length; i++) store.putInt("own" + i, owned[i] ? 1 : 0);
        missions.save(store);
        store.commit();
    }
}
