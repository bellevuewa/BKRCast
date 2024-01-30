from decimal import ROUND_CEILING, ROUND_UP
from xmlrpc.client import DateTime
import pandas as pd
import numpy as np
import os
import sys
import datetime
import getopt
sys.path.append(os.getcwd())
import input_configuration as prj


daysim_hhs_output_file = '_household.tsv'
daysim_persons_output_file = '_person.tsv'

  
def summarize_hhs(output_file, customized_location_file = ''):
    hhs_df = pd.read_csv(os.path.join(prj.project_folder,  prj.report_output_location, daysim_hhs_output_file), sep = '\t')
    taz_subarea_df = pd.read_csv(os.path.join(prj.main_inputs_folder, 'subarea_definition', 'TAZ_subarea.csv'))
    hhs_df = pd.merge(hhs_df, taz_subarea_df, left_on = 'hhtaz', right_on = 'BKRCastTAZ', how = 'left')
    hh_summary_list = ['hhexpfac', 'hhsize', 'hhvehs', 'hhwkrs', 'hhftw', 'hhptw', 'hhwhome','hhret', 'hhoad', 'hhuni', 'hhhsc', 'hh515', 'hhcu5']
    # for unknow reason, hhwkrs is negative. so need to recalculate the total workers of each household
    hhs_df['hhwkrs'] = hhs_df['hhftw'] + hhs_df['hhptw']
    
    persons_df = pd.read_csv(os.path.join(prj.project_folder, prj.report_output_location, daysim_persons_output_file), sep = '\t')
    persons_df = pd.merge(persons_df, hhs_df[['hhno', 'hhparcel']], on = 'hhno', how = 'left')
    work_at_home_df = persons_df.query('pwpcl == hhparcel').groupby('hhno')[['psexpfac']].sum()
    work_at_home_df.rename(columns = {'psexpfac':'hhwhome'}, inplace = True)
    hhs_df = pd.merge(hhs_df, work_at_home_df, on = 'hhno', how = 'left')

    hhs_by_taz_df = hhs_df.groupby('hhtaz')[hh_summary_list].sum()
    hhs_by_subarea_df = hhs_df.groupby('Subarea')[hh_summary_list].sum()
    hhs_by_jurisdiction_df = hhs_df.groupby('Jurisdiction')[hh_summary_list].sum()

        

    # calculate average household size    
    hhs_by_jurisdiction_df['avg_hhsize'] = (hhs_by_jurisdiction_df['hhsize'] / hhs_by_jurisdiction_df['hhexpfac']).round(2)
    hhs_by_subarea_df['avg_hhsize'] = (hhs_by_subarea_df['hhsize'] / hhs_by_subarea_df['hhexpfac']).round(2)
    hhs_by_taz_df['avg_hhsize'] = (hhs_by_taz_df['hhsize'] / hhs_by_taz_df['hhexpfac']).round(2)

    hhs_by_restype_df = hhs_df.groupby('hrestype')[['hhexpfac']].sum()
    
    if customized_location_file != '':
        customized_tazs = pd.read_csv(customized_location_file)
        customized_hhs_df = pd.merge(hhs_df, customized_tazs, left_on = 'hhtaz', right_on = 'TAZ', how = 'inner')
        cust_hhs_by_subarea_df = customized_hhs_df[hh_summary_list].sum()
        cust_hhs_by_restype_df = customized_hhs_df.groupby('hrestype')[['hhexpfac']].sum()

    with open(os.path.join(prj.project_folder, prj.report_lu_output_location, output_file), 'w') as f:
        f.write('%s\n' % str(datetime.datetime.now()))   
        f.write('%s\n' % prj.project_folder)
        f.write('    %s\n' % daysim_hhs_output_file)
        f.write('    %s\n' % daysim_persons_output_file)
        f.write('\n\n')
        
        if customized_location_file != '': 
            f.write('Households by Customized Locations\n') 
            f.write('%s\n\n' % customized_location_file)
            dfstring = cust_hhs_by_subarea_df.to_string()
            f.write('%s\n\n' % dfstring)       
            f.write(f'Households by Residence Type\n')
            dfstring = cust_hhs_by_restype_df.to_string()
            f.write(f'{dfstring}\n')

        f.write('Households by Jurisdiction\n') 
        dfstring = hhs_by_jurisdiction_df.to_string()
        f.write('%s\n\n' % dfstring)

        f.write('Households by Residence Type\n')
        dfstring = hhs_by_restype_df.to_string()
        f.write(f'{dfstring}\n')

        f.write('Households by Subarea\n') 
        dfstring = hhs_by_subarea_df.to_string()
        f.write('%s\n\n' % dfstring)

        f.write('Households by TAZ\n') 
        dfstring = hhs_by_taz_df.to_string()
        f.write('%s\n\n' % dfstring)


