package com.endlessrush.core;

/** Original playable characters (colour + style definitions). */
public final class CharacterDef {
    public static final int HAIR = 0, CAP = 1, BEANIE = 2, HELMET = 3, BUNS = 4;

    public final String name, tagline;
    public final int price;
    public final int skin, hair, top, topAccent, pants, shoes, headwear, style;

    public CharacterDef(String name, String tagline, int price, int skin, int hair, int top, int topAccent,
                        int pants, int shoes, int headwear, int style) {
        this.name = name; this.tagline = tagline; this.price = price;
        this.skin = skin; this.hair = hair; this.top = top; this.topAccent = topAccent;
        this.pants = pants; this.shoes = shoes; this.headwear = headwear; this.style = style;
    }

    public static final CharacterDef[] ALL = {
            new CharacterDef("Jax", "Street artist. Always late.", 0,
                    0xE8B38A, 0x3A2415, 0x2F7DE1, 0xFFFFFF, 0x2B3A55, 0xE94B3C, 0xE94B3C, CAP),
            new CharacterDef("Nova", "Skater with a sonic boom.", 6000,
                    0xF2C9A0, 0x8E3FD6, 0xFFC928, 0x222222, 0x3B3B46, 0xFFFFFF, 0x8E3FD6, BUNS),
            new CharacterDef("Rook", "Parkour prodigy.", 12000,
                    0x8D5A3B, 0x111111, 0xFF7A1A, 0x1B1B1B, 0x4A5A2E, 0x2BD17E, 0x2BD17E, BEANIE),
            new CharacterDef("Mika", "Never met a wall she couldn't paint.", 20000,
                    0xF5D0B0, 0xF06FA5, 0x29C7C7, 0xF06FA5, 0x1E2230, 0xFFE14D, 0xF06FA5, HAIR),
            new CharacterDef("Bolt-9", "Runs on pure voltage.", 40000,
                    0xB8C3CF, 0x22303F, 0x39475A, 0x3DF0FF, 0x2A3442, 0x3DF0FF, 0x3DF0FF, HELMET),
    };
}
