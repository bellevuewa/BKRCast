#BKR Sensitivity Tests
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 02/20/17

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os, sys, shutil
import pandas as pd
import numpy as np
import h5py
import subprocess

model_directory = r'E:\Projects\Clients\bkr\model\bkrcast_tod_new'
os.chdir(model_directory)
sys.path.append(model_directory)
sys.path.append(os.path.join(model_directory,"scripts"))

from emme_configuration import *
from input_configuration import *
from EmmeProject import *

#Sensitivity Tests - when all are false then a test setup is run
first_round = True          # effects of super/sub-sampling in population synthesis
second_round = False        # tests of number of sampled destinations
third_round = False         # tests of global iteration strategies

#directories
working_directory = r'E:\Projects\Clients\bkr\tasks\sensitivity_tests'
taz_districts = r'E:\Projects\Clients\bkr\model\bkrcast_tod_new\inputs\trucks\districts19_ga.ens'

dir_daysim = os.path.join(working_directory, 'daysim_run\daysim')
dir_input = os.path.join(working_directory, 'daysim_run\inputs')
dir_output = os.path.join(working_directory, 'daysim_run\outputs')
dir_store = os.path.join(working_directory, 'saved_outputs')

config_template_path = "daysim_configuration_template.properties"
popsyn_file = 'hh_and_persons.h5'
shadow_prices_file = 'shadow_prices.txt'
shadow_prices_pnr_file = 'park_and_ride_shadow_prices.txt'
daysim_output = 'daysim_outputs.h5'

zone_district_file = 'TAZ_District_CrossWalk.csv' #input to generate taz_sample_rate_file below
taz_sample_rate_file = 'taz_sample_rate.txt' #intermediate output, input to popsampler script

#columns in the summary file
columns = ['hhtaz', 'cars_per_hh', 'trips_per_hh', 'work_trips_per_hh', 'avg_commute_dist', 'trips_per_tour', 
               'transit_share', 'at_share', 'avg_trip_dist', 'avg_trip_time', 'am_share', 'pm_share', 'op_share']

#time periods
periods = {'am': [5*60, 9*60],
           'pm': [15*60, 18*60]}

#10 random seeds
random_seeds = [1,2,3,4,5,6,7,8,9,10]
#random_seeds = [1,2] #test

#ROUND 1
if (first_round):
    
    # Popsampler - super/sub-sampling in population synthesis - five options (for round 1)
    pop_sample_district = {'BKR':[1,4,8,2,2],
                        'Seattle':[1,0.50,1,0.50,0.25], 
                        'Rest of King':[1,0.20,0.40,0.20,0.10], 
                        'Pierce':[1,0.10,0.20,0.10,0.05], 
                        'Snohomish':[1,0.10,0.20,0.10,0.05], 
                        'Kitsap':[1,0.10,0.20,0.10,0.05]} #population sampling by districts - 5 options to choose from (each option is a column)

    #sampled destinations - base (for round 1)
    sampled_destination = {'work_location':[50],
                           'school_location':[50],
                           'tour_destination':[50],
                           'inter_stop_location':[25]}

#ROUND2
elif (second_round):
    
    #popsampler - best 2 from round 1 (for round2)
    pop_sample_district = {'BKR':[1,4],
                        'Seattle':[1,0.50], 
                        'Rest of King':[1,0.20], 
                        'Pierce':[1,0.10], 
                        'Snohomish':[1,0.10], 
                        'Kitsap':[1,0.10]} #population sampling by districts - each option is a column

    #sampled destinations - base, option 2, and option 3 (for round 2)
    sampled_destination = {'work_location':[50,25,100],
                           'school_location':[50,25,100],
                           'tour_destination':[50,25,100],
                           'inter_stop_location':[25,25,50]}

