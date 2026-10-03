import com.pongo.core.*;

import java.io.*;

/** Harness test: Pongo skinned + animated (run cycle from behind, idle from the front). */
public class TestPongo {
    public static void main(String[] a) throws Exception {
        PongoAssets as = PongoAssets.load(new BufferedInputStream(new FileInputStream(a[0])), false);
        int mesh = as.lod("pongo", 0), floor = as.mesh("test_floor");
        PongoAssets.Skeleton sk = as.skeletons[as.meshes[mesh].skeleton];
        System.out.println("bones " + sk.bones + " clips " + sk.clips.length);
        Animator an = new Animator(sk);
        String[][] shots = {{"run", "back"}, {"run", "back"}, {"run", "side"}, {"idle", "front"}, {"jump", "side"}, {"roll", "side"}, {"board", "back"}, {"glide", "front"}, {"idle", "backclose"}};
        try (DataOutputStream o = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(a[1])))) {
            o.write("PGF1".getBytes());
            o.writeInt(Integer.reverseBytes(shots.length));
            for (int i = 0; i < shots.length; i++) {
                an.restart(shots[i][0], 0);
                an.update(0.13f + i * 0.05f);
                RenderFrame f = new RenderFrame();
                f.screenW = 540; f.screenH = 760;
                float ex, ey, ez;
                switch (shots[i][1]) {
                    case "back": ex = 0.6f; ey = 2.4f; ez = 4.2f; break;
                    case "backclose": ex = 0.1f; ey = 1.3f; ez = 1.4f; break;
                    case "side": ex = 3.6f; ey = 1.4f; ez = 1.2f; break;
                    default: ex = 0.8f; ey = 1.4f; ez = -3.8f;
                }
                Mat4.lookAt(f.view, ex, ey, ez, 0, 0.95f, 0, 0, 1, 0);
                Mat4.perspective(f.proj, 40, 540f / 760f, 0.1f, 200f);
                Mat4.mul(f.viewProj, f.proj, f.view);
                Mat4.invert(f.invViewProj, f.viewProj);
                f.camPos[0] = ex; f.camPos[1] = ey; f.camPos[2] = ez;
                float[] sd = {0.45f, 0.8f, 0.4f};
                float l = (float) Math.sqrt(sd[0] * sd[0] + sd[1] * sd[1] + sd[2] * sd[2]);
                for (int k = 0; k < 3; k++) f.sunDir[k] = sd[k] / l;
                float[] lv = new float[16], lp = new float[16];
                Mat4.lookAt(lv, f.sunDir[0] * 20, f.sunDir[1] * 20, f.sunDir[2] * 20, 0, 0, 0, 0, 1, 0);
                Mat4.ortho(lp, -2.5f, 2.5f, -2.5f, 2.5f, 1, 40);
                Mat4.mul(f.shadowVP, lp, lv);
                f.shadowOn = true; f.shadowSize = 2048;
                if (floor >= 0) f.draw(floor);
                f.draw(mesh);
                f.bonesForLast(an.palette, sk.bones);
                f.write(o);
            }
        }
    }
}
