package android.opengl;

/** Desktop stand-in for the preview build (only the Renderer interface). */
public class GLSurfaceView {
    public interface Renderer {
        void onSurfaceCreated(javax.microedition.khronos.opengles.GL10 gl, javax.microedition.khronos.egl.EGLConfig config);

        void onSurfaceChanged(javax.microedition.khronos.opengles.GL10 gl, int width, int height);

        void onDrawFrame(javax.microedition.khronos.opengles.GL10 gl);
    }
}