#ROUND3
elif (third_round):
    #popsampler - best 2 from round 2
    pop_sample_district = {'BKR':[1,4],
                        'Seattle':[1,0.50], 
                        'Rest of King':[1,0.20], 
                        'Pierce':[1,0.10], 
                        'Snohomish':[1,0.10], 
                        'Kitsap':[1,0.10]} #population sampling by districts - each option is a column

    #sampled destinations
    sampled_destination = {'work_location':[50,25],
                           'school_location':[50,25],
                           'tour_destination':[50,25],
                           'inter_stop_location':[25,25]}

    #global iterations - rows are options
    pop_sample = {'1A':[1,1,1],
                  '1B':[1,1,1,1],
                  '1C':[1,1,1,1,1],
                  '2A':[4,2,1,1],
                  '2B':[4,2,1,1,1],
                  '3':[10,4,2,1,1]} #1=100%; 2=50%; 4=25%; 10=10%

    #save results after every feedback iteration
    #open time dependant emme tables
    #export table

#TEST
else:
    #random seed
    random_seeds = [1234,5678]

    #popsampler
    pop_sample_district = {'BKR':[1,4],
                        'Seattle':[1,0.50], 
                        'Rest of King':[1,0.20], 
                        'Pierce':[1,0.10], 
                        'Snohomish':[1,0.10], 
                        'Kitsap':[1,0.10]} #population sampling by districts - each option is a column

    #pop_sample_district = {'BKR':[1],
    #                    'Seattle':[1], 
    #                    'Rest of King':[1], 
    #                    'Pierce':[1], 
    #                    'Snohomish':[1], 
    #                    'Kitsap':[1]} #population sampling by districts - each option is a column

    #sampled destinations
    sampled_destination = {'work_location':[50],
                           'school_location':[50],
                           'tour_destination':[50],
                           'inter_stop_location':[25]}

    #global iterations - current soundcast setup
    pop_sample = {'base':[10,2,1]}


'''
Purpose:
-inclusion of population sampler
-performs daysim sampling by district

Input:
-zone_district_file
-popsyn_file
-daysim configuration files (template and config to run)

Output:
-popsyn_out_file
-taz_sample_rate_file (intermediate)

Other scripts used:
-scripts/popsampler.py

Steps:
-reads zone to district file
-assigns sample rates to zones using user inputs (input_configuration: pop_sample_district and option)
-writes out taz_sample_rate_file
-finds popsyn file name in daysim properties
-runs popsampler
-updates daysim properties file with new popsyn file output by popsampler
'''
def daysim_popsampler(option):
    #read zone district cross file
    zone_district = pd.read_csv(os.path.join(dir_input,zone_district_file))
    zone_district['sample_rate'] = 0 #initialize

    #get districts for sampling population
    districts = pop_sample_district.keys()

    #assign sampling rate
    for district in districts:
        #print district
        zone_district.ix[zone_district['district'] == district, 'sample_rate'] = pop_sample_district[district][option-1] #option-1, as index starts from 0

    #output a text file for popsampler to use
    zone_district[['zone_id','sample_rate']].to_csv(os.path.join(dir_input, taz_sample_rate_file), index = False, sep = '\t')
                       
    #run popsampler
    popsyn_out_file = popsyn_file.replace('.h5', '_sampled.h5')
    returncode = subprocess.call([sys.executable,'daysim_run/popsampler.py',taz_sample_rate_file, popsyn_file, popsyn_out_file, dir_input])
        
    if returncode != 0:
        print('population sampler did not work')
        #sys.exit(1)
    else:
        print('Created new popsyn file')

    return(popsyn_out_file)

'''
update the configuration file with user defined settings
a dictionary of settings and corresponding values are passed as an argument
'''
def update_config_file(config_file, settings):
    #update properties file with new popsyn file
    #config_path = "daysim/daysim_configuration.properties"
    config_path = os.path.join(os.getcwd(), 'daysim_run',config_file)

    #read config file
    filedata=None
    with open(config_path, 'r') as config:
        filedata = config.read()

    #update the setting
    for setting in settings:
        if filedata.find(setting) >= 0:
            filedata = filedata.replace(setting, settings[setting])

    #write the file out
    config_file_new = config_file.replace('_template','')
    config_path_new = os.path.join(dir_daysim, config_file_new)
    with open(config_path_new, 'w') as config:
        config.write(filedata)

'''
copy shadow_prices.txt to working folder for daysim to use
'''
def copy_shadow_prices():
    if not os.path.exists('working'):
        os.makedirs('working')

    shutil.copy2(os.path.join(dir_input, shadow_prices_file), os.path.join('working', shadow_prices_file))
    shutil.copy2(os.path.join(dir_input, shadow_prices_pnr_file), os.path.join('working', shadow_prices_pnr_file))

