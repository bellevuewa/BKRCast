"""Replay the household/parcel section of generation.py without writing model outputs.

Uses the local buffered parcel snapshot, whose JBLM employment is already excluded.
The unused resources column is supplied as zero because buffering omits it.
"""
import ast
import os
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
os.chdir(root)
pd.set_option('compute.use_numexpr', False)
tree = ast.parse((root / 'scripts/supplemental/generation.py').read_text())
main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
ns = dict(pd=pd, np=np, h5py=h5py, os=os)
for node in main.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        try:
            ns[node.targets[0].id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            pass

def load_parcels(path):
    frame = pd.read_csv(path, sep=r'\s+')
    frame['emprsc_p'] = 0.0
    print('parcel rows', len(frame), 'duplicate IDs', int(frame.parcelid.duplicated().sum()))
    return frame

def h5_to_df(store, group):
    return pd.DataFrame({k: np.asarray(v) for k, v in store[group].items()})

ns.update(bkr_config=SimpleNamespace(households_persons_file='inputs/popsim/hh_and_persons.h5',
                                   input_folder_for_supplemental='inputs/supplemental'),
          data_wrangling=SimpleNamespace(h5_to_df=h5_to_df,
                                        load_parcel_data_without_JBLM_jobs=load_parcels),
          parcel_file='outputs/landuse/buffered_parcels.txt', total_delivery_trips=1,
          df_psrc=pd.read_csv('inputs/supplemental/BKR_zones.csv')[['BKRCastTAZ', 'county', 'jblm', 'external']],
          df_rates=pd.read_csv('inputs/supplemental/trip_rates.csv'),
          seatac_enplanements=float(pd.read_csv('inputs/supplemental/seatac_bkr.csv').query('year == 2026').enplanements.iloc[0]),
          )
start = next(i for i, n in enumerate(main.body) if isinstance(n, ast.Assign)
             and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'hh_person')
stop = next(i for i in range(start, len(main.body))
            if any(isinstance(n, ast.Name) and n.id == 'heavy_trucks_taz' for n in ast.walk(main.body[i])))
exec(compile(ast.Module(body=main.body[start:stop], type_ignores=[]), str(root/'scripts/supplemental/generation.py'), 'exec'), ns)
ns['hh_people'].close()
actual = ns['df_taz'].set_index('BKRCastTAZ')
saved = pd.read_csv('outputs/supplemental/1_unadjusted_unbalanced.csv').set_index('BKRCastTAZ')
cols = ns['trip_productions'] + ns['trip_attractions'] + ['cvhpro', 'cvhatt', 'mtkpro', 'mtkatt', 'dtkpro', 'dtkatt', 'airport']
diff = (actual[cols] - saved[cols]).abs()
print('Replayed initial generation max zonal absolute differences:', diff.max().to_dict())
print('Replayed key totals:', actual[['hbopro', 'hspatt', 'hboatt', 'colpro']].sum().to_dict())
hh = ns['hh_df']
people = ns['person_df']
print('HH ID duplicates', int(hh.hhno.duplicated().sum()), 'person household IDs missing from households',
      int((~people.hhno.isin(hh.hhno)).sum()))
print('household parcels missing from parcel input', int((~hh.hhparcel.isin(ns['parcels']['parcel-id'])).sum()))
rates = ns['df_rates']
print('duplicate rate keys', int(rates.duplicated(['group', 'segmentation']).sum()))
gq = pd.read_csv('inputs/supplemental/group_quarters_bkr.csv').query('year == 2015')
gqr = rates.query("group == 'group_quarters'").set_index('segmentation')
for kind, share in [('dorms', 'dorm_share'), ('military', 'military_share'), ('other', 'other_share')]:
    print('group quarters type', kind, 'people', float((gq.group_quarters*gq[share]).sum()),
          'hsppro before forecast growth', float((gq.group_quarters*gq[share]).sum()*gqr.loc[kind,'hsppro']))
