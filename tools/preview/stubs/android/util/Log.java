package android.util;

/** Desktop stand-in for the preview build. */
public final class Log {
    public static int w(String tag, String msg) { System.err.println(tag + ": " + msg); return 0; }
}
