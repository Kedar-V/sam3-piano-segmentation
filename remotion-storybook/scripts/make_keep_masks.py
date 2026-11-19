"""Build per-frame 'keep' masks (RGBA PNG, alpha = keep) that drop tiny disconnected specks from the exported combined masks.
Non-destructive: the exported foreground video is untouched; Remotion multiplies its alpha by this mask.
Usage: python scripts/make_keep_masks.py [min_component_px=5000] [grow_px=8]"""
import sys, os, glob, cv2, numpy as np
min_px = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
grow = int(sys.argv[2]) if len(sys.argv) > 2 else 8
src, dst = 'public/masks/combined', 'public/masks/keep'
os.makedirs(dst, exist_ok=True)
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1))
removed = []
for p in sorted(glob.glob(f'{src}/*.png')):
    m = (cv2.imread(p, 0) > 20).astype(np.uint8)          # include feathered pixels
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros(n, np.uint8)
    keep[1:] = (st[1:, cv2.CC_STAT_AREA] >= min_px)
    removed.append(int(((st[1:, cv2.CC_STAT_AREA] < min_px)).sum()))
    kept = cv2.dilate(keep[lab], k)
    out = np.zeros((*m.shape, 4), np.uint8); out[..., :3] = 255; out[..., 3] = kept * 255
    cv2.imwrite(os.path.join(dst, os.path.basename(p)), out)
print(f'{len(removed)} frames; specks removed per frame: min {min(removed)} max {max(removed)} total {sum(removed)}')
