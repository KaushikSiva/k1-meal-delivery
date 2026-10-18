"""Lossless image transport for SSH-tunneled, bounded model proposals."""
import base64
import io
import json
import time
from urllib.request import Request, urlopen
import numpy as np
from PIL import Image
from vla.adapter import VLAProposal


def encode_image(rgb):
    rgb=np.asarray(rgb)
    if rgb.dtype!=np.uint8 or rgb.shape!=(480,640,3):
        raise ValueError('Expected uint8 480x640 RGB')
    stream=io.BytesIO()
    Image.fromarray(rgb).save(stream,format='PNG',compress_level=1)
    return dict(shape=list(rgb.shape),dtype='uint8',encoding='png',
                b64=base64.b64encode(stream.getvalue()).decode())


def decode_image(image):
    if image['shape']!=[480,640,3] or image['dtype']!='uint8':
        raise ValueError('Invalid image metadata')
    raw=base64.b64decode(image['b64'],validate=True)
    if image.get('encoding')=='png':
        with Image.open(io.BytesIO(raw)) as png:
            if png.format!='PNG' or png.size!=(640,480) or png.mode!='RGB':
                raise ValueError('Invalid PNG image')
            rgb=np.asarray(png).copy()
    elif image.get('encoding') in (None,'raw'):
        if len(raw)!=480*640*3:raise ValueError('Invalid raw image bytes')
        rgb=np.frombuffer(raw,np.uint8).reshape(480,640,3).copy()
    else:raise ValueError('Unsupported image encoding')
    return rgb


class LosslessRemoteVLAClient:
    def __init__(self,endpoint,timeout_s=5.):
        self.endpoint=endpoint;self.timeout_s=timeout_s;self.failures=0

    def propose(self,inputs):
        started=time.monotonic()
        try:
            body=dict(task=inputs['task'],state=np.asarray(inputs['observation.state']).tolist(),
                      timestamp=inputs['timestamp'],image=encode_image(inputs['observation.images.head']))
            request=Request(self.endpoint,json.dumps(body).encode(),{'Content-Type':'application/json'})
            with urlopen(request,timeout=self.timeout_s) as response:result=json.load(response)
            return VLAProposal(np.asarray(result['actions'],float),inputs['timestamp'],
                               result['model_id'],time.monotonic()-started)
        except Exception:
            self.failures+=1
            return None