'''
read daysim outputs
'''
def read_daysim_output(data_dir, fileName):
    #read h5 file
    mydata = h5py.File(os.path.join(data_dir, fileName))

    #get field names
    tripFields = map(lambda x: x[0], mydata.get("Trip").items())
    tourFields = map(lambda x: x[0], mydata.get("Tour").items())
    hhFields = map(lambda x: x[0], mydata.get("Household").items())
    perFields = map(lambda x: x[0], mydata.get("Person").items())
    
    #store data in dataframes

    #household data
    hhTable = pd.DataFrame()
    for hhField in hhFields:
        hhTable[hhField] = mydata.get("Household").get(hhField)[:]

    #person data
    perTable = pd.DataFrame()
    for perField in perFields:
        perTable[perField] = mydata.get("Person").get(perField)[:]

    #trip data
    tripTable = pd.DataFrame()
    for tripField in tripFields:
        tripTable[tripField] = mydata.get("Trip").get(tripField)[:]

    #tour data
    tourTable = pd.DataFrame()
    for tourField in tourFields:
        tourTable[tourField] = mydata.get("Tour").get(tourField)[:]

    return(tripTable, tourTable, hhTable, perTable)

def get_regions_districts():
    #groups
    #ga: '1B 2K 3R 4BF 5KF 6RF 7ext 8extSta 9PnR
    #ga<=6 are BKR

    # read psrc zone group file
    zoneGroups = pd.read_table(taz_districts, sep='\s+', names = ["t","group","taz"], comment = "c", skiprows = 5)
    zoneGroups = zoneGroups[zoneGroups['group']!='gb:'] #remove a line that is not useful
    zoneGroups['taz'] = zoneGroups['taz'].astype(np.int)

    #identify BKR districts
    zoneGroups['districts']=zoneGroups['group'].str.contains('gb')

    #BKR districts
    districts = zoneGroups[(zoneGroups['districts']==True)][['group','taz']]
    districts['group'] = districts['group'].str.replace('gb','')
    districts['group'] = districts['group'].str.replace(':','').astype(np.int)
    districts = districts.rename(columns = {'group': 'district'})
    
    #model regions
    regions = zoneGroups[zoneGroups['districts']==False][['group','taz']]
    regions['group'] = regions['group'].str.replace('ga','')
    regions['group'] = regions['group'].str.replace(':','').astype(np.int)
    regions = regions.rename(columns = {'group': 'region'})

    #combine the two
    taz_correspondence = pd.merge(regions, districts, on = 'taz', how = 'left')
    taz_correspondence = taz_correspondence.fillna(0)

    #debug
    #district - redmond fringe has 29 tazs instead of 32 tazs - why? ask Hu
    #also, 22 pnr tazs are assigned to districts - why? - are they one district? check before asking Hu.
    region_count = taz_correspondence[['region','district']].groupby('region').count() 

    #clean districts file
    #districts = pd.merge(districts, regions, on = 'taz', how = 'left')
    #districts = districts[districts['region'] <= 6] #to remove 22 pnr tazs in the districts file

    return(taz_correspondence)

