#!/usr/bin/env python3
"""Plot recorded PPO metrics without inferring evaluation success rates."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('metrics',type=Path);parser.add_argument('output',type=Path)
args=parser.parse_args()
if args.output.exists():raise FileExistsError(args.output)
rows=[json.loads(s) for s in args.metrics.read_text().splitlines()]
steps=[r['environment_steps'] for r in rows]
fig,axes=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
axes[0].plot(steps,[r['reward_mean'] for r in rows],color='#1c6976',linewidth=1.5)
axes[0].set(title='Actual training reward (per rollout)',ylabel='Mean reward per transition')
for key,label,color in [('drops','Payload drop','#b24c3d'),('timeouts','Time limit','#1c6976'),('falls','Robot fall','#6a5b83')]:
    axes[1].plot(steps,[r[key] for r in rows],label=label,color=color)
axes[1].set(title='Cumulative training episode endings',ylabel='Count');axes[1].legend(frameon=False)
for ax in axes:
    ax.set_xlabel('Physics transitions across all environments');ax.grid(alpha=.2)
    ax.spines[['top','right']].set_visible(False)
fig.suptitle('Supported-tray residual PPO · development training, not held-out evaluation',fontsize=11)
fig.savefig(args.output,dpi=170)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
args.output.with_suffix('.provenance.json').write_text(json.dumps({
    'metrics_sha256':sha(args.metrics),'plot_sha256':sha(args.output),'script_sha256':sha(Path(__file__)),
    'matplotlib_version':matplotlib.__version__,'iterations':len(rows),'smoothing':'none',
    'limits':'training measurements; time limit is not a successful delivery'},indent=2)+'\n')
