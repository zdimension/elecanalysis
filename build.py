import os
import subprocess
from pathlib import Path
import nicegui
import sys

# get current commit hash and write to _version.py
commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
with open('_version.py', 'w') as f:
    f.write(f'__version__ = "{commit_hash}"\n')

cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    'elecanalysis.spec'
]
subprocess.call(cmd)
