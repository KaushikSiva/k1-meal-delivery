"""Build the Tableside hackathon demo video (1920x1080, 30 fps) from real project footage +
motion graphics + verified Gemini TTS narration. Outputs: tableside_demo.mp4 (full narration) and
tableside_demo_live_narration.mp4 (final demo segment without voice, music only)."""
import json, math, subprocess, wave
from pathlib import Path

import imageio.v2 as iio
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

V = Path(__file__).resolve().parent
R = Path.home() / "workspace/k1-meal-delivery"
W, H, FPS = 1920, 1080, 30
NAVY = (9, 14, 28); AMBER = (255, 176, 59); WHITE = (245, 247, 250); GREY = (160, 170, 190); TEAL = (64, 214, 196)
AV = "/System/Library/Fonts/Avenir Next.ttc"


def font(size, bold=True):
    return ImageFont.truetype(AV, size, index=(2 if bold else 7))  # 2: Demi Bold, 7: Regular (fallback-safe)


def ease(t):  # smooth in-out 0..1
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ audio prep
def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


names = ["n1_why", "n2_name", "n3_arch", "n4_rl", "n4b_vla", "n5_team", "n6_demo"]
dur = {}
for n in names:
    run(["ffmpeg", "-y", "-i", str(V / f"{n}.wav"), "-af",
         "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
         "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,atempo=1.1,"
         "highpass=f=70,acompressor=threshold=-18dB:ratio=2.5:attack=8:release=120,loudnorm=I=-16:TP=-1.5",
         "-ar", "48000", "-ac", "1", str(V / f"{n}_proc.wav")])
    with wave.open(str(V / f"{n}_proc.wav")) as w:
        dur[n] = w.getnframes() / w.getframerate()
LEAD, GAP, END = 0.4, 0.25, 2.6
seg = {n: dur[n] + GAP for n in names}
seg["n1_why"] += LEAD
seg["n6_demo"] = min(max(dur["n6_demo"] + 0.3, 19.6), 24.8)
TOTAL = sum(seg.values()) + END
print("segments", {k: round(v, 2) for k, v in seg.items()}, "total", round(TOTAL, 2))

# ------------------------------------------------------------------ assets
import os
# Café footage: set CAFE_CLIP to an experiment dir with evaluator.mp4 (e.g. Codex's hand-carry run);
# CAFE_CAPTION / RL_NOTE must then describe that run honestly.
CAFE_DIR = Path(os.environ.get("CAFE_CLIP", R / "experiments/codex-20261017T2150-k1-appearance-repeat"))
CAFE_CAPTION = os.environ.get("CAFE_CAPTION", "Isaac Sim café · K1 + PPO policy · tray on a torso bracket (hand-carry physics in progress)")
RL_NOTE = os.environ.get("RL_NOTE", "PPO chart: torso-bracket tray run · hand-held PPO is next")
cafe_vid = iio.get_reader(str(CAFE_DIR / "evaluator.mp4"))
ISAAC_HAND = R / "experiments/codex-20261017T2305-hand-carry-isaac/attempt04/evaluator.mp4"  # Codex: café hand-carry, close tracking view, 15 s
isaac_reader = iio.get_reader(str(ISAAC_HAND))
isaac_frames = [isaac_reader.get_data(i) for i in range(isaac_reader.count_frames())]
HAND = R / "experiments/codex-20261017T2305-hand-carry-isaac/attempt03/evaluator.mp4"  # café wide, hand carry  # Codex hand-carry-10 (report: experiments/codex-20261017T2300-hand-carry): free tray + box + can, both hands, following camera
hand_reader = iio.get_reader(str(HAND))
HAND_VISIBLE_S = 14.96  # following camera keeps the robot in frame for the whole 15 s run
hand_frames = [hand_reader.get_data(i) for i in range(int(HAND_VISIBLE_S * 25) + 1)]
cafe_frames = [cafe_vid.get_data(i) for i in range(0, cafe_vid.count_frames())]  # 375 @25fps
hero = Image.open(R / "experiments/codex-20261017T2008-cafe-lit-preview/hero.png").convert("RGB")
nav_dir = R / "experiments/codex-20261017T2310-loaded-navigation/attempt05"  # camera-guided hand-carry nav, 25 fps
_ev = iio.get_reader(str(nav_dir / "evaluator.mp4")); _rc = iio.get_reader(str(nav_dir / "robot_camera.mp4"))
nav_eval = [_ev.get_data(i) for i in range(0, _ev.count_frames())]
nav_cam = [_rc.get_data(i) for i in range(0, _rc.count_frames())]
nav_times = np.arange(len(nav_eval)) / 25.0


