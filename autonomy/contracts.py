"""PROPOSED observation/command contracts for the autonomy stack (Claude draft).

Status: proposal for Codex to consolidate into contracts/. Documented in
docs/autonomy/CONTRACTS.md. Not yet integration-tested against the simulator.

Conventions
-----------
- Units: meters, radians, seconds (timestamps are robot monotonic clock, float seconds).
- Frames: "map" (z up, floor z=0, fixed for an episode), "base" (robot base, x forward,
  y left, z up), camera = OpenCV optical frame (x right, y down, z forward).
  MuJoCo/Isaac cameras in OpenGL convention: T_cv = T_gl @ GL_TO_CV.
- Depth: metric z-depth along the optical axis; 0/NaN/inf = no return.
- Every input declares Provenance. SIM_PRIVILEGED data (ground-truth poses, object ids,
  rendered instance masks) may be used for diagnostics/evaluation/training labels only;
  `assert_deployable()` rejects it on the actor path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

CONTRACT_VERSION = "0.2.0-proposal"

GL_TO_CV = np.diag([1.0, -1.0, -1.0, 1.0])


class Provenance(str, Enum):
    MEASURED = "measured"  # real sensor, or simulated sensor emulation (rendered RGB/depth, IMU)
    ESTIMATED = "estimated"  # output of an estimator (odometry, VSLAM, detector)
    OPERATOR = "operator"  # provided by a human (instruction, map annotations)
    SIM_PRIVILEGED = "sim_privileged"  # simulator ground truth: NEVER on the deployed actor path


class PrivilegedInputError(RuntimeError):
    pass


# --------------------------------------------------------------------------- geometry
@dataclass(frozen=True)
class Pose2D:
    x: float
    y: float
    yaw: float

    def xy(self) -> np.ndarray:
        return np.array([self.x, self.y])

    def matrix(self, z: float = 0.0) -> np.ndarray:
        c, s = np.cos(self.yaw), np.sin(self.yaw)
        T = np.eye(4)
        T[:2, :2] = [[c, -s], [s, c]]
        T[:3, 3] = [self.x, self.y, z]
        return T


class LocalizationStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"  # usable for local motion, not for committing to far goals
    LOST = "lost"


@dataclass(frozen=True)
class PoseEstimate:
    """Base pose in the map frame as *estimated* by the robot (odometry/VSLAM)."""

    pose: Pose2D
    cov: np.ndarray  # (3,3) covariance of (x, y, yaw)
    timestamp: float
    source: str  # "wheel_odom" | "leg_odom" | "vslam" | "sim_gt"
    provenance: Provenance = Provenance.ESTIMATED
    status: LocalizationStatus = LocalizationStatus.OK

    @property
    def xy_sigma(self) -> float:
        """Std-dev along the worst xy axis (meters)."""
        return float(np.sqrt(max(np.linalg.eigvalsh(self.cov[:2, :2]).max(), 0.0)))

    @property
    def yaw_sigma(self) -> float:
        return float(np.sqrt(max(self.cov[2, 2], 0.0)))


@dataclass(frozen=True)
class CameraIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int

    @staticmethod
    def from_fovy(fovy_deg: float, width: int, height: int) -> "CameraIntrinsics":
        f = 0.5 * height / np.tan(np.deg2rad(fovy_deg) / 2)
        return CameraIntrinsics(f, f, (width - 1) / 2, (height - 1) / 2, width, height)

    @property
    def hfov(self) -> float:
        return 2 * np.arctan(self.width / (2 * self.fx))


@dataclass
class CameraFrame:
    timestamp: float
    intrinsics: CameraIntrinsics
    T_base_camera: np.ndarray  # (4,4) optical frame -> base frame (calibrated extrinsics + head joints)
    rgb: np.ndarray | None = None  # (H,W,3) uint8
    depth: np.ndarray | None = None  # (H,W) float32 meters
    provenance: Provenance = Provenance.MEASURED
    # Instance masks rendered by the simulator are privileged; a learned segmenter's are ESTIMATED.
    segmentation: np.ndarray | None = None  # (H,W) int32, 0 = background
    segment_labels: dict[int, str] = field(default_factory=dict)
    segmentation_provenance: Provenance = Provenance.SIM_PRIVILEGED


@dataclass
class Observation:
    """One synchronized snapshot handed to autonomy. Any field may be missing (None)."""

    timestamp: float
    camera: CameraFrame | None
    pose: PoseEstimate | None
    base_twist: np.ndarray | None = None  # (3,) measured vx, vy (base frame), wz
    extra: dict[str, Any] = field(default_factory=dict)  # diagnostics only, never read by the actor

    def T_map_camera(self) -> np.ndarray | None:
        if self.camera is None or self.pose is None:
            return None
        return self.pose.pose.matrix() @ self.camera.T_base_camera

    def assert_deployable(self) -> None:
        if self.pose is not None and self.pose.provenance == Provenance.SIM_PRIVILEGED:
            raise PrivilegedInputError("pose estimate is simulator ground truth")
        if self.camera is not None:
            if self.camera.provenance == Provenance.SIM_PRIVILEGED:
                raise PrivilegedInputError("camera frame is privileged")
            if self.camera.segmentation is not None and self.camera.segmentation_provenance == Provenance.SIM_PRIVILEGED:
                raise PrivilegedInputError("rendered instance segmentation is simulator ground truth")


# --------------------------------------------------------------------------- perception
@dataclass
class Detection:
    label: str  # "table", "person", "chair", "counter" ...
    position: np.ndarray  # (3,) map frame
    position_cov: np.ndarray  # (3,3) incl. propagated pose uncertainty
    confidence: float  # detector score in [0,1]
    timestamp: float
    provenance: Provenance
    # Visual attributes used for destination grounding, each with its own confidence.
    # e.g. {"table_number": ("3", 0.9), "color": ("blue", 0.7)}
    attributes: dict[str, tuple[str, float]] = field(default_factory=dict)
    track_id: str | None = None  # detector/tracker id; NOT a simulator object id on the actor path
    bbox: tuple[int, int, int, int] | None = None
    extent: np.ndarray | None = None


@dataclass
class OccupancyGrid:
    """2D traversability grid in the map frame. data[row, col]; row = y, col = x."""

    FREE = 0
    OCCUPIED = 1
    UNKNOWN = 255

    data: np.ndarray
    resolution: float
    origin: tuple[float, float]
    provenance: Provenance = Provenance.OPERATOR  # prior floor plan vs. live-mapped

    def world_to_cell(self, xy) -> tuple[int, int]:
        return (
            int(np.floor((xy[1] - self.origin[1]) / self.resolution)),
            int(np.floor((xy[0] - self.origin[0]) / self.resolution)),
        )

    def cell_to_world(self, rc) -> np.ndarray:
        return np.array(
            [self.origin[0] + (rc[1] + 0.5) * self.resolution, self.origin[1] + (rc[0] + 0.5) * self.resolution]
        )

    def in_bounds(self, rc) -> bool:
        return 0 <= rc[0] < self.data.shape[0] and 0 <= rc[1] < self.data.shape[1]


@dataclass(frozen=True)
class Region:
    """Operator-annotated semantic region (e.g. "dining_area"). Used as a search prior only;
    it never reveals which table is the destination."""

    name: str
    center: tuple[float, float]
    radius: float
    tags: tuple[str, ...] = ()


# --------------------------------------------------------------------------- task
@dataclass(frozen=True)
class DestinationSpec:
    """What the destination looks like, grounded from the instruction."""

    category: str  # "table" | "person" | "counter"
    attributes: tuple[tuple[str, str], ...] = ()  # (("table_number", "3"),)
    region_hint: str | None = None  # e.g. "window" -> Region name/tag, prior only

    def attr(self) -> dict[str, str]:
        return dict(self.attributes)


@dataclass(frozen=True)
class DeliveryTask:
    instruction: str
    destination: DestinationSpec
    issued_at: float
    time_limit_s: float = 300.0


# --------------------------------------------------------------------------- autonomy -> navigation/control
class CommandKind(str, Enum):
    NAVIGATE = "navigate"  # follow path toward goal_pose at <= max_speed
    FINAL_APPROACH = "final_approach"  # decelerate and stop at goal_pose within tolerance
    SCAN = "scan"  # turn in place by scan_yaw (rad) to observe; no translation
    HOLD = "hold"  # stand still, keep balance, keep observing
    STOP = "stop"  # controlled stop and stay stopped (terminal)


@dataclass(frozen=True)
class AutonomyCommand:
    kind: CommandKind
    issued_at: float
    expires_at: float  # control must stop/hold if no newer command arrives before this
    goal_pose: Pose2D | None = None  # map frame
    path: tuple[tuple[float, float], ...] | None = None  # map-frame waypoints from navigation
    max_speed: float = 0.0  # m/s, upper bound; carrying controller may go slower
    scan_yaw: float = 0.0
    position_tolerance: float = 0.15
    yaw_tolerance: float = 0.2
    reason: str = ""
    state: str = ""  # executive state that produced it (for logs / eval attribution)
    selected_by: str = "executive"  # "executive" | "vla" | "baseline" — label which policy chose it


class FeedbackStatus(str, Enum):
    RUNNING = "running"
    REACHED = "reached"
    BLOCKED = "blocked"  # local obstacle/foothold check failed
    FAILED = "failed"  # fall, balance alarm, payload alarm, timeout


@dataclass
class ControlFeedback:
    """Navigation/carrying control -> autonomy, each tick."""

    timestamp: float
    command_issued_at: float  # which command this refers to
    status: FeedbackStatus
    message: str = ""
    blocked_at: tuple[float, float] | None = None  # map xy of obstacle if known
    info: dict[str, Any] = field(default_factory=dict)  # e.g. tray tilt estimate (with provenance)


class Outcome(str, Enum):
    DELIVERED = "delivered"  # stably stopped at a confirmed destination
    DESTINATION_NOT_FOUND = "destination_not_found"
    AMBIGUOUS_DESTINATION = "ambiguous_destination"
    NO_PATH = "no_path"
    LOCALIZATION_LOST = "localization_lost"
    SENSOR_TIMEOUT = "sensor_timeout"
    CONTROL_FAILURE = "control_failure"
    TIMEOUT = "timeout"
