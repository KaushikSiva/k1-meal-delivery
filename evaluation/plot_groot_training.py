"""Plot all recorded GR00T updates and fixed validation samples, including regressions."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('experiment',type=Path);a=ap.parse_args()
    metrics=json.loads((a.experiment/'metrics.json').read_text())
    val=json.loads((a.experiment/'validation_metrics.json').read_text())
    manifest=json.loads((a.experiment/'manifest.json').read_text())
    train=[row for row in metrics if 'loss' in row]
    steps=[row['step'] for row in train];loss=np.array([row['loss'] for row in train])
    total=manifest['optimizer_updates']
    assert len(steps)==len(set(steps)) and steps==sorted(steps)
    assert all(1<=step<=total for step in steps) and np.isfinite(loss).all()
    missing=sorted(set(range(1,total+1))-set(steps))
    full_loss=np.full(total,np.nan);full_loss[np.array(steps)-1]=loss
    vx=np.array([r['optimizer_step'] for r in val]);vy=np.array([r['validation_loss'] for r in val])
    assert np.array_equal(vx,np.arange(0,manifest['optimizer_updates']+1,25))
    assert np.isfinite(vy).all()
    fig,ax=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    ax[0].plot(np.arange(1,total+1),full_loss,color='#8aa2b2',alpha=.7,lw=.7,label='Recorded training loss (gaps retained)')
    ax[0].plot(steps[24:],np.convolve(loss,np.ones(25)/25,mode='valid'),
               color='#136f63',lw=2,label='25-record trailing mean')
    ax[0].set(title=f'Training: {len(train)} loss records / {total} updates',xlabel='Optimizer update',ylabel='Masked denoising loss')
    ax[1].plot(vx,vy,'o-',color='#b74d2f',lw=1.5,ms=4,label='Same 16 validation rows + fixed noise seeds')
    ax[1].axhline(vy[0],ls='--',lw=1,color='#777777',label=f'Initial: {vy[0]:.3f}')
    ax[1].set(title=f'Validation: {vy[0]:.3f} → {vy[-1]:.3f} (lower is better)',
              xlabel='Optimizer update',ylabel='Fixed validation denoising loss')
    for axis in ax:
        axis.set_xlim(0,manifest['optimizer_updates']);axis.set_ylim(bottom=0)
        axis.spines[['top','right']].set_visible(False);axis.grid(alpha=.15)
        axis.legend(frameon=False,fontsize=8)
    verdict='Validation worsened; no generalization improvement established' if vy[-1]>vy[0] else 'Offline validation changed; delivery benefit unmeasured'
    fig.suptitle('GR00T N1.7 · 3 training episodes / 1 validation episode\n'+verdict,fontsize=12)
    fig.savefig(a.experiment/'training_validation.png',dpi=180)
    svg=a.experiment/'training_validation.svg'
    fig.savefig(svg)
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    summary=dict(optimizer_updates=total,training_loss_records=len(train),missing_training_loss_steps=missing,validation_evaluations=len(val),
        initial_validation_loss=float(vy[0]),final_validation_loss=float(vy[-1]),
        validation_relative_change=float(vy[-1]/vy[0]-1),
        first_50_train_loss_mean=float(loss[:50].mean()),last_50_train_loss_mean=float(loss[-50:].mean()),
        plotting_version=matplotlib.__version__,verdict=verdict)
    (a.experiment/'curve_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
