"""Grid planning, coverage tracking and search viewpoint selection (2D, map frame).

Limitation: a 2D inflated-grid planner is not validated humanoid navigation; foothold and
stepping constraints are the carrying controller's / Codex's responsibility to check.
"""

from .coverage import CoverageMap
from .planner import astar, inflate, path_length, plan_path, simplify_path
from .search import NavGoal, Navigator

__all__ = ["CoverageMap", "NavGoal", "Navigator", "astar", "inflate", "path_length", "plan_path", "simplify_path"]
