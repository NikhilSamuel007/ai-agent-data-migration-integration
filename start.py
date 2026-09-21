"""Optional launcher for the two independent services: python start.py."""
from pathlib import Path
import os
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
environment = ROOT / '.venv'
python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11 or newer is required.')
if not python.exists():
    venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'backend/requirements.txt')], check=True)
processes = []
try:
    for service in ('backend', 'frontend'):
        processes.append(subprocess.Popen([str(python), str(ROOT / service / 'server.py')], cwd=ROOT))
    import time
    while all(p.poll() is None for p in processes):
        time.sleep(.5)
except KeyboardInterrupt:
    pass
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        process.wait()
