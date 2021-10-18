import pandas as pd
import os, sys
import datetime
import getopt
sys.path.append(os.getcwd())
import input_configuration as prj

# To calculate mode share from daysim output _trips.tsv. User is allowed to define a subarea in the format of a list of TAZ. 
# If so, the mode share will be calculated for that subarea. Otherwise it will be for the whole region.
# The TAZ file contains only one column named TAZ. The column name cannot be changed to other names.

# 1/29/2019
# New feature: allows to look into mode share by time period

# 2/6/2019
# New feature: allows to select trips starting from subarea_taz_file or ending at subarea_taz_file or both

#8/23/2019
# fixed a bug in trips with both ends in subarea.
# add trip distance calculation.

# 3/26/2021
# new feature: calculate total trips by HBW, HBSchool, HBO, and NHB 
##############################################################################################################
# Below are inputs that need to modify

# 5/26/2021
# new feature: calculate trips by residence and workplaces

# 6/8/2021
# move trip_mode_share_calculator from BKRCast_tool repository to BKRCast repository.
# add options to command line.
# make it part of a standard tool of BKRCast model.

# 10/18/2021
# allow a different trip df name other than _trips.tsv to be entered through -i option in the command line.
#################################################################################################################
mode_dict = {0:'Other',1:'Walk',2:'Bike',3:'SOV',4:'HOV2',5:'HOV3+',6:'Transit',8:'School_Bus'}
purp_dict = {-1: 'All_Purpose', 0: 'home', 1: 'work', 2: 'school', 3: 'escort', 4: 'personal_biz', 5: 'shopping', 6: 'meal', 7: 'social', 8: 'rec', 9: 'medical', 10: 'change'}
time_periods = ['daily', 'am', 'md', 'pm', 'ni']


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
        print 'No subarea is defined. Use the whole trip table.'
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
        print 'period ' + period + ' is invalid.'
        exit()
    return start_time, end_time

def write_file_header(output_file, overwritten = False):
    if overwritten:
        file_mode = 'w'
    else:
        file_mode = 'a'
    
    with open(output_file, file_mode) as output:
        output.write(str(datetime.datetime.now()) + '\n')
        output.write(trips_file + '\n')
        output.write(hhs_file + '\n')
        output.write(subarea_taz_file + '\n')
        output.write('Start time: ' + str(start_time) + '\n')
        output.write('End time: ' + str(end_time) + '\n')
        output.write('From the subarea: ' + str(trips_from_only) + '\n')
        output.write('To the subarea: ' + str(trips_end_only) + '\n')
        output.write('\n')

def calculateModeSharebyTripPurpose(purpose, trip_df, Output_file, overwritten=False, comments=''):
    if purpose == -1:
        # all purpose
        model_df = trip_df[['mode', 'trexpfac', 'travdist']].groupby('mode').sum()
    elif purpose >=0 and purpose <= 10:
        model_df = trip_df.loc[((trip_df['opurp'] == 0) & (trip_df['dpurp'] == purpose)) | ((trip_df['opurp'] == purpose) & (trip_df['dpurp'] == 0))][['mode', 'trexpfac', 'travdist']].groupby('mode').sum()
    else:
        print 'Purpose ' + str(purpose) + 'is invalid'
        return

    model_df['share'] = model_df['trexpfac'] / model_df['trexpfac'].sum()
    model_df['avgdist'] = model_df['travdist'] / model_df['trexpfac']
    model_df.reset_index(inplace = True)
    model_df.replace({'mode': mode_dict}, inplace = True)
    model_df.columns = ['mode', 'trips', 'total_dist', 'share', 'avgdist']
    model_df['trips'] = model_df['trips'].astype(int)
    model_df['total_dist'] = model_df['total_dist'].map('{:.1f}'.format)
    model_df['share'] = model_df['share'].map('{:.1%}'.format)
    model_df['avgdist'] = model_df['avgdist'].map('{:.1f}'.format)

    if overwritten:
        filemode = 'w'
    else: 
        filemode = 'a'

    with open(Output_file, filemode) as output:
        output.write(comments + '\n')
        output.write('Mode Share from trips, ' + purp_dict[purpose] + '\n')
        output.write('%s' % model_df)
        output.write('\n\n')     

def select_trips_either_end_in_subarea(trips_df, subarea_taz_df):
    subarea_trips_1 = select_trips_by_subarea(trips_df, subarea_taz_df, True, False)
    subarea_trips_2 = select_trips_by_subarea(trips_df, subarea_taz_df, False, True)
    subarea_trips_df = pd.concat([subarea_trips_1, subarea_trips_2])
    return subarea_trips_df

