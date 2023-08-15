import pandas as pd
import os
import datetime
import sys
import getopt
sys.path.append(os.getcwd())
import input_configuration as prj

# To calculate mode share (from tours) from daysim output _tour.tsv. User is allowed to define a subarea in the format of a list of TAZ. 
# If so, the mode share will be calculated for that subarea. Otherwise it will be for the whole region.
# The TAZ file contains only one column named TAZ. The column name cannot be changed to other names.


# 2/6/2019
# New feature: allows to select trips starting from subarea_taz_file or ending at subarea_taz_file or both

# 8/29/2019
# fixed a bug in trip filtering.

# 5/25/2021
# New feature: allow to calculate mode share by residence, workplace and subtours at workplace.

# 6/1/2021
# allow calculate mode share by either end in the subarea.
# add options to command line.

# 11/10/2021
# Change transit to Transit Walk Access.
# Change park-n-ride to Transit Auto Access
# 10/25/2021
# modified to be compatible with python 3

# 2/16/2022
# add TNC mode

# 3/1/2022
# new features: calculate mode share by business locations.

# 5/23/2023
# add Kirkland and Redmond to subarea_code option.



tour_purpose = {0: 'all',
                1: 'work',
                2: 'school',
                3: 'escort',
                4: 'personal business',
                5: 'shopping',
                6: 'meal',
                7: 'social'}
mode_dict = {0:'Other',1:'Walk',2:'Bike',3:'SOV',4:'HOV2',5:'HOV3+',6:'Transit_walk_access', 7: 'Transit_auto_access', 8:'School_Bus', 9:'TNC'}
time_periods = ['daily', 'am', 'md', 'pm', 'ni']
#purpose: 0: all purpose, 1: work, 2:school,3:escort, 4: personal buz, 5: shopping, 6: meal, 7: social/recreational, 8: not defined, 9: not defined
def CalModeSharebyPurpose(purpose, tour_df, Output_file, overwritten=False, comments=''):
    purpose_df = None
    if (purpose > 0 and purpose <= 7): 
        print('Calculating mode share for purpose ', purpose, ':', tour_purpose[purpose]);
        purpose_df = tour_df.loc[tour_df['pdpurp']==purpose][['tmodetp', 'toexpfac']].groupby('tmodetp').sum()
    elif purpose == 0:
        print('Calculating mode share for all purpose...')
        purpose_df = tour_df[['tmodetp', 'toexpfac']].groupby('tmodetp').sum()
    else:
        print('invalid purpose ', purpose)
        return

    purpose_df['share'] = purpose_df['toexpfac'] / purpose_df['toexpfac'].sum()
    purpose_df.reset_index(inplace = True)
    purpose_df.replace({'tmodetp': mode_dict}, inplace = True)
    purpose_df.columns = ['mode', 'trips', 'share']
    purpose_df['trips'] = purpose_df['trips'].astype(int)
    purpose_df['share'] = purpose_df['share'].map('{:.1%}'.format)

    if overwritten:
        filemode = 'w'
    else:
        filemode = 'a'

    with open(Output_file, filemode) as output:
        if comments != '':
            output.write(comments + '\n')
        if purpose == 0:
            output.write('All purposes\n')
        else: 
            output.write(tour_purpose[purpose] + '\n')
        output.write('%s' % purpose_df)
        output.write('\n\n')


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

def select_tours_by_time(tours_df, start_time= None, end_time = None):
    if (start_time == 0 and end_time == 0):
        selected_tours_df = tours_df
    elif (start_time < end_time):
        selected_tours_df = tours_df.loc[((tours_df['tlvorig'] >= start_time) & (tours_df['tardest'] < end_time)) | ((tours_df['tlvdest'] >= start_time) & (tours_df['tarorig'] < end_time))]
    else: # at night period
        selected_tours_df = tours_df.loc[(((tours_df['tlvorig'] >= start_time) & (tours_df['tardest'] < 1440)) | ((tours_df['tlvdest'] >= start_time) & (tours_df['tarorig'] < 1440)))|(((tours_df['tlvorig'] >= 0) & (tours_df['tardest'] < end_time)) | ((tours_df['tlvdest'] >= 0) & (tours_df['tarorig'] < end_time)))]
    return selected_tours_df

def select_tours_by_subarea(tours_df, subarea_taz_df, tours_from_only, tours_end_only):
    if subarea_taz_df.empty == False:
        if tours_from_only == True:
            from_subarea_tours_df = tours_df.join(subarea_taz_df.set_index('TAZ'), on = 'totaz', how = 'right')
        if tours_end_only == True:
            to_subarea_tours_df = tours_df.join(subarea_taz_df.set_index('TAZ'), on = 'tdtaz', how = 'right')
        if ((tours_from_only == True) and (tours_end_only == True)):
            subarea_tours_df = from_subarea_tours_df.merge(subarea_taz_df, left_on = 'tdtaz', right_on = 'TAZ')
        elif tours_from_only == True:
            subarea_tours_df = pd.concat([from_subarea_tours_df])
        else:
            subarea_tours_df = pd.concat([to_subarea_tours_df])
    else:
        print('No subarea is defined. Use the whole trip table.')
        subarea_tours_df = tours_df
    return subarea_tours_df

