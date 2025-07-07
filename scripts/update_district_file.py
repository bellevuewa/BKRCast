import os
import pandas as pd

from input_configuration import districtfile

"""This script is to let the district file be consistent with the TAZ data in the subarea_definition folder
"""
# read files
district_file = pd.read_csv(districtfile)
taz_bkr = pd.read_csv(os.path.join('inputs', 'subarea_definition', 'BKR_only_TAZ.txt'))

# update district file
district_file.rename(columns={'Region': 'Region_old'}, inplace=True)
district_file['Region'] = district_file['Region_old']
district_file.loc[district_file['Region']=='BKR', 'Region'] = 'BKR Fringe'

district_file.loc[district_file['TAZ'].isin(taz_bkr['TAZ']), 'Region'] = 'BKR'

# export the updated district file
district_file.to_csv(districtfile, index=False)