def cover(img: Image.Image, w=W, h=H, zoom=1.0, cx=0.5, cy=0.5):
    iw, ih = img.size
    s = max(w / iw, h / ih) * zoom
    nw, nh = int(iw * s), int(ih * s)
    im = img.resize((nw, nh), Image.LANCZOS)
    x0 = int((nw - w) * cx); y0 = int((nh - h) * cy)
    return im.crop((x0, y0, x0 + w, y0 + h))


def gradient_overlay(img, strength=0.75, side="left"):
    a = np.linspace(strength, 0.0, W) if side == "left" else np.full(W, strength)
    mask = (np.tile(a, (H, 1)) * 255).astype(np.uint8)
    dark = Image.new("RGB", (W, H), NAVY)
    return Image.composite(dark, img, Image.fromarray(mask))


def text(d, xy, s, size, fill=WHITE, bold=True, alpha=1.0, anchor="la"):
    f = font(size, bold)
    col = tuple(int(c * alpha + n * (1 - alpha)) for c, n in zip(fill, NAVY))
    d.text(xy, s, font=f, fill=fill + (int(255 * alpha),), anchor=anchor)


def rgba_layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def lower_third(img, label, t, alpha_in=0.4):
    a = ease(t / alpha_in)
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([60, H - 120, 60 + 18 + font(26, False).getlength(label) + 30, H - 64], 12, fill=(9, 14, 28, int(200 * a)))
    d.rectangle([60, H - 120, 66, H - 64], fill=AMBER + (int(255 * a),))
    d.text((90, H - 92), label, font=font(26, False), fill=WHITE + (int(255 * a),), anchor="lm")
    return Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")


# ------------------------------------------------------------------ segments
def seg_why(t, D):
    k = min(int(t * 25), len(isaac_frames) - 1)  # real time
    bg = cover(Image.fromarray(isaac_frames[k]), zoom=1.25, cx=0.05, cy=0.55)  # tracking camera keeps the robot ~centered
    img = gradient_overlay(bg, 0.85, "left")
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    lines = [(0.6, "Restaurants are", 76), (1.2, "running out of hands.", 76)]
    for t0, s, sz in lines:
        a = ease((t - t0) / 0.6); y_off = (1 - a) * 30
        d.text((120, 300 + (0 if "Restaurants" in s else 100) + y_off), s, font=font(sz), fill=WHITE + (int(255 * a),))
    a2 = ease((t - 4.6) / 0.6)
    d.text((120, 560 + (1 - a2) * 20), "The hardest part is the", font=font(52, False), fill=GREY + (int(255 * a2),))
    d.text((120, 630 + (1 - a2) * 20), "last ten meters.", font=font(64), fill=AMBER + (int(255 * a2),))
    return lower_third(Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB"),
                       "Real hand-contact simulation • Isaac Sim • 2.19 m • 8 mm max payload shift • no drop • scripted baseline, one trial", t - 0.3)


hero_blur = cover(hero, zoom=1.1).filter(ImageFilter.GaussianBlur(14))


