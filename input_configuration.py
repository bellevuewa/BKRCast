
# This file contains model input parameters imported by BKRCast scripts.   

# If you are using the simple configuration, in the file input_configuration_simple, you will set use_simple_configuration = True, and
# the values of variables to run will be set in that file.  Otherwise the values can be over-ridden below.

# CONFIGURATION TO RUN SOUNDCAST
# Note there are many other configuration files for specific model steps in their respective directories, such as Daysim, or skimming.

#################################### PRIMARY SETTINGS  ####################################

#for a new setup, update the four settings below
project_folder = r'D:\BKRCastCodeandTestBed\BKRCast'
parcels_file_folder = r'Z:\Modeling Group\BKRCast\2018LU'
base_year = '2018'  # This should always be 2014 unless the base year changes
scenario_name = '2018' #name of the folder with scenario data

#settings automatically assigned
daysim_code = project_folder + '/daysim_2019' 
main_inputs_folder =  project_folder + '/inputs/'
base_inputs = main_inputs_folder + scenario_name

# modeller name will be updated in the EMME databank
modeller_initial = "hd"

#################################### SUB-PROCESS FLAGS  ####################################

    
# For Overriding the simple configuration, when you want to run things in more detail:
run_update_parking = False #Only update parking for future-year analysis!
run_accessibility_calcs = True
run_copy_daysim_code = False
run_copy_input_files = False
run_setup_emme_project_folders = False
run_setup_emme_bank_folders = False
run_copy_seed_supplemental_trips = False #generally set to True unless you already have trips under 'outputs/supplemental'
run_import_networks = False

# if run copy seed skims is tru (intentional typo for find and replace), you don't need to run skims and paths seed trips
# the model run will start with daysim
run_copy_seed_skims = False   
create_no_toll_network = True
run_skims_and_paths_seed_trips = False

##### Shadow prices now copied and are always used. Only Run this if building shadow prices from scratch!
should_build_shadow_price = True
run_skims_and_paths = True
run_truck_model = True
run_supplemental_trips = True
run_daysim = True
run_daysim_popsampler = False
run_accessibility_summary = True
run_bkrcast_summary =  True
run_create_daily_bank = True
run_truck_summary = False

# Specific reports to run
run_daysim_report = True
run_day_pattern_report = True
run_mode_choice_report = True
run_dest_choice_report = True
run_long_term_report = True
run_time_choice_report = True
run_district_summary_report = True
run_landuse_summary = True
    
#delete parcel files from the project directory
delete_parcel_data = False

# DaySim - household sampling rate input
pop_sample = [1, 1, 1]
    
# Assignment Iterations:
max_iterations_list = [50, 100, 100]
min_pop_sample_convergence_test = 10
    
# start building shadow prices - only run work locations
shadow_work = [1, 1, 1]
shadow_con = 30 #%RMSE for shadow pricing to consider being converged

#################################### LOG FILES  ####################################

# run daysim and assignment in feedback until convergence
main_log_file = 'bkrcast_log.txt'

#This is what you get if the model runs cleanly, but it's random:
good_thing = ["cookie", "run", "puppy", "seal sighting",  "beer", "snack", "nap","venti cinnamon dolce latte"]

transit_modes = {"lbus": "bus", "ebus": "express", 
       "fry": "ferry", "crt": "commuter_rail", "lrt": "light_rail", 'brt':'brt'} # will compute nearest distance to these

input_ensemble = "inputs\\parking_gz.csv"

# daysim mode definition
mode_dict = {0:'Other',1:'Walk',2:'Bike',3:'SOV',4:'HOV2',5:'HOV3+',6:'Transit',8:'School_Bus'}
#daysim trip purpose definition
purp_trip_dict = {-1: 'All_Purpose', 0: 'home', 1: 'work', 2: 'school', 3: 'escort', 4: 'personal_biz', 5: 'shopping', 6: 'meal', 7: 'social', 8: 'rec', 9: 'medical', 10: 'change'}

#################################### INPUT CHECKS ####################################

# These files are often missing from a run.  We want to check they are present and warn if not.
# Please add to this list as you find files that are missing.
commonly_missing_files = ['buffered_parcels.dat', 'tazdata.in']

