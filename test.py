import subprocess
import sys

returncode = subprocess.call([sys.executable,'scripts/supplemental/generation1.py'])
if returncode != 0 and returncode != 3221225477:
    print(f'Supplemental trip generation crashed unexpectedly. The return code is {returncode}')
    sys.exit(1)