def seg_name(t, D):
    bg = cover(hero, zoom=1.12 + 0.04 * t / D).filter(ImageFilter.GaussianBlur(float(10 + 4 * (1 - ease(t / 1.0)))))
    img = Image.blend(bg, Image.new("RGB", (W, H), NAVY), 0.62)
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    a = ease(t / 0.9)
    word = "TABLESIDE"
    f = font(170); spacing = 34 * (1 - a) + 10
    total = sum(f.getlength(c) for c in word) + spacing * (len(word) - 1)
    x = (W - total) / 2
    for c in word:
        d.text((x, 470), c, font=f, fill=WHITE + (int(255 * a),), anchor="ls"); x += f.getlength(c) + spacing
    w_line = 520 * ease((t - 0.5) / 0.8)
    d.rectangle([W / 2 - w_line / 2, 505, W / 2 + w_line / 2, 509], fill=AMBER + (255,))
    a2 = ease((t - 1.1) / 0.7)
    d.text((W / 2, 585), "Hears “table three.”  Gets it there.", font=font(54, False), fill=WHITE + (int(255 * a2),), anchor="mm")
    a3 = ease((t - 1.8) / 0.7)
    d.text((W / 2, 670), "Booster K1  ·  MuJoCo  ·  Isaac Sim  ·  PPO  ·  VLA-ready", font=font(30, False), fill=GREY + (int(255 * a3),), anchor="mm")
    return Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")


NODES = [("Head RGB-D", "camera · gyro · joints"), ("Perception", "tables from depth\nnumbers from pixels"),
         ("Scene memory", "what it saw ·\nhow sure it is"), ("Executive", "search · verify ·\nnever guess"),
         ("Follower", "smooth, bounded\nvelocity"), ("K1 walking", "Booster policy\n+ PPO tray residual")]


def seg_arch(t, D):
    img = Image.new("RGB", (W, H), NAVY)
    d0 = ImageDraw.Draw(img)
    for gx in range(0, W, 60):  # subtle grid
        d0.line([(gx, 0), (gx, H)], fill=(14, 21, 40))
    for gy in range(0, H, 60):
        d0.line([(0, gy), (W, gy)], fill=(14, 21, 40))
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    a = ease(t / 0.6)
    d.text((120, 150), "How it works", font=font(64), fill=WHITE + (int(255 * a),))
    d.text((120, 232), "Camera to footsteps, with uncertainty at every step", font=font(32, False), fill=GREY + (int(255 * a),))
    n = len(NODES); bw, bh, gap = 262, 200, 44
    x0 = (W - (n * bw + (n - 1) * gap)) / 2; y = 470
    step = (D - 2.5) / n
    for i, (title, sub) in enumerate(NODES):
        ai = ease((t - 0.5 - i * step) / 0.5)
        x = x0 + i * (bw + gap)
        col = AMBER if title in ("Scene memory", "Executive") else TEAL
        d.rounded_rectangle([x, y + (1 - ai) * 25, x + bw, y + bh + (1 - ai) * 25], 22,
                            fill=(20, 30, 56, int(235 * ai)), outline=col + (int(255 * ai),), width=3)
        d.text((x + bw / 2, y + 60 + (1 - ai) * 25), title, font=font(30), fill=WHITE + (int(255 * ai),), anchor="mm")
        d.multiline_text((x + bw / 2, y + 128 + (1 - ai) * 25), sub, font=font(22, False), fill=GREY + (int(255 * ai),), anchor="mm", align="center", spacing=6)
        if i < n - 1:
            aa = ease((t - 0.8 - i * step) / 0.5)
            xa = x + bw + 8; xb = xa + (gap - 16) * aa
            d.line([(xa, y + bh / 2), (xb, y + bh / 2)], fill=WHITE + (int(200 * aa),), width=4)
            if aa > 0.95:
                d.polygon([(xb, y + bh / 2 - 9), (xb + 12, y + bh / 2), (xb, y + bh / 2 + 9)], fill=WHITE + (200,))
    # "not sure -> look again" loop from executive back to camera
    al = ease((t - (0.5 + 3.4 * step)) / 0.8)
    if al > 0:
        xe = x0 + 3 * (bw + gap) + bw / 2; xc = x0 + bw / 2; yl = y + bh + 70
        d.line([(xe, y + bh + 8), (xe, yl), (xc, yl), (xc, y + bh + 8)], fill=AMBER + (int(255 * al),), width=4, joint="curve")
        d.polygon([(xc - 10, y + bh + 22), (xc + 10, y + bh + 22), (xc, y + bh + 6)], fill=AMBER + (int(255 * al),))
        d.text(((xe + xc) / 2, yl + 36), "not sure?  look again", font=font(30), fill=AMBER + (int(255 * al),), anchor="mm")
    return Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")


