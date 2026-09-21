"""Local MiniLM inference using the same quantized ONNX weights as the JS version."""
from pathlib import Path
from threading import Lock
from .config import MODEL_CACHE

ROOT = Path(__file__).resolve().parents[1]
MODEL_STATE = dict(status='not loaded', name='Xenova/all-MiniLM-L6-v2', error=None)
DESCRIPTIONS = dict(employee_id='employee staff identification number', first_name='employee first given name', last_name='employee last family surname',
                    email='employee work email address', department='department team business unit',
                    date_of_birth='employee date of birth birthday', employment_status='HR employment lifecycle status active inactive leave', account_status='platform login account access status active inactive locked')
_lock = Lock()
_session = _tokenizer = None

def suggest(header, fields):
    global _session, _tokenizer
    with _lock:
        try:
            MODEL_STATE['status'] = 'loading'
            import numpy as np
            import onnxruntime as ort
            from tokenizers import Tokenizer
            from huggingface_hub import hf_hub_download
            if _session is None:
                cache = MODEL_CACHE / MODEL_STATE['name']
                def asset(name):
                    existing = cache / name
                    if existing.is_file():
                        return str(existing)
                    return hf_hub_download(MODEL_STATE['name'], name, local_dir=cache)
                _tokenizer = Tokenizer.from_file(asset('tokenizer.json'))
                _tokenizer.enable_padding(pad_id=0, pad_token='[PAD]')
                _tokenizer.enable_truncation(max_length=256)
                _session = ort.InferenceSession(asset('onnx/model_quantized.onnx'), providers=['CPUExecutionProvider'])
            encoded = _tokenizer.encode_batch([header] + [DESCRIPTIONS.get(f, f) for f in fields])
            arrays = {
                'input_ids': np.array([e.ids for e in encoded], dtype=np.int64),
                'attention_mask': np.array([e.attention_mask for e in encoded], dtype=np.int64),
                'token_type_ids': np.array([e.type_ids for e in encoded], dtype=np.int64),
            }
            hidden = _session.run(None, {i.name: arrays[i.name] for i in _session.get_inputs()})[0]
            mask = arrays['attention_mask'][..., None]
            pooled = (hidden * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1)
            vectors = pooled / np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-12)
            scores = [dict(field=f, score=float(vectors[0] @ vectors[i+1])) for i, f in enumerate(fields)]
            MODEL_STATE.update(status='ready', error=None)
            return sorted(scores, key=lambda x: x['score'], reverse=True)[:3]
        except Exception as exc:
            _session = _tokenizer = None
            MODEL_STATE.update(status='unavailable', error=str(exc))
            return []
