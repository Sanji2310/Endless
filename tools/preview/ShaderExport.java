import com.pongo.core.Shaders;

import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;

/** Writes shaders.json for the WebGL harness from com.pongo.core.Shaders. */
public class ShaderExport {
    public static void main(String[] a) throws Exception {
        StringBuilder sb = new StringBuilder("{\"programs\":[");
        for (int i = 0; i < Shaders.PROGRAMS.length; i++) {
            String[] p = Shaders.PROGRAMS[i];
            if (i > 0) sb.append(',');
            sb.append('[').append(q(p[0])).append(',').append(q(p[1])).append(',').append(q(p[2])).append(',').append(q(p[3])).append(']');
        }
        sb.append("],\"sources\":{");
        String[] keys = {"MAIN_VS", "MAIN_FS", "OUTLINE_VS", "OUTLINE_FS", "SHADOW_VS", "SHADOW_FS", "SKY_VS", "SKY_FS", "PART_VS", "PART_FS", "SCREEN_VS", "SCREEN_FS"};
        for (int i = 0; i < keys.length; i++) {
            if (i > 0) sb.append(',');
            sb.append(q(keys[i])).append(':').append(q(Shaders.source(keys[i])));
        }
        sb.append("}}");
        try (Writer w = new OutputStreamWriter(new FileOutputStream(a[0]), StandardCharsets.UTF_8)) { w.write(sb.toString()); }
    }

    static String q(String s) {
        StringBuilder b = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                default: b.append(c);
            }
        }
        return b.append('"').toString();
    }
}
