"""Read-only probe of large-array arithmetic; does not run or alter model outputs."""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import numexpr as ne

parser = argparse.ArgumentParser()
parser.add_argument('--trials', type=int, default=500)
parser.add_argument('--mode', choices=['default', 'disabled', 'single'], default='default')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
if args.mode == 'disabled':
    pd.set_option('compute.use_numexpr', False)
elif args.mode == 'single':
    ne.set_num_threads(1)
print(json.dumps(dict(python=sys.version, pandas=pd.__version__, numpy=np.__version__,
                      numexpr=ne.__version__, threads=ne.get_num_threads(), mode=args.mode)), flush=True)
d = pd.read_csv(root / 'outputs/landuse/buffered_parcels.txt', sep=r'\s+',
                usecols=['empret_p', 'empfoo_p'])
retail = d.empret_p.to_numpy(copy=True)
food = d.empfoo_p.to_numpy(copy=True)
expected = retail * 3.64 + food * 3.64
start = time.monotonic()
failures = []
for i in range(args.trials):
    # The generation loop repeatedly adds zero-rate contributions after retail/food.
    actual = pd.Series(np.zeros(len(d)))
    actual = actual + d.empret_p * np.float64(3.64)
    actual = actual + d.empfoo_p * np.float64(3.64)
    for _ in range(11):
        actual = actual + d.empret_p * np.float64(0.0)
    values = actual.to_numpy()
    if not np.array_equal(values, expected):
        failure = dict(trial=i, expected_sum=float(expected.sum()),
                       actual_sum=float(values.sum()), mismatches=int(np.count_nonzero(values != expected)),
                       missing=int(np.isnan(values).sum()))
        failures.append(failure)
        print(json.dumps(failure), flush=True)
        if len(failures) >= 5:
            break
    if (i + 1) % 100 == 0:
        print('completed', i + 1, 'trials', flush=True)
print(json.dumps(dict(completed=i+1, failures=len(failures), seconds=time.monotonic()-start)), flush=True)
