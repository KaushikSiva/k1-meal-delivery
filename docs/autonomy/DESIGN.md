# Autonomy design — perception, memory, search, executive, VLA interface

Author: Claude · Status: **implemented and software-tested on a synthetic CPU fixture only**.
Nothing here has run in a physics simulator or on a K1. Proposed contracts: [CONTRACTS.md](CONTRACTS.md).
VLA data/action proposal: [VLA_DATA_SPEC.md](VLA_DATA_SPEC.md).

## 1. Scope

Task: the robot gets an instruction ("deliver the pizza and drink to table 3"), finds the destination
using its own camera, and walks there carrying a preloaded tray. It then decelerates and stops steadily
at the destination. Pickup and placement are out of scope for this milestone (GOAL.md).

This layer decides **where to go and when to stop**. It never commands joints. Balance, gait and tray
stabilization belong to the carrying controller (Codex), which is the single actuator-command owner.

```
camera (RGB-D) ─► perception ─► scene memory ◄── pose estimate (odom/VSLAM, with covariance)
                                  │
instruction ─► grounding ─► DeliveryExecutive (state machine) ◄── control feedback
                                  │      ▲
                                  │      └── VLA proposal ─► BoundedActionAdapter (optional)
                                  ▼
                          AutonomyCommand (bounded, expiring)
                                  ▼
                     navigation feasibility ─► carrying controller ─► K1
```

## 2. Camera-based destination grounding (`autonomy/grounding.py`)

- The instruction is parsed into a `DestinationSpec`: a category (`table`, `person`, `counter`) plus
  required visual attributes (`table_number=3`, `color=red`) and an optional region hint (`window`).
  The parser is keyword-based for now. An LLM/VLM can replace it if it returns the same spec.
- The destination's **location only ever comes from detections in scene memory**. Region hints only
  bias where to search; they never confirm a destination. No evaluation markers or simulator object
  ids are involved.
- Each remembered object of the right category gets a verdict:
  - **CONFIRMED**: every required attribute has been observed matching (fused conf ≥ 0.6).
  - **POSSIBLE**: the category matches, but some attribute hasn't been read yet (e.g. the number
    placard was too far away for OCR).
  - **REJECTED**: an attribute was confidently read with a different value.
- POSSIBLE candidates trigger a **VERIFY** detour: walk to ~1.2 m and hold to read the attribute.
  After two failed attempts a candidate is marked unverifiable, so the robot doesn't loop forever.
- **Ambiguity is reported, not guessed.** If two objects are CONFIRMED (e.g. "the table" with several
  tables in view, or two placards both reading "3"), the outcome is `AMBIGUOUS_DESTINATION`. This is
  also checked during approach, in case the second match only appears then.
  Known gap: "the table" with only one table seen so far gets approached. An operator clarification
  channel is future work.

## 3. Perception (`perception/`)

- **Deployable path, `BoxLifter`**: takes 2D detections (bbox/mask + score + attributes) from any
  image model, lifts them to 3D with depth and the *estimated* camera pose, and outputs
  provenance `ESTIMATED`. Candidate image models (open-vocabulary detector + OCR for table numbers)
  are not yet selected or benchmarked on Orin-class compute.
- Each lifted point gets a covariance: depth noise (2% of range) plus propagated pose uncertainty
  (`xy_sigma² + (range·yaw_sigma)²`).
- **Simulator-only paths**: `SimSegmentationDetector` (rendered masks) and `GroundTruthDetector` are
  tagged `SIM_PRIVILEGED`. The executive refuses them when `deployable=True`, and
  `Observation.assert_deployable()` refuses privileged pose or segmentation inputs.
- `visible_mask()` decides whether a remembered point *should* be visible: in frustum, in range,
  and not occluded according to the depth image. Memory uses it for negative evidence.

## 4. Timestamped scene memory (`memory/scene_memory.py`)

- Objects in the map frame, each with position + scalar variance, confidence, `first_seen`,
  `last_seen`, sighting/miss counts, fused attributes and the set of provenances.
- **Association**: the tracker id, else the nearest same-label object inside a gate of
  `max(0.5 m, 2.5σ, 0.8 × observed footprint diagonal)`. The footprint term exists because partial
  views of a large table move its centroid by more than 0.5 m; without it, testing showed duplicate
  tracks. Confidently conflicting attributes veto association, so adjacent tables numbered 2 and 3
  never merge.
- **Confidence**:
  - noisy-OR on each sighting;
  - exponential decay with time (half-life 300 s);
  - ×0.6 per frame on **negative evidence**: the object should be visible from the current pose
    but wasn't detected.
- Negative evidence is suspended while localization is not OK, so a bad pose estimate can't erase
  correct memories.
- Remembered positions are never treated as proof the object stayed put. Stale memory (older than
  60 s) is approached slowly as a *hypothesis* and must be re-observed before arrival can be
  declared.

## 5. Localization uncertainty

- The pose arrives as a `PoseEstimate` with a 3×3 covariance, a source (`leg_odom`, `vslam`, …),
  a provenance and a status. The deployed actor never receives exact simulator poses.