'''
create summaries for a daysim run outputs
'''
def create_run_summaries(output_dir):
    print('reading daysim output...')
    #output_dir = 'outputs_1_1234_0'
    daysim_output = 'daysim_outputs.h5'
    
    trips, tours, households, persons = read_daysim_output(os.path.join(dir_store, output_dir), daysim_output)

    run_summaries = pd.DataFrame()
    # 1. cars per HH
    households['count'] = 1
    households['hhvehs'] = households['hhvehs'] * households['hhexpfac'] #expand number of vehicles

    vehs_taz = households[['hhtaz', 'hhvehs', 'hhexpfac', 'count']].groupby(['hhtaz']).sum().reset_index()
    vehs_taz[columns[1]] = (vehs_taz['hhvehs'])/(vehs_taz['hhexpfac'])

    run_summaries = vehs_taz[['hhtaz', columns[1]]]

    #vehs_taz.describe() #debug

    # 2. trips per HH 
    #merge households to trips
    trips_hh = pd.merge(trips, households, left_on = 'hhno', right_on = 'hhno')

    #total trips per household
    trips_taz = trips_hh[['hhtaz', 'trexpfac']].groupby(['hhtaz']).sum().reset_index()

    trips_taz = pd.merge(trips_taz, vehs_taz[['hhtaz', 'hhexpfac']], on = 'hhtaz')
    trips_taz[columns[2]] = trips_taz['trexpfac']/trips_taz['hhexpfac']
    
    #add to dataframe
    run_summaries = pd.merge(run_summaries, trips_taz[['hhtaz', columns[2]]], on = 'hhtaz', how = 'left')

    # 3. work trips per household
    #work trips - destination purpose as work
    #trips_work = trips_hh[(trips_hh['opurp'] == 1) | (trips_hh['dpurp'] == 1) ]
    trips_work = trips_hh[(trips_hh['dpurp'] == 1) ]

    trips_work_taz = trips_work[['hhtaz', 'trexpfac']].groupby(['hhtaz']).sum().reset_index()
    trips_work_taz = pd.merge(trips_work_taz, vehs_taz[['hhtaz', 'hhexpfac']], on = 'hhtaz')
    trips_work_taz[columns[3]] = trips_work_taz['trexpfac']/trips_work_taz['hhexpfac']

    #add to dataframe
    run_summaries = pd.merge(run_summaries, trips_work_taz[['hhtaz', columns[3]]], on = 'hhtaz', how = 'left')

    # avg. commute distance
    commute_dist_taz = trips_work[['hhtaz', 'travdist','trexpfac']].groupby(['hhtaz']).apply(lambda x: weighted_avg(x, 'travdist'))
    commute_dist_taz = commute_dist_taz.reset_index()
    commute_dist_taz = commute_dist_taz.rename(columns = {0 : columns[4]})
    
    #add to dataframe
    run_summaries = pd.merge(run_summaries, commute_dist_taz[['hhtaz', columns[4]]], on = 'hhtaz', how = 'left')

    # 4. trips per tour
    #merge households to tours
    tours_hh = pd.merge(tours, households, left_on = 'hhno', right_on = 'hhno')

    #tours per household
    tours_taz = tours_hh[['hhtaz', 'toexpfac']].groupby(['hhtaz']).sum().reset_index()

    #merge tours by taz to trips by taz
    trips_tours_taz = pd.merge(trips_taz, tours_taz, on = 'hhtaz')
    trips_tours_taz[columns[5]] = trips_tours_taz['trexpfac']/trips_tours_taz['toexpfac']
    
    #add to dataframe
    run_summaries = pd.merge(run_summaries, trips_tours_taz[['hhtaz', columns[5]]], on = 'hhtaz', how = 'left')

    # 5. transit mode share
    trips_mode_taz = trips_hh[['hhtaz', 'mode','trexpfac']].groupby(['hhtaz','mode']).agg({'trexpfac': 'sum'})
    trips_mode_share_taz = trips_mode_taz.groupby(level=0).apply(lambda x: 100*x/float(x.sum())).reset_index()

    trips_transit_share_taz = trips_mode_share_taz[trips_mode_share_taz['mode']==6]
    trips_transit_share_taz = trips_transit_share_taz.rename(columns = {'trexpfac' : columns[6]})
    
    #add to dataframe
    run_summaries = pd.merge(run_summaries, trips_transit_share_taz[['hhtaz', columns[6]]], on = 'hhtaz', how = 'left')

    # 6. active transport (walk+bike) mode share
    trips_at_share_taz = trips_mode_share_taz[(trips_mode_share_taz['mode']==1)|(trips_mode_share_taz['mode']==2)] #1-walk #2-bike
    trips_at_share_taz = trips_at_share_taz[['hhtaz', 'trexpfac']].groupby(['hhtaz']).sum().reset_index()
    
    trips_at_share_taz = trips_at_share_taz.rename(columns = {'trexpfac' : columns[7]})
    
    #add to dataframe
    run_summaries = pd.merge(run_summaries, trips_at_share_taz[['hhtaz', columns[7]]], on = 'hhtaz', how = 'left')
    
    # 7. avg. trip distance - weighted average
    trips_dist_taz = trips_hh[['hhtaz', 'travdist','trexpfac']].groupby(['hhtaz']).apply(lambda x: weighted_avg(x, 'travdist'))
    trips_dist_taz = trips_dist_taz.reset_index()
    trips_dist_taz = trips_dist_taz.rename(columns = {0 : columns[8]})

    #add to dataframe
    run_summaries = pd.merge(run_summaries, trips_dist_taz[['hhtaz', columns[8]]], on = 'hhtaz', how = 'left')

    # 8. avg. trip time - weighted average
    trips_time_taz = trips_hh[['hhtaz', 'travtime','trexpfac']].groupby(['hhtaz']).apply(lambda x: weighted_avg(x, 'travtime'))
    trips_time_taz = trips_time_taz.reset_index()
    trips_time_taz = trips_time_taz.rename(columns = {0 : columns[9]})

    #add to dataframe
    run_summaries = pd.merge(run_summaries, trips_time_taz[['hhtaz', columns[9]]], on = 'hhtaz', how = 'left')

    # 9. % trips in AM peak

    #calculate trip time
    trips_hh['triptime'] = trips_hh['deptm']
    trips_hh.triptime[trips_hh['half']==1] = trips_hh['arrtm']

    #assign time of day
    trips_hh['tod'] = 0
    trips_hh.tod[trips_hh['triptime'].isin(periods['am'])] = 1
    trips_hh.tod[trips_hh['triptime'].isin(periods['pm'])] = 2

    #calculate tod shares
    trips_tod_taz = trips_hh[['hhtaz', 'tod','trexpfac']].groupby(['hhtaz','tod']).agg({'trexpfac': 'sum'})
    trips_tod_share_taz = trips_tod_taz.groupby(level=0).apply(lambda x: 100*x/float(x.sum())).reset_index()

    trips_am_share_taz = trips_tod_share_taz[trips_tod_share_taz['tod']==1]
    trips_am_share_taz = trips_am_share_taz.rename(columns = {'trexpfac' : columns[10]})

    #add to dataframe
    run_summaries = pd.merge(run_summaries, trips_am_share_taz[['hhtaz', 'am_share']], on = 'hhtaz', how = 'left')
    
    # 10. % trips in PM peak
    trips_pm_share_taz = trips_tod_share_taz[trips_tod_share_taz['tod']==2]
    trips_pm_share_taz = trips_pm_share_taz.rename(columns = {'trexpfac' : columns[11]})

    # create a dataframe with all measures for a taz
    #add to dataframe
    run_summaries = pd.merge(run_summaries, trips_pm_share_taz[['hhtaz', columns[11]]], on = 'hhtaz', how = 'left')

    trips_op_share_taz = trips_tod_share_taz[trips_tod_share_taz['tod']==0]
    trips_op_share_taz = trips_op_share_taz.rename(columns = {'trexpfac' : columns[12]})
    run_summaries = pd.merge(run_summaries, trips_op_share_taz[['hhtaz', columns[12]]], on = 'hhtaz', how = 'left')

    run_summaries = run_summaries.fillna(0)   

    return(run_summaries)

