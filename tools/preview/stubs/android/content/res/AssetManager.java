package android.content.res;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;

/** Desktop stand-in for the preview build: serves files from a directory (the repo's assets/). */
public final class AssetManager {
    private final File dir;

    public AssetManager(File dir) { this.dir = dir; }

    public InputStream open(String name) throws IOException { return new FileInputStream(new File(dir, name)); }
}