def seg_rl(t, D):
    tc = min(t, HAND_VISIBLE_S)  # real time, then hold the last in-frame moment
    k = min(int(tc * 25), len(hand_frames) - 1)
    left = cover(Image.fromarray(hand_frames[k]), 1120, H, zoom=1.35, cx=0.22, cy=0.35)  # follow robot in wide café shot
    img = Image.new("RGB", (W, H), NAVY); img.paste(left, (0, 0))
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    a = ease(t / 0.6)
    X = 1200
    d.text((X, 170), "Carrying is learned", font=font(58), fill=WHITE + (int(255 * a),))
    d.text((X, 245), "PPO residual on Booster's walking policy", font=font(28, False), fill=GREY + (int(255 * a),))
    # payload shift bars (cup-holder v2, one trial each)
    bars = [("Baseline walking", 8.4, (230, 90, 90)), ("+ PPO (ours)", 3.3, TEAL)]
    for i, (lab, val, col) in enumerate(bars):
        ab = ease((t - 1.0 - i * 0.6) / 0.9)
        yb = 400 + i * 150
        d.text((X, yb), lab, font=font(30, False), fill=WHITE + (int(255 * a),))
        L = 560 * (val / 10.0) * ab
        d.rounded_rectangle([X, yb + 46, X + max(L, 1), yb + 96], 10, fill=col + (255,))
        d.text((max(X + L + 18, X + 560 * 0.4 + 18), yb + 71), f"{val * ab:.1f} cm", font=font(34), fill=col + (int(255 * ab),), anchor="lm")
    lim = X + 560 * 0.4
    al = ease((t - 2.4) / 0.6)
    for yb in (446, 596):  # limit marker only across the bars
        d.line([(lim, yb - 6), (lim, yb + 56)], fill=AMBER + (int(255 * al),), width=4)
    d.text((lim, 668), "4 cm pass limit", font=font(24, False), fill=AMBER + (int(255 * al),), anchor="ma")
    a3 = ease((t - 3.2) / 0.7)
    d.text((X, 790), "3.56 m · no drop · tilt 4.2°", font=font(44), fill=WHITE + (int(255 * a3),))
    d.text((X, 850), "payload shift on the tray · cup holder v2 · simulation, 1 trial", font=font(24, False), fill=GREY + (int(255 * a3),))
    d.text((X, 890), RL_NOTE, font=font(24, False), fill=AMBER + (int(255 * a3),))
    # hand-carry label on the footage
    ah = ease((t - 0.4) / 0.5)
    lab = "HANDS: free tray · pizza + Coke · real contact · Isaac Sim · 2.19 m, no drop · scripted baseline"
    f = font(22, False); wl = f.getlength(lab) + 40
    d.rounded_rectangle([30, H - 90, 30 + wl, H - 44], 23, fill=(9, 14, 28, int(210 * ah)), outline=TEAL + (int(220 * ah),), width=2)
    d.text((50, H - 67), lab, font=f, fill=WHITE + (int(255 * ah),), anchor="lm")
    return Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")


import json as _json, sys as _sys
_sys.path.insert(0, str(V.parent / "pylib"))
import segno
SMOL = [r["loss"] for r in _json.load(open(R / "experiments/codex-20261017T2215-smolvla-training/metrics.json"))]
GVAL = [(r["optimizer_step"], r["validation_loss"]) for r in _json.load(open(R / "experiments/codex-20261017T2320-groot-curve/validation_metrics.json"))]
WANDB = "https://wandb.ai/kaushik-siva88/k1-meal-delivery-20261017"
_qr = segno.make(WANDB, error="m"); _buf = __import__("io").BytesIO(); _qr.save(_buf, kind="png", scale=8, border=2, dark="#090e1c", light="#ffffff")
QR = Image.open(_buf).convert("RGB")


def _ema(xs, a=0.15):
    out, m = [], xs[0]
    for x in xs:
        m = a * x + (1 - a) * m; out.append(m)
    return out


SMOL_EMA = _ema(SMOL)


