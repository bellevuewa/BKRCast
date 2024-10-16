from pickle import TRUE
from tokenize import triple_quoted
import pandas as pd
import os
import sys
import datetime
import getopt
sys.path.append(os.getcwd())
import input_configuration as prj

'''
This tool is calculating person trips aggregated by origin and destination.
'''
# 10/25/2021
# modified to be compatible with python 3

# 9/18/2022
# generate Ps and As by trip purpose.

# 11/16/2023
# calculate PA (person and auto trips, all purpose only) density (trips per square mile)

def help():
    print(' This program is used to calculate daily person trip ends aggregated by origin and destination taz.')
    print(' The results are saved in an outputs/named scenario_name_daily_person_trips_by_OD.txt.')
    print(' It also calculates daily trip ends (for all purpose only) per squared mile.')    
    print(' Attention: ')    
    print('   All calculation from this tool is based on daysim output, which means the supplemental trips are EXCLUDED from this calculation.')    
    print(' Inside the output file:')
    print('    Three columns are associated with each purpose. They are production, attraction, and total trip ends for each purpose.')
    print('    for example: ')
    print('        all_prod: production of all purposes')
    print('        all_attr: attraction of all purposes')
    print('        all:      all_prod + all_attr')
    print('    others: trip ends sum of four purposes: escort, shopping, personal_biz, social')
    print('    ')
    print('python pacalculator.py -h -f <trip_filename.tsv>')
    print('    -h: help')
    print('    -f: name of a file equivalent to _trip.tsv')
    print('')

def main() :
    trip_file_name = ''
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hf:')
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-f':
            if arg == None:
                print('a trip file is missing from the command. Please use -h option for details.')
                sys.exit(2)
            trip_file_name = arg

    print('Loading trip file...')
    if trip_file_name == '':
        trips_file = os.path.join(prj.project_folder, 'outputs/daysim', '_trip.tsv')
    else:
        trips_file = os.path.join(prj.project_folder, 'outputs/daysim', trip_file_name)
    total_trips_df = pd.read_csv(trips_file, low_memory = True, sep = '\t')
    taz = pd.unique(total_trips_df[['otaz', 'dtaz']].values.ravel('K'))
    taz.sort()
    taz_df = pd.DataFrame(taz)
    taz_df.columns = ['taz']

    # open TAZ subarea file and add TAZ area
    taz_area_file = os.path.join(prj.main_inputs_folder, 'subarea_definition/TAZ_subarea.csv')
    taz_subarea_df = pd.read_csv(taz_area_file) 
    taz_df = taz_df.merge(taz_subarea_df[['BKRCastTAZ', 'Area']], left_on = 'taz', right_on = 'BKRCastTAZ', how = 'left') 
    taz_df.drop(columns = ['BKRCastTAZ'], inplace = True)       

    prod_df = total_trips_df[['otaz', 'trexpfac']].groupby('otaz').sum().reset_index()
    prod_df.rename(columns = {'trexpfac':'all_prod'}, inplace = True)
    attr_df = total_trips_df[['dtaz', 'trexpfac']].groupby('dtaz').sum().reset_index()
    attr_df.rename(columns = {'trexpfac':'all_attr'}, inplace = True)
    combined_df = pd.merge(taz_df, prod_df, left_on = 'taz', right_on = 'otaz', how = 'left') 
    combined_df = pd.merge(combined_df, attr_df, left_on = 'taz', right_on = 'dtaz', how = 'left') 
    combined_df.drop(['otaz', 'dtaz'], axis = 1, inplace = True)
    combined_df['all'] = combined_df['all_prod'] +combined_df['all_attr']

    for dpurp, dpurp_name in prj.purp_trip_dict.items():
        print(f'{dpurp_name}')
        if dpurp not in [-1, 8, 9]: # -1: all purpose, 8 and 9 are not available in BKRCast
            prod_by_purp_df = total_trips_df[['otaz', 'dpurp', 'trexpfac']].loc[total_trips_df['dpurp'] == dpurp].groupby('otaz').sum().reset_index()
            attr_by_purp_df = total_trips_df[['dtaz', 'dpurp', 'trexpfac']].loc[total_trips_df['dpurp'] == dpurp].groupby('dtaz').sum().reset_index()

            prod_by_purp_df.rename(columns = {'trexpfac': dpurp_name + '_prod'}, inplace = True)
            combined_df = pd.merge(combined_df, prod_by_purp_df, left_on = 'taz', right_on = 'otaz', how = 'left')
            combined_df.drop(['otaz', 'dpurp'], axis = 1, inplace = True)

            attr_by_purp_df.rename(columns = {'trexpfac': dpurp_name + '_attr'}, inplace = True)
            combined_df = pd.merge(combined_df, attr_by_purp_df, left_on = 'taz', right_on = 'dtaz', how = 'left')
            combined_df.drop(['dtaz', 'dpurp'], axis = 1, inplace = True)
            combined_df.fillna({dpurp_name + '_prod': 0, dpurp_name + '_attr': 0}, inplace = True)
            combined_df[dpurp_name] = combined_df[dpurp_name + '_prod'] + combined_df[dpurp_name + '_attr']

    combined_df['others'] = combined_df['escort'] + combined_df['personal_biz'] + combined_df['shopping'] + combined_df['social']
    # calculate daily person trip density for all purpose only.    
    combined_df['PA_person_all_sqmile'] = combined_df['all'] / (combined_df['Area'] / (5280 * 5280))    
    combined_df['PA_person_all_sqmile'] = combined_df['PA_person_all_sqmile'].map('{:,.4f}'.format)   

    # calculate daily auto trip density for all purpose only 
    auto_prod_df = total_trips_df[['otaz', 'mode', 'trexpfac']].loc[total_trips_df['mode'].isin([3,4,5,7,9])].groupby('otaz').sum().reset_index()
    auto_prod_df.rename(columns = {'trexpfac':'auto_all_prod'}, inplace = True)  
    combined_df = combined_df.merge(auto_prod_df, left_on = 'taz', right_on = 'otaz', how = 'left')      
    combined_df.drop(columns = ['otaz', 'mode'], inplace = True)    
    
    auto_attr_df = total_trips_df[['dtaz', 'mode', 'trexpfac']].loc[total_trips_df['mode'].isin([3,4,5,7,9])].groupby('dtaz').sum().reset_index()
    auto_attr_df.rename(columns = {'trexpfac': 'auto_all_attr'}, inplace = True) 
    combined_df = combined_df.merge(auto_attr_df, left_on = 'taz', right_on = 'dtaz', how = 'left')
    combined_df.drop(columns = ['dtaz','mode'], inplace = True)

    combined_df['auto_all'] = combined_df['auto_all_prod'] + combined_df['auto_all_attr']
    combined_df['PA_auto_all_sqmile'] = (combined_df['auto_all'] / (combined_df['Area'] / (5280 * 5280))).map('{:,.4f}'.format)  
     
    combined_df.fillna(0, inplace = True)
    outputfilename = os.path.join(prj.project_folder, 'outputs/summary', prj.scenario_name + '_' + 'daily_person_trips_by_OD.txt')

    with open(outputfilename, 'w') as output:
        output.write(str(datetime.datetime.now()) + '\n')
        output.write(trips_file + '\n')
        output.write(taz_area_file + '\n')        
        output.write('Daily person trips by origin and destination\n')
        dfstr = combined_df.to_string(index = False)
        output.write(dfstr)

    print('done')
if __name__ == '__main__':
    main()