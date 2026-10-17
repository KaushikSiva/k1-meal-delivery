import numpy as np
import pytest
from training.prepare_sensor_dataset import chunk, episode_arrays, normalization


def test_chunk_masks_boundary_without_crossing_episodes():
    actions=np.arange(15,dtype=np.float32).reshape(3,5)
    values,pad=chunk(actions,1,4)
    np.testing.assert_array_equal(values,actions[[1,2,2,2]])
    np.testing.assert_array_equal(pad,[False,False,True,True])


def test_privileged_rows_cannot_become_deployment_data(tmp_path):
    with pytest.raises(ValueError,match='privileged'):
        episode_arrays([{'privileged_features':True}],tmp_path)


def test_normalization_uses_supplied_training_rows_and_floors_constant_std():
    values=np.array([[1,2],[3,2]],np.float32)
    norm=normalization([values])
    np.testing.assert_allclose(norm['mean'],[2,2])
    np.testing.assert_allclose(norm['std'],[1,.05])
