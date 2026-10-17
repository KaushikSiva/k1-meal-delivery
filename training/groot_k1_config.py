"""K1 bounded subgoals, not joint actions; matches the existing VLA interface."""
from gr00t.configs.data.embodiment_configs import register_modality_config
from gr00t.data.embodiment_tags import EmbodimentTag
from gr00t.data.types import ActionConfig,ActionFormat,ActionRepresentation,ActionType,ModalityConfig
K1_CONFIG={
 'video':ModalityConfig(delta_indices=[0],modality_keys=['head']),
 'state':ModalityConfig(delta_indices=[0],modality_keys=['telemetry']),
 # Inputs already encode a relative subgoal in the 5D bounded action space.
 # ABSOLUTE prevents GR00T from subtracting unrelated 16D telemetry values.
 'action':ModalityConfig(delta_indices=list(range(10)),modality_keys=['subgoal'],action_configs=[ActionConfig(rep=ActionRepresentation.ABSOLUTE,type=ActionType.NON_EEF,format=ActionFormat.DEFAULT)]),
 'language':ModalityConfig(delta_indices=[0],modality_keys=['annotation.human.task_description'])}
register_modality_config(K1_CONFIG,embodiment_tag=EmbodimentTag.NEW_EMBODIMENT)
