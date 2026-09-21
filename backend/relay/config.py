"""Application settings, independent of the frontend and current directory."""
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DATA_PATH = Path(os.environ.get('DB_PATH', PROJECT_ROOT / 'data/relay-v3.sqlite'))
MODEL_CACHE = Path(os.environ.get('MODEL_CACHE_DIR', PROJECT_ROOT / '.cache/models'))

def frontend_origins():
    return {value.strip().rstrip('/') for value in os.environ.get(
        'FRONTEND_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000'
    ).split(',') if value.strip()}