def summarize_persons(output_file, customized_location_file):
    persons_df = pd.read_csv(os.path.join(prj.project_folder, prj.report_output_location, daysim_persons_output_file), sep = '\t')
    hhs_df = pd.read_csv(os.path.join(prj.project_folder,  prj.report_output_location, daysim_hhs_output_file), sep = '\t')
    taz_subarea_df = pd.read_csv(os.path.join(prj.main_inputs_folder, 'subarea_definition', 'TAZ_subarea.csv'))
    persons_df = pd.merge(persons_df, hhs_df[['hhno', 'hhtaz', 'hhparcel']], on = 'hhno', how = 'left')
    persons_df = pd.merge(persons_df, taz_subarea_df[['BKRCastTAZ', 'Subarea', 'PMA_ID', 'Jurisdiction']]   , left_on = 'hhtaz', right_on = 'BKRCastTAZ', how = 'left')
    bellevue_persons_df = persons_df.loc[persons_df['Jurisdiction'] == 'BELLEVUE']
    if customized_location_file != '':
        customized_tazs = pd.read_csv(customized_location_file)
        customized_persons_df = pd.merge(persons_df, customized_tazs, left_on = 'hhtaz', right_on = 'TAZ', how = 'inner')

    output_file = os.path.join(prj.project_folder, prj.report_lu_output_location, output_file)
    with open(output_file, 'w') as f:
        f.write('%s\n' % str(datetime.datetime.now()))   
        f.write('%s\n' % prj.project_folder)
        f.write('    %s\n' % daysim_hhs_output_file)
        f.write('    %s\n' % daysim_persons_output_file)
        f.write('\n\n')  
        f.write('******************** below is population characteristics in the customized locations**********************\n')
        f.write('customized location: %s\n' % customized_location_file)

    ## customized locations is an addition.
    if customized_location_file != '':
        process_person_type(customized_persons_df, output_file, 'a')
        process_person_gender(customized_persons_df, output_file, 'a')
        process_person_age(customized_persons_df, output_file, 'a')
        process_worker_types(customized_persons_df, output_file, 'a')
        process_workplace_taz(customized_persons_df, output_file, 'a')
        process_student_type(customized_persons_df, output_file, 'a')
        process_school_taz(customized_persons_df, output_file, 'a')

    
    with open(output_file, 'a') as f:
        f.write('******************** population characteristics in the PSRC region **********************\n')
    process_person_type(persons_df, output_file, 'a')
    process_person_gender(persons_df, output_file, 'a')
    process_person_age(persons_df, output_file, 'a')
    process_worker_types(persons_df, output_file, 'a')
    process_workplace_taz(persons_df, output_file, 'a')
    process_student_type(persons_df, output_file, 'a')
    process_school_taz(persons_df, output_file, 'a')

    with open(output_file, 'a') as f:
        f.write('******************** population characteristics in Bellevue **********************\n')
    process_person_type(bellevue_persons_df, output_file, 'a')
    process_person_gender(bellevue_persons_df, output_file, 'a')
    process_person_age(bellevue_persons_df, output_file, 'a')
    process_worker_types(bellevue_persons_df, output_file, 'a')
    process_workplace_taz(bellevue_persons_df, output_file, 'a')
    process_student_type(bellevue_persons_df, output_file, 'a')
    process_school_taz(bellevue_persons_df, output_file, 'a')


def process_student_type(persons_df, export_file, mode):
    ps_df = persons_df.groupby('pstyp')[['psexpfac']].sum()
    pstype = {0: 'non-student', 1: 'FT student', 2: 'PT student'}
    pstyp_df = pd.DataFrame(list(pstype.items()), columns = ['pstyp', 'student_type'])
    ps_df = pd.merge(ps_df, pstyp_df, on = 'pstyp', how = 'left')
    with open(export_file, mode) as f:
        f.write('Student Type\n')
        dfstring = ps_df[['pstyp', 'student_type', 'psexpfac']].to_string()
        f.write('%s\n' % dfstring)
        f.write('\n\n')
    
def process_school_taz(persons_df, export_file, mode):
    school_df = persons_df.groupby('pstaz')[['psexpfac']].sum()
    with open(export_file, mode) as f:
        f.write('School Locations by TAZ\n')
        dfstring = school_df.to_string()
        f.write('%s\n' % dfstring)
        f.write('\n\n')

def process_workplace_taz(persons_df, export_file, mode):
    workplace_df = persons_df.groupby('pwtaz')[['psexpfac']].sum()
    work_at_home_df = persons_df.query('pwpcl == hhparcel')[['psexpfac']].sum()
    with open(export_file, mode) as f:
        f.write('Number of workers always working at home\n')
        dfstring = work_at_home_df.to_string()
        f.write('%s\n' % dfstring)
        f.write('\n\n')

        f.write('Workplace by TAZ\n')
        dfstring = workplace_df.to_string()
        f.write('%s\n' % dfstring)
        f.write('\n\n')

