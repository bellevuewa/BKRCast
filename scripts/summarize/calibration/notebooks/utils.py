from input_configuration import *
from IPython.display import display, Javascript

import pandas as pd


survey_year = 2014
if base_year in ['2023', '2024']:
    survey_year = '2023'

def copy_to_clipboard(df):
    df.to_clipboard(index=True)
    display(Javascript('alert("Copied to clipboard!")'))


def get_data(data1, data2, data3, taz_subarea, if_region=True):
    fname_tail = ''
    if not if_region:
        fname_tail = '_BKR'
        taz_bkr = taz_subarea[taz_subarea['Jurisdiction'].isin(['BELLEVUE', 'KIRKLAND', 'REDMOND', 'Bellevue'])]['TAZ'].unique()
        data2.pop('PersonDay')
        data2.pop('Tour')
        data2.pop('Trip')
        # merge hhtaz to all tables
        for key in ['Person', 'Trip', 'Tour', 'PersonDay']:
            data1[key] = pd.merge(data1[key], data1['Household'][['hhno', 'hhtaz']], on='hhno', how='left')
            if key == 'Trip':
                data2[f'{key}_cloned'] = pd.merge(data2[f'{key}_cloned'], data2['Household'][['hhno', 'hhtaz']], on='hhno', how='left')
                data3[key] = pd.merge(data3[key], data3['Household'][['hhno', 'hhtaz']], on='hhno', how='left')
            elif key == 'Tour' or key == 'PersonDay':
                data2[f'{key}_cloned'] = pd.merge(data2[f'{key}_cloned'], data2['Household'][['hhno', 'hhtaz']], on='hhno', how='left')
            else:
                data2[key] = pd.merge(data2[key], data2['Household'][['hhno', 'hhtaz']], on='hhno', how='left')
                data3[key] = pd.merge(data3[key], data3['Household'][['hhno', 'hhtaz']], on='hhno', how='left')
        # retain records in BKR only
        for data in [data1, data2, data3]:
            for key in data.keys():
                if key == 'HouseholdDay': continue
                data[key] = data[key][data[key]['hhtaz'].isin(taz_bkr)].copy(deep=True)
    
    return fname_tail, data1, data2, data3


def get_subarea(_data, taz_subarea, taz_colname='hhtaz'):
    data = _data.copy(deep=True)    
    data = data.merge(taz_subarea[['TAZ', 'DistrictFlowName']], 
                      left_on=taz_colname, right_on='TAZ', how='left')
    return data