'''
calculate weighted average for a group
'''
def weighted_avg(group, field):
    value = group[field]
    weight = group['trexpfac']

    avg_value = (value*weight).sum()/weight.sum()

    return(avg_value)

'''
add a chart
'''
def add_chart(writer, sheet_name, chart_type, chart_name, x_axis_name, y_axis_name, data_length, num_options, colors, chart_position):
    #get worksheet
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]

    #create a chart
    chart = workbook.add_chart({'type':chart_type})
    sheet = sheet_name

    #add series
    #settings:
    #'name': [sheet_name, row_num, col_num]
    #'categories': [sheet_name, start_row_num, start_col_num, last_row_num, last_col_num]
    #'values': [sheet_name, start_row_num, start_col_num, last_row_num, last_col_num]

    for col_num in range(1,num_options+1):

        series_options = {'name':[sheet, 0, col_num],
                          'categories':[sheet, 1, 0, data_length, 0],
                          'values':[sheet, 1, col_num, data_length, col_num]}

        #if a scatter chart
        if (chart_type == 'scatter'):
            series_options['marker']= {'type': 'circle', 'size': 5, 'color':colors[col_num-1]}

        chart.add_series(series_options)

    #set legend and axis names
    chart.set_legend({'position':'bottom'})
    chart.set_x_axis({'name':x_axis_name})
    chart.set_y_axis({'name':y_axis_name})
    chart.set_title({'name': chart_name})

    #add chart to worksheet
    worksheet.insert_chart(chart_position, chart)

