#!/usr/bin/env python3
"""Export compositing assets from SAM 3 raw masks: refined masks, outline mattes,
ProRes 4444 alpha video, audio, manifest, previews and validation.

Reuses existing raw masks (does not run SAM 3). Streams frames, so it works for long clips.

Raw mask layout (written by the Colab notebook):
  <raw>/performer/NNNNN.png   0/255, full frame size, frame index NNNNN == decoded frame index in the segment
  <raw>/piano/NNNNN.png
  <raw>/reflection/NNNNN.png  (optional: person-prompt object that is the hands' reflection in the lid)
"""
import argparse, glob, hashlib, json, os, shutil, subprocess, sys, time
import numpy as np
import cv2
from scipy import ndimage as ndi

DEFAULTS = {
    "outline": {"enabled": True, "color": "#F5EBDD", "widthPx": 3, "blurPx": 1.5, "opacity": 0.65, "externalSilhouetteOnly": True},
    "edgeFeatherPx": 2,
    "lightWrap": {"enabled": True, "opacity": 0.15},
    "refinement": {"minComponentPx": 400, "minHolePx": 150, "smoothSigmaPx": 1.2, "edgeShrinkPx": 1,
                   "temporal": "median3", "closeUnionPx": 1, "pianoUnderPerformerPx": 2},
}


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def ffprobe_json(path, extra):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-of", "json"] + extra + [path])
    return json.loads(out)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ mask refinement
