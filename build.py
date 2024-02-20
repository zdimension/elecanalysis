import os
import subprocess
from pathlib import Path
import nicegui
import sys

cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    'elecanalysis.spec'
]
subprocess.call(cmd)
