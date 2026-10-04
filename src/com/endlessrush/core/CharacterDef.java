package com.endlessrush.core;

/** Playable characters. Pongo is the only one; she is drawn from pongo.bin by PongoScene. */
public final class CharacterDef {
    public final String name, tagline;
    public final int price;

    public CharacterDef(String name, String tagline, int price) {
        this.name = name; this.tagline = tagline; this.price = price;
    }

    public static final CharacterDef[] ALL = {
            new CharacterDef("Pongo", "Freerunner of the Sakura Line.", 0),
    };
}