- **OK**: normal behavior.
- **DEGRADED** (σxy > 0.15 m or status degraded): every command is capped at 0.15 m/s at a single
  choke point (`_issue`). FINAL_APPROACH and the arrival declaration are blocked; near the goal
  the robot holds.
- **LOST** (σxy > 0.4 m or status lost) → **RELOCALIZE**: HOLD, then scan in place to give
  VSLAM new views. The robot never translates toward stale coordinates. It resumes the previous
  state on recovery and reports `LOCALIZATION_LOST` after a 20 s budget.
- Search coverage is only updated while localization is OK.

## 6. Search when the destination has never been seen (`navigation/search.py`)

- A coverage grid records which floor cells the camera frustum has swept (rays stop at known
  obstacles).
- Candidate viewpoints are sampled from free cells of the robot-radius-inflated map. Each is
  scored by prior-weighted unseen area in a 90° wedge, divided by `(1 + 0.5 × path length)`,
  with a revisit penalty.
- Priors come from operator-annotated regions; an instruction hint such as "window" boosts the
  matching region ×6.
- Every goal comes with a planned A* path (8-connected, no corner cutting, line-of-sight
  shortcutting). Paths start at the true robot position and end at the exact goal.
- Termination: no reachable unexplored viewpoint, or 30 explore goals →
  `DESTINATION_NOT_FOUND`.

## 7. Target out of view, reacquisition

- Once confirmed, the destination is tracked through memory, so walking around an obstacle or a
  passer-by occluding it doesn't restart search. The software test checks it stays a single track
  with no fallback to exploration.
- If the target hasn't been seen for more than 4 s while within 3 m, the executive enters
  **REACQUIRE**: it turns toward the remembered bearing.
- If it is seen again, approach continues. If negative evidence drives its confidence below 0.25
  (it moved, or was a false positive), the executive goes back to SEARCH.
- Arrival is never declared "blind": the destination must have been seen within the last 3 s.

## 8. Obstacle handling

- Static obstacles come from the prior map (operator-provided occupancy grid), inflated by robot
  radius + tray clearance (0.3 m default).
- Runtime obstacles: when control reports `BLOCKED` with an obstacle point, navigation adds a
  0.4 m blocked patch and the executive replans. More than 6 blocks, or no path left →
  `NO_PATH`.
- Limitation: a 2D grid planner is not validated humanoid navigation. Foothold, step and doorway
  checks belong to the carrying controller / navigation integration (Codex, G4).
  Live depth-based obstacle mapping is not implemented yet. Today runtime obstacles enter only
  through BLOCKED feedback.

## 9. Completion: stable arrival

Final approach is a dedicated `FINAL_APPROACH` command capped at 0.15 m/s. `DELIVERED` is declared
only when all of these hold:

1. position error ≤ 0.2 m and yaw error ≤ 0.35 rad from the stop pose;
2. measured base speed `|v_xy| + 0.3·|ω|` ≤ 0.03 continuously for 1.5 s (from measured twist, not
   commanded speed);
3. localization is OK;
4. the destination was seen within the last 3 s.

If the base keeps swaying (software test with a jittering controller), success is never declared and
the run times out. Drifting more than 0.4 m from the stop pose sends the executive back to approach.

These thresholds are **engineering placeholders**. Codex's frozen evaluation protocol should define
the official tolerances; the executive's config should be set from it, not the other way round.

## 10. Failure and uncertainty reporting

- Every terminal path ends in a `STOP` command with an explicit `Outcome`:
  `delivered`, `destination_not_found`, `ambiguous_destination`, `no_path`, `localization_lost`,
  `sensor_timeout`, `control_failure`, `timeout`.
- **Missing observations**: if the camera or pose is missing, or the camera frame is older than
  0.5 s, the executive enters SENSOR_WAIT and HOLDs. After 5 s it reports `SENSOR_TIMEOUT`.
- Commands expire after 1 s (TTL), so control must hold if autonomy goes silent.
- The executive keeps a timestamped event log for evaluation and failure analysis.

## 11. VLA integration (summary; details in VLA_DATA_SPEC.md)

The VLA is an optional **proposer** of short-horizon local subgoals. The executive stays in charge
of task state, memory, safety and completion. It always wins in RELOCALIZE, SENSOR_WAIT,
FINAL_APPROACH, SETTLE and terminal states.

Memory is injected explicitly into the VLA inputs (state vector + text); we do not assume a VLA has
memory or SLAM. Every command is labeled `selected_by ∈ {executive, vla}` for attribution.

## 12. Evidence status

| Capability | State |
| --- | --- |
| Grounding, memory, search, executive, adapter | implemented → **software-tested** (synthetic fixture, `tests/autonomy`) |
| Perception with a learned detector/OCR | planned (BoxLifter interface implemented; no model selected) |
| Integration with K1 sim camera/pose | planned (needs Codex sim; contract proposed) |
| VLA fine-tuning | planned (spec only; no data, no training) |
| Hardware | none |

Fixture limitations: point robot with kinematic motion; perfect depth; the fixture's 2D detector reads
rendered masks (so fixture runs are not "deployable"); no tray, gait, foothold or dynamics; static
lighting.
