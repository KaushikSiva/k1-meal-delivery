#!/usr/bin/env python3
"""Plot recorded pilot metrics; no smoothing or invented samples."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('experiment',type=Path);args=ap.parse_args()
    rows=json.loads((args.experiment/'metrics.json').read_text())
    m=json.loads((args.experiment/'manifest.json').read_text())
    assert [r['step'] for r in rows]==list(range(1,m['optimizer_updates']+1))
    fig,axes=plt.subplots(1,2,figsize=(10,3.6),layout='constrained')
    axes[0].plot([r['step'] for r in rows],[r['loss'] for r in rows],color='#147a73',lw=1)
    axes[0].set(xlabel='Optimizer update',ylabel='Batch flow-matching loss',title='All 200 recorded updates')
    x=np.arange(2);width=.34
    for offset,key,label,color in [(-width/2,'initial_evaluation','Before','#888888'),
                                    (width/2,'final_evaluation','After','#147a73')]:
        axes[1].bar(x+offset,[m[key][s]['first_action_normalized_mse'] for s in ['train','validation']],
                    width,label=label,color=color)
    axes[1].set_xticks(x,['Train','Validation'])
    axes[1].set(ylabel='Normalized action MSE',title='16 sampled rows per split; offline only')
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.suptitle('SmolVLA pilot · 3 training episodes · 1 validation episode · no closed-loop VLA test',fontsize=10)
    fig.savefig(args.experiment/'training_metrics.png',dpi=160)


if __name__=='__main__':main()