'''
calculate variation summaries across different daysim runs
'''
def calculate_variation_summaries():

    #get regions and districts correspondence
    taz_corr = get_regions_districts()

    #for each of the five options - variation across 10 random seed runs
    for sampling_option_pop in range(1,len(pop_sample_district['BKR']) + 1):
        for sampling_option_dest in range(0,len(sampled_destination['work_location'])):
            #1. calculate summaries for a run
            file_path = os.path.join(dir_store, 'summaries_seed_' + str(sampling_option_pop) + '_' + str(sampling_option_dest) + '.xlsx')
            excel_writer = pd.ExcelWriter(file_path, engine = 'xlsxwriter')
            for seed in random_seeds:
                folder_name = 'outputs' + '_' + str(sampling_option_pop) + '_' + str(seed) + '_' + str(sampling_option_dest)
                summaries = create_run_summaries(folder_name)

                worksheet_name = 'seed_' + str(seed)
                summaries = summaries.set_index('hhtaz')
                #summaries['seed'] = seed
                summaries.to_excel(excel_writer, sheet_name = worksheet_name)

            #close excel file
            excel_writer.save()

            #2. calculate variation across 10 random seed runs
            calculate_summaries_random_seed_runs(sampling_option_pop, sampling_option_dest, file_path, taz_corr)

    #3. compare summaries across different options
    compare_summaries_options()

def excelize(n):
    """
    Returns excel formated column number for n
    
    Expects an int value greater than 0.
    """
    n-=1
    div = n/26
    if div==0:
        return chr(65+n)
    else:
        return excelize(div)+chr(65+n%26)

'''
compare summaries across different options
'''
def compare_summaries_options():
    #std_per_mean_taz_bkr
    #std_per_mean_districts_bkr
    #std_per_mean_total

    data_by_options_taz = {}
    data_by_options_district = {}
    #data_by_options_total = {}

    num_options = 0
    for sampling_option_pop in range(1,len(pop_sample_district['BKR']) + 1):
        for sampling_option_dest in range(0,len(sampled_destination['work_location'])):
            #open summary file
            file_path = os.path.join(dir_store, 'summaries_std_' + str(sampling_option_pop) + '_' + str(sampling_option_dest) + '.xlsx')
            summary_all = pd.read_excel(file_path, sheet_name = None)

            #std_tazs_bkr
            summary_taz = summary_all['std_tazs_bkr']
            summary_district = summary_all['std_districts_bkr']
            summary_total = summary_all['std_total']

            #save summaries by column names
            for column in columns[1:]:
                
                if (sampling_option_pop == 1):
                    data_by_options_taz[column] = summary_taz[['hhtaz', column]]
                    data_by_options_district[column] = summary_district[['district', column]]      
                else:
                    data_by_options_taz[column] = pd.merge(data_by_options_taz[column], summary_taz[['hhtaz', column]], on = 'hhtaz', how = 'left')
                    data_by_options_district[column] = pd.merge(data_by_options_district[column], summary_district[['district', column]], on = 'district', how = 'left')
                
                #rename the column
                data_by_options_taz[column] = data_by_options_taz[column].rename(columns = {column: 'option_'+str(sampling_option_pop)+'_'+str(sampling_option_dest)})
                data_by_options_district[column] = data_by_options_district[column].rename(columns = {column: 'option_'+str(sampling_option_pop)+'_'+str(sampling_option_dest)})
            
            if (sampling_option_pop == 1):
                data_by_options_total_regional = summary_total[['measure', 'regional_total']]
                data_by_options_total_bkr = summary_total[['measure', 'bkr_total']]
            else:
                data_by_options_total_regional = pd.merge(data_by_options_total_regional, summary_total[['measure', 'regional_total']], on = 'measure')
                data_by_options_total_bkr = pd.merge(data_by_options_total_bkr, summary_total[['measure', 'bkr_total']], on = 'measure')

            data_by_options_total_regional = data_by_options_total_regional.rename(columns = {'regional_total': 'regional_option_'+str(sampling_option_pop)+'_'+str(sampling_option_dest)})
            data_by_options_total_bkr = data_by_options_total_bkr.rename(columns = {'bkr_total': 'bkr_option_'+str(sampling_option_pop)+'_'+str(sampling_option_dest)})

            num_options += 1

    #excel writer
    file_path = os.path.join(dir_store, 'summaries_all_options.xlsx')
    excel_writer = pd.ExcelWriter(file_path, engine = 'xlsxwriter')
    colors = ['#228b22', '#8b4513', '#004488', '#00C0C0', '#9400d3']

    #write regional and bkr totals
    data_by_options_total = pd.merge(data_by_options_total_regional, data_by_options_total_bkr, on = 'measure')
    data_by_options_total.to_excel(excel_writer, sheet_name = 'total', index = False)

    #add line chart
    add_chart(excel_writer, 'total', 'line', 'total', 'measure', 
                'avg. std. per mean', len(data_by_options_total), 2*num_options, colors, str(excelize(2*num_options+3))+'1')

    #write taz and district level summaries
    for column in columns[1:]:
        #write data - by taz and by district
        data_by_options_taz[column].to_excel(excel_writer, sheet_name = column+'_taz', index = False)
        data_by_options_district[column].to_excel(excel_writer, sheet_name = column+'_district', index = False)
        #add scatter chart
        add_chart(excel_writer, column+'_taz', 'scatter', column+'_taz', 'tazs', 
                    'avg. std. per mean', len(data_by_options_taz[column]), num_options, colors, str(excelize(num_options+3))+'1')

        add_chart(excel_writer, column+'_district', 'scatter', column+'_district', 'districts', 
                    'avg. std. per mean', len(data_by_options_district[column]), num_options, colors, str(excelize(num_options+3))+'1')

    excel_writer.save()

