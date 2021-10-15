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

def help():
    print 'This program is used to calculate person trips aggregated by origin and destination taz.'
    print 'The results are saved in an outputs/named scenario_name_daily_person_trips_by_OD.txt.'
    print 'python pacalculator.py -h'
    print '    -h: help'
    print ''

def main() :

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h')
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)

    trips_file = os.path.join(prj.project_folder, 'outputs', '_trip.tsv')
    total_trips_df = pd.read_csv(trips_file, low_memory = True, sep = '\t')
    taz = pd.unique(total_trips_df[['otaz', 'dtaz']].values.ravel('K'))
    taz.sort()
    taz_df = pd.DataFrame(taz)
    taz_df.columns = ['taz']

    prod_df = total_trips_df[['otaz', 'trexpfac']].groupby('otaz').sum().reset_index()
    prod_df.rename(columns = {'trexpfac':'trips_from'}, inplace = True)
    attr_df = total_trips_df[['dtaz', 'trexpfac']].groupby('dtaz').sum().reset_index()
    attr_df.rename(columns = {'trexpfac':'trips_to'}, inplace = True)
    combined_df = pd.merge(taz_df, prod_df, left_on = 'taz', right_on = 'otaz', how = 'left') 
    combined_df = pd.merge(combined_df, attr_df, left_on = 'taz', right_on = 'dtaz', how = 'left') 
    combined_df.drop(['otaz', 'dtaz'], axis = 1, inplace = True)
    outputfilename = os.path.join(prj.project_folder, 'outputs', prj.scenario_name + '_' + 'daily_person_trips_by_OD.txt')

    with open(outputfilename, 'w') as output:
        output.write(str(datetime.datetime.now()) + '\n')
        output.write(trips_file + '\n')
        output.write('Daily person trips by origin and destination\n')
        dfstr = combined_df.to_string()
        output.write(dfstr)

    print 'done'
if __name__ == '__main__':
    main()