def clean(m, min_comp, min_hole):
    """Remove isolated specks and fill tiny holes. m: uint8 0/1."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= min_comp
    m = keep[lab].astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(1 - m, connectivity=4)
    small = np.zeros(n, bool)
    small[1:] = st[1:, cv2.CC_STAT_AREA] < min_hole
    return np.where(small[lab], 1, m).astype(np.uint8)


def smooth_binary(m, sigma):
    """Smooth jagged edges without changing shape much: blur then re-threshold."""
    return (cv2.GaussianBlur(m.astype(np.float32), (0, 0), sigma) > 0.5).astype(np.uint8)


def shrink(m, px):
    if px <= 0:
        return m
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    return cv2.erode(m, k)


def grow(m, px):
    if px <= 0:
        return m
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    return cv2.dilate(m, k)


def feather(m, feather_px):
    """Soft alpha 0..1 with ~feather_px transition width (gaussian sigma = feather/2)."""
    if feather_px <= 0:
        return m.astype(np.float32)
    return np.clip(cv2.GaussianBlur(m.astype(np.float32), (0, 0), feather_px / 2.0), 0, 1)


def load_mask(raw, name, i):
    p = os.path.join(raw, name, f"{i:05d}.png")
    if not os.path.exists(p):
        return None
    m = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    return (m > 127).astype(np.uint8)


class MaskWindow:
    """Sliding window over raw masks for temporal median-of-3 without loading everything."""

    def __init__(self, raw, name, n, shape):
        self.raw, self.name, self.n, self.shape = raw, name, n, shape
        self.cache = {}

    def get(self, i):
        i = min(max(i, 0), self.n - 1)
        if i not in self.cache:
            m = load_mask(self.raw, self.name, i)
            self.cache[i] = np.zeros(self.shape, np.uint8) if m is None else m
            for k in [k for k in self.cache if k < i - 2]:
                del self.cache[k]
        return self.cache[i]

    def temporal(self, i, mode):
        if mode != "median3":
            return self.get(i)
        s = self.get(i - 1).astype(np.uint8) + self.get(i) + self.get(i + 1)
        return (s >= 2).astype(np.uint8)


def decontaminate_edges(rgb, alpha, band_px=4):
    """Optional: replace colours in the semi-transparent band with nearby fully-opaque colours (normalised blur)."""
    core = (alpha > 0.98).astype(np.float32)
    k = (2 * band_px + 1, 2 * band_px + 1)
    num = cv2.blur(rgb.astype(np.float32) * core[..., None], k)
    den = cv2.blur(core, k)[..., None]
    fill = num / np.maximum(den, 1e-4)
    band = ((alpha > 0.0) & (alpha <= 0.98))[..., None]
    out = np.where(band & (den > 1e-3), fill, rgb.astype(np.float32))
    return np.clip(out, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ I/O helpers
def frame_reader(src, start, seconds, W, H):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", src, "-t", str(seconds), "-an",
           "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.stdout.close()
    p.wait()


def alpha_encoder(path, W, H, fps_str, qscale):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", fps_str, "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv",
           "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16",
           "-qscale:v", str(qscale), "-vendor", "apl0",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def mp4_encoder(path, W, H, fps_str, audio=None, seconds=None):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", fps_str, "-i", "-"]
    if audio:
        cmd += ["-i", audio]
    cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-crf", "18",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-movflags", "+faststart", path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def write_png(path, arr):
    cv2.imwrite(path, arr, [cv2.IMWRITE_PNG_COMPRESSION, 3])


# ------------------------------------------------------------------ backgrounds / compositing (previews)
def checkerboard(W, H, sq=40):
    y, x = np.indices((H, W))
    c = (((x // sq) + (y // sq)) % 2).astype(np.uint8)
    img = np.where(c[..., None] == 0, 204, 153).astype(np.uint8)
    return np.repeat(img, 3, axis=2) if img.shape[2] == 1 else img


def solid(W, H, rgb=(255, 79, 163)):
    return np.full((H, W, 3), rgb, np.uint8)


def warm_gradient(W, H):
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top, bot = np.array([255, 214, 153], np.float32), np.array([214, 96, 77], np.float32)
    g = top * (1 - t) + bot * t
    y, x = np.indices((H, W))
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)[..., None]
    g = g * (1 - 0.18 * np.clip(r - 0.4, 0, 1))
    return np.clip(np.broadcast_to(g, (H, W, 3)), 0, 255).astype(np.uint8)


_WRAP_CACHE = {}


def composite(fg_rgba, bg, outline_a=None, outline_cfg=None, light_wrap_cfg=None):
    a = fg_rgba[..., 3:4].astype(np.float32) / 255.0
    rgb = fg_rgba[..., :3].astype(np.float32)
    out = bg.astype(np.float32)
    if outline_a is not None and outline_cfg and outline_cfg["enabled"]:
        oa = (outline_a.astype(np.float32) / 255.0)[..., None] * outline_cfg["opacity"]
        col = np.array(hex_to_rgb(outline_cfg["color"]), np.float32)
        out = out * (1 - oa) + col * oa
    if light_wrap_cfg and light_wrap_cfg["enabled"]:
        edge = (a[..., 0] * (1 - cv2.GaussianBlur(a[..., 0], (0, 0), 6)))[..., None]
        edge = np.clip(edge * 2.0, 0, 1)
        key = id(bg)
        if key not in _WRAP_CACHE:
            _WRAP_CACHE[key] = cv2.GaussianBlur(bg.astype(np.float32), (0, 0), 12)
        wrap = _WRAP_CACHE[key]
        rgb =rgb * (1 - light_wrap_cfg["opacity"] * edge) + wrap * (light_wrap_cfg["opacity"] * edge)
    return np.clip(rgb * a + out * (1 - a), 0, 255).astype(np.uint8)


def decode_rgba(path, W, H, nframes):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-frames:v", str(nframes), "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                         stdout=subprocess.PIPE)
    n = W * H * 4
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 4)
    p.stdout.close()
    p.wait()


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="original video")
    ap.add_argument("--raw", required=True, help="raw_masks dir with performer/ piano/ [reflection/]")
    ap.add_argument("--out", required=True, help="output root (piano_compositing)")
    ap.add_argument("--start", type=float, default=0.0, help="segment start in source (s)")
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--config", default=None, help="compositing.json overrides")
    ap.add_argument("--work", default="/tmp/piano_export_work", help="local scratch dir (big files are written here then copied)")
    ap.add_argument("--qscale", type=int, default=6, help="ProRes qscale (lower=bigger/better)")
    ap.add_argument("--preview-seconds", type=float, default=5.0)
    ap.add_argument("--no-decontaminate", action="store_true")
    a = ap.parse_args()

    cfg = json.loads(json.dumps(DEFAULTS))
    if a.config:
        user = json.load(open(a.config))
        for k, v in user.items():
            cfg[k] = {**cfg[k], **v} if isinstance(v, dict) and isinstance(cfg.get(k), dict) else v
    rf = cfg["refinement"]
    t0 = time.time()

    # ---- 1. inspect inputs
    vs = ffprobe_json(a.src, ["-select_streams", "v:0", "-show_entries",
                              "stream=codec_name,profile,width,height,r_frame_rate,avg_frame_rate,pix_fmt,color_space,duration,nb_frames:stream_side_data=rotation"])["streams"][0]
    fps_str = vs["r_frame_rate"]
    num, den = map(int, fps_str.split("/"))
    fps = num / den
    has_audio = bool(ffprobe_json(a.src, ["-select_streams", "a:0", "-show_entries", "stream=codec_name,sample_rate,channels"])["streams"])
    raw_sets = {n: len(glob.glob(os.path.join(a.raw, n, "*.png"))) for n in ("performer", "piano", "reflection")}
    print("source:", vs)
    print("raw mask counts:", raw_sets)
    N = raw_sets["performer"]
    assert N > 0 and raw_sets["piano"] == N, f"performer/piano mask counts differ: {raw_sets}"
    first = load_mask(a.raw, "performer", 0)
    H, W = first.shape
    expected = int(round(a.seconds * fps))
    print(f"mask size {W}x{H}, {N} frames (segment expects {expected} at {fps_str})")
    rot = 0
    for sd in vs.get("side_data_list", []):
        rot = int(sd.get("rotation", rot))
    dw, dh = (int(vs["height"]), int(vs["width"])) if abs(rot) in (90, 270) else (int(vs["width"]), int(vs["height"]))
    assert (dw, dh) == (W, H), f"mask size {W}x{H} != displayed source size {dw}x{dh} (rotation {rot})"
    assert abs(N - expected) <= 1, f"mask count {N} != expected frames {expected} for {a.seconds}s at {fps_str}"
    has_refl = raw_sets["reflection"] == N

    root = a.out
    sub = {k: os.path.join(root, k) for k in ("source", "alpha", "masks/combined", "masks/performer", "masks/piano", "masks/outline", "previews", "config")}
    for d in sub.values():
        os.makedirs(d, exist_ok=True)
    work = a.work
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)

    # ---- audio
    audio_path = os.path.join(sub["source"], "original_audio.wav")
    if has_audio:
        sh(["ffmpeg", "-y", "-v", "error", "-ss", str(a.start), "-i", a.src, "-t", str(a.seconds), "-vn", "-c:a", "pcm_s16le", audio_path])

    # ---- 2/3/4. per-frame refinement + export
    winP = MaskWindow(a.raw, "performer", N, (H, W))
    winQ = MaskWindow(a.raw, "piano", N, (H, W))
    winR = MaskWindow(a.raw, "reflection", N, (H, W)) if has_refl else None
    encs = {n: alpha_encoder(os.path.join(work, f"{n}_alpha.mov"), W, H, fps_str, a.qscale) for n in ("foreground", "performer", "piano")}
    stats = {"combined_area": [], "performer_area": [], "piano_area": [], "outline_area": []}
    prev = {"combined": None, "performer": None}
    iou_c, iou_p = [], []
    n_done = 0
    for i, rgb in enumerate(frame_reader(a.src, a.start, a.seconds, W, H)):
        if i >= N:
            break
        P = clean(smooth_binary(clean(winP.temporal(i, rf["temporal"]), rf["minComponentPx"], rf["minHolePx"]), rf["smoothSigmaPx"]), rf["minComponentPx"], rf["minHolePx"])
        Qraw = winQ.temporal(i, rf["temporal"])
        if winR is not None:
            Qraw = np.maximum(Qraw, winR.temporal(i, rf["temporal"]))
        Q = clean(smooth_binary(clean(Qraw, rf["minComponentPx"], rf["minHolePx"]), rf["smoothSigmaPx"]), rf["minComponentPx"], rf["minHolePx"])
        # union with hairline-crack closing; performer has visual priority by construction (union keeps real hand pixels)
        U = np.maximum(P, Q)
        if rf["closeUnionPx"] > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rf["closeUnionPx"] + 1,) * 2)
            U = cv2.morphologyEx(U, cv2.MORPH_CLOSE, k)
        U = clean(U, rf["minComponentPx"], rf["minHolePx"])
        # visible piano only (occluded piano cannot be reconstructed); keep a thin band under the performer edge to avoid seams when stacked
        Qvis = (Q & (1 - shrink(P, rf["pianoUnderPerformerPx"]))).astype(np.uint8)
        e = rf["edgeShrinkPx"]
        Us, Ps, Qs = shrink(U, e), shrink(P, e), shrink(Qvis, e)
        aU, aP, aQ = feather(Us, cfg["edgeFeatherPx"]), feather(Ps, cfg["edgeFeatherPx"]), feather(Qs, cfg["edgeFeatherPx"])
        # outline: external silhouette only (fill interior holes), ring outside the shrunk silhouette, then blur
        S = ndi.binary_fill_holes(Us).astype(np.uint8)
        ring = (grow(S, int(cfg["outline"]["widthPx"])) & (1 - S)).astype(np.float32)
        ol = np.clip(cv2.GaussianBlur(ring, (0, 0), max(cfg["outline"]["blurPx"], 0.01)), 0, 1)
        for nm, al in (("foreground", aU), ("performer", aP), ("piano", aQ)):
            col = rgb if a.no_decontaminate else decontaminate_edges(rgb, al)
            rgba = np.dstack([col, (al * 255 + 0.5).astype(np.uint8)])
            encs[nm].stdin.write(rgba.tobytes())
        write_png(os.path.join(sub["masks/combined"], f"{i:05d}.png"), (aU * 255 + 0.5).astype(np.uint8))
        write_png(os.path.join(sub["masks/performer"], f"{i:05d}.png"), (aP * 255 + 0.5).astype(np.uint8))
        write_png(os.path.join(sub["masks/piano"], f"{i:05d}.png"), (aQ * 255 + 0.5).astype(np.uint8))
        write_png(os.path.join(sub["masks/outline"], f"{i:05d}.png"), (ol * 255 + 0.5).astype(np.uint8))
        stats["combined_area"].append(int(Us.sum())); stats["performer_area"].append(int(Ps.sum())); stats["piano_area"].append(int(Qs.sum())); stats["outline_area"].append(int((ol > 0.5).sum()))
        for key, m in (("combined", Us), ("performer", Ps)):
            if prev[key] is not None:
                u = (m | prev[key]).sum()
                (iou_c if key == "combined" else iou_p).append(float((m & prev[key]).sum() / max(u, 1)))
            prev[key] = m
        n_done += 1
        if i % 40 == 0:
            print(f"  frame {i}/{N}  {time.time() - t0:.0f}s", flush=True)
    for e_ in encs.values():
        e_.stdin.close()
    for e_ in encs.values():
        e_.wait()
    assert n_done == N, f"decoded {n_done} frames but have {N} masks"

    for nm in ("foreground", "performer", "piano"):
        shutil.copy(os.path.join(work, f"{nm}_alpha.mov"), os.path.join(sub["alpha"], f"{nm}_alpha.mov"))

    # ---- 7. previews decoded from the exported ProRes file (validates alpha round-trip)
    pn = int(round(a.preview_seconds * fps))
    fgmov = os.path.join(sub["alpha"], "foreground_alpha.mov")
    bg_chk, bg_sol, bg_warm = checkerboard(W, H), solid(W, H), warm_gradient(W, H)
    tw, th = W // 3, H // 3
    ex = {"checkerboard": mp4_encoder(os.path.join(sub["previews"], "checkerboard.mp4"), W, H, fps_str, audio_path if has_audio else None),
          "illustrated": mp4_encoder(os.path.join(sub["previews"], "illustrated_test.mp4"), W, H, fps_str, audio_path if has_audio else None),
          "compare": mp4_encoder(os.path.join(sub["previews"], "outline_comparison.mp4"), tw * 3, th * 2, fps_str, audio_path if has_audio else None)}
    for i, fg in enumerate(decode_rgba(fgmov, W, H, pn)):
        olm = cv2.imread(os.path.join(sub["masks/outline"], f"{i:05d}.png"), cv2.IMREAD_GRAYSCALE)
        ex["checkerboard"].stdin.write(composite(fg, bg_chk).tobytes())
        ex["illustrated"].stdin.write(composite(fg, bg_warm, olm, cfg["outline"], cfg["lightWrap"]).tobytes())
        rows = []
        for use_outline in (False, True):
            tiles = []
            for bg in (bg_sol, bg_chk, bg_warm):
                img = composite(fg, bg, olm if use_outline else None, cfg["outline"] if use_outline else None, cfg["lightWrap"] if use_outline else None)
                tiles.append(cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA))
            rows.append(np.hstack(tiles))
        ex["compare"].stdin.write(np.vstack(rows).tobytes())
    for e_ in ex.values():
        e_.stdin.close()
    for e_ in ex.values():
        e_.wait()

    # ---- 10. validation
    def info(path):
        v = ffprobe_json(path, ["-count_frames", "-select_streams", "v:0", "-show_entries",
                                "stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,nb_read_frames,duration,color_space,color_primaries,color_transfer:stream_tags=encoder"])["streams"][0]
        v["size_bytes"] = os.path.getsize(path)
        return v

    files = {f"alpha/{n}_alpha.mov": info(os.path.join(sub["alpha"], f"{n}_alpha.mov")) for n in ("foreground", "performer", "piano")}
    for pv in ("checkerboard.mp4", "illustrated_test.mp4", "outline_comparison.mp4"):
        files[f"previews/{pv}"] = info(os.path.join(sub["previews"], pv))
    alpha_checks = {}
    for nm in ("foreground", "performer", "piano"):
        mp = os.path.join(sub["alpha"], f"{nm}_alpha.mov")
        res = []
        for idx in (0, N // 2, N - 1):
            fr = next(iter(decode_rgba_at(mp, W, H, idx)))
            al = fr[..., 3]
            res.append({"frame": idx, "alpha_min": int(al.min()), "alpha_max": int(al.max()),
                        "frac_transparent": round(float((al == 0).mean()), 4), "frac_opaque": round(float((al == 255).mean()), 4),
                        "frac_partial": round(float(((al > 0) & (al < 255)).mean()), 4)})
        alpha_checks[nm] = res
    ts = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time", "-of", "csv=p=0",
                                  "-read_intervals", f"{a.start}%+{a.seconds + 1}", a.src]).decode().split()
    ts = [float(x.split(",")[0]) for x in ts if x.strip(",")][:N]
    mov_ts = [float(x.split(",")[0]) for x in subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time", "-of", "csv=p=0", fgmov]).decode().split() if x.strip(",")]
    audio_dur = float(ffprobe_json(audio_path, ["-show_entries", "format=duration"])["format"]["duration"]) if has_audio else None
    sync = {"source_frames_in_segment": len(ts), "masks": N, "foreground_mov_frames": int(files["alpha/foreground_alpha.mov"]["nb_read_frames"]),
            "mov_fps": files["alpha/foreground_alpha.mov"]["r_frame_rate"], "source_fps": fps_str,
            "mov_pts_constant_step": bool(len(mov_ts) > 1 and np.allclose(np.diff(mov_ts), 1 / fps, atol=1e-4)),
            "source_pts_max_deviation_from_ideal_s": round(float(np.max(np.abs(np.array(ts) - (a.start + np.arange(len(ts)) / fps)))), 5) if ts else None,
            "mov_pts_max_deviation_from_ideal_s": round(float(np.max(np.abs(np.array(mov_ts) - np.arange(len(mov_ts)) / fps))), 5) if mov_ts else None,
            "video_duration_s": round(N / fps, 4), "audio_duration_s": audio_dur,
            "audio_minus_video_s": None if audio_dur is None else round(audio_dur - N / fps, 4)}

    manifest = {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {"path": a.src, "video": vs, "has_audio": has_audio},
        "segment": {"start_s": a.start, "duration_s": a.seconds, "frames": N, "fps": fps_str, "fps_float": fps,
                    "width": W, "height": H, "frame_timestamps_s": [round(a.start + i / fps, 6) for i in range(N)],
                    "source_pts_s": ts},
        "alpha_format": {"container": "QuickTime .mov", "codec": "ProRes 4444 (prores_ks, profile 4444)", "pix_fmt": "encoded from yuva444p10le (ffprobe reports the decoded format as yuva444p12le)",
                         "alpha_bits": 16, "alpha_mode": "STRAIGHT (non-premultiplied); RGB is not multiplied by alpha",
                         "colour": "BT.709, limited range, tagged", "frame_rate_preserved": True},
        "mask_identities": {"verified_by": "mask area/centroid/overlap statistics below plus visual crops; NOT by overlay colours",
                            "performer": "SAM 3 text prompt 'person playing piano', object id 0 (largest, person body/hands/face)",
                            "reflection": "same prompt, object id 1 (small, located in the piano lid: the reflection of the hands)" if has_refl else "NOT AVAILABLE in this run",
                            "piano": "SAM 3 text prompt 'grand piano'"},
        "raw_masks": {"dir": a.raw, "type": "binary (0/255), not probability, not alpha-matted", "counts": raw_sets},
        "refinement": {**rf, "edgeFeatherPx": cfg["edgeFeatherPx"], "decontaminate_edges": not a.no_decontaminate},
        "layering": {"combined": "union(performer, piano[+reflection]); real pixels unchanged",
                     "performer_alpha": "performer only",
                     "piano_alpha": "VISIBLE piano only (piano minus performer, plus a thin band under the performer edge); occluded piano is NOT reconstructed",
                     "stacking": "piano_alpha under performer_alpha reproduces foreground_alpha except for a possible 1-2 px feather seam"},
        "mask_stats": {"consecutive_iou_combined_min": round(min(iou_c), 4) if iou_c else None, "consecutive_iou_combined_mean": round(float(np.mean(iou_c)), 4) if iou_c else None,
                       "consecutive_iou_performer_min": round(min(iou_p), 4) if iou_p else None,
                       "area_px_median": {k: int(np.median(v)) for k, v in stats.items()}},
        "files": files, "alpha_checks": alpha_checks, "sync": sync,
        "outputs": {"audio": "source/original_audio.wav" if has_audio else None},
        "elapsed_s": round(time.time() - t0, 1),
    }
    json.dump(manifest, open(os.path.join(sub["config"], "manifest.json"), "w"), indent=2)
    json.dump({k: cfg[k] for k in ("outline", "edgeFeatherPx", "lightWrap")}, open(os.path.join(sub["config"], "compositing.json"), "w"), indent=2)
    write_readme(root, manifest, has_refl)
    print(json.dumps({"sync": sync, "alpha_checks": alpha_checks["foreground"], "files": {k: (v["codec_name"], v["pix_fmt"], v["size_bytes"]) for k, v in files.items()}}, indent=1))
    print(f"done in {time.time() - t0:.0f}s -> {root}")


def decode_rgba_at(path, W, H, idx):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"select=eq(n\\,{idx})", "-fps_mode", "passthrough", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                         stdout=subprocess.PIPE)
    b = p.stdout.read(W * H * 4)
    p.stdout.close(); p.wait()
    yield np.frombuffer(b, np.uint8).reshape(H, W, 4)


def write_readme(root, m, has_refl):
    s = m["segment"]
    txt = f"""# Piano compositing export