def chart(d, box, xs, ys, upto, col, ymax, label, xlab, a):
    x0, y0, x1, y1 = box
    d.rectangle(box, outline=(40, 52, 80, int(255 * a)), width=2)
    n = max(2, int(len(xs) * upto))
    pts = [(x0 + (x1 - x0) * (xs[i] - xs[0]) / (xs[-1] - xs[0]), y1 - (y1 - y0) * min(ys[i], ymax) / ymax) for i in range(n)]
    if len(pts) > 1:
        d.line(pts, fill=col + (int(255 * a),), width=5, joint="curve")
        d.ellipse([pts[-1][0] - 7, pts[-1][1] - 7, pts[-1][0] + 7, pts[-1][1] + 7], fill=col + (int(255 * a),))
    d.text((x0, y0 - 44), label, font=font(30), fill=WHITE + (int(255 * a),))
    d.text((x1, y1 + 14), xlab, font=font(22, False), fill=GREY + (int(255 * a),), anchor="ra")


def seg_vla(t, D):
    img = Image.new("RGB", (W, H), NAVY)
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    a = ease(t / 0.5)
    d.text((100, 80), "Vision-language-action models, fine-tuned on the robot's own sensor data", font=font(40), fill=WHITE + (int(255 * a),))
    d.text((100, 140), "Inputs: head camera + 16-d state/memory + instruction  >  5-d bounded subgoal  >  executive can veto", font=font(26, False), fill=GREY + (int(255 * a),))
    up = ease((t - 0.8) / (D * 0.55))
    chart(d, (100, 300, 820, 760), list(range(1, len(SMOL_EMA) + 1)), SMOL_EMA, up, TEAL, 1.6,
          "SmolVLA (450M): training loss", "optimizer updates (200)", a)
    v1 = ease((t - D * 0.55) / 0.6)
    d.text((100, 800), "held-out validation loss  0.99 to 0.26", font=font(34), fill=TEAL + (int(255 * v1),))
    up2 = ease((t - 1.6) / (D * 0.55))
    gs = [s for s, _ in GVAL]; gv = [v for _, v in GVAL]
    chart(d, (920, 300, 1500, 760), gs, gv, up2, (230, 120, 90), 3.0, "NVIDIA GR00T N1.7: validation loss", "optimizer updates (500)", a)
    v2 = ease((t - D * 0.6) / 0.6)
    d.text((920, 800), f"{gv[0]:.2f} to {gv[-1]:.2f}  (38.9% worse; shown as-is)", font=font(30), fill=(230, 120, 90, int(255 * v2)))
    v3 = ease((t - D * 0.7) / 0.6)
    d.text((100, 900), "Closed loop: SmolVLA 2/4 vs our planner 2/4. Not better yet.", font=font(28, False), fill=WHITE + (int(255 * v3),))
    aq = ease((t - 1.0) / 0.6)
    q = QR.resize((260, 260), Image.NEAREST)
    img.paste(q, (1580, 330))
    d.text((1710, 610), "live W&B curves", font=font(24, False), fill=WHITE + (int(255 * aq),), anchor="ma")
    out = Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")
    if aq < 1:
        out = Image.blend(Image.new("RGB", (W, H), NAVY), out, 1.0) if False else out
    return out


MSGS = [("Claude → Codex", "handoff: perception + 61 tests"), ("Codex → Claude", "review: provenance leak found"),
        ("Claude → Codex", "fix + regression test"), ("Codex → Claude", "sensor-only run: DELIVERED")]


