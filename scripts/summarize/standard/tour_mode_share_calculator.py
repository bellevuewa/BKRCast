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

# 11/6/2023
# add -i option to allow substitue of _tour.tsv file

# 1/2/2024
# add outputs excluding workbased subtours

# 1/5/2024
# write outputs to excel file xlsx rather than text file.


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

def CalModeSharebyPurpose(purpose, tour_df):
    purpose_df = None
    if (purpose > 0 and purpose <= 7): 
        print('Calculating mode share for purpose ', purpose, ':', tour_purpose[purpose]);
        purpose_df = tour_df.loc[tour_df['pdpurp']==purpose][['tmodetp', 'toexpfac']].groupby('tmodetp').sum()
    elif purpose == 0:
        print('Calculating mode share for all purpose...')
        purpose_df = tour_df[['tmodetp', 'toexpfac']].groupby('tmodetp').sum()
    else:
        print('invalid purpose ', purpose)
        return None

    purpose_df['share'] = purpose_df['toexpfac'] / purpose_df['toexpfac'].sum()
    purpose_df.reset_index(inplace = True)
    purpose_df.replace({'tmodetp': mode_dict}, inplace = True)
    purpose_df.columns = ['mode', 'tours', 'share']
    purpose_df['tours'] = purpose_df['tours'].astype(int)

    # create a sum row in dataframe, then add it to the original one
    columns_to_sum = ['tours', 'share']
    sum_values = purpose_df[columns_to_sum].sum()    
    sum_df = pd.DataFrame([sum_values], columns = columns_to_sum) 
    
    purpose_df['share'] = purpose_df['share'].map('{:.1%}'.format)
    sum_df['share'] = sum_df['share'].map('{:.1%}'.format)
    purpose_df = purpose_df.append(sum_df, ignore_index = True)           

    return purpose_df    

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
    print('tour_mode_share_calculator.py -h -i <input_file> -o <output_file> -s <subarea_definition_file> -t <time period> --stime <start_time> -- etime <end_time> subarea_code')
    print('    -h: help')
    print('    -i input file name. This file, if available, needs to be saved in outputs folder')    
    print('    -o: output file name. This file is saved in outputs/summary folder.')
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
    tours_file = ''    

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
        elif opt == '-i':
            tours_file = os.path.join(prj.project_folder, 'outputs', arg)
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

    if tours_file == '':
        tours_file = os.path.join(prj.project_folder, 'outputs\daysim', '_tour.tsv')                

    if Output_file == '':
        Output_file = os.path.join(prj.project_folder, 'outputs/summary', prj.scenario_name + '_' + subarea_code + '_'+ time_period + '_tour_mode_share.xlsx')
    print('Output file: ' + Output_file)
    print('subarea definition file: ' + subarea_taz_file)

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

    with pd.ExcelWriter(Output_file, engine = 'xlsxwriter') as writer:
        # write readme tab        
        wksheet = writer.book.add_worksheet('readme')
        wksheet.write(0, 0, str(datetime.datetime.now())) 
        wksheet.write(1, 0, 'model folder')
        wksheet.write(1, 1, prj.project_folder)
        wksheet.write(2, 0, 'tour file')
        wksheet.write(2, 1, tours_file)
        wksheet.write(3, 0, 'household file')
        wksheet.write(3, 1, hhs_file)
        wksheet.write(4, 0, 'subarea')
        wksheet.write(4, 1, subarea_taz_file)
        wksheet.write(5, 0, 'mode share area') 
        wksheet.write(5, 1, subarea_code)     
        wksheet.write(6, 0, 'start time')        
        wksheet.write(6, 1, str(start_time))
        wksheet.write(7, 0, 'end time')
        wksheet.write(7, 1, str(end_time))
        wksheet.write(8, 0, 'time period') 
        wksheet.write(8, 1, time_period)        

               
        cal_mode_share_by_each_purpose(writer, either_end_in_subarea_tours_df, 'either_end_in_subarea', comments = 'Either end in the subarea')   

        subarea_tours_df = select_tours_by_subarea(tours_df, subarea_taz_df, True, False)
        cal_mode_share_by_each_purpose(writer, subarea_tours_df, 'from_subarea', comments = 'from the subarea')   
                                            
        subarea_tours_df = select_tours_by_subarea(tours_df, subarea_taz_df, False, True)
        cal_mode_share_by_each_purpose(writer, subarea_tours_df, 'to_subarea', comments = 'to the subarea')

        subarea_tours_df = select_tours_by_subarea(tours_df, subarea_taz_df, True, True)
        cal_mode_share_by_each_purpose(writer, subarea_tours_df, 'inside_subarea', comments = 'inside the subarea')


        hhs_df = hhs_df[['hhno','hhparcel', 'hhtaz']]
        tours_by_residence_df = select_tours_by_residence(hhs_df, tours_df, subarea_taz_df)
        cal_mode_share_by_each_purpose(writer, tours_by_residence_df, 'residence', comments = 'by Residence Only')
        print('Tour mode share by residence is finished.')

        # tours by workplace = tours from home for work purpose + all subtours from workplace.
        tours_work_purpose_df = select_tours_by_workplace(tours_df, subarea_taz_df)
        work_subtours_df = select_work_subtours(tours_df, subarea_taz_df)
        tours_by_workplace_df = pd.concat([tours_work_purpose_df, work_subtours_df])
        cal_mode_share_by_each_purpose(writer, tours_by_workplace_df, 'workplace(w subtours)', comments = 'By Workplace Only (with subtours)')
        print('Tour mode share by workplace (with subtours) is finished.')

        cal_mode_share_by_each_purpose(writer, tours_work_purpose_df, 'workplace(no subtours)', comments = 'By Workplace Only (without subtours)')
        print('Tour mode share by workplace (without subtours) is finished.')

        cal_mode_share_by_each_purpose(writer, work_subtours_df, 'subtours', comments = 'Subtours at Workplace Only')
        print('Tour mode share by subtours at workplace is finished.')
        
        cal_mode_share_by_other_destinations(writer, tours_df, subarea_taz_df, 'Other Locations', 'by other activity locations')        

    print('Done.')