Segment: {s['start_s']}s - {s['start_s'] + s['duration_s']}s of the source ({s['frames']} frames, {s['fps']} fps, {s['width']}x{s['height']}).
Generated by `src/export/export_composite.py`. SAM 3 was not re-run for this export (raw masks reused).

## Alpha videos (`alpha/`)
- `foreground_alpha.mov`: performer + piano{' + lid reflection' if has_refl else ''}, original pixels, transparent background. **No outline, no background, no colour grade baked in.**
- `performer_alpha.mov`: performer only.
- `piano_alpha.mov`: VISIBLE piano only. Piano hidden behind the performer is not reconstructed (nothing invented).
- Codec: ProRes 4444, `yuva444p10le`, 16-bit alpha, **straight (non-premultiplied) alpha**, BT.709 limited range.

## Masks (`masks/`)
8-bit grayscale PNGs, one per frame (`NNNNN.png`, index = frame number in the segment). `combined/`, `performer/`, `piano/` are refined and feathered
(alpha). `outline/` is the external-silhouette outline matte at full strength (apply colour/opacity in the compositor).
Raw SAM 3 masks stay untouched at `{m['raw_masks']['dir']}`.

## Config (`config/`)
`compositing.json` holds outline / feather / light-wrap parameters (starting points). `manifest.json` holds timing, file info and validation results.

## Known limitations
- Raw SAM 3 masks are binary; soft alpha comes from 2 px feathering, not true matting. Hair strands and finger motion blur are not matted.
- Piano standalone layer lacks pixels hidden by the performer (documented, not invented).
- Frame images are the decoded source; semi-transparent edge pixels are colour-decontaminated unless disabled.
"""
    open(os.path.join(root, "README.md"), "w").write(txt)


if __name__ == "__main__":
    main()
