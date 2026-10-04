package android.os;

/** Desktop stand-in for the preview build. */
public final class SystemClock {
    public static long elapsedRealtime() { return System.nanoTime() / 1000000L; }
}