'''
calculate summaries of different random seed runs of a sampling option
'''
def calculate_summaries_random_seed_runs(sampling_option_pop, sampling_option_dest, file_path, taz_corr):
    #read the excel file
    summary_all = pd.read_excel(file_path, sheet_name = None)
    sheet_names = summary_all.keys()

    df_list = []
    for sheet in sheet_names:
        summary = summary_all[sheet]
        df_list.append(summary)

    #concate all dataframes into one
    alldata = pd.concat(df_list)

    #debug
    #sampling_option_pop=1
    #sampling_option_dest=0

    file_path = os.path.join(dir_store, 'summaries_std_' + str(sampling_option_pop) + '_' + str(sampling_option_dest) + '.xlsx')
    excel_writer = pd.ExcelWriter(file_path, engine = 'xlsxwriter')

    #all tazs
    alldata_std = alldata.groupby('hhtaz').std().reset_index() #standard deviation
    alldata_mean = alldata.groupby('hhtaz').mean().reset_index() #mean
    alldata_std.to_excel(excel_writer, sheet_name = 'std_tazs_all', index = False)
    alldata_mean.to_excel(excel_writer, sheet_name = 'mean_tazs_all', index = False)

    #change column names
    for column in columns:
        if (column != columns[0]):
            #print(column)
            alldata_std = alldata_std.rename(columns = {column: column + '_std'})
            alldata_mean = alldata_mean.rename(columns = {column: column + '_mean'})
                        
    #merge the two data together
    alldata_std_per_mean = pd.merge(alldata_std, alldata_mean, on = columns[0])
    #print(alldata_std_per_mean.columns)
    for column in columns:
        if (column != columns[0]):
            #print(column)
            alldata_std_per_mean[column] = alldata_std_per_mean[column + '_std']/alldata_std_per_mean[column + '_mean']

    alldata_std_per_mean = alldata_std_per_mean[columns]
    alldata_std_per_mean.to_excel(excel_writer, sheet_name = 'std_per_mean_tazs_all', index = False)
            
    #join region and districts
    alldata_std_per_mean = pd.merge(alldata_std_per_mean, taz_corr, left_on = 'hhtaz', right_on = 'taz', how = 'left')

    #bkr taz (region <= 6)
    alldata_std_per_mean_bkr = alldata_std_per_mean[alldata_std_per_mean['region']<=6]
    alldata_std_per_mean_bkr[columns].to_excel(excel_writer, sheet_name = 'std_tazs_bkr', index = False)

    #within BKR Districts
    summary_bkr_districts = alldata_std_per_mean_bkr.groupby('district').mean().reset_index()
    summary_bkr_districts[['district']+columns[1:]].to_excel(excel_writer, sheet_name = 'std_districts_bkr', index = False)

    #regional total
    summary_regional = alldata_std_per_mean.mean().reset_index()
    summary_regional = summary_regional.rename(columns = {'index' : 'measure', 0 : 'regional_total'})

    #bkr total
    summary_bkr = alldata_std_per_mean_bkr.mean().reset_index()
    summary_bkr = summary_bkr.rename(columns = {'index' : 'measure', 0 : 'bkr_total'})

    #merge the two summaries
    summary_both = pd.merge(summary_regional, summary_bkr, on = 'measure')
    summary_both = summary_both[summary_both['measure'].isin(columns[1:])]
    summary_both.to_excel(excel_writer, sheet_name = 'std_total', index = False)

    #add column chart
    colors = ['#004488', '#00C0C0']
    add_chart(excel_writer, 'std_total', 'column', 'std_total', 'measure', 
                'avg. std. per mean', len(summary_both), 2, colors, 'E1')

    #close excel file
    excel_writer.save()

