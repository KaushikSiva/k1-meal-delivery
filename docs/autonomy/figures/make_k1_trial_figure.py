"""F6: top-down trajectories + command traces of Claude's K1 camera-driven MuJoCo diagnostic trials.
Reads the committed experiment data only (no re-simulation). Run: python3 <this file>.
Caption on-image: privileged sim pose, unloaded, restricted placards; A/B deadband compensation on, C off."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "experiments/claude-20261017T2008Z-k1-camera-autonomy-diagnostic"
OUT = Path(__file__).resolve().parent
TABLES = {"3": ((4.0, 0.0), (0.4, 0.5)), "1": ((2.6, 2.2), (0.4, 0.5))}  # from the trial script's scene
COLORS = {"search": "#4C78A8", "verify": "#F58518", "approach": "#54A24B", "reacquire": "#B279A2",
          "final_approach": "#E45756", "settle": "#E45756", "done": "#333333", "sensor_wait": "#BAB0AC",
          "relocalize": "#9D755D", "failed": "#000000"}
TRIALS = {"A": "A: facing tables, comp. 0.3 → delivered", "B": "B: facing away, comp. 0.3 → search, delivered",
          "C": "C: facing tables, no comp. → stalled (timeout)"}
STYLE = {"A": "-", "B": "-", "C": "--"}


def load(t):
    d = np.genfromtxt(RUN / f"trial-{t}" / "trajectory.csv", delimiter=",", names=True)
    st = [ln.split() for ln in (RUN / f"trial-{t}" / "states.txt").read_text().splitlines()]
    st_t = np.array([float(a) for a, _ in st])
    states = [b for _, b in st]
    idx = np.clip(np.searchsorted(st_t, d["t"], side="right") - 1, 0, len(states) - 1)
    return d, [states[i] for i in idx]


def main():
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1.15, 1]})
    for num, ((x, y), (hx, hy)) in TABLES.items():
        ax.add_patch(Rectangle((x - hx, y - hy), 2 * hx, 2 * hy, color="#C9A66B"))
        ax.text(x, y, f"table {num}", ha="center", va="center", fontsize=9)
    seen = set()
    for t in "ABC":
        d, states = load(t)
        x, y = d["x"], d["y"]
        for i in range(0, len(x) - 1, 2):
            c = COLORS.get(states[i], "k")
            ax.plot(x[i:i + 3], y[i:i + 3], STYLE[t], color=c, lw=3 if t != "C" else 1.5, alpha=0.9 if t != "C" else 0.6,
                    label=states[i] if states[i] not in seen else None)
            seen.add(states[i])
        ax.plot(x[-1], y[-1], "*" if t != "C" else "x", color="k", ms=13)
        ax.annotate(t, (x[-1], y[-1]), textcoords="offset points", xytext=(6, 6 if t != "B" else -14), fontsize=11, weight="bold")
    ax.plot(0, 0, "ko", ms=7)
    ax.annotate("start (0,0)", (0, 0), textcoords="offset points", xytext=(-10, -16), fontsize=9)
    ax.set_aspect("equal"); ax.set_xlim(-0.6, 4.8); ax.set_ylim(-1.2, 3.0)
    ax.set_title("K1 (official k1_walk) driven by its head camera — top-down", fontsize=11)
    ax.legend(loc="upper left", fontsize=8, title="executive state", title_fontsize=8)
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    for t, c in (("A", "#54A24B"), ("C", "#E45756")):
        d, _ = load(t)
        ax2.plot(d["t"], d["cmd_vx"], color=c, lw=1.6, label=TRIALS[t])
    ax2.axhspan(0, 0.2, color="#999", alpha=0.18)
    ax2.text(60, 0.1, "≈ deadband of unloaded k1_walk\n(Codex sweep: 0.2 m/s cmd → ~0.03 m/s)", fontsize=8, ha="center")
    ax2.set_xlim(0, 120); ax2.set_ylim(-0.02, 0.42)
    ax2.set_xlabel("sim time (s)"); ax2.set_ylabel("commanded forward speed (m/s)")
    ax2.set_title("Why C stalled: final-approach commands sit in the deadband", fontsize=11)
    ax2.legend(fontsize=8, loc="upper right")
    fig.text(0.01, 0.01, "MuJoCo PRIVILEGED diagnostic: sim pose, unloaded, restricted placards, n=1 per condition; "
             "A/B use opt-in deadband compensation (default off). Data: " + str(RUN.relative_to(ROOT)), fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "fig6_k1_trials_topdown.png", dpi=110)
    print("wrote fig6_k1_trials_topdown.png")


if __name__ == "__main__":
    main()
