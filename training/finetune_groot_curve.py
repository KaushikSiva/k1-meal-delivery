"""Extend the audited GR00T pilot with fixed, train-normalized validation losses."""
import copy
import hashlib
import json
import random
import sys
from pathlib import Path
import numpy as np
import torch
from transformers import TrainerCallback
from transformers.trainer_utils import SaveStrategy
import gr00t.experiment.experiment as experiment
from gr00t.data.dataset.sharded_single_step_dataset import ShardedSingleStepDataset
from gr00t.data.embodiment_tags import EmbodimentTag
from training.groot_k1_config import K1_CONFIG
from training import finetune_groot_pilot as pilot


class FixedValidation(TrainerCallback):
    def __init__(self, trainer, runtime, output):
        self.trainer=trainer;self.output=output;self.rows=[]
        processor=copy.deepcopy(trainer.train_dataset.processor)
        processor.eval()  # deterministic evaluation image transform; no state dropout
        from gr00t.data.stats import generate_stats,generate_rel_stats
        validation_path=str(runtime/'groot-dataset-01/validation')
        # Loader requires metadata; these values are not merged into the processor.
        generate_stats(validation_path)
        generate_rel_stats(validation_path,EmbodimentTag.NEW_EMBODIMENT)
        dataset=ShardedSingleStepDataset(
            dataset_path=str(runtime/'groot-dataset-01/validation'),
            embodiment_tag=EmbodimentTag.NEW_EMBODIMENT,modality_configs=K1_CONFIG,
            shard_size=256,episode_sampling_rate=1.,seed=9501,allow_padding=True)
        dataset.set_processor(processor)  # Never merge validation normalization statistics.
        episode=dataset.episode_loader[0]
        self.indices=np.linspace(0,len(episode)-1,16,dtype=int).tolist()
        self.batches=[trainer.data_collator([dataset.get_datapoint(episode,i)]) for i in self.indices]
        (output/'validation_protocol.json').write_text(json.dumps(dict(
            episode='validation-00',indices=self.indices,training_rows=262,
            normalization='unchanged training processor statistics; validation stats never merged',
            image_transform='processor.eval deterministic',noise_seeds=[9500+i for i in range(16)],
            metric='official masked flow-matching denoising loss; not delivery success',
            every_optimizer_steps=25,validation_used_for_optimization=False),indent=2)+'\n')

    def evaluate(self, state, model):
        was_training=model.training;model.eval();losses=[]
        py_state=random.getstate();np_state=np.random.get_state()
        try:
            with torch.random.fork_rng(devices=[torch.cuda.current_device()]),torch.inference_mode():
                for i,batch in enumerate(self.batches):
                    random.seed(9500+i);np.random.seed(9500+i);torch.manual_seed(9500+i)
                    prepared=self.trainer._prepare_inputs(copy.deepcopy(batch))
                    with self.trainer.compute_loss_context_manager():
                        loss=self.trainer.compute_loss(model,prepared)
                    value=float(loss.detach().float().cpu());assert np.isfinite(value)
                    losses.append(value)
        finally:
            random.setstate(py_state);np.random.set_state(np_state)
            model.train(was_training)
        row=dict(optimizer_step=int(state.global_step),validation_loss=float(np.mean(losses)),
                 per_row_loss=losses,validation_rows=len(losses))
        self.rows.append(row)
        (self.output/'validation_metrics.json').write_text(json.dumps(self.rows,indent=2)+'\n')
        # Trainer.log invokes DefaultFlowCallback.on_log, which clears should_log.
        # Preserve the pending training log when validation runs on_step_end.
        pending_training_log=self.trainer.control.should_log
        try:
            self.trainer.log({'validation/fixed_denoising_loss':row['validation_loss'],
                              'validation/rows':len(losses)})
        finally:
            self.trainer.control.should_log=pending_training_log
        print('FIXED_VALIDATION '+json.dumps(row),flush=True)

    def on_train_begin(self,args,state,control,model=None,**kwargs):
        self.evaluate(state,model)

    def on_step_end(self,args,state,control,model=None,**kwargs):
        if state.global_step%25==0:self.evaluate(state,model)

    def on_log(self,args,state,control,logs=None,**kwargs):
        (self.output/'metrics_live.json').write_text(json.dumps(state.log_history,indent=2)+'\n')


class CurveTrainer(experiment.Gr00tTrainer):
    def train(self,*args,**kwargs):
        runtime=Path(sys.argv[sys.argv.index('--runtime')+1])
        output=Path(sys.argv[sys.argv.index('--output')+1])
        output.joinpath('curve_source_sha256.json').write_text(json.dumps({
            str(Path(__file__).name):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2))
        # experiment.run saves the final model after train; avoid a second 12.6GB copy.
        self.args.save_strategy=SaveStrategy.NO
        self.add_callback(FixedValidation(self,runtime,output))
        return super().train(*args,**kwargs)


if __name__=='__main__':
    experiment.Gr00tTrainer=CurveTrainer
    pilot.main()