def help():
    print 'Calculate mode share from trips in a defined subarea and time period. Region wide is the default if no subarea is specified. Daily is the default if no time period is specified.'
    print ''
    print 'trip_mode_share_calculator.py -h -i <input_file> -o <output_file> -s <subarea_definition_file> -t <time period> --stime <start_time> -- etime <end_time> subarea_code'
    print '    -h: help'
    print '    -i: input file name. This file is saved in outputs folder.'
    print '    -o: output file name. This file is saved in outputs folder.'
    print '    -s: subarea definition file name. This file needs absolute file path.'
    print "    -t: time period. Can only be either of 'daily, 'am', 'md', 'pm', 'ni'. This predefined time period is superior to the user defined time period."
    print '    --stime: start time in number of minutes from midnight.'
    print '    --etime: end time in number of minutes from midnight.'
    print '    subarea_code: '
    print "        'Region': the whole region"
    print "        'Bellevue': Bellevue"
    print "        'BelDT':   Bellevue downtown"
    print ''

def cal_trip_distance(trips_df, output_file, overwritten = False, comments=''):
    subtotal_trips = trips_df['trexpfac'].count()
    trips_by_purpose = trips_df[['dpurp', 'travdist', 'trexpfac']].groupby('dpurp').sum()
    trips_by_purpose['share'] = trips_by_purpose['trexpfac'] / subtotal_trips
    trips_by_purpose['avgdist'] = trips_by_purpose['travdist'] / trips_by_purpose['trexpfac']
    trips_by_purpose.reset_index(inplace = True)
    trips_by_purpose.replace({'dpurp' : purp_dict}, inplace = True)
    trips_by_purpose.columns = ['purp', 'dist', 'trips', 'share', 'avgdist']
    trips_by_purpose['avgdist'] = trips_by_purpose['avgdist'].map('{:.1f}'.format)
    trips_by_purpose['dist'] = trips_by_purpose['dist'].map('{:.1f}'.format)
    trips_by_purpose['share'] = trips_by_purpose['share'].map('{:.1%}'.format)
    trips_by_purpose['trips'] = trips_by_purpose['trips'].astype(int)

    # distance < 3 miles
    trips_df['dist<=3'] = trips_df['travdist'] <= 3
    trips_by_dist = trips_df[['travdist', 'dist<=3', 'trexpfac']].groupby('dist<=3').sum()
    trips_by_dist['share'] = trips_by_dist['trexpfac'] / subtotal_trips
    trips_by_dist['avgdist'] = trips_by_dist['travdist'] / trips_by_dist['trexpfac']
    trips_by_dist['avgdist'] = trips_by_dist['avgdist'].map('{:.1f}'.format)
    trips_by_dist['share'] = trips_by_dist['share'].map('{:.1%}'.format)
    trips_by_dist['travdist'] = trips_by_dist['travdist'].map('{:.1f}'.format)

    # calculate commute trips
    commute_trips = trips_df.loc[(trips_df['dpurp']==1) | (trips_df['dpurp']==0)][['trexpfac', 'travdist', 'dist<=3']].groupby('dist<=3').sum()
    commute_trips['share'] = commute_trips['trexpfac'] / commute_trips['trexpfac'].sum()
    commute_trips['avgdist'] = commute_trips['travdist'] / commute_trips['trexpfac']
    commute_trips['avgdist'] = commute_trips['avgdist'].map('{:.1f}'.format)
    commute_trips['share'] = commute_trips['share'].map('{:.1%}'.format)
    commute_trips['travdist'] = commute_trips['travdist'].map('{:.1f}'.format)

    print 'Total trips: ' + str(subtotal_trips)
    # NHB trips calculation
    nhb_df = trips_df[['oadtyp','dadtyp', 'otaz', 'dtaz', 'trexpfac', 'opurp', 'dpurp']]
    nhb_df = nhb_df.loc[(nhb_df['oadtyp'] != 1) & (nhb_df['dadtyp'] != 1)]
    nhb_counts = nhb_df['trexpfac'].sum()
    print 'Total NHB trips: ' + str(nhb_counts)

    # HBW trip calculation
    hbw_df = trips_df[['oadtyp','dadtyp','otaz', 'dtaz', 'trexpfac', 'opurp', 'dpurp']]
    hbw_df = hbw_df.loc[((hbw_df['oadtyp'] == 1) & (hbw_df['dadtyp'] == 2)) | ((hbw_df['oadtyp'] == 2) & (hbw_df['dadtyp'] == 1))]
    hbw_counts = hbw_df['trexpfac'].sum()
    print 'Total NBW trips: ' + str(hbw_counts)

    # HBSchool trip calculation
    hbsch_df = trips_df[['oadtyp','dadtyp','otaz', 'dtaz', 'trexpfac', 'opurp', 'dpurp']]
    hbsch_df = hbsch_df.loc[((hbsch_df['oadtyp'] == 1) & (hbsch_df['dadtyp'] == 3)) | ((hbsch_df['oadtyp'] == 3) & (hbsch_df['dadtyp'] == 1))]
    hbsch_counts = hbsch_df['trexpfac'].sum()
    print 'Total HBSchool trips: ' + str(hbsch_counts)

    # HBO trip calculation
    hbo_df = trips_df[['oadtyp','dadtyp','otaz', 'dtaz', 'trexpfac', 'opurp', 'dpurp']]
    hbo_df = hbo_df.loc[((hbo_df['oadtyp'] == 1) & (hbo_df['dadtyp'] > 3)) | ((hbo_df['oadtyp'] > 3) & (hbo_df['dadtyp'] == 1))]
    hbo_counts = hbo_df['trexpfac'].sum()
    print 'Total HBO trips: ' + str(hbo_counts)

    if overwritten:
        file_mode = 'w'
    else:
        file_mode = 'a'

    # output to file
    with open(output_file, file_mode) as f:
        f.write(comments+'\n')
        f.write('\n')
        f.write('Total trips within the defined subarea: %d\n' % subtotal_trips)
        f.write('Trips by purpose\n')
        f.write('%s' % trips_by_purpose)
        f.write('\n\n')
        f.write('Trips by distance (for all purpose)\n')
        f.write('%s' % trips_by_dist)
        f.write('\n\n')
        f.write("Distance of commute trips\n")
        f.write('%s' % commute_trips)
        f.write('\n\n')
        f.write('Total trips: %d\n' % subtotal_trips)
        f.write('HBW trips: %d\n' % hbw_counts)
        f.write('HBSchool trips: %d\n' % hbsch_counts)
        f.write('HBO trips: %d\n' % hbo_counts)
        f.write('NHB trips: %d\n' % nhb_counts)

