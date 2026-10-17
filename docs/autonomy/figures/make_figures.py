"""Render presentation figures (v2) from the SYNTHETIC CPU fixture (tests/autonomy/fake_world.py).

These illustrate software behavior of the autonomy executive. They are NOT simulator or robot
results; every figure is stamped accordingly. Run from repo root:
    python3 docs/autonomy/figures/make_figures.py
v1 PNGs (*_v1_historical.png) were made before the live depth layer became the executive default;
the v1 F2 "prior map only" panel was valid at that time but this generator no longer reproduces v1.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests/autonomy")]
from autonomy.contracts import Pose2D  # noqa: E402
from fake_world import Box, restaurant, run  # noqa: E402
from test_nominal import make  # noqa: E402

OUT = Path(__file__).resolve().parent
STAMP = "SYNTHETIC SOFTWARE FIXTURE — not simulator or robot evidence"
COLORS = {"search": "#4C78A8", "verify": "#F58518", "approach": "#54A24B", "reacquire": "#B279A2",
          "final_approach": "#E45756", "settle": "#E45756", "relocalize": "#9D755D", "sensor_wait": "#BAB0AC"}


def draw_room(ax, room, title):
    x0, y0, x1, y1 = room.bounds
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=2, color="k"))
    for b in room.boxes:
        color = {"table": "#C9A66B", "wall": "#555", "counter": "#888", "cart": "#D62728", "person": "#9467BD"}.get(b.label, "#aaa")
        ax.add_patch(Rectangle(b.lo[:2], *(b.hi[:2] - b.lo[:2]), color=color, alpha=0.9 if b.in_map else 0.6,
                               hatch=None if b.in_map else "//"))
        name = f"table {b.attributes['table_number']}" if "table_number" in b.attributes else b.label
        if not b.in_map:
            name += "\n(not on map)"
        ax.text(*b.center[:2], name, ha="center", va="center", fontsize=8)
    ax.set_xlim(x0 - 0.2, x1 + 0.2); ax.set_ylim(y0 - 0.2, y1 + 0.2); ax.set_aspect("equal")
    ax.set_title(title, fontsize=11); ax.set_xticks([]); ax.set_yticks([])


def traced_run(room, ex, extra_hook=None):
    trace = []

    def hooks(t, room, ex):
        trace.append((room.true_pose.x, room.true_pose.y, ex.state.value))
        if extra_hook:
            extra_hook(t, room, ex)

    run(ex, room, hooks=hooks)
    trace.append((room.true_pose.x, room.true_pose.y, ex.state.value))
    return trace


def plot_trace(ax, trace):
    for (xa, ya, s), (xb, yb, _) in zip(trace, trace[1:]):
        ax.plot([xa, xb], [ya, yb], color=COLORS.get(s, "k"), lw=2.5)
    ax.plot(*trace[0][:2], "ko", ms=8); ax.plot(*trace[-1][:2], "k*", ms=14)


def fig_search_verify_deliver():
    room = restaurant()
    ex = make(room)
    trace = traced_run(room, ex)
    fig, ax = plt.subplots(figsize=(8, 6.6))
    draw_room(ax, room, '"Deliver the pizza and drink to table 3" — search → read numbers → deliver')
    plot_trace(ax, trace)
    used = [s for s in COLORS if any(t[2] == s for t in trace)]
    for s in used:
        ax.plot([], [], color=COLORS[s], lw=3, label=s)
    ax.legend(loc="lower right", fontsize=8)
    ax.text(0.02, 0.02, f"outcome: {ex.outcome.value} · t={room.t:.0f}s\n{STAMP}", transform=ax.transAxes, fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "fig1_search_verify_deliver_v2.png", dpi=110); plt.close(fig)


def fig_depth_layer():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    for ax, use in zip(axes, (False, True)):
        room = restaurant(start=Pose2D(2.0, 6.0, np.deg2rad(-20)))
        room.boxes.append(Box(60, "cart", np.array([3.6, 4.5, 0.0]), np.array([4.6, 5.5, 0.9]), in_map=False))
        # Ablation is the executive's own switch: obstacle_layer=False -> prior map + contact feedback only.
        ex = make(room, ocr_range=10.0, obstacle_layer=use)
        trace = traced_run(room, ex)
        draw_room(ax, room, "with live depth obstacle layer" if use else "prior map only")
        if use:
            occ = ex.obstacles.occupied  # the layer the executive actually planned with
            g = room.grid()
            ax.imshow(np.ma.masked_where(~occ, occ), origin="lower", cmap="autumn", alpha=0.45,
                      extent=(g.origin[0], g.origin[0] + occ.shape[1] * g.resolution,
                              g.origin[1], g.origin[1] + occ.shape[0] * g.resolution))
        plot_trace(ax, trace)
        bumps = sum("blocked" in e.msg for e in ex.events)
        ax.text(0.02, 0.02, f"contacts (BLOCKED): {bumps} · outcome: {ex.outcome.value}\n{STAMP}",
                transform=ax.transAxes, fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "fig2_depth_obstacle_layer_v2.png", dpi=110); plt.close(fig)


def write_provenance():
    import hashlib
    srcs = ["autonomy/executive.py", "autonomy/grounding.py", "memory/scene_memory.py", "navigation/search.py",
            "navigation/depth_obstacles.py", "navigation/planner.py", "perception/detectors.py",
            "tests/autonomy/fake_world.py", "tests/autonomy/test_nominal.py", "docs/autonomy/figures/make_figures.py"]
    lines = ["# v2 figures: source hashes at generation time (fixture = synthetic software evidence)"]
    lines += [f"{hashlib.sha256((ROOT / s).read_bytes()).hexdigest()}  {s}" for s in srcs]
    lines += [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  docs/autonomy/figures/{p.name}"
              for p in sorted(OUT.glob("*_v2.png"))]
    (OUT / "FIGURES_V2_PROVENANCE.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    fig_search_verify_deliver()
    fig_depth_layer()
    write_provenance()
    print("wrote", sorted(p.name for p in OUT.glob("*_v2.png")))
