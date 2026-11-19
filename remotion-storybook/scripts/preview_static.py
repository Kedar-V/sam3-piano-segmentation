"""Quick numpy composite of the layers + one decoded foreground frame, for art review (not the Remotion render)."""
import subprocess, sys, numpy as np, cv2
from PIL import Image
PX, PY = 60, 107; W, H = 1080, 1920
n = int(sys.argv[1]) if len(sys.argv) > 1 else 90
raw = subprocess.run(['ffmpeg','-v','error','-i','public/footage/foreground_alpha.mov','-vf',f'select=eq(n\\,{n})','-fps_mode','passthrough','-frames:v','1','-f','rawvideo','-pix_fmt','rgba','-'],capture_output=True,check=True).stdout
fg = np.frombuffer(raw, np.uint8).reshape(H, W, 4).astype(np.float32)
keep = cv2.imread(f'public/masks/keep/{n:05d}.png', cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255
fg[..., 3] *= keep
def load(p, mode):
    a = np.asarray(Image.open(p).convert(mode)).astype(np.float32); return a[PY:PY+H, PX:PX+W]
bg = load('src/assets/illustrations/background.jpg', 'RGB')
mid = load('src/assets/illustrations/midground.png', 'RGBA')
fgl = load('src/assets/illustrations/foreground.png', 'RGBA')
fgb = load('src/assets/illustrations/foreground_blur.png', 'RGBA')
def over(dst, src):
    a = src[..., 3:4] / 255; return dst * (1 - a) + src[..., :3] * a
out = over(over(bg, mid), fg)
out = over(over(out, fgl), fgb)
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize((540, 960), Image.LANCZOS).save('/tmp/static_preview.png')
Image.fromarray(np.clip(over(bg, mid), 0, 255).astype(np.uint8)).resize((540, 960), Image.LANCZOS).save('/tmp/static_bgmid.png')
print('ok')