def main():  
    Output_file = ''
    trips_file = ''
    Output_file_trip_dist = ''
    subarea_taz_file = ''
    subarea_code = ''
    time_period = ''
    start_time = 0
    end_time = 0

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hi:o:s:t:', ['stime=', 'etime='])
    except getopt.GetoptError:
        help()
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-o':
            Output_file = os.path.join(prj.project_folder, 'outputs', arg) 
            fn, ext = os.path.splitext(arg)
            Output_file_trip_dist =  os.path.join(prj.project_folder, 'outputs', fn + '_trip_distance' + ext)
        elif opt == '-i':
            trips_file = os.path.join(prj.project_folder, 'outputs', arg)
        elif opt == '-t':
            if arg in time_periods:
                time_period = arg
                start_time, end_time = get_time_period_by_minutes(time_period)
            else: 
                print 'invalid value for the -t option.'
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
            print 'invalid argument. Use -h for help.'
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

    if trips_file == '':
        trips_file = os.path.join(prj.project_folder, 'outputs', '_trip.tsv')

    if Output_file == '':
        Output_file = os.path.join(prj.project_folder, 'outputs', prj.scenario_name + '_' + subarea_code + '_'+ time_period + '_trip_mode_share.txt')
    if Output_file_trip_dist == '':
        Output_file_trip_dist = os.path.join(prj.project_folder, 'outputs', prj.scenario_name +'_' + subarea_code + '_' + time_period + '_trip_distance.txt')
    print 'Input file: ' + trips_file
    print 'Output file: ' + Output_file
    print 'Output trip distance file: ' + Output_file_trip_dist
    print 'subarea definition file: ' + subarea_taz_file

    hhs_file = os.path.join(prj.project_folder, 'outputs', '_household.tsv')
    total_trips_df = pd.read_csv(trips_file, low_memory = True, sep = '\t')
    subarea_taz_df = pd.read_csv(subarea_taz_file)
    subarea_taz_df.reset_index(inplace = True)
    trips_df = select_trips_by_time(total_trips_df, start_time, end_time)
    hhs_df = pd.read_csv(hhs_file, sep = '\t' )

    
    if subarea_code == 'Region':
        either_end_in_subarea_trips_df = select_trips_by_subarea(trips_df, subarea_taz_df, True, False)
    else:
        either_end_in_subarea_trips_df = select_trips_either_end_in_subarea(trips_df, subarea_taz_df)

        # write file headers.    
    with open(Output_file, 'w') as output:
        output.write(str(datetime.datetime.now()) + '\n')
        output.write(trips_file + '\n')
        output.write(subarea_taz_file + '\n')
        output.write('Mode share area: ' + subarea_code + '\n')
        output.write('Start time: ' + str(start_time) + '\n')
        output.write('End time: ' + str(end_time) + '\n')
        output.write('Time period: ' + time_period + '\n')
        output.write('\n')

    print 'Calculating mode share (all trip purpose)... either end inside the subarea...'
    calculateModeSharebyTripPurpose(-1, either_end_in_subarea_trips_df, Output_file, overwritten = False,comments = 'Either end in the subarea')

    print 'Calculating mode share (HBW only)...either end inside the subarea...'
    hbw_df = either_end_in_subarea_trips_df.loc[((either_end_in_subarea_trips_df['oadtyp']==1) & (either_end_in_subarea_trips_df['dadtyp']==2))| ((either_end_in_subarea_trips_df['oadtyp']==2) & (either_end_in_subarea_trips_df['dadtyp']==1))]
    calculateModeSharebyTripPurpose(-1, hbw_df, Output_file, overwritten = False, comments = 'HBW')

    print 'Calculating mode share by other purposes... either end inside the subarea...'
    for purpose in [1,2,3,4,5,6,7, 8, 9, 10]:
        calculateModeSharebyTripPurpose(purpose, either_end_in_subarea_trips_df, Output_file, overwritten = False, comments = 'Either end in the subarea')

    print 'Calculating mode share (all trip purpose)...within the subarea...'
    subarea_trip_df = select_trips_by_subarea(trips_df, subarea_taz_df, True, True)
    calculateModeSharebyTripPurpose(-1, subarea_trip_df, Output_file, overwritten = False,comments = 'within the subarea')
    print 'Calculating mode share by other purposes... either end inside the subarea...'
    for purpose in [1,2,3,4,5,6,7, 8, 9, 10]:
        calculateModeSharebyTripPurpose(purpose, subarea_trip_df, Output_file, overwritten = False,comments = 'within the subarea')

    # calculate mode share by residence
    print 'Calculating mode share by residence...'
    hhs_df = hhs_df[['hhno','hhparcel', 'hhtaz']]
    trips_by_residence_df = trips_df.merge(hhs_df, left_on = 'hhno', right_on = 'hhno', how = 'left')
    trips_by_residence_df = trips_by_residence_df.merge(subarea_taz_df, left_on = 'hhtaz', right_on = 'TAZ', how = 'inner')
    calculateModeSharebyTripPurpose(-1, trips_by_residence_df, Output_file, comments = 'by residence only' )
    print 'Calculating mode share by other purposes... '
    for purpose in [1,2,3,4,5,6,7, 8, 9, 10]:
        calculateModeSharebyTripPurpose(purpose, trips_by_residence_df, Output_file, overwritten = False, comments = 'by residence only')

    # calculate mode share by workplace
    print 'Calculating mode share by workplace...'
    trips_to_workplace_df = trips_df.loc[trips_df['dadtyp'] == 2].merge(subarea_taz_df, left_on = 'dtaz', right_on = 'TAZ', how = 'inner')
    trips_from_workplace_df = trips_df.loc[trips_df['oadtyp'] == 2].merge(subarea_taz_df, left_on = 'otaz', right_on = 'TAZ', how = 'inner')
    trips_by_workplace_df = pd.concat([trips_to_workplace_df, trips_from_workplace_df])
    calculateModeSharebyTripPurpose(-1, trips_by_workplace_df, Output_file, comments = 'by workplace only')
    print 'Calculating mode share by other purposes... '
    for purpose in [1,2,3,4,5,6,7, 8, 9, 10]:
        calculateModeSharebyTripPurpose(purpose, trips_by_workplace_df, Output_file, overwritten = False, comments = 'by workplace only')
    print 'Mode share calculation is finished.'

    print 'Calculating tirp distance ...'
    # output to file
    with open(Output_file_trip_dist, 'w') as f:
        f.write('Trip file: %s\n' % trips_file)
        f.write('Subarea: %s\n' % subarea_taz_file)
        f.write('Trip Distance calculation area: %s\n' % subarea_code)
        f.write('Time period: %s\n' % time_period)
        f.write('Start time: %d\n' % start_time)
        f.write('End time: %d\n' % end_time)
        
    cal_trip_distance(either_end_in_subarea_trips_df, Output_file_trip_dist, overwritten = False, comments = 'either end in the subarea')
    print 'Done'

if __name__ == '__main__':
    main()