"""Build gap-closed mattes from the EXISTING refined masks (outputs/piano_compositing/masks), non-destructively.

Why: the raw performer and piano masks overlap by exactly 0 px, so a thin sliver of background shows between the hands and the
keys (a halo). Here the seam between the two refined masks is filled, tiny specks are removed, and a matching outline is rebuilt.
  public/masks/matte/NNNNN.png          RGBA white, alpha = soft combined matte (use as a CSS mask over the opaque plate)
  public/masks/outline_closed/NNNNN.png grayscale external-silhouette outline matte (3px, blurred 1.5px)
  public/masks/wrapband/NNNNN.png       RGBA white, alpha = soft band inside the edge (for the sampled light wrap)
Usage: python scripts/make_mattes.py [seam_px=7] [min_component_px=5000] [fill_holes_below_px=1500] [wrap_band_px=10]"""
import sys, os, glob, cv2, numpy as np
from scipy import ndimage as ndi
seam_r = int(sys.argv[1]) if len(sys.argv) > 1 else 7
min_px = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
hole_px = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
wrap_px = int(sys.argv[4]) if len(sys.argv) > 4 else 10
base = '../outputs/piano_compositing/masks'
os.makedirs('public/masks/matte', exist_ok=True); os.makedirs('public/masks/outline_closed', exist_ok=True); os.makedirs('public/masks/wrapband', exist_ok=True)
ell = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
filled_px = []
for p in sorted(glob.glob(f'{base}/combined/*.png')):
    nm = os.path.basename(p)
    U = (cv2.imread(p, 0) > 127).astype(np.uint8)
    P = (cv2.imread(f'{base}/performer/{nm}', 0) > 40).astype(np.uint8)
    Q = (cv2.imread(f'{base}/piano/{nm}', 0) > 40).astype(np.uint8)
    seam = cv2.dilate(P, ell(seam_r)) & cv2.dilate(Q, ell(seam_r))      # only where hand/arm meets the piano
    U2 = U | seam
    U2 = cv2.morphologyEx(U2, cv2.MORPH_CLOSE, ell(2))                    # pinholes
    inv = 1 - U2                                                          # fill small interior holes (fingertip/key pinholes)
    n0, lab0, st0, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    small = np.zeros(n0, bool); small[1:] = st0[1:, cv2.CC_STAT_AREA] < hole_px
    U2 = np.where(small[lab0], 1, U2).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(U2, connectivity=8)  # drop specks
    keep = np.zeros(n, np.uint8); keep[1:] = st[1:, cv2.CC_STAT_AREA] >= min_px
    U2 = keep[lab]
    filled_px.append(int((U2 & (1 - U)).sum()))
    Us = cv2.erode(U2, ell(1))
    alpha = np.clip(cv2.GaussianBlur(Us.astype(np.float32), (0, 0), 1.0), 0, 1)       # ~2px feather
    out = np.zeros((*U.shape, 4), np.uint8); out[..., :3] = 255; out[..., 3] = (alpha * 255 + .5).astype(np.uint8)
    cv2.imwrite(f'public/masks/matte/{nm}', out)
    # light-wrap band: soft strip just INSIDE the silhouette edge, used to let the blurred background bleed onto the edges
    inner = cv2.erode(Us, ell(wrap_px))
    band = np.clip(alpha - cv2.GaussianBlur(inner.astype(np.float32), (0, 0), 1.0), 0, 1)
    band = np.clip(cv2.GaussianBlur(band, (0, 0), wrap_px * 0.35), 0, 1) * alpha
    bo = np.zeros((*U.shape, 4), np.uint8); bo[..., :3] = 255; bo[..., 3] = (band * 255 + .5).astype(np.uint8)
    cv2.imwrite(f'public/masks/wrapband/{nm}', bo)
    S = ndi.binary_fill_holes(Us).astype(np.uint8)                        # external silhouette only
    ring = (cv2.dilate(S, ell(3)) & (1 - S)).astype(np.float32)
    ol = np.clip(cv2.GaussianBlur(ring, (0, 0), 1.5), 0, 1)
    cv2.imwrite(f'public/masks/outline_closed/{nm}', (ol * 255 + .5).astype(np.uint8))
print(f'{len(filled_px)} frames; px added by seam fill per frame: median {int(np.median(filled_px))} max {max(filled_px)}')