def seg_team(t, D):
    img = Image.new("RGB", (W, H), NAVY)
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    a = ease(t / 0.6)
    d.text((W / 2, 150), "Two AI engineers. One day.", font=font(64), fill=WHITE + (int(255 * a),), anchor="mm")
    cards = [(330, "Codex", "simulation · control\nPPO · evaluation · Git", (120, 170, 255)),
             (W - 330 - 520, "Claude", "perception · memory\nsearch · navigation · VLA", AMBER)]
    for i, (x, name, roles, col) in enumerate(cards):
        ac = ease((t - 0.4 - i * 0.3) / 0.6)
        d.rounded_rectangle([x, 300, x + 520, 560], 26, fill=(20, 30, 56, int(240 * ac)), outline=col + (int(255 * ac),), width=4)
        d.text((x + 260, 375), name, font=font(60), fill=col + (int(255 * ac),), anchor="mm")
        d.multiline_text((x + 260, 475), roles, font=font(28, False), fill=WHITE + (int(255 * ac),), anchor="mm", align="center", spacing=10)
    # messages flying between cards
    for j, (who, msg) in enumerate(MSGS):
        t0 = 1.6 + j * (D - 3.0) / len(MSGS)
        p = ease((t - t0) / 1.0)
        if t < t0:
            continue
        right = who.startswith("Claude")
        xs, xe = (W - 330 - 260, 330 + 260) if right else (330 + 260, W - 330 - 260)
        x = xs + (xe - xs) * p
        y = 650 + j * 72
        f = font(26, False); w = f.getlength(msg) + 60
        d.rounded_rectangle([x - w / 2, y - 26, x + w / 2, y + 26], 26, fill=(255, 255, 255, 30), outline=WHITE + (120,), width=2)
        d.text((x, y), msg, font=f, fill=WHITE + (255,), anchor="mm")
    a4 = ease((t - (D - 1.6)) / 0.6)
    d.text((W / 2, 1000), "shared Markdown handoffs · frozen files · hash-checked reviews · every failure kept", font=font(26, False), fill=GREY + (int(255 * a4),), anchor="mm")
    return Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")


def nav_frame(frames, t):
    k = int(np.searchsorted(nav_times, t, side="right") - 1)
    k = min(max(k, 0), len(frames) - 1)
    k2 = min(k + 1, len(frames) - 1)
    f0, f1 = frames[k].astype(float), frames[k2].astype(float)
    t0 = nav_times[k]; t1 = nav_times[k2] if k2 > k else t0 + 0.2
    w = 0.0 if t1 <= t0 else min(max((t - t0) / (t1 - t0), 0), 1)
    return Image.fromarray((f0 * (1 - w) + f1 * w).astype(np.uint8))  # cross-fade between 5 Hz frames


def seg_demo(t, D):
    st = min(t + max(nav_times[-1] - D, 0.0), nav_times[-1])  # show the final D seconds of the run, real time
    img = Image.new("RGB", (W, H), NAVY)
    pw, ph = 930, 698
    ev = nav_frame(nav_eval, st).resize((pw, ph), Image.LANCZOS)
    rc = nav_frame(nav_cam, st).resize((pw, ph), Image.LANCZOS)
    img.paste(ev, (20, 150)); img.paste(rc, (W - 20 - pw, 150))
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    d.text((40, 70), "LIVE SIM  ·  MuJoCo", font=font(40), fill=AMBER + (255,))
    d.text((W - 40, 70), f"t = {st:4.1f} s  (real time)", font=font(34, False), fill=WHITE + (255,), anchor="ra")
    d.text((40, 870), "Evaluator view", font=font(28), fill=GREY + (255,))
    d.text((W - 20 - pw + 20, 870), "What the robot sees", font=font(28), fill=GREY + (255,))
    chips = ["tray carried in its hands", "no markers", "no simulator pose", "camera + gyro + joints only"]
    x = 40
    for c in chips:
        f = font(26, False); w = f.getlength(c) + 44
        d.rounded_rectangle([x, 930, x + w, 980], 25, fill=(255, 255, 255, 26), outline=TEAL + (200,), width=2)
        d.text((x + w / 2, 955), c, font=f, fill=WHITE + (255,), anchor="mm"); x += w + 16
    if st > 22.6:
        ad = ease((st - 22.6) / 0.5)
        d.rounded_rectangle([W / 2 - 360, 470, W / 2 + 360, 560], 18, fill=(9, 14, 28, int(220 * ad)), outline=TEAL + (int(255 * ad),), width=3)
        d.text((W / 2, 515), "DELIVERED  ·  3.8 mm payload shift", font=font(32), fill=TEAL + (int(255 * ad),), anchor="mm")
    d.text((W - 40, 1040), "Camera-guided hand-carry · MuJoCo · first development pass · no PPO/VLA active", font=font(22, False), fill=GREY + (255,), anchor="ra")
    return Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")