def process_worker_types(persons_df, export_file, mode):
    pw_df = persons_df.groupby('pwtyp')[['psexpfac']].sum()
    pwtype = {0: 'non-worker', 1: 'FT worker', 2: 'PT worker'}
    pwtyp_df = pd.DataFrame(list(pwtype.items()), columns = ['pwtyp', 'work_type'])
    pw_df = pd.merge(pw_df, pwtyp_df, on = 'pwtyp', how = 'left')
    with open(export_file, mode) as f:
        f.write('Worker Type\n')
        dfstring = pw_df[['pwtyp', 'work_type', 'psexpfac']].to_string()
        f.write('%s\n' % dfstring)
        f.write('\n\n')

def process_person_age(persons_df, export_file, mode):
    persons_df_copy = persons_df.copy()
    persons_df_copy['agecode'] = (persons_df_copy['pagey'] / 10.0)
    persons_df_copy['agecode'] = persons_df_copy['agecode'].apply(np.floor).astype(int)
    age_df = persons_df_copy.groupby('agecode')[['psexpfac']].sum()
    ages = {0: '<10', 1: '11-20', 2:'21-30', 3:'31-40', 4:'41-50', 5:'51-60', 6:'61-70', 7:'71-80', 8: '81-90', 9:'91-100', 10:'>100'}
    agecode_df = pd.DataFrame(list(ages.items()), columns = ['agecode', 'ages'])
    age_df = pd.merge(age_df, agecode_df, on = 'agecode', how = 'left')
    with open(export_file, mode) as f:
        f.write('Person Age\n')
        dfstring = age_df[['agecode', 'ages', 'psexpfac']].to_string()
        f.write('%s\n' % dfstring)
        f.write('\n\n')               

def process_person_gender(persons_df, export_file, mode):
    pgender_df = persons_df.groupby('pgend')[['psexpfac']].sum() 
    genderType = {1: 'M', 2: 'F', 9: 'N/A'}
    gender_df = pd.DataFrame(list(genderType.items()), columns = ['pgend', 'pgend_dscr'])
    pgender_df = pd.merge(pgender_df, gender_df, on = 'pgend', how = 'left')
    with open(export_file, mode) as f:
        f.write('Person Gender\n')
        dfstring = pgender_df[['pgend', 'pgend_dscr', 'psexpfac']].to_string()
        f.write('%s\n' % dfstring)
        f.write('\n\n')


def process_person_type(persons_df, export_file, mode):
    pptype_df = persons_df.groupby('pptyp')[['psexpfac']].sum()
    pptype = {1: 'FT worker', 2: 'PT worker', 3: 'non-worker age 65+', 4: 'other non-worker adult', 5: 'University Student', 6: 'Grade Student age 16+', 7: 'Child age 5-15', 8: 'Child age 0-4'}
    ppd = pd.DataFrame(list(pptype.items()), columns = ['pptyp', 'pptyp_dscr'])
    pptype_df = pd.merge(pptype_df, ppd, on = 'pptyp')
    
    with open(export_file, mode) as f:
        f.write('Person Type\n')
        dfstring = pptype_df[['pptyp', 'pptyp_dscr', 'psexpfac']].to_string()
        f.write('%s\n' % dfstring)
        f.write('\n\n')
        

def help():
    print('Summarize demographic information (household and person) in standard locations and customized locations using finalized synthetic population')
    print('output from daysim.')
    print('summarize_daysim_hhs_and_persons.py -h -f <file name> -m <subarea code> SubareaName')
    print('   -h: help')
    print('   -f: customized location file path. It should have only one column named BKRCastTAZ')
    print('   -m: subarea code (1-14)')
    print('   SubareaName:')
    print('         BelDT')
    print('         Redmond')
    print('         Kirkland\n')
    print('Household summary always includes jurisdiction, subarea and TAZ level report. If any option is used, it is an addition to the household summary report.')
    print('Person summary only includes regional and Bellevue, plus customized location if it is specified in the option.')

def main():
    subarea_code = -1
    customized_location_file = ''
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hf:m:')
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-m':
            subarea_code = int(arg)
            customized_location_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'Bellevue_MMA_' + str(subarea_code) + '.txt')
        elif opt == '-f':
            customized_location_file = arg

    for arg in args:
        if arg == 'Region':
            customized_location_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'Regional.txt')
            break
        elif arg =='Bellevue':
            customized_location_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'Bellevue_TAZ.txt')
            break
        elif arg == 'BelDT':
            customized_location_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'BellevueDTTAZ.txt')
            break
        elif arg == 'Redmond':
            customized_location_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'Redmond_TAZ.txt')
            break
        else:
            print('invalid argument. Use -h for help.')
            sys.exit(2)

    output_hhs_summary_file = 'daysim_households_summary.txt'
    output_persons_summary_file = 'daysim_persons_summary.txt'

    summarize_hhs(output_hhs_summary_file, customized_location_file)
    summarize_persons(output_persons_summary_file, customized_location_file)

 
    print('Done')

if __name__ == '__main__':
    main()