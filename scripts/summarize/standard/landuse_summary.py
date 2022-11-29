import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import pandas as pd
import numpy as np
import h5py
import getopt
import datetime
import input_configuration as prj
import accessibility.accessibility_configuration as access_config
import data_wrangling as utility




def parcel_file_summary(writer, Output_Field, taz_subarea, parcels):
    print("Summarizing parcel file...")
    parcels = parcels.merge(taz_subarea, how = 'left',  left_on = 'TAZ_P', right_on = 'BKRCastTAZ')
    summary_by_jurisdiction = parcels.groupby('Jurisdiction')[Output_Field].sum()
    summary_by_jurisdiction.to_excel(writer, sheet_name = 'LU_sum_juris')

    summary_by_taz = parcels.groupby('TAZ_P')[Output_Field].sum()
    summary_by_taz.to_excel(writer, sheet_name = 'LU_sum_TAZ')

    summary_by_subarea = parcels[parcels['Subarea'] > 0].groupby('Subarea')[Output_Field].sum()
    taz_subarea = parcels[['Subarea', 'SubareaName']].drop_duplicates()
    taz_subarea.set_index('Subarea', inplace = True)
    summary_by_subarea = pd.merge(summary_by_subarea, taz_subarea[['SubareaName']], left_index = True, right_index = True, how = 'left')
    summary_by_subarea.to_excel(writer, sheet_name = 'LU_sum_subarea')

def synthetic_population_summary(writer, taz_subarea, lookup_parcels_df, export_parcel_level_dataset = False):
    print('Summarizing synthetic population file...')   
    hdf_file = h5py.File(os.path.join(prj.project_folder, prj.households_persons_file), "r")
    person_df = utility.h5_to_df(hdf_file, 'Person')
    hh_df = utility.h5_to_df(hdf_file, 'Household')
    hdf_file.close()

    hh_taz = hh_df.merge(taz_subarea, left_on = 'hhtaz', right_on = 'BKRCastTAZ', how = 'left')
    hh_taz['total_persons'] = hh_taz['hhexpfac'] * hh_taz['hhsize']
    hh_taz['total_hhs'] = hh_taz['hhexpfac']

    summary_by_jurisdiction = hh_taz.groupby('Jurisdiction')[['total_hhs', 'total_persons']].sum()   
    summary_by_mma = hh_taz.groupby('Subarea')[['total_hhs', 'total_persons']].sum()
    summary_by_parcels = hh_taz.groupby('hhparcel')[['total_hhs', 'total_persons']].sum()

    taz_subarea.reset_index()
    subarea_def = taz_subarea[['Subarea', 'SubareaName']]
    subarea_def = subarea_def.drop_duplicates(keep = 'first')
    subarea_def.set_index('Subarea', inplace = True)
    summary_by_mma = summary_by_mma.join(subarea_def)
    summary_by_taz = hh_taz.groupby('hhtaz')[['total_hhs', 'total_persons']].sum()


    summary_by_jurisdiction.to_excel(writer, sheet_name = 'popsim_sum_juris')
    summary_by_mma.to_excel(writer, sheet_name = 'popsim_sum_mma')
    summary_by_taz.to_excel(writer, sheet_name = 'popsim_sum_taz')
    
    hh_taz = hh_taz.merge(lookup_parcels_df, how = 'left', left_on = 'hhparcel', right_on = 'PSRC_ID')
    summary_by_geoid10 = hh_taz.groupby('GEOID10')[['total_hhs', 'total_persons']].sum()
    summary_by_geoid10.to_excel(writer, sheet_name = 'popsim_sum_geoid10')

    print('exporting summary by parcel...')   # too big for xlsx file
    summary_by_parcels.to_csv(os.path.join(prj.report_summary_output_location, 'hh_summary_by_parcel.csv'), header = True)
    

    if export_parcel_level_dataset == True:
        print('exporting households and persons by parcel...')
        hh_df.to_csv(os.path.join(prj.report_summary_output_location, 'households.csv'), header = True)
        person_df.to_csv(os.path.join(prj.report_summary_output_location, 'persons.csv'), header = True)

def daysim_popsim_summary():
    daysim_hhs_df = pd.read_csv(os.path.join(prj.report_output_location, '_household.tsv'), low_memory = True, sep = '\t')
    daysim_prs_df = pd.read_csv(os.path.join(prj.report_output_location, '_person.tsv'), low_memory = True, sep = '\t')
    writer = pd.ExcelWriter(os.path.join(prj.report_summary_output_location, "daysim_hhs_summary_report.xlsx"), engine = 'xlsxwriter')

def help():
    print('Summarize number of jobs by category and jurisdiction, subarea, and BKRCastTAZ; summarize number of households and persons')
    print('by jurisdiction, subarea, BKRCastTAZ, and census block group. The outputs are exported to land_use_summary_report.xlsx. ')
    print('\n')
    print('    landuse_summary.py -hp\n')
    print('      -h: help')
    print('      -p: export households and persons to csv file.')
    print('\n')

def main():
    export_parcel_level_dataset = False    

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hp')
    except getopt.GetoptError:
        help()
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-p':
            export_parcel_level_dataset = True    
    
    # add summary of daysim calculated synthetic population by jurisdiction.    
    #for arg in args:
    
    Output_Field = ['EMPEDU_P', 'EMPFOO_P', 'EMPGOV_P', 'EMPIND_P', 'EMPMED_P', 'EMPOFC_P', 'EMPOTH_P', 'EMPRET_P', 'EMPSVC_P', 'EMPTOT_P', 'STUGRD_P', 'STUHGH_P', 'STUUNI_P', 'HH_P']
    writer = pd.ExcelWriter(os.path.join(prj.report_summary_output_location, "land_use_summary_report.xlsx"), engine = 'xlsxwriter')
    wksheet = writer.book.add_worksheet('readme')
    wksheet.write(0, 0, str(datetime.datetime.now()))
    wksheet.write(1, 0, 'model folder')
    wksheet.write(1, 1, prj.project_folder)
    wksheet.write(2, 0, 'parcel file')
    wksheet.write(2, 1, prj.parcels_file_folder)

    taz_subarea = pd.read_csv(os.path.join(prj.main_inputs_folder, 'model','TAZ_Subarea.csv'), sep = ',')
    parcels_df = pd.read_csv(os.path.join(prj.parcels_file_folder, access_config.parcels_file_name), sep = ' ')
    lookup_parcels_df = pd.read_csv(os.path.join(prj.main_inputs_folder, 'model', 'parcel_TAZ_2014_lookup.csv'), low_memory = False)

    parcel_file_summary(writer, Output_Field, taz_subarea, parcels_df)
    synthetic_population_summary(writer, taz_subarea, lookup_parcels_df, export_parcel_level_dataset)

    writer.save()
    print('Done')

if __name__ == '__main__':
    main()