import pandas as pd
import os, sys
import datetime
import getopt
sys.path.append(os.getcwd())
import input_configuration as prj

'''
    I developed this tool with intention to calculate modeled average vehicle occupancy. However, I found the AVO of HOV2 is less than 2 and AVO of
    HOV3+ is less than 3. Ben and Mark of RSG confirmed that AVO is not explicitly modeled in Daysim. There is no vehicle level accounting in the system to 
    make sure HOV2 has only two people and HOV3+ has more than 3 people. Therefore, this tool is no longer useful, and we should not calculate modeled AVO.
    9/29/2021. 
'''
# 10/25/2021
# modified to be compatible with python 3

def select_trips_by_time(total_trips_df, start_time= None, end_time = None):
    if (start_time == 0 and end_time == 0):
        selected_trips_df = total_trips_df
    elif start_time <= end_time:
        selected_trips_df = total_trips_df.loc[(total_trips_df['deptm'] >= start_time) & (total_trips_df['deptm'] < end_time)]
    else: # night period
        selected_trips_df = total_trips_df.loc[((total_trips_df['deptm'] >= start_time) & (total_trips_df['deptm'] < 1440)) | ((total_trips_df['deptm'] >= 0) & (total_trips_df['deptm'] < end_time))]
    return selected_trips_df

def select_trips_by_subarea(trips_df, subarea_taz_df, trips_from_only, trips_end_only):
    if subarea_taz_df.empty == False:
        if trips_from_only == True:
            from_subarea_trips_df = trips_df.merge(subarea_taz_df, left_on = 'otaz', right_on = 'TAZ', how = 'inner')
        if trips_end_only == True:
            to_subarea_trips_df = trips_df.merge(subarea_taz_df, left_on = 'dtaz', right_on = 'TAZ', how = 'inner')
        if ((trips_from_only == True) and (trips_end_only == True)):
            subarea_trips_df = from_subarea_trips_df.merge(subarea_taz_df, left_on = 'dtaz', right_on = 'TAZ')
        elif trips_from_only == True:
            subarea_trips_df = pd.concat([from_subarea_trips_df])
        else:
            subarea_trips_df = pd.concat([to_subarea_trips_df])
    else:
        print('No subarea is defined. Use the whole trip table.')
        subarea_trips_df = trips_df
    return subarea_trips_df

def get_time_period_by_minutes(period):
    # start_time and end_time are number of minutes from midnight.
    if period == 'daily':
        start_time = 0
        end_time= 0
    elif period == 'pm':
        start_time = 930
        end_time = 1110
    elif period == 'am':
        start_time = 360
        end_time = 540
    elif period == 'md':
        start_time = 540
        end_time = 930
    elif period == 'ni':
        start_time = 1110
        end_time = 360
    else:
        print('period ' + period + ' is invalid.')
        exit()
    return start_time, end_time

def select_trips_either_end_in_subarea(trips_df, subarea_taz_df):
    subarea_trips_1 = select_trips_by_subarea(trips_df, subarea_taz_df, True, False)
    subarea_trips_2 = select_trips_by_subarea(trips_df, subarea_taz_df, False, True)
    subarea_trips_df = pd.concat([subarea_trips_1, subarea_trips_2])
    return subarea_trips_df

