"""Plot measured hand-carry PPO rewards and matched physical diagnostics."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True)
    args=ap.parse_args();root=args.evidence
    rows=[json.loads(s) for s in (root/'metrics.jsonl').read_text().splitlines()]
    comparison=json.loads((root/'comparison.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    axes[0].plot([r['environment_steps'] for r in rows],[r['reward_mean'] for r in rows],lw=1)
    axes[0].set(xlabel='Actual control transitions',ylabel='Mean rollout reward',title='Hand-contact PPO training')
    modes=['baseline','trained_residual']
    values=[sum(t['diagnostic_pass'] for t in comparison['trials'] if t['mode']==m) for m in modes]
    axes[1].bar(['Baseline','Trained residual'],values,color=['#65758b','#087f8c'])
    axes[1].set(ylim=(0,8),ylabel='Passing conditions / 8',title='Matched physical diagnostics')
    for i,v in enumerate(values):axes[1].text(i,v+.15,str(v),ha='center')
    fig.suptitle('Simulation development evidence — not camera-guided delivery or hardware')
    fig.savefig(root/'training_evaluation.png',dpi=160)
    fig.savefig(root/'training_evaluation.svg')
    svg=root/'training_evaluation.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')


if __name__=='__main__':main()
