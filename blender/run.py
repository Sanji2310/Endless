"""Entry point: blender -b -P blender/run.py -- <module> [function] [args...]"""
import sys, os, importlib, time
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("lib", "assets", "scenes"):
    p = os.path.join(HERE, d)
    if p not in sys.path:
        sys.path.insert(0, p)
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not args:
    print("usage: blender -b -P blender/run.py -- <module> [function] [args]")
    sys.exit(1)
t0 = time.time()
mod = importlib.import_module(args[0])
fn = getattr(mod, args[1] if len(args) > 1 else "main")
fn(*args[2:])
print("done in %.1fs" % (time.time() - t0))