def save_assignment_results():
    #project_list = ['Projects/6to9/6to9.emp'] #test
    for project in project_list:
        print(project)
        tod = project.split('/')[1]
        my_project = EmmeProject(project)
        network = my_project.current_scenario.get_network()
        link_data = []
        for link in network.links():
            print(link.id)
            link_data.append({'link_id': link.id,
                              'length': link.length,
                              'from_node': link.i_node,
                              'to_node': link.j_node,
                              'vol_auto': link.auto_volume,
                              'time_auto': link.auto_time})

        link_data_df = pd.DataFrame(link_data, columns = link_data[0].keys())
        file_path = os.path.join(dir_store, 'hwyload_' + tod + '_' + str(1) +'.csv')
        link_data_df.to_csv(file_path, index = False)

'''
main function
'''
def main():
    #five sampling options
    for sampling_option_pop in range(1,len(pop_sample_district['BKR']) + 1):
        os.chdir(working_directory)
        #generate new synthetic population
        print('running pop sampler...')
        popsyn_file_new = daysim_popsampler(sampling_option_pop)
        #popsyn_file_new = os.path.splitext(popsyn_file)[0] + '_sampled.h5' #debug

        #choose a seed
        for seed in random_seeds:

            #sampled destination
            for sampling_option_dest in range(0,len(sampled_destination['work_location'])):

                #update the configuration file
                print('updating configuration file...')
                os.chdir(working_directory)
                update_config_file(config_template_path,{"$RUN_ALL":"true", "$SAMPLE":"1", "$SHADOW_PRICE":"true", 
                                                         '$POPSYN_FILE':popsyn_file_new, 
                                                         '$SEED':str(seed),
                                                         '$WORK_LOCATION':str(sampled_destination['work_location'][sampling_option_dest]), 
                                                         '$SCHOOL_LOCATION':str(sampled_destination['school_location'][sampling_option_dest]),
                                                         '$TOUR_DESTINATION':str(sampled_destination['tour_destination'][sampling_option_dest]),
                                                         '$INTER_STOP_LOCATION ':str(sampled_destination['inter_stop_location'][sampling_option_dest])})

                #copy shadow prices
                print('copying shadow prices...')
                copy_shadow_prices()

                #run daysim
                print('running daysim...')
                os.chdir(os.path.join(working_directory, 'daysim_run'))
                returncode = subprocess.call('daysim/Daysim.exe -c daysim/daysim_configuration.properties')

                if returncode != 0:
                    sys.exit(1)

                #save outputs to a seperate folder and rename to the current run
                print('copying output...')
                folder_name = 'outputs' + '_' + str(sampling_option_pop) + '_' + str(seed) + '_' + str(sampling_option_dest)
                shutil.move(dir_output, os.path.join(dir_store, folder_name))

                print('FINISHED')

    #calculate summaries
    calculate_variation_summaries()

if __name__== "__main__":
    main()