def select_tours_by_residence(hhs_df, tours_df, subarea_taz_df):
    hhs_df = hhs_df[['hhno','hhparcel', 'hhtaz']]
    tours_by_residence_df = tours_df.loc[(tours_df['parent'] == 0)].merge(hhs_df, left_on = 'hhno', right_on = 'hhno', how = 'left')
    if subarea_taz_df.empty == False:
        tours_by_residence_df = tours_by_residence_df.merge(subarea_taz_df, left_on = 'hhtaz', right_on = 'TAZ', how = 'inner')
    return tours_by_residence_df

def select_tours_by_workplace(tours_df, subarea_taz_df):
    tours_work_purpose_df = tours_df.loc[(tours_df['parent'] == 0) & (tours_df['pdpurp'] == 1)]
    if subarea_taz_df.empty == False:
        tours_work_purpose_df = tours_work_purpose_df.merge(subarea_taz_df, how = 'inner', left_on = 'tdtaz', right_on= 'TAZ')
    return tours_work_purpose_df

def select_tours_by_purpose(tours_df, subarea_taz_df, purpose):
    '''
    select tours by purpose code. 1: work, 2: school, 3: escort, 4: personal business, 5. shopping, 6: meal, 7: social
    subtours from workplace are also included in this selection.
    '''
    tours_work_purpose_df = tours_df.loc[tours_df['pdpurp'] == purpose]
    if subarea_taz_df.empty == False:
        tours_work_purpose_df = tours_work_purpose_df.merge(subarea_taz_df, how = 'inner', left_on = 'tdtaz', right_on= 'TAZ')
    return tours_work_purpose_df

def select_work_subtours(tours_df, subarea_taz_df):
    work_subtours_df = tours_df.loc[tours_df['parent'] > 0]
    if subarea_taz_df.empty == False:
        work_subtours_df = work_subtours_df.merge(subarea_taz_df, how = 'inner', left_on = 'totaz', right_on = 'TAZ')
    return work_subtours_df

def select_tours_either_end_in_subarea(tours_df, subarea_taz_df):
    subarea_tours_df_1 = select_tours_by_subarea(tours_df, subarea_taz_df, True, False)
    subarea_tours_df_2 = select_tours_by_subarea(tours_df, subarea_taz_df, False, True)
    subarea_tours_df = pd.concat([subarea_tours_df_1, subarea_tours_df_2])
    return subarea_tours_df

def help():
    print('Calculate mode share from tours in a defined subarea and time period. Region wide is the default if no subarea is specified. Daily is the default if no time period is specified.')
    print('')
    print('tour_mode_share_calculator.py -h -o <output_file> -s <subarea_definition_file> -t <time period> --stime <start_time> -- etime <end_time> subarea_code')
    print('    -h: help')
    print('    -o: output file name. This file is saved in outputs folder.')
    print('    -s: subarea definition file name. This file needs absolute file path.')
    print("    -t: time period. Can only be either of 'daily, 'am', 'md', 'pm', 'ni'. This predefined time period is superior to the user defined time period.")
    print('    --stime: start time in number of minutes from midnight.')
    print('    --etime: end time in number of minutes from midnight.')
    print('    subarea_code: ')
    print("        'Region':    the whole region")
    print("        'Bellevue':  Bellevue")
    print("        'BelDT':     Bellevue downtown")
    print("        'Kirkland':  Kirkland")
    print("        'Redmond':   Redmond")
    print('')

