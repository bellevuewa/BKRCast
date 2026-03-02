import os, sys
import pandas as pd

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import input_configuration as config

def analyze_telecommute(person_day):
    print("Analyzing telecommute data...")
    person_day['worker_type'] = 'not worker'
    person_day.loc[person_day['pwtyp'] > 0, 'worker_type'] = 'commuter'
    person_day.loc[(person_day['pwtyp']>0) & (person_day['pwpcl']==person_day['hhparcel']),'worker_type'] = 'wfh'
    person_day.loc[(person_day['pwtyp']>0) & (person_day['pwpcl']!=person_day['hhparcel']) & (person_day['wkathome']>=3),'worker_type'] = 'telecommuter'
  
    return person_day



person_day = pd.read_csv(os.path.join(config.report_output_location, '_person_day.tsv'), sep = '\t')
person = pd.read_csv(os.path.join(config.report_output_location, '_person.tsv'), sep = '\t')
household = pd.read_csv(os.path.join(config.report_output_location, '_household.tsv'), sep = '\t')
taz_subarea = pd.read_csv(os.path.join(config.main_inputs_folder, 'subarea_definition','TAZ_Subarea.csv'), sep = ',')

person = person.merge(household[['hhno', 'hhparcel', 'hhtaz']], on='hhno', how='left')
person = person.merge(taz_subarea, left_on='hhtaz', right_on='BKRCastTAZ', how='left')

regional_workers = person[['pwtyp', 'psexpfac']].groupby('pwtyp').sum().reset_index()
king_workers = person.loc[person['County'] == 'King', ['pwtyp', 'psexpfac']].groupby('pwtyp').sum().reset_index()
bkr_workers = person.loc[person['Jurisdiction'].isin(['BELLEVUE','REDMOND','KIRKLAND']), ['pwtyp', 'psexpfac']].groupby('pwtyp').sum().reset_index()
bel_workers = person.loc[person['Jurisdiction'] == 'BELLEVUE', ['pwtyp', 'psexpfac']].groupby('pwtyp').sum().reset_index()
red_workers = person.loc[person['Jurisdiction'] == 'REDMOND', ['pwtyp', 'psexpfac']].groupby('pwtyp').sum().reset_index()
kir_workers = person.loc[person['Jurisdiction'] == 'KIRKLAND', ['pwtyp', 'psexpfac']].groupby('pwtyp').sum().reset_index()
out_out_of_king_workers = person.loc[person['County'] != 'King', ['pwtyp', 'psexpfac']].groupby('pwtyp').sum().reset_index()
beldt_workers = person.loc[person['Subarea'] == 3, ['pwtyp', 'psexpfac']].groupby('pwtyp').sum().reset_index()

person_day = person_day.merge(person[['hhno', 'pno', 'pwtyp', 'pwpcl', 'hhparcel', 'hhtaz', 'County', 'Jurisdiction', 'Subarea']], on=['hhno', 'pno'], how='left')
kingc_persons_day = person_day[person_day['County'] == 'King'].copy()
bkr_person_day = person_day[person_day['Jurisdiction'].isin(['BELLEVUE','REDMOND','KIRKLAND'])].copy()
bel_person_day = person_day[person_day['Jurisdiction'] == 'BELLEVUE'].copy()
red_person_day = person_day[person_day['Jurisdiction'] == 'REDMOND'].copy()
kir_person_day = person_day[person_day['Jurisdiction'] == 'KIRKLAND'].copy()
out_of_king_person_day = person_day[person_day['County'] != 'King'].copy()
beldt_person_day = person_day[person_day['Subarea'] == 3].copy()

regional_person_day = analyze_telecommute(person_day)
kingc_persons_day = analyze_telecommute(kingc_persons_day)
out_of_king_person_day = analyze_telecommute(out_of_king_person_day)
bkr_person_day = analyze_telecommute(bkr_person_day)
bel_person_day = analyze_telecommute(bel_person_day)
red_person_day = analyze_telecommute(red_person_day)
kir_person_day = analyze_telecommute(kir_person_day)
beldt_person_day = analyze_telecommute(beldt_person_day)


with pd.ExcelWriter(os.path.join(config.report_output_location, 'telecommute_analysis.xlsx')) as writer:
    regional_workers.to_excel(writer, sheet_name='regional_workers')
    start = regional_workers.shape[0] + 3
    person_day['worker_type'].value_counts().to_excel(writer, startrow = start, sheet_name='regional_workers')
 
    king_workers.to_excel(writer, sheet_name='king_workers')
    start = king_workers.shape[0] + 3
    kingc_persons_day['worker_type'].value_counts().to_excel(writer, startrow = start, sheet_name='king_workers')

    out_out_of_king_workers.to_excel(writer, sheet_name='out_of_king_workers')
    start = out_out_of_king_workers.shape[0] + 3
    out_of_king_person_day['worker_type'].value_counts().to_excel(writer, startrow = start, sheet_name='out_of_king_workers')

    bkr_workers.to_excel(writer, sheet_name='bkr_workers')
    start = bkr_workers.shape[0] + 3    
    bkr_person_day['worker_type'].value_counts().to_excel(writer, startrow = start, sheet_name='bkr_workers')

    bel_workers.to_excel(writer, sheet_name='bel_workers')
    start = bel_workers.shape[0] + 3
    bel_person_day['worker_type'].value_counts().to_excel(writer, startrow = start, sheet_name='bel_workers')

    beldt_workers.to_excel(writer, sheet_name='beldt_workers')
    start = beldt_workers.shape[0] + 3  
    beldt_person_day['worker_type'].value_counts().to_excel(writer, startrow = start, sheet_name='beldt_workers')

    red_workers.to_excel(writer, sheet_name='red_workers')
    start = red_workers.shape[0] + 3
    red_person_day['worker_type'].value_counts().to_excel(writer, startrow = start, sheet_name='red_workers')

    kir_workers.to_excel(writer, sheet_name='kirk_workers')
    start = kir_workers.shape[0] + 3
    kir_person_day['worker_type'].value_counts().to_excel(writer, startrow = start, sheet_name='kirk_workers')

print('Done')