#################################### DAYSIM ####################################
households_persons_file = r'inputs\hh_and_persons.h5'
# Popsampler - super/sub-sampling in population synthesis
sampling_option = 1 #1-3: five options available - each option is a column in pop_sample_district below
pop_sample_district = {'BKR':[1,4,2],
					'Seattle':[1,0.50,0.50], 
					'Rest of King':[1,0.20,0.20], 
					'Pierce':[1,0.10,0.10], 
					'Snohomish':[1,0.10,0.10], 
					'Kitsap':[1,0.10,0.10]} #population sampling by districts - 3 options to choose from (each option is a column) - base case and two preferred sampling plans
zone_district_file = 'TAZ_District_CrossWalk.csv' #input to generate taz_sample_rate_file below
taz_sample_rate_file = 'taz_sample_rate.txt' #intermediate output, input to popsampler script

#################################### BIKE MODEL ####################################

bike_assignment_tod = ['6to9', '1530to1830', '9to1530', '1830to6']

# Distance perception penalties for link AADT from Broach et al., 2012
# 1 is AADT 10k-20k, 2 is 20k-30k, 3 is 30k+
# No penalty applied for AADT < 10k
aadt_dict = {'volume_wt': {1: 0.368, 2: 1.40, 3: 7.157}}

# AADT segmentation breaks to apply volume penalties
# old values are aadt_bins = [0,10000,20000,30000,9999999]. AADT usually refers to bidirectional. But in EMME it is directional. so use half of it.
aadt_bins = [0,5000,10000,15000,9999999]
aadt_labels = [0,1,2,3] # Corresponding "bucket" labels for AADT segmentation for aadt_dict

# Crosswalk of bicycle facilities from geodatabase to a 2-tier typology - premium, standard (and none)
# premium (@biketype=1) - Trail/Separated bike lane
# standard (@biketype=2,3,4) - bike lane striped, Bike shoulder, and Wider lane/shared shoulder (Redmond does not have this category)
bike_facility_crosswalk = {'@bkfac': {  0:'none', 1:'premium', 2:'standard', 
                                        3:'standard', 4:'standard'}}

# Perception factor values corresponding to these tiers, from Broch et al., 2012
facility_dict = {'facility_wt': {	'premium': -0.860,
                                    'standard': -0.108, 
                                    'none': 0.5}}

# Perception factor values for 3-tiered measure of elevation gain per link
slope_dict = {'slope_wt': {1: .371,     # between 2-4% grade
                                2: 1.203,    # between 4-6% grade
                                3: 3.239}}   # greater than 6% grade

# Bin definition of total elevation gain (per link)
slope_bins = [-1,0.02,0.04,0.06,1]
slope_labels = [0,1,2,3]                

avg_bike_speed = 10 # miles per hour

# Outputs directory
bike_link_vol = 'outputs/bike_volumes.csv'
bike_count_data = 'inputs/bikes/bike_counts.csv'
#edges_file = 'inputs/bikes/edges_0.txt'

# Multiplier for storing skim results
bike_skim_mult = 100    # divide by 100 to store as int

extra_attributes_dict = {'@tveh' : 'total vehicles', 
                         '@mveh' : 'medium trucks', 
                         '@hveh' : 'heavy trucks', 
                         '@vmt' : 'vmt',\
                         '@vht' : 'vht', 
                         '@trnv' : 'buses in auto equivalents',
                         '@ovol' : 'observed volume', 
                         '@bveh' : 'number of buses'}
transit_extra_attributes_dict = {'@board' : 'total boardings', '@timtr' : 'transit line time'}


#################################### CALIBRATION/VALIDATION ####################################

# Calibration Summary Configuration
h5_results_file = 'outputs/daysim_outputs.h5'
h5_results_name = 'DaysimOutputs'
h5_comparison_file = 'scripts/summarize/inputs/calibration/survey.h5'
h5_comparison_name = 'Survey'
guidefile = 'scripts/summarize/inputs/calibration/CatVarDict.xlsx'
districtfile = 'scripts/summarize/inputs/calibration/TAZ_TAD_County.csv'
FAZ_TAZ = 'scripts/summarize/inputs/calibration/FAZ_TAZ.xlsx'
LEHD_work_flows = 'scripts/summarize/inputs/calibration/HFAZ_WFAZ_LEHD2014.xlsx'

acs_data = 'scripts/summarize/inputs/calibration/ACS_2014.xlsx'
report_output_location = 'outputs'