def seg_end(t, D):
    img = Image.blend(hero_blur, Image.new("RGB", (W, H), NAVY), 0.7)
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    a = ease(t / 0.6)
    d.text((W / 2, 440), "TABLESIDE", font=font(140), fill=WHITE + (int(255 * a),), anchor="mm")
    d.rectangle([W / 2 - 220, 520, W / 2 + 220, 524], fill=AMBER + (int(255 * a),))
    d.text((W / 2, 600), "github.com/KaushikSiva/k1-meal-delivery", font=font(40, False), fill=WHITE + (int(255 * a),), anchor="mm")
    d.text((W / 2, 680), "Built by Codex + Claude  ·  NVIDIA Isaac  ·  Crusoe  ·  You.com", font=font(28, False), fill=GREY + (int(255 * a),), anchor="mm")
    return Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")


plan = [(seg_why, seg["n1_why"]), (seg_name, seg["n2_name"]), (seg_arch, seg["n3_arch"]), (seg_rl, seg["n4_rl"]), (seg_vla, seg["n4b_vla"]),
        (seg_team, seg["n5_team"]), (seg_demo, seg["n6_demo"]), (seg_end, END)]
XF = 0.35  # cross-fade between segments


def render():
    p = subprocess.Popen(["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(V / "video_only.mp4")],
                         stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    starts = np.cumsum([0] + [d for _, d in plan])
    nframes = int(round(starts[-1] * FPS))
    for fi in range(nframes):
        t = fi / FPS
        i = int(np.searchsorted(starts, t, side="right") - 1); i = min(i, len(plan) - 1)
        fn, D = plan[i]; lt = float(t - starts[i])
        frame = fn(lt, D)
        if i + 1 < len(plan) and D - lt < XF:  # cross-fade into next segment
            nxt = plan[i + 1][0](0.0, plan[i + 1][1])
            frame = Image.blend(frame, nxt, 1 - (D - lt) / XF)
        p.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{nframes}", flush=True)
    p.stdin.close(); p.wait()
    return starts


def music(total, path):
    sr = 48000; tt = np.arange(int(total * sr)) / sr
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]  # Am F C G
    out = np.zeros_like(tt); clen = 4.0
    for ci in range(int(total / clen) + 1):
        ch = chords[ci % 4]; s0 = int(ci * clen * sr); s1 = min(int((ci + 1) * clen * sr) + sr, len(tt))
        if s0 >= len(tt): break
        seg_t = tt[s0:s1] - tt[s0]
        env = np.minimum(1, seg_t / 1.2) * np.exp(-np.maximum(seg_t - clen, 0) * 3)
        for f in ch:
            out[s0:s1] += env * (np.sin(2 * np.pi * f * seg_t) + 0.3 * np.sin(2 * np.pi * f * 2 * seg_t + 0.3)) / len(ch)
    out += 0.15 * np.sin(2 * np.pi * 55 * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * tt / 8))
    out *= np.minimum(1, tt / 2.0) * np.minimum(1, (total - tt) / 2.5)
    out = (out / np.max(np.abs(out)) * 0.9 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(out.tobytes())


def mix(starts, voice_segments, out):
    total = starts[-1]
    music(total, V / "music.wav")
    inputs = ["-i", str(V / "video_only.mp4"), "-i", str(V / "music.wav")]
    filt = ["[1:a]lowpass=f=2400,volume=0.10[m]"]
    labels = ["[m]"]
    for j, n in enumerate(names):
        if n not in voice_segments:
            continue
        inputs += ["-i", str(V / f"{n}_proc.wav")]
        delay = int((starts[j] + (LEAD if n == "n1_why" else 0.15)) * 1000)
        idx = len(labels) + 1
        filt.append(f"[{idx}:a]adelay={delay}|{delay}[v{j}]"); labels.append(f"[v{j}]")
    filt.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95[a]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])


if __name__ == "__main__":
    starts = render()
    mix(starts, names, V / "tableside_demo.mp4")
    mix(starts, names[:-1], V / "tableside_demo_live_narration.mp4")
    json.dump({"segments": {k: v for k, v in seg.items()}, "total_s": float(starts[-1])}, open(V / "timeline.json", "w"), indent=1)
    print("done", float(starts[-1]))