def cal_mode_share_by_other_destinations(writer, tour_df, subarea_taz_df, sheet_name, comments):
    dict_df = {}    
    for purpose in [2, 3, 4, 5, 6, 7]:
        selected_tours_df = select_tours_by_purpose(tour_df, subarea_taz_df, purpose)    
        share_df_locations = CalModeSharebyPurpose(0, selected_tours_df)
        dict_df[f'By {tour_purpose[purpose]} Locations'] = share_df_locations
        print(f'Tour mode share by {tour_purpose[purpose]} Locations is finished.')

    write_to_sheet(writer, 'by other locations', dict_df)              
    print(f'{sheet_name} tab is created.')

def cal_mode_share_by_each_purpose(writer, tour_df, sheet_name, comments):
    df_0 = CalModeSharebyPurpose(0, tour_df) 
    dict_df = {f'{comments}, {tour_purpose[0]}': df_0}           
    for purpose in [1,2,3,4,5,6,7]:
        df = CalModeSharebyPurpose(purpose, tour_df) 
        dict_df[f'{comments}, {tour_purpose[purpose]}'] = df.copy() 

    write_to_sheet(writer, sheet_name, dict_df)                       

def write_to_sheet(writer, name_of_sheet, dict_dfs, write_index = True, horizontal = True):
    '''
       writer: ExcelWriter variable
       name_of_sheet: the sheet that dfs are to be exported
       dict_dfs: dictionary of dfs: {title1: df1, title2:df2...}
       write_index: write indices if True
       horizontal: export dfs horizontally or vertically. Default is horizontal
    '''    
    srow = 1
    scol = 0
    bold_format = writer.book.add_format({'bold':True})    
    for title, df in dict_dfs.items():
        df.to_excel(writer, sheet_name = name_of_sheet, index = write_index, startrow = srow, startcol = scol)
        sheet = writer.sheets[name_of_sheet]
        sheet.write(srow - 1, scol, title, bold_format)
        if horizontal == True:
            srow = srow + df.shape[0] + 3
        else:
            if write_index == True:
                scol = scol + df.shape[1] + len(df.index.names) + 3
            else:
                scol = scol + df.shape[1] + 3

    return srow, scol

if __name__  == '__main__':
    main()