"""Combine independent navigation stop checks with measured load/contact gates."""
import argparse,json
from pathlib import Path
from evaluation.run_vla_comparison import score


def score_loaded(run, protocol):
    m=json.loads((run/'manifest.json').read_text());gate=protocol['criteria']
    result=score(m,run/'trajectory.csv',{'table':m['protocol']['table']},gate)
    h=m['hand_metrics']
    checks=result['checks']
    checks.update(no_payload_drop=h['payload_drop'] is False,
        payload_shift=h['max_payload_shift_m']<=gate['max_payload_shift_m'],
        tray_tilt=h['max_tray_tilt_deg']<=gate['max_tray_tilt_deg'],
        contact_loss=max(h['max_hand_contact_loss_s'])<=gate['max_hand_contact_loss_s'],
        hand_only_support=not h['other_robot_contact_steps'],
        effort_limit=h['max_arm_torque_Nm']<=h['torque_limit_Nm']+1e-6,
        no_tray_constraint=h['equality_constraints']==0)
    result['physical_delivery_pass']=all(checks.values())
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('run',type=Path)
    ap.add_argument('--protocol',type=Path,default=Path('evaluation/LOADED_NAV_PROTOCOL.json'))
    a=ap.parse_args();print(json.dumps(score_loaded(a.run,json.loads(a.protocol.read_text())),indent=2))
