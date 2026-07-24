from input_configuration import *
from IPython.display import display, Javascript

import pandas as pd


survey_year = 2014
if int(base_year) >= 2023:
    survey_year = '2023'

def copy_to_clipboard(df):
    df.to_clipboard(index=True)
    display(Javascript('alert("Copied to clipboard!")'))


def get_data(data1, data2, data3, taz_subarea, if_region=True):
    """Get data in the whole region or in the BKR area."""
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


def get_data_outbkr(data1, data2, data3, taz_subarea):
    """Get data only households outside the BKR area."""
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
            data[key] = data[key][~data[key]['hhtaz'].isin(taz_bkr)].copy(deep=True)
    
    return data1, data2, data3


def get_subarea(_data, taz_subarea, taz_colname='hhtaz', subarea_colname='DistrictFlowName'):
    data = _data.copy(deep=True)    
    data = data.merge(taz_subarea[['TAZ', subarea_colname]], 
                      left_on=taz_colname, right_on='TAZ', how='left')
    return data


def get_districtflowname(_data, taz_subarea, taz_colname='hhtaz', new_colname='DistrictFlowName'):
    data = _data.copy(deep=True)    
    data = data.merge(taz_subarea[['TAZ', 'DistrictFlowName']], 
                      left_on=taz_colname, right_on='TAZ', how='left')
    data = data.rename(columns={'DistrictFlowName': new_colname})
    if 'TAZ_x' in data.columns:
        data = data.drop(columns=['TAZ_x'])
    if 'TAZ_y' in data.columns:
        data = data.drop(columns=['TAZ_y'])
    return data


def get_homebased_tag(df, tag_colname='hb_tag'):
    # put HBO, HBW, NHB tags
    df[tag_colname] = ''

    # NHB
    condition = (df['oadtyp'] != 'Home') & (df['dadtyp'] != 'Home')
    df.loc[condition, tag_colname] = 'NHB'

    # HBW
    condition = ((df['oadtyp'] == 'Home') & (df['dadtyp'] == 'Usual Workplace')) | \
                ((df['oadtyp'] == 'Usual Workplace') & (df['dadtyp'] == 'Home'))
    df.loc[condition, tag_colname] = 'HBW'

    # HBO
    condition = ((df['oadtyp'] == 'Home') & (~df['dadtyp'].isin(['Home', 'Usual Workplace', 'Usual School']))) | \
                ((~df['oadtyp'].isin(['Home', 'Usual Workplace', 'Usual School'])) & (df['dadtyp'] == 'Home'))
    df.loc[condition, tag_colname] = 'HBO'

    # HBS
    condition = ((df['oadtyp'] == 'Home') & (df['dadtyp'] == 'Usual School')) | \
                ((df['oadtyp'] == 'Usual School') & (df['dadtyp'] == 'Home'))
    df.loc[condition, tag_colname] = 'HBS'
    return df


def get_telecommute(person_day):
    person_day['worker_type'] = 'Not Worker'
    person_day.loc[person_day['pwtyp']!='Not a Paid Worker', 'worker_type'] = 'Commuter'
    person_day.loc[(person_day['pwtyp']!='Not a Paid Worker') & (person_day['pwpcl']==person_day['hhparcel']),'worker_type'] = 'WFH'
    person_day.loc[(person_day['pwtyp']!='Not a Paid Worker') & (person_day['pwpcl']!=person_day['hhparcel']) & (person_day['wkathome']>=3),'worker_type'] = 'Telecommuter'
    return person_day