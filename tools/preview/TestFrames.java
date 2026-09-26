import com.pongo.core.*;

import java.io.*;

/** Quick harness test: coin turntable on a floor with sun shadows. */
public class TestFrames {
    public static void main(String[] a) throws Exception {
        PongoAssets as = PongoAssets.load(new BufferedInputStream(new FileInputStream(a[0])), false);
        int coin = as.lod("coin", 0), floor = as.mesh("test_floor");
        int n = 4;
        try (DataOutputStream o = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(a[1])))) {
            o.write("PGF1".getBytes());
            o.writeInt(Integer.reverseBytes(n));
            for (int i = 0; i < n; i++) {
                RenderFrame f = new RenderFrame();
                f.screenW = 720; f.screenH = 720;
                float yaw = i * 25f;
                Mat4.lookAt(f.view, 1.2f, 1.1f, 2.2f, 0, 0.6f, 0, 0, 1, 0);
                Mat4.perspective(f.proj, 32, 1f, 0.1f, 200f);
                Mat4.mul(f.viewProj, f.proj, f.view);
                Mat4.invert(f.invViewProj, f.viewProj);
                f.camPos[0] = 1.2f; f.camPos[1] = 1.1f; f.camPos[2] = 2.2f;
                float[] sd = {0.55f, 0.75f, 0.45f};
                float l = (float) Math.sqrt(sd[0] * sd[0] + sd[1] * sd[1] + sd[2] * sd[2]);
                for (int k = 0; k < 3; k++) f.sunDir[k] = sd[k] / l;
                float[] lv = new float[16], lp = new float[16];
                Mat4.lookAt(lv, f.sunDir[0] * 20, f.sunDir[1] * 20, f.sunDir[2] * 20, 0, 0, 0, 0, 1, 0);
                Mat4.ortho(lp, -3, 3, -3, 3, 1, 40);
                Mat4.mul(f.shadowVP, lp, lv);
                f.shadowOn = true; f.shadowSize = 1024;
                f.fogStart = 50; f.fogEnd = 150;
                if (floor >= 0) f.draw(floor);
                float[] m = f.draw(coin);
                Mat4.translate(m, 0, 0.62f, 0);
                Mat4.rotY(m, yaw - 20);
                f.write(o);
            }
        }
    }
}
