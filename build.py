import os
import subprocess
from pathlib import Path
import nicegui
import sys

# get current commit hash and date
commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode('utf-8')
commit_hash = commit_hash[:8]
commit_date = subprocess.check_output(['git', 'show', '-s', '--format=%ci', 'HEAD']).strip().decode('utf-8')
commit_date = commit_date.split(' ')[0]
version = f'{commit_hash} ({commit_date})'
with open('_version.py', 'w') as f:
    f.write(f'__version__ = "{version}"\n')

cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    'elecanalysis.spec'
]
subprocess.call(cmd)
