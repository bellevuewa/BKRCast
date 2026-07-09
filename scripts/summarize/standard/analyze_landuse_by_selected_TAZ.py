import pandas as pd
import numpy as np
import os, sys
import datetime
import h5py
import getopt
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import input_configuration as prj
import data_wrangling as utility


def help():
    print('Pull land use data related to the tazs defined in an external file.')
    print('Data are saved in an external excel spreadsheet, located in outputs/landuse/')
    print('')
    print('analyze_landuse_by_selected_TAZ.py -h -i <input file name with absolute path> -o <output file name with relative path>')
    print(' -h: help')
    print(' -i: input file (absolute filepath) for defined TAZ list. Only one column inside this file with the attribute "TAZ". ')
    print(' -o: output file name (relative path). The file is output to outputs/landuse folder. The default name is land_use_analysis_by_selected_taz.xlsx')

def main():

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hi:o:')
        if not opts:
            help()
            exit(2)

    except getopt.GetoptError:
        help()
        sys.exit(2)
 
    output_file = os.path.join(prj.report_lu_output_location, 'land_use_analysis_by_selected_taz.xlsx' )
   
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-o':
            output_file = os.path.join(prj.project_folder, 'outputs', arg)
        elif opt == '-i':
            customized_file = arg 
        else:
            print('Wrong option.')
            help()
            exit(0)



    print('loading...')
    tazlist_df = pd.read_csv(customized_file)

    parcels_df = pd.read_csv(os.path.join(prj.parcels_file_folder, 'parcels_urbansim.txt'), sep = ' ', low_memory = False )
    selected_parcels_df = parcels_df.loc[parcels_df['TAZ_P'].isin(tazlist_df['TAZ'])]

    # synthetic population from hh_and_persons.h5
    hdf_file = h5py.File(os.path.join(prj.project_folder, prj.households_persons_file), "r")
    person_df = utility.h5_to_df(hdf_file, 'Person')
    hh_df = utility.h5_to_df(hdf_file, 'Household')

    selected_hhs_df = hh_df.loc[hh_df['hhtaz'].isin(tazlist_df['TAZ'])]
    selected_persons_df = person_df.loc[person_df['hhno'].isin(selected_hhs_df['hhno'])]

    # sysnthetic population from daysim outputs _household.tsv and _person.tsv.
    hhs_daysim_df = pd.read_csv(os.path.join(prj.report_output_location, '_household.tsv'), sep = '\t')
    persons_daysim_df = pd.read_csv(os.path.join(prj.report_output_location, '_person.tsv'), sep = '\t')
    selected_hhs_daysim_df = hhs_daysim_df.loc[hhs_daysim_df['hhtaz'].isin(tazlist_df['TAZ'])]
    selected_persons_daysim_df = persons_daysim_df.loc[persons_daysim_df['hhno'].isin(selected_hhs_daysim_df['hhno'])]

    # workers coming to work in the selected tazs
    persons_work_in_selected_taz_df = persons_daysim_df.loc[persons_daysim_df['pwtaz'].isin(tazlist_df['TAZ'])]
    hhs_list = persons_work_in_selected_taz_df['hhno'].unique()
    hhs_work_in_selected_taz_df = hhs_daysim_df.loc[hhs_daysim_df['hhno'].isin(hhs_list)]
    persons_work_in_selected_taz_df = persons_work_in_selected_taz_df.merge(hhs_work_in_selected_taz_df[['hhno', 'hhtaz']], on = 'hhno')
    workers_by_hhtaz_df = persons_work_in_selected_taz_df[['hhtaz', 'psexpfac']].groupby('hhtaz').sum().reset_index()

    with pd.ExcelWriter(output_file, engine = 'xlsxwriter') as writer:
        # write readme tab        
        wksheet = writer.book.add_worksheet('readme')
        wksheet.write(0, 0, str(datetime.datetime.now())) 
        wksheet.write(1, 0, 'model folder')
        wksheet.write(1, 1, prj.project_folder)
        wksheet.write(2, 0, 'taz file')
        wksheet.write(2, 1, os.path.join(prj.project_folder, customized_file))

        selected_parcels_df.to_excel(writer, sheet_name = 'parcels', index = False) 
        selected_hhs_df.to_excel(writer, sheet_name = 'res_hhs', index = False)
        selected_persons_df.to_excel(writer, sheet_name = 'res_persons', index = False)
        selected_hhs_daysim_df.to_excel(writer, sheet_name = 'res_hhs_daysim', index = False)
        selected_persons_daysim_df.to_excel(writer, sheet_name = 'res_persons_daysim', index = False)
        persons_work_in_selected_taz_df.to_excel(writer, sheet_name = 'workers_to_tazs', index = False)
        hhs_work_in_selected_taz_df.to_excel(writer, sheet_name = 'workers_Hhs', index = False)
        workers_by_hhtaz_df.to_excel(writer, sheet_name = 'workers_by_hhtaz', index = False)
          
    print(f'Output file: {output_file}')
    print('Done')


if __name__ == '__main__':
    logger, start_time = utility.open_main_logger('Data Processing')
    logger.info(f"Running script: {os.path.basename(__file__)} %s", " ".join(sys.argv[1:]))
    main()
    end_time = datetime.datetime.now()
    elapsed_total = end_time - start_time
    logger.info(f'Total run time: {elapsed_total}')