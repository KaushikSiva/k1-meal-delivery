"""Delivery task executive: a CPU-only state machine that turns observations into bounded,
expiring AutonomyCommands for navigation/carrying control.

    SEARCH --(unique confirmed dest)--> APPROACH --(near)--> FINAL_APPROACH --> SETTLE --> DONE
      |  ^                                   |                                   |
      |  +---------(dest lost / moved)-------+---- REACQUIRE (scan toward memory)-+
      +--(possible dest, attribute unread)--> VERIFY (go closer, hold, read) --+
    any moving state --(pose lost / too uncertain)--> RELOCALIZE --(recovered)--> previous
    any state --(camera/pose missing)--> SENSOR_WAIT (hold) --(timeout)--> FAILED
    BLOCKED feedback -> mark obstacle, replan; no path after retries -> FAILED(no_path)

Every terminal path ends with a STOP command and an explicit Outcome. The executive never
invents state: if it can't confirm, it searches, holds, or reports.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from memory import SceneMemory
from navigation import Navigator
from navigation.depth_obstacles import DepthObstacleLayer
from perception.detectors import Detector
from .contracts import (
    AutonomyCommand,
    CommandKind,
    ControlFeedback,
    DeliveryTask,
    FeedbackStatus,
    LocalizationStatus,
    Observation,
    OccupancyGrid,
    Outcome,
    Pose2D,
    PrivilegedInputError,
    Provenance,
    Region,
)
from .grounding import Candidate, Verdict, match_candidates


class State(str, Enum):
    SEARCH = "search"
    VERIFY = "verify"
    APPROACH = "approach"
    REACQUIRE = "reacquire"
    FINAL_APPROACH = "final_approach"
    SETTLE = "settle"
    RELOCALIZE = "relocalize"
    SENSOR_WAIT = "sensor_wait"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ExecutiveConfig:
    # speeds (m/s) — upper bounds; carrying control may go slower
    search_speed: float = 0.35
    approach_speed: float = 0.35
    final_speed: float = 0.15
    degraded_speed: float = 0.15
    command_ttl_s: float = 1.0
    # destination
    standoff_m: float = 0.7  # stop this far from the destination's centroid
    verify_range_m: float = 1.2  # get this close to read attributes (e.g. table number)
    verify_hold_s: float = 1.5
    max_verify_attempts: int = 2
    final_approach_dist_m: float = 1.0
    replan_if_target_moved_m: float = 0.3
    # memory
    reacquire_after_s: float = 4.0  # target unseen this long while close -> look for it
    stale_memory_s: float = 60.0  # older target memory is a hypothesis: approach slowly, must re-see
    confirm_window_s: float = 3.0  # arrival requires destination seen within this window
    # arrival
    stop_pos_tol_m: float = 0.2
    stop_yaw_tol: float = 0.35
    stop_speed_eps: float = 0.03
    settle_s: float = 1.5
    # localization
    degraded_sigma_m: float = 0.15
    lost_sigma_m: float = 0.4
    relocalize_budget_s: float = 20.0
    relocalize_scan_rad: float = 0.8
    # sensors
    sensor_stale_s: float = 0.5
    pose_stale_s: float = 0.5
    future_tol_s: float = 0.05  # timestamps later than the snapshot by more than this are invalid
    sensor_timeout_s: float = 5.0
    # search
    max_explore_goals: int = 30
    max_blocked: int = 6
    max_replans: int = 60  # proactive replans (observed obstacle on the active path)
    blocked_mark_radius_m: float = 0.4
    time_limit_s: float | None = None  # defaults to task.time_limit_s


@dataclass
class ExecutiveEvent:
    t: float
    state: str
    msg: str


@dataclass
class _Ctx:
    target_key: str | None = None
    target_xy: np.ndarray | None = None
    goal: Pose2D | None = None
    verify_key: str | None = None
    verify_attempts: dict[str, int] = field(default_factory=dict)
    unverifiable: set[str] = field(default_factory=set)
    explore_goals: int = 0
    blocked_count: int = 0
    state_since: float = 0.0
    resume_state: "State | None" = None
    sensor_lost_since: float | None = None
    reloc_since: float | None = None
    settle_since: float | None = None
    replans: int = 0


class DeliveryExecutive:
    def __init__(
        self,
        task: DeliveryTask,
        grid: OccupancyGrid,
        detector: Detector,
        regions: list[Region] = (),
        config: ExecutiveConfig | None = None,
        deployable: bool = False,
        robot_radius: float = 0.3,
        memory: SceneMemory | None = None,
        obstacle_layer: DepthObstacleLayer | bool = True,
    ):
        self.task = task
        self.cfg = config or ExecutiveConfig()
        self.deployable = deployable
        if deployable and detector.provenance == Provenance.SIM_PRIVILEGED:
            raise PrivilegedInputError(f"{type(detector).__name__} is simulator-privileged")
        self.detector = detector
        self.regions = list(regions)
        self.memory = memory or SceneMemory()
        self.nav = Navigator(grid, robot_radius=robot_radius)
        # Live depth obstacles (ESTIMATED from depth + estimated pose). False disables (ablation).
        self.obstacles = DepthObstacleLayer(grid) if obstacle_layer is True else (obstacle_layer or None)
        self.state = State.SEARCH
        self.outcome: Outcome | None = None
        self.ctx = _Ctx(state_since=task.issued_at)
        self.active: AutonomyCommand | None = None
        self.events: list[ExecutiveEvent] = []
        self.now = task.issued_at
        self.last_pose: Pose2D | None = None
        self.last_obs_t: float | None = None
        self._degraded = False
        self._resumed = False
        self._planned_map_version: dict[float, int] = {}

    # ================================================================== main entry
    def step(self, obs: Observation | None, feedback: ControlFeedback | None = None,
             now: float | None = None) -> AutonomyCommand:
        """`now` is an independent clock (robot monotonic time). Adapters should call step every
        tick even without a snapshot (obs=None or an empty timestamped Observation) so sensor
        timeouts advance."""
        self._prev_obs_t = self.last_obs_t
        if now is not None:
            self.now = max(self.now, now)
        if obs is not None and np.isfinite(obs.timestamp):
            self.now = max(self.now, obs.timestamp)
        if self.state in (State.DONE, State.FAILED):
            return self._stop(self.outcome.value if self.outcome else "terminal")

        limit = self.cfg.time_limit_s or self.task.time_limit_s
        if self.now - self.task.issued_at > limit:
            return self._fail(Outcome.TIMEOUT, "time limit exceeded")

        # ---- sensing / perception -----------------------------------------------
        if obs is not None and self.deployable:
            obs.assert_deployable()
        sensors_ok = self._sensors_ok(obs)
        if sensors_ok:
            dets = self.detector.detect(obs)
            if self.deployable:
                dets = [d for d in dets if d.provenance != Provenance.SIM_PRIVILEGED]
            self.memory.update(obs, dets)
            if obs.pose.status == LocalizationStatus.OK:
                self.nav.coverage.update(obs)
                if self.obstacles is not None and self.obstacles.update(obs):
                    self.nav.set_dynamic_obstacles(self.obstacles.occupied)
            self.last_pose = obs.pose.pose
            self.last_obs_t = obs.timestamp

        # ---- control feedback ---------------------------------------------------
        if feedback is not None and self.active is not None and feedback.command_issued_at == self.active.issued_at:
            if feedback.status == FeedbackStatus.FAILED:
                return self._fail(Outcome.CONTROL_FAILURE, f"control failed: {feedback.message}")
            if feedback.status == FeedbackStatus.BLOCKED:
                cmd = self._on_blocked(feedback)
                if cmd is not None:
                    return cmd

        # ---- interrupts: sensors, then localization ----------------------------
        if not sensors_ok:
            return self._sensor_wait()
        if self.state == State.SENSOR_WAIT:
            self._log("sensors restored")
            self._goto(self.ctx.resume_state or State.SEARCH)
            self._resumed = True
            self.ctx.sensor_lost_since = None
        loc = self._localization(obs)
        if loc == LocalizationStatus.LOST:
            return self._relocalize(obs)
        if self.state == State.RELOCALIZE:
            self._log(f"relocalized (sigma={obs.pose.xy_sigma:.2f} m)")
            self._goto(self.ctx.resume_state or State.SEARCH)
            self._resumed = True
            self.ctx.reloc_since = None
        degraded = loc == LocalizationStatus.DEGRADED
        self._degraded = degraded
        if self._resumed:
            # The active command is the interrupt's HOLD/SCAN: re-enter the resumed state so it
            # issues its own command again (never keep refreshing the interrupt's HOLD).
            self._resumed = False
            cmd = self._reenter(obs, degraded)
            if cmd is not None:
                return cmd
        cmd = self._revalidate_path(obs)
        if cmd is not None:
            return cmd

        # ---- task states --------------------------------------------------------
        reached = (feedback is not None and self.active is not None and
                   feedback.command_issued_at == self.active.issued_at and feedback.status == FeedbackStatus.REACHED) \
            or self._goal_reached_by_pose(obs)
        handler = {
            State.SEARCH: self._search,
            State.VERIFY: self._verify,
            State.APPROACH: self._approach,
            State.REACQUIRE: self._reacquire,
            State.FINAL_APPROACH: self._final_approach,
            State.SETTLE: self._settle,
        }[self.state]
        return handler(obs, reached, degraded)

    # ================================================================== states
    def _search(self, obs: Observation, reached: bool, degraded: bool) -> AutonomyCommand:
        cands = [c for c in match_candidates(self.task.destination, self.memory) if c.verdict != Verdict.REJECTED]
        confirmed = [c for c in cands if c.verdict == Verdict.CONFIRMED]
        possible = [c for c in cands if c.verdict == Verdict.POSSIBLE and c.obj.key not in self.ctx.unverifiable]

        if len(confirmed) == 1:
            return self._start_approach(obs, confirmed[0])
        if len(confirmed) > 1:
            # Several objects satisfy everything the instruction said: don't guess.
            return self._fail(Outcome.AMBIGUOUS_DESTINATION,
                              f"{len(confirmed)} candidates match {self.task.destination}: "
                              + ", ".join(c.obj.key for c in confirmed))
        if possible:
            pose = obs.pose.pose
            c = min(possible, key=lambda c: np.linalg.norm(c.obj.position[:2] - pose.xy()))
            return self._start_verify(obs, c)

        # Nothing known: explore. Keep the current explore command until reached.
        if self.active is not None and self.active.kind == CommandKind.NAVIGATE and self.active.state == State.SEARCH.value \
                and not reached:
            return self._refresh(self.active)
        if reached:
            self.nav.mark_visited(obs.pose.pose)
        if self.ctx.explore_goals >= self.cfg.max_explore_goals:
            return self._fail(Outcome.DESTINATION_NOT_FOUND, "exploration budget exhausted")
        goal = self.nav.explore(obs.pose.pose, self.regions, self.task.destination.region_hint)
        if goal is None:
            return self._fail(Outcome.DESTINATION_NOT_FOUND, "no reachable unexplored viewpoints left")
        self.ctx.explore_goals += 1
        speed = self.cfg.degraded_speed if degraded else self.cfg.search_speed
        return self._issue(CommandKind.NAVIGATE, goal.pose, goal.path, speed, "explore for destination")

    def _start_verify(self, obs: Observation, c: Candidate) -> AutonomyCommand:
        key = c.obj.key
        n = self.ctx.verify_attempts.get(key, 0)
        if n >= self.cfg.max_verify_attempts:
            self.ctx.unverifiable.add(key)
            self._log(f"could not read {c.missing} on {key}; skipping it")
            return self._search(obs, False, False)
        self.ctx.verify_attempts[key] = n + 1
        goal = self.nav.approach(c.obj.position, obs.pose.pose, self.cfg.verify_range_m)
        if goal is None:
            self.ctx.unverifiable.add(key)
            self._log(f"no path to view {key}")
            return self._search(obs, False, False)
        self.ctx.verify_key = key
        self._goto(State.VERIFY)
        return self._issue(CommandKind.NAVIGATE, goal.pose, goal.path, self.cfg.approach_speed,
                           f"go read {','.join(c.missing)} on {key}")

    def _verify(self, obs: Observation, reached: bool, degraded: bool) -> AutonomyCommand:
        key = self.ctx.verify_key
        cand = next((c for c in match_candidates(self.task.destination, self.memory) if c.obj.key == key), None)
        if cand is None or cand.verdict != Verdict.POSSIBLE:
            # confirmed, rejected or forgotten -> let SEARCH re-evaluate everything
            self._log(f"verify {key}: {cand.verdict.value if cand else 'gone'}")
            self._goto(State.SEARCH)
            return self._search(obs, False, degraded)
        if self.active.kind == CommandKind.NAVIGATE and not reached:
            return self._refresh(self.active)
        if self.active.kind == CommandKind.NAVIGATE and reached:
            return self._issue(CommandKind.HOLD, None, None, 0.0, f"look at {key}",
                               ttl=self.cfg.verify_hold_s + self.cfg.command_ttl_s)
        if self.now - self.active.issued_at < self.cfg.verify_hold_s:
            return self._refresh(self.active)
        self._goto(State.SEARCH)  # held long enough without reading: try again / elsewhere
        return self._search(obs, False, degraded)

    def _start_approach(self, obs: Observation, c: Candidate) -> AutonomyCommand:
        goal = self.nav.approach(c.obj.position, obs.pose.pose, self.cfg.standoff_m)
        if goal is None:
            return self._fail(Outcome.NO_PATH, f"no reachable standoff pose at {c.obj.key}")
        self.ctx.target_key, self.ctx.target_xy, self.ctx.goal = c.obj.key, c.obj.position[:2].copy(), goal.pose
        self._goto(State.APPROACH)
        stale = c.obj.age(self.now) > self.cfg.stale_memory_s
        speed = self.cfg.degraded_speed if stale else self.cfg.approach_speed
        return self._issue(CommandKind.NAVIGATE, goal.pose, goal.path, speed,
                           f"approach {c.obj.key}" + (" (stale memory, re-observe)" if stale else ""))

    def _target(self):
        return self.memory.get(self.ctx.target_key) if self.ctx.target_key else None

    def _approach(self, obs: Observation, reached: bool, degraded: bool) -> AutonomyCommand:
        confirmed = [c for c in match_candidates(self.task.destination, self.memory) if c.verdict == Verdict.CONFIRMED]
        if len(confirmed) > 1:
            return self._fail(Outcome.AMBIGUOUS_DESTINATION,
                              f"another candidate also matches while approaching: "
                              + ", ".join(c.obj.key for c in confirmed))
        t = self._target()
        if t is None or t.confidence < 0.25:
            self._log("destination lost from memory (moved or false positive); searching again")
            self._goto(State.SEARCH)
            return self._search(obs, False, degraded)
        pose = obs.pose.pose
        if t.age(self.now) > self.cfg.reacquire_after_s and np.linalg.norm(t.position[:2] - pose.xy()) < 3.0:
            self._goto(State.REACQUIRE)
            return self._reacquire(obs, False, degraded)
        if np.linalg.norm(t.position[:2] - self.ctx.target_xy) > self.cfg.replan_if_target_moved_m:
            self._log(f"destination estimate moved {np.linalg.norm(t.position[:2] - self.ctx.target_xy):.2f} m; replanning")
            return self._start_approach(obs, Candidate(t, Verdict.CONFIRMED, t.confidence))
        dist_goal = np.linalg.norm(self.ctx.goal.xy() - pose.xy())
        if (reached or dist_goal < self.cfg.final_approach_dist_m) and not degraded:
            if t.age(self.now) <= self.cfg.confirm_window_s:
                self._goto(State.FINAL_APPROACH)
                return self._issue(CommandKind.FINAL_APPROACH, self.ctx.goal, None, self.cfg.final_speed,
                                   f"decelerate and stop at {t.key}")
            self._goto(State.REACQUIRE)
            return self._reacquire(obs, False, degraded)
        if reached:  # degraded localization: hold until it improves rather than committing
            return self._issue(CommandKind.HOLD, None, None, 0.0, "localization degraded near destination")
        if degraded and self.active.max_speed > self.cfg.degraded_speed:
            return self._issue(CommandKind.NAVIGATE, self.ctx.goal, self.active.path, self.cfg.degraded_speed,
                               "localization degraded: slow down")
        return self._refresh(self.active)

    def _reacquire(self, obs: Observation, reached: bool, degraded: bool) -> AutonomyCommand:
        t = self._target()
        if t is None or t.confidence < 0.25:
            self._log("reacquire failed: destination not where remembered")
            self._goto(State.SEARCH)
            return self._search(obs, False, degraded)
        if t.age(self.now) <= 0.5:  # seen again
            self._log(f"reacquired {t.key}")
            self._goto(State.APPROACH)
            return self._approach(obs, False, degraded)
        if self.active.kind == CommandKind.SCAN and self.active.state == State.REACQUIRE.value and not reached:
            return self._refresh(self.active)
        pose = obs.pose.pose
        bearing = np.arctan2(t.position[1] - pose.y, t.position[0] - pose.x)
        dyaw = float(np.angle(np.exp(1j * (bearing - pose.yaw))))
        if abs(dyaw) < 0.15 and reached:
            # Facing it, still not seen, negative evidence is accumulating; hold one beat.
            return self._issue(CommandKind.HOLD, None, None, 0.0, f"looking for {t.key}")
        return self._issue(CommandKind.SCAN, None, None, 0.0, f"turn toward remembered {t.key}", scan_yaw=dyaw)

    def _final_approach(self, obs: Observation, reached: bool, degraded: bool) -> AutonomyCommand:
        if degraded:
            return self._issue(CommandKind.HOLD, None, None, 0.0, "localization degraded during final approach")
        if reached:
            self._goto(State.SETTLE)
            self.ctx.settle_since = None
            return self._settle(obs, False, degraded)
        return self._refresh(self.active)

    def _settle(self, obs: Observation, reached: bool, degraded: bool) -> AutonomyCommand:
        pose = obs.pose.pose
        goal = self.ctx.goal
        t = self._target()
        pos_err = float(np.linalg.norm(goal.xy() - pose.xy()))
        yaw_err = abs(float(np.angle(np.exp(1j * (goal.yaw - pose.yaw)))))
        speed = float(np.linalg.norm(obs.base_twist[:2])) + 0.3 * abs(float(obs.base_twist[2])) \
            if obs.base_twist is not None else np.inf
        ok = pos_err <= self.cfg.stop_pos_tol_m and yaw_err <= self.cfg.stop_yaw_tol and speed <= self.cfg.stop_speed_eps \
            and not degraded
        if pos_err > 2 * self.cfg.stop_pos_tol_m:
            self._log(f"drifted {pos_err:.2f} m from stop pose; re-approaching")
            self._goto(State.APPROACH)
            return self._issue(CommandKind.NAVIGATE, goal, None, self.cfg.final_speed, "re-approach after drift")
        if not ok:
            self.ctx.settle_since = None
            return self._hold_or_refresh("settling: waiting for stable stop")
        if self.ctx.settle_since is None:
            self.ctx.settle_since = self.now
        if self.now - self.ctx.settle_since < self.cfg.settle_s:
            return self._hold_or_refresh("settling: stable, timing dwell")
        if t is None or t.age(self.now) > self.cfg.confirm_window_s:
            # Stable, but can't currently see the destination: don't declare success blind.
            self._goto(State.REACQUIRE)
            return self._reacquire(obs, False, degraded)
        self.outcome = Outcome.DELIVERED
        self._goto(State.DONE)
        self._log(f"delivered at {t.key}: pos_err={pos_err:.3f} m yaw_err={yaw_err:.3f} rad speed={speed:.3f}")
        return self._stop("delivered")

    # ================================================================== interrupts
    def _sensors_ok(self, obs: Observation | None) -> bool:
        if obs is None or obs.camera is None or obs.pose is None:
            return False
        cam, pe, c = obs.camera, obs.pose, self.cfg
        if cam.depth is None and cam.rgb is None:
            return False
        ts = (obs.timestamp, cam.timestamp, pe.timestamp)
        if not all(np.isfinite(t) for t in ts):
            return False
        if self._prev_obs_t is not None and obs.timestamp <= self._prev_obs_t:
            return False  # non-monotonic or repeated snapshot
        if cam.timestamp > obs.timestamp + c.future_tol_s or pe.timestamp > obs.timestamp + c.future_tol_s:
            return False  # from the future: clock fault
        if self.now - cam.timestamp > c.sensor_stale_s or self.now - pe.timestamp > c.pose_stale_s:
            return False
        p = pe.pose
        if not (np.isfinite([p.x, p.y, p.yaw]).all() and np.isfinite(pe.cov).all()):
            return False
        if obs.base_twist is not None and not np.isfinite(obs.base_twist).all():
            return False
        return True

    def _sensor_wait(self) -> AutonomyCommand:
        if self.state != State.SENSOR_WAIT:
            self.ctx.resume_state = self.state if self.state != State.RELOCALIZE else self.ctx.resume_state
            self.ctx.sensor_lost_since = self.now
            self._goto(State.SENSOR_WAIT)
            self._log("camera/pose missing or stale: holding")
            return self._issue(CommandKind.HOLD, None, None, 0.0, "sensors unavailable")
        if self.now - self.ctx.sensor_lost_since > self.cfg.sensor_timeout_s:
            return self._fail(Outcome.SENSOR_TIMEOUT, "no valid camera/pose observations")
        return self._refresh(self.active)

    def _localization(self, obs: Observation) -> LocalizationStatus:
        s = obs.pose.status
        sig = obs.pose.xy_sigma
        if s == LocalizationStatus.LOST or sig > self.cfg.lost_sigma_m:
            return LocalizationStatus.LOST
        if s == LocalizationStatus.DEGRADED or sig > self.cfg.degraded_sigma_m:
            return LocalizationStatus.DEGRADED
        return LocalizationStatus.OK

    def _relocalize(self, obs: Observation) -> AutonomyCommand:
        if self.state != State.RELOCALIZE:
            self.ctx.resume_state = self.state
            self.ctx.reloc_since = self.now
            self._goto(State.RELOCALIZE)
            self._log(f"localization lost (status={obs.pose.status.value}, sigma={obs.pose.xy_sigma:.2f} m): stop and observe")
            return self._issue(CommandKind.HOLD, None, None, 0.0, "localization lost: hold")
        if self.now - self.ctx.reloc_since > self.cfg.relocalize_budget_s:
            return self._fail(Outcome.LOCALIZATION_LOST, "could not relocalize within budget")
        if self.active.kind == CommandKind.HOLD and self.now - self.active.issued_at > 1.0 or \
                self.active.kind == CommandKind.SCAN and self.now - self.active.issued_at > 3.0:
            # Turn in place to give VSLAM new views; never translate on a lost pose.
            return self._issue(CommandKind.SCAN, None, None, 0.0, "relocalize: scan for features",
                               scan_yaw=self.cfg.relocalize_scan_rad)
        return self._refresh(self.active)

    def _on_blocked(self, fb: ControlFeedback) -> AutonomyCommand | None:
        self.ctx.blocked_count += 1
        if fb.blocked_at is not None:
            self.nav.mark_blocked(fb.blocked_at, self.cfg.blocked_mark_radius_m)
        self._log(f"blocked ({fb.message}) at {fb.blocked_at}; #{self.ctx.blocked_count}")
        if self.ctx.blocked_count > self.cfg.max_blocked:
            return self._fail(Outcome.NO_PATH, "blocked too many times")
        # Force the current state to re-plan from scratch on this tick.
        if self.state in (State.APPROACH, State.FINAL_APPROACH, State.SETTLE, State.REACQUIRE):
            t = self._target()
            if t is not None and self.last_pose is not None:
                goal = self.nav.approach(t.position, self.last_pose, self.cfg.standoff_m)
                if goal is None:
                    return self._fail(Outcome.NO_PATH, f"no path to {t.key} after blockage")
                self.ctx.goal = goal.pose
                self._goto(State.APPROACH)
                return self._issue(CommandKind.NAVIGATE, goal.pose, goal.path, self.cfg.approach_speed,
                                   "replan around obstacle")
        self.active = None  # SEARCH/VERIFY handlers will pick a new goal with the updated map
        if self.state == State.VERIFY:
            self._goto(State.SEARCH)
        return None

    def _reenter(self, obs: Observation, degraded: bool) -> AutonomyCommand | None:
        self._log(f"re-entering {self.state.value} after interruption")
        if self.state in (State.SEARCH, State.VERIFY):
            self.active = None
            self._goto(State.SEARCH)
            return None  # SEARCH handler re-evaluates candidates / picks a new goal
        t = self._target()
        if self.state in (State.APPROACH, State.REACQUIRE):
            if t is None or t.confidence < 0.25:
                self.active = None
                self._goto(State.SEARCH)
                return None
            return self._start_approach(obs, Candidate(t, Verdict.CONFIRMED, t.confidence))
        if self.state == State.FINAL_APPROACH and self.ctx.goal is not None:
            return self._issue(CommandKind.FINAL_APPROACH, self.ctx.goal, None, self.cfg.final_speed,
                               "resume final approach after interruption")
        return None  # SETTLE: its handler issues HOLD and restarts the dwell

    def _revalidate_path(self, obs: Observation) -> AutonomyCommand | None:
        """Replan *before* contact if the live map now blocks the active path or its goal."""
        a = self.active
        if a is None or a.goal_pose is None or a.kind not in (CommandKind.NAVIGATE, CommandKind.FINAL_APPROACH):
            return None
        # Only re-check when the obstacle map changed since this command's path was planned; a path
        # the planner just produced is by definition consistent with the current map.
        if self._planned_map_version.get(a.issued_at) == self.nav.map_version:
            return None
        self._planned_map_version[a.issued_at] = self.nav.map_version
        pose = obs.pose.pose
        ahead = list(a.path or ()) + [tuple(a.goal_pose.xy())]
        if self.nav.path_is_free(ahead, pose.xy()):
            return None
        self.ctx.replans += 1
        if self.ctx.replans > self.cfg.max_replans:
            return self._fail(Outcome.NO_PATH, "too many replans around observed obstacles")
        g = self.nav.grid.world_to_cell(a.goal_pose.xy())
        new = self.nav.plan(pose.xy(), a.goal_pose.xy()) if self.nav.grid.in_bounds(g) and self.nav.free[g] else None
        if new is not None:
            self._log(f"observed obstacle on path; replanned ({len(new)} waypoints)")
            return self._issue(a.kind, a.goal_pose, new, a.max_speed, f"replan around observed obstacle: {a.reason}")
        t = self._target()
        if self.state in (State.APPROACH, State.FINAL_APPROACH, State.SETTLE, State.REACQUIRE) and t is not None:
            goal = self.nav.approach(t.position, pose, self.cfg.standoff_m)
            if goal is None:
                return self._fail(Outcome.NO_PATH, f"observed obstacles leave no path to {t.key}")
            self._log("observed obstacle at goal; new approach pose")
            self.ctx.goal = goal.pose
            self._goto(State.APPROACH)
            return self._issue(CommandKind.NAVIGATE, goal.pose, goal.path, self.cfg.approach_speed,
                               "new approach pose around observed obstacle")
        self._log("observed obstacle blocks search goal; choosing another")
        self.active = None
        if self.state == State.VERIFY:
            self._goto(State.SEARCH)
        return None

    # ================================================================== helpers
    def _goal_reached_by_pose(self, obs: Observation) -> bool:
        """Arrival from the pose estimate, so goals complete even when another proposer (VLA)
        drove the robot there or control feedback was lost."""
        a = self.active
        if a is None or a.goal_pose is None or a.kind not in (CommandKind.NAVIGATE, CommandKind.FINAL_APPROACH):
            return False
        p = obs.pose.pose
        pos_ok = np.linalg.norm(a.goal_pose.xy() - p.xy()) <= min(a.position_tolerance, 0.1 if a.kind == CommandKind.FINAL_APPROACH else 0.3)
        yaw_ok = abs(float(np.angle(np.exp(1j * (a.goal_pose.yaw - p.yaw))))) <= a.yaw_tolerance
        return bool(pos_ok and yaw_ok)

    def _goto(self, s: State) -> None:
        if s != self.state:
            if State.SETTLE in (s, self.state):
                self.ctx.settle_since = None  # dwell must be continuous within one SETTLE visit
            self._log(f"{self.state.value} -> {s.value}")
            self.state = s
            self.ctx.state_since = self.now

    def _issue(self, kind: CommandKind, goal: Pose2D | None, path, speed: float, reason: str,
               scan_yaw: float = 0.0, ttl: float | None = None) -> AutonomyCommand:
        self._planned_map_version = {self.now: self.nav.map_version}  # path consistent with current map
        if self._degraded:
            speed = min(speed, self.cfg.degraded_speed)  # single choke point for the uncertainty cap
        self.active = AutonomyCommand(
            kind=kind, issued_at=self.now, expires_at=self.now + (ttl or self.cfg.command_ttl_s), goal_pose=goal,
            path=tuple(map(tuple, path)) if path else None, max_speed=speed, scan_yaw=scan_yaw,
            position_tolerance=self.cfg.stop_pos_tol_m if kind == CommandKind.FINAL_APPROACH else 0.3,
            yaw_tolerance=self.cfg.stop_yaw_tol, reason=reason, state=self.state.value,
        )
        return self.active

    def _refresh(self, cmd: AutonomyCommand | None) -> AutonomyCommand:
        if cmd is None:
            return self._issue(CommandKind.HOLD, None, None, 0.0, "no active command")
        self.active = dataclasses.replace(cmd, expires_at=self.now + self.cfg.command_ttl_s)
        return self.active

    def _hold_or_refresh(self, reason: str) -> AutonomyCommand:
        if self.active is not None and self.active.kind == CommandKind.HOLD:
            return self._refresh(self.active)
        return self._issue(CommandKind.HOLD, None, None, 0.0, reason)

    def _stop(self, reason: str) -> AutonomyCommand:
        if self.active is not None and self.active.kind == CommandKind.STOP:
            return self._refresh(self.active)
        return self._issue(CommandKind.STOP, None, None, 0.0, reason, ttl=1e9)

    def _fail(self, outcome: Outcome, msg: str) -> AutonomyCommand:
        self.outcome = outcome
        self._log(f"FAILED {outcome.value}: {msg}")
        self._goto(State.FAILED)
        return self._stop(f"{outcome.value}: {msg}")

    def _log(self, msg: str) -> None:
        self.events.append(ExecutiveEvent(self.now, self.state.value, msg))