def main():
    Output_file = ''
    Output_file_trip_dist = ''
    subarea_taz_file = ''
    subarea_code = ''
    time_period = ''
    start_time = 0
    end_time = 0

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ho:s:t:', ['stime=', 'etime='])
    except getopt.GetoptError:
        help()
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-o':
            Output_file = os.path.join(prj.project_folder, 'outputs', arg) 
        elif opt == '-t':
            if arg in time_periods:
                time_period = arg
                start_time, end_time = get_time_period_by_minutes(time_period)
            else: 
                print('invalid value for the -t option.')
                sys.exit(2)
        elif opt == '-s':
            subarea_taz_file = arg
            subarea_code = 'Customized'
        elif opt == '--stime':
            start_time = int(arg)
        elif opt == '--etime':
            end_time = int(arg)

    for arg in args:
        if arg == 'Region':
            subarea_taz_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'Regional.txt')
            subarea_code = arg
        elif arg =='Bellevue':
            subarea_taz_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'Bellevue_TAZ.txt')
            subarea_code = arg
        elif arg == 'BelDT':
            subarea_taz_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'BellevueDTTAZ.txt')
            subarea_code = arg
        else:
            print('invalid argument. Use -h for help.')
            sys.exit(2)

    if subarea_code == '':
        subarea_taz_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'Regional.txt')
        subarea_code = 'Region'

    # predefined time period is superior to customized time period.
    if time_period != '':
        start_time, end_time = get_time_period_by_minutes(time_period)
    elif start_time == 0 and end_time == 0:
        time_period = 'daily'
    else:
        time_period = str(start_time) + '-' + str(end_time)

    trips_file = os.path.join(prj.project_folder, 'outputs', '_trip.tsv')
    total_trips_df = pd.read_csv(trips_file, low_memory = True, sep = '\t')
    subarea_taz_df = pd.read_csv(subarea_taz_file)
    subarea_taz_df.reset_index(inplace = True)
    trips_df = select_trips_by_time(total_trips_df, start_time, end_time)

    
    if subarea_code == 'Region':
        either_end_in_subarea_trips_df = select_trips_by_subarea(trips_df, subarea_taz_df, True, False)
    else:
        either_end_in_subarea_trips_df = select_trips_either_end_in_subarea(trips_df, subarea_taz_df)

    if Output_file == '':
        Output_file = os.path.join(prj.project_folder, 'outputs', prj.scenario_name + '_' + subarea_code + '_'+ time_period + '_AVO.txt')
    if Output_file_trip_dist == '':
        Output_file_trip_dist = os.path.join(prj.project_folder, 'outputs', prj.scenario_name +'_' + subarea_code + '_' + time_period + '_AVO.txt')

    print('Output file: ' + Output_file)
    print('subarea definition file: ' + subarea_taz_file)

    hov2_d_only = either_end_in_subarea_trips_df.loc[(either_end_in_subarea_trips_df['mode'] == 4) & (either_end_in_subarea_trips_df['dorp'] == 1), 'trexpfac'].sum()
    hov2_p_only = either_end_in_subarea_trips_df.loc[(either_end_in_subarea_trips_df['mode'] == 4) & (either_end_in_subarea_trips_df['dorp'] == 2), 'trexpfac'].sum()
    hov3_d_only = either_end_in_subarea_trips_df.loc[(either_end_in_subarea_trips_df['mode'] == 5) & (either_end_in_subarea_trips_df['dorp'] == 1), 'trexpfac'].sum()
    hov3_p_only = either_end_in_subarea_trips_df.loc[(either_end_in_subarea_trips_df['mode'] == 5) & (either_end_in_subarea_trips_df['dorp'] == 2), 'trexpfac'].sum()

    AVO_HOV2 = (hov2_d_only + hov2_p_only) * 1.0 / hov2_d_only
    AVO_HOV3plus = (hov3_d_only + hov3_p_only) * 1.0 / hov3_d_only
    AVO_HOV2plus = (hov2_d_only + hov2_p_only + hov3_d_only + hov3_p_only) * 1.0 / (hov2_d_only + hov3_d_only)

    # write file headers.    
    with open(Output_file, 'w') as output:
        output.write(str(datetime.datetime.now()) + '\n')
        output.write(trips_file + '\n')
        output.write(subarea_taz_file + '\n')
        output.write('AVO calculation area: ' + subarea_code + '\n')
        output.write('Start time: ' + str(start_time) + '\n')
        output.write('End time: ' + str(end_time) + '\n')
        output.write('Time period: ' + time_period + '\n')
        output.write('\n')

        output.write('Mode' + '\t' + 'Drivers' + '\t' 'Passengers' + '\t'+ 'AVO' + '\n')
        output.write('HOV2\t' + str(hov2_d_only) + '\t' + str(hov2_p_only) + '\t' + str(round(AVO_HOV2, 2)) + '\n')
        output.write('HOV3+\t' + str(hov3_d_only) + '\t' + str(hov3_p_only) + '\t' + str(round(AVO_HOV3plus, 2)) + '\n')
        output.write('HOV2+\t' + str(hov2_d_only + hov3_d_only) + '\t' + str(hov2_p_only + hov3_p_only) + '\t' + str(round(AVO_HOV2plus, 2)) + '\n')


    print('Done')

if __name__ == '__main__':
    main()