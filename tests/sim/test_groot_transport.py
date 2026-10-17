"""Lossless transport must preserve pixels, including noisy camera content."""
import base64
import numpy as np
import pytest
from deployment.groot_remote_client import encode_image,decode_image


def test_png_preserves_every_pixel_and_legacy_raw_still_decodes():
    rng=np.random.default_rng(9711)
    for image in [np.zeros((480,640,3),np.uint8),rng.integers(0,256,(480,640,3),dtype=np.uint8)]:
        np.testing.assert_array_equal(decode_image(encode_image(image)),image)
        raw=dict(shape=list(image.shape),dtype='uint8',b64=base64.b64encode(image.tobytes()).decode())
        np.testing.assert_array_equal(decode_image(raw),image)


def test_wrong_shape_and_encoding_are_rejected():
    with pytest.raises(ValueError):encode_image(np.zeros((480,640),np.uint8))
    payload=encode_image(np.zeros((480,640,3),np.uint8))
    payload['encoding']='jpeg'
    with pytest.raises(ValueError):decode_image(payload)
