"""Grid path planning (8-connected A*) on OccupancyGrid."""

from __future__ import annotations

import heapq

import numpy as np

from autonomy.contracts import OccupancyGrid

SQRT2 = float(np.sqrt(2))
_NEIGHBORS = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
              (-1, -1, SQRT2), (-1, 1, SQRT2), (1, -1, SQRT2), (1, 1, SQRT2)]


def inflate(grid: OccupancyGrid, radius_m: float, unknown_is_obstacle: bool = False) -> np.ndarray:
    """Boolean (H,W) traversability after inflating obstacles by the robot radius."""
    blocked = grid.data == OccupancyGrid.OCCUPIED
    if unknown_is_obstacle:
        blocked |= grid.data == OccupancyGrid.UNKNOWN
    r = int(np.ceil(radius_m / grid.resolution))
    if r <= 0:
        return ~blocked
    out = blocked.copy()
    H, W = blocked.shape
    rr, cc = np.nonzero(blocked)
    for dr in range(-r, r + 1):
        for dc in range(-r, r + 1):
            if dr * dr + dc * dc > r * r:
                continue
            r2, c2 = rr + dr, cc + dc
            ok = (r2 >= 0) & (r2 < H) & (c2 >= 0) & (c2 < W)
            out[r2[ok], c2[ok]] = True
    return ~out


def astar(free: np.ndarray, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
    H, W = free.shape
    if not (0 <= goal[0] < H and 0 <= goal[1] < W) or not free[goal]:
        return None
    if start == goal:
        return [start]

    def h(rc):
        dr, dc = abs(rc[0] - goal[0]), abs(rc[1] - goal[1])
        return (dr + dc) + (SQRT2 - 2) * min(dr, dc)

    g = {start: 0.0}
    parent: dict = {start: None}
    pq = [(h(start), 0.0, start)]
    closed = set()
    while pq:
        _, gc, cur = heapq.heappop(pq)
        if cur in closed:
            continue
        if cur == goal:
            path = [cur]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return path[::-1]
        closed.add(cur)
        for dr, dc, cost in _NEIGHBORS:
            nb = (cur[0] + dr, cur[1] + dc)
            if not (0 <= nb[0] < H and 0 <= nb[1] < W) or not free[nb]:
                continue
            if dr and dc and not (free[cur[0] + dr, cur[1]] and free[cur[0], cur[1] + dc]):
                continue  # no corner cutting
            ng = gc + cost
            if ng < g.get(nb, np.inf):
                g[nb] = ng
                parent[nb] = cur
                heapq.heappush(pq, (ng + h(nb), ng, nb))
    return None


def nearest_free(free: np.ndarray, rc: tuple[int, int], max_r: int = 20) -> tuple[int, int] | None:
    H, W = free.shape
    if 0 <= rc[0] < H and 0 <= rc[1] < W and free[rc]:
        return rc
    for r in range(1, max_r + 1):
        best, best_d = None, np.inf
        for dr in range(-r, r + 1):
            for dc in (-r, r) if abs(dr) != r else range(-r, r + 1):
                q = (rc[0] + dr, rc[1] + dc)
                if 0 <= q[0] < H and 0 <= q[1] < W and free[q]:
                    d = dr * dr + dc * dc
                    if d < best_d:
                        best, best_d = q, d
        if best is not None:
            return best
    return None


def simplify_path(free: np.ndarray, cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Greedy line-of-sight shortcutting."""
    if len(cells) <= 2:
        return cells
    out = [cells[0]]
    i = 0
    while i < len(cells) - 1:
        j = len(cells) - 1
        while j > i + 1 and not _line_free(free, cells[i], cells[j]):
            j -= 1
        out.append(cells[j])
        i = j
    return out


def _line_free(free: np.ndarray, a, b) -> bool:
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) * 2 + 1
    rs = np.round(np.linspace(a[0], b[0], n)).astype(int)
    cs = np.round(np.linspace(a[1], b[1], n)).astype(int)
    return bool(free[rs, cs].all())


def plan_path(
    grid: OccupancyGrid, start_xy, goal_xy, robot_radius: float = 0.25, free: np.ndarray | None = None
) -> list[tuple[float, float]] | None:
    """World-frame waypoints from start to goal (goal snapped to nearest free cell)."""
    if free is None:
        free = inflate(grid, robot_radius)
    s = nearest_free(free, grid.world_to_cell(start_xy))
    g = nearest_free(free, grid.world_to_cell(goal_xy))
    if s is None or g is None:
        return None
    cells = astar(free, s, g)
    if cells is None:
        return None
    pts = [tuple(map(float, grid.cell_to_world(c))) for c in simplify_path(free, cells)]
    # Start at the true start (not the snapped cell center) so re-planning every tick doesn't
    # pull the robot back to a cell center; end at the exact goal when its cell is free.
    pts[0] = (float(start_xy[0]), float(start_xy[1]))
    gr = grid.world_to_cell(goal_xy)
    if grid.in_bounds(gr) and free[gr]:
        pts[-1] = (float(goal_xy[0]), float(goal_xy[1]))
    return pts


def path_length(path: list[tuple[float, float]]) -> float:
    if not path or len(path) < 2:
        return 0.0
    p = np.asarray(path)
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())
