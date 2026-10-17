# Codex status

Updated (UTC): 2026-10-17T23:53:48.189540+00:00
State: working — verify new footage and evaluate trained GR00T in loaded closed loop.
Previous turn: progress (cbb4264 public checkpoint, 3/4 varied loaded trials, complete500-loss GR00T repeat, physical appearance parity and turn-drift diagnostic). Team-name reply alone added no engineering evidence; jobs rechecked on resume.

## Current claims

Codex ownership per OWNERSHIP.md. Exact active paths: sim/run_k1_sensor_navigation.py,
sim/k1_mujoco_appearance.py, tests/sim/test_mujoco_appearance.py,
evaluation/run_loaded_navigation.py, evaluation/LOADED_NAV_VARIATION_PROTOCOL.json,
evaluation/run_hand_turn_probe.py, deployment/serve_groot.py,
experiments/codex-20261017T2320-groot-curve/attempt03/,
experiments/codex-20261017T2340-loaded-variation/,
experiments/codex-20261017T2345-printed-navigation/,
experiments/codex-20261017T2350-hand-turn-probe/,
README.md, sim/README.md, docs/RESOURCES.md and own coordination files.

## Verified evidence

- Public HEAD cbb4264 pushed. Loaded05 delivered22.8s+2ssettle; all14 individual checks pass, no collision/drop/fall,3.8mm payload shift. Both videos621frames/25fps.
- Prospective four-condition loaded batch:3/4 pass. Right-offset run timed out with wall contact,1.09m poseerror,13.66degtraytilt andbrief nonhand armcontact. Allattempts retained and hashes verified.
- Seven pure-yaw probes finished: ±.15/.25rad/s commands produce1.6–1.8m unintended translation over8s and keepmovingafterzeroingcommands. ±.05rad/s produces almostno rotation. Need carrying-controller improvement, not just localization tuning.
- GR00T02:500updates,480losslogs,21validationpoints; validation38.9%worse,strictreloadpassed.
- GR00T03 fixedlogger:500updates,500losslogs,21validationpoints; validation22.3%lower. Sameinitialization/declaredseed didnotreproduceidenticaltrajectory; bothresults retained. Strictreload passedfinite[1,10,5],0.39295s firstinference. Frozenweights unchanged. No delivery benefit yet.
- PrintedMuJoCoappearance preserves exact masses/inertias/contactproperties and100-step free dynamics; one meaningful testpassed. Newphysicaltable/floor scene01timedout60s withoutdrop/contact. Scene02running withdeclared90s diagnosticbudget; never retroactively a60s pass.

## Next and boundaries

Verify scene02, publish reports and sources, then run bounded GR00T proposals on the same four loaded conditions using authenticated model access on existingL40S and a localhost SSH tunnel. No hardware actuation. Do not edit/stage Claude WIP navigation/localization.py.
Read Claude handoff through23:11:12 CL12; graph+films delivered through CODEX_HANDOFF.
L40S retained for17:15–18:30PDT demo; disk3.2GBfree, no more checkpoint duplication. No model currentlytraining. Goalactive; learned hand-carry, robust varied delivery and hardware verification remain unfinished.

Claim evaluation/GROOT_LOADED_PROTOCOL.json and experiments/codex-20261017T2355-groot-loaded/. Live healthverifiedgroot-c788024b6205,500updates,all3shards. Four-condition matchedbatch launch, freshimmutablecbb4264snapshotplusremoteproposalrunneronly. Previous turnprogress: servinghash-verifiedcheckpointviaSSH, printed02delivered65.6s+2ssettle,1691frames25fps67.64sverified.

Previousgoalturnprogress: submissionpageverified(publicthemeonly; exacttrackoptionspendinguser), printedrunscored and tenfocusedtests passed. GR00Trawbatchlive: firstpass had22validcalls/zeroaccepted due.76–2.84slatency; secondfailed andaccepted9ticks with97validcalls. Claim deployment/groot_remote_client.py, tests/sim/test_groot_transport.py for losslessPNGtransport, no raisedproposalagedlimit. Preserve originalserver source beforechange; newserver waitsfororiginalbatchcompletion.

GR00Trawbatchcompleted3/4vsbaseline3/4, VLA-ownedticks0/9/27/119. No modelHTTPfailures; delayoften>.6sfreshnesslimit. Allartifacthasheschecked; report/sourcepreserved. LosslessPNGtwo tests passed (randomimageandrawcompatibility, invalidmetadata rejection). Stoponlyownserver01pythonafterterminalbatch, launchserver02on8767 withsamecheckpoint/seed; preparematchedPNGbatch.

Claim evaluation/GROOT_LOADED_PNG_PROTOCOL.json and experiments/codex-20261017T2355-groot-loaded/png/. Server02readyhashmatches, samecheckpointseed9701, newPNG4conditionbatchlaunched. Server01processstoppedafterrawbatchfinished; VMremainsrunning. Identicalfrozen-sharddedupe03↔02verified4.986GB, bothpathsandbytespreserved. Printed18.64sexcerpt466frames25fpsdecoded. Publishingcurrentcompleteevidencenext.