def main():
    Output_file = ''
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
        elif arg == 'Kirkland':
            subarea_taz_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'Kirkland_TAZ.txt')
            subarea_code = arg
        elif arg == 'Redmond':
            subarea_taz_file = os.path.join(prj.main_inputs_folder, 'subarea_definition', 'Redmond_TAZ.txt')
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

    if Output_file == '':
        Output_file = os.path.join(prj.project_folder, 'outputs/summary', prj.scenario_name + '_' + subarea_code + '_'+ time_period + '_tour_mode_share.txt')
    print('Output file: ' + Output_file)
    print('subarea definition file: ' + subarea_taz_file)

    tours_file = os.path.join(prj.project_folder, 'outputs\daysim', '_tour.tsv')
    hhs_file = os.path.join(prj.project_folder, 'outputs\daysim', '_household.tsv')
    total_tours_df = pd.read_csv(tours_file, sep = '\t')
    subarea_taz_df = pd.read_csv(subarea_taz_file)
    subarea_taz_df.reset_index(inplace = True)
    hhs_df = pd.read_csv(hhs_file, sep = '\t' )


    tours_df = select_tours_by_time(total_tours_df, start_time, end_time)
    if subarea_code == 'Region':
        either_end_in_subarea_tours_df = select_tours_by_subarea(tours_df, subarea_taz_df, True, False)
    else:
        either_end_in_subarea_tours_df = select_tours_either_end_in_subarea(tours_df, subarea_taz_df)
    # write file headers.    
    with open(Output_file, 'w') as output:
        output.write(str(datetime.datetime.now()) + '\n')
        output.write(tours_file + '\n')
        output.write(hhs_file + '\n')
        output.write(subarea_taz_file + '\n')
        output.write('Mode share area: ' + subarea_code + '\n')
        output.write('Start time: ' + str(start_time) + '\n')
        output.write('End time: ' + str(end_time) + '\n')
        output.write('Time period: ' + time_period + '\n')
        output.write('\n')
    CalModeSharebyPurpose(0, either_end_in_subarea_tours_df, Output_file, comments = 'Either end in the subarea')        

    subarea_tours_df = select_tours_by_subarea(tours_df, subarea_taz_df, True, False)
    CalModeSharebyPurpose(0, subarea_tours_df, Output_file, comments = 'from the subarea')        

    subarea_tours_df = select_tours_by_subarea(tours_df, subarea_taz_df, False, True)
    CalModeSharebyPurpose(0, subarea_tours_df, Output_file, comments = 'to the subarea')        

    subarea_tours_df = select_tours_by_subarea(tours_df, subarea_taz_df, True, True)
    CalModeSharebyPurpose(0, subarea_tours_df, Output_file, comments = 'inside the subarea')        

    for purpose in [1,2,3,4,5,6,7]:
        CalModeSharebyPurpose(purpose, either_end_in_subarea_tours_df, Output_file, comments = 'either end in the subarea')        

    print('Tour mode share calculation is finished.')
    hhs_df = hhs_df[['hhno','hhparcel', 'hhtaz']]
    tours_by_residence_df = select_tours_by_residence(hhs_df, tours_df, subarea_taz_df)
    CalModeSharebyPurpose(0, tours_by_residence_df, Output_file, comments='By Residence Only')        
    for purpose in [1,2,3,4,5,6,7]:
        CalModeSharebyPurpose(purpose, tours_by_residence_df, Output_file, comments='By Residence Only')        

    print('Tour mode share by residence is finished.')

    # tours by workplace = tours from home for work purpose + all subtours from workplace.
    tours_work_purpose_df = select_tours_by_workplace(tours_df, subarea_taz_df)
    work_subtours_df = select_work_subtours(tours_df, subarea_taz_df)
    tours_by_workplace_df = pd.concat([tours_work_purpose_df, work_subtours_df])
    CalModeSharebyPurpose(0, tours_by_workplace_df, Output_file, comments='By Workplace Only (with subtours)')        
    for purpose in [1,2,3,4,5,6,7]:
        CalModeSharebyPurpose(purpose, tours_by_workplace_df, Output_file, comments='By Workplace Only (with subtours)')        
    print('Tour mode share by workplace (with subtours) is finished.')

    CalModeSharebyPurpose(0, tours_work_purpose_df, Output_file, comments='By Workplace Only (without subtours)')        
    print('Tour mode share by workplace (without subtours) is finished.')

    CalModeSharebyPurpose(0, work_subtours_df, Output_file, comments='Subtours at Workplace Only')        
    for purpose in [1,2,3,4,5,6,7]:
        CalModeSharebyPurpose(purpose, work_subtours_df, Output_file, comments='Subtours at Workplace Only')
    print('Tour mode share by subtours at workplace is finished.')

    # school by destination
    tours_school_df = select_tours_by_purpose(tours_df, subarea_taz_df, 2)
    CalModeSharebyPurpose(0, tours_school_df, Output_file, comments='By School Locations')    
    print('Tour mode share by school locations is finished.')

    #school by destination
    tours_escort_df = select_tours_by_purpose(tours_df, subarea_taz_df, 3)
    CalModeSharebyPurpose(0, tours_escort_df, Output_file, comments='By Escort Locations')    
    print('Tour mode share by escort locations is finished.')

    # personal business by destination 
    tours_person_biz_df = select_tours_by_purpose(tours_df, subarea_taz_df, 4)
    CalModeSharebyPurpose(0, tours_person_biz_df, Output_file, comments='By Personal Biz Locations')    
    print('Tour mode share by personal business locations is finished.')
   
    # shopping by destination
    tours_shopping_df = select_tours_by_purpose(tours_df, subarea_taz_df, 5)
    CalModeSharebyPurpose(0, tours_shopping_df, Output_file, comments='By Shopping Locations')    
    print('Tour mode share by shopping locations is finished.')

    # meal by destination
    tours_meal_df = select_tours_by_purpose(tours_df, subarea_taz_df, 6)
    CalModeSharebyPurpose(0, tours_meal_df, Output_file, comments='By Meal Locations')    
    print('Tour mode share by meal locations is finished.')

    #social by destination
    tours_social_df = select_tours_by_purpose(tours_df, subarea_taz_df, 7)
    CalModeSharebyPurpose(0, tours_social_df, Output_file, comments='By Social Locations')    
    print('Tour mode share by social locations is finished.')

    print('Done.')



if __name__  == '__main__':
    main()