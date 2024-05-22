
# This file contains model input parameters imported by BKRCast scripts.   

# If you are using the simple configuration, in the file input_configuration_simple, you will set use_simple_configuration = True, and
# the values of variables to run will be set in that file.  Otherwise the values can be over-ridden below.

# CONFIGURATION TO RUN SOUNDCAST
# Note there are many other configuration files for specific model steps in their respective directories, such as Daysim, or skimming.

#################################### PRIMARY SETTINGS  ####################################

#for a new setup, update the four settings below
project_folder = r'C:\Users\hdong\source\repos\bellevuewa\BKRCastCodeandTestBed\BKRCast_2044_TNC_Recbike'
parcels_file_folder = r'Z:\Modeling Group\BKRCast\LandUse\Complan\Complan2044\2044LU\DT_rebalance_btw_job_category'
base_year = '2019'  # BKRCast base year
model_year = '2044'
supplemental_module_base_year = '2018'   # this is the base year used only by supplemental module, which comes from SC. SC latest base year is 2018
scenario_name = '2044' #name of the folder with scenario data

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
run_import_networks = False

# if run copy seed skims is tru (intentional typo for find and replace), you don't need to run skims and paths seed trips
# the model run will start with daysim
create_no_toll_network = True
run_skims_and_paths_seed_trips = False

##### Shadow prices now copied and are always used. Only Run this if building shadow prices from scratch!
should_build_shadow_price = True
run_skims_and_paths = True
run_truck_model = True
run_supplemental_trips = True
run_daysim = True
run_daysim_popsampler = False
run_bkrcast_summary =  True
run_create_daily_bank = True
run_truck_summary = False

##############################
# Modes and Path Types
##############################
# In daysim, TNC mode is called PRS, paid ride share. We use TNC to be consistent with Soundcast.
include_tnc = False
include_tnc_to_transit = False # AV to transit path type allowed #not implemented yet

## Recreational bike
include_rec_bike = True # inplemented as part of supplemental

include_delivery = False

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

 # in the future if we want to add express bus or brt to the transit mode, add {"ebus": "express"} {'brt':'brt'}to the transit_modes.  
transit_modes = {"lbus": "bus", "ebus": "express", "fry": "ferry", "crt": "commuter_rail", "lrt": "light_rail"} # will compute nearest distance to these

input_ensemble = r"inputs/landuse/parking_gz.csv"

input_folder_for_supplemental = 'inputs/supplemental'

# daysim mode definition
mode_dict = {0:'Other',1:'Walk',2:'Bike',3:'SOV',4:'HOV2',5:'HOV3+',6:'Transit',8:'School_Bus', 9:'TNC'}

bkrlink_dict = {1:'Bellevue', 2:'Kirkland', 3:'Redmond', 4:'Rest of KC', 5: 'Rest of KC', 0:'Outside KC'}

#daysim trip purpose definition
purp_trip_dict = {-1: 'All_Purpose', 0: 'home', 1: 'work', 2: 'school', 3: 'escort', 4: 'personal_biz', 5: 'shopping', 6: 'meal', 7: 'social', 8: 'rec', 9: 'medical', 10: 'change'}
tour_purpose_dict = {0: 'all',
                1: 'work',
                2: 'school',
                3: 'escort',
                4: 'personal business',
                5: 'shopping',
                6: 'meal',
                7: 'social'}
#################################### INPUT CHECKS ####################################

# These files are often missing from a run.  We want to check they are present and warn if not.
# Please add to this list as you find files that are missing.
commonly_missing_files = [r'buffered_parcels.txt', r'node_to_node_distance_2014.h5']

#################################### DAYSIM ####################################
households_persons_file = r'inputs/popsim/hh_and_persons.h5'
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
# premium (@biketype=1, 10) - 1: Separated bike lane, 10: trail
# standard (@biketype=2,3,4) - bike lane striped, Bike shoulder, and Wider lane/shared shoulder (Redmond does not have this category)
bike_facility_crosswalk = {'@bkfac': {  0:'none', 1:'premium', 2:'standard', 
                                        3:'standard', 4:'standard', 10:'premium'}}

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
bike_link_vol = 'outputs/bikes/bike_volumes.csv'
bike_count_data = 'inputs/bikes/bike_counts.csv'
#edges_file = 'inputs/bikes/edges_0.txt'

# Multiplier for storing skim results
bike_skim_mult = 100    # divide by 100 to store as int

extra_attributes_dict = {'@tveh' : 'total vehicles', 
                         '@mveh' : 'medium trucks', 
                         '@hveh' : 'heavy trucks', 
                         '@vmt' : 'vmt',\
                         '@vht' : 'vht', 
                         '@trnv3' : 'transit vehicles in PCE',
                         '@ovol' : 'observed volume', 
                         '@bveh' : 'number of buses'}
transit_extra_attributes_dict = {'@board' : 'total boardings', '@timtr' : 'transit line time'}
transit_segment_extra_attributes_dict = {'@talight':'total segment alighting', '@finalight': 'final alighting', '@transalight':'transfer alighting', 
                                         '@tboard': 'total segment boarding', 
                                         '@iboard':'initial boarding', '@trsboard': 'transfer boarding'}

### Equity analysis
# 2016 federal poverty line   
fed_poverty_1st_person = 11770
fed_poverty_extra_person = 4160
income_bins = [-1, 0, 0.5, 1, 2, 5, 10, 500]  # by how many times of the fed poverty line
income_bins2 = [-1, 1, 500]
income_bins3 = [-1, 2, 500]
veh_bins = [-1, 0, 1, 2, 3, 10]
age_bins = [0, 5, 15, 30, 50, 65, 200]
hhsize_bins = [0, 1, 2, 3, 4, 20]
trip_distance_bin = [0, 1, 2, 3, 5, 200]

### GHG and VMT
auto_speed_bins = [-999999, 2.5, 7.5, 12.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 999999 ]

# to decide which hour of emission rate should be used.
emission_tod_lookup = {'6to9': 7, '9to1530': 12, '1530to1830': 17, '1830to6': 19}
# List of pollutants to be summarized for summer
# All other are to be summarized for winter season
# using wintertime rates for all start emission rates except for VOCs
# per X:\Trans\AIRQUAL\T2040 2018 Update\EmissionCalcs\Start Emissions\Starts_2040.xls
summer_list = [87]

pollutant_map = {
    '1': 'Total Gaseous HCs',
    '2': 'CO',
    '3': 'NOx',
    '5': 'Methane',
    '6': 'N20',
    '79': 'Non-methane HCs',
    '87': 'VOCs',             
    '90': 'Atmospheric CO2',
    '91': 'Total Energy',
    '98': 'CO2 Equivalent',
    '100': 'PM10 Exhaust',
    '106': 'PM10 Brakewear',
    '107': 'PM10 Tirewear',
    '110': 'PM25 Exhaust',
    '112': 'Elemental Carbon',
    '115': 'Sulfate Particulate',
    '116': 'PM25 Brakewear',
    '117': 'PM25 Tirewear',   
    '118': 'Composite NonECPM',
    '119': 'H20 Aerosol',
    '200': 'Total PM10',
    '201': 'Total PM25'        
}


#################################### CALIBRATION/VALIDATION ####################################

# Calibration Summary Configuration
h5_results_file = 'outputs/daysim/daysim_outputs.h5'
h5_results_name = 'DaysimOutputs'
h5_comparison_file = 'inputs/model/survey/survey.h5'
h5_comparison_name = 'Survey'
guidefile = 'inputs/model/CatVarDict.xlsx'
districtfile = 'inputs/model/TAZ_TAD_County.csv'
FAZ_TAZ = 'inputs/model/FAZ_TAZ.xlsx'
LEHD_work_flows = 'inputs/model/HFAZ_WFAZ_LEHD2014.xlsx'

acs_data = 'inputs/model/survey/ACS_2014.xlsx'

network_validation_output_filename = scenario_name + '_network_validation.xlsx'

report_output_location = 'outputs/daysim'
report_lu_output_location = 'outputs/landuse'
report_bikes_output_location = 'outputs/bikes'
report_net_output_location = 'outputs/network'
report_summary_output_location = 'outputs/summary'
report_transit_location = 'outputs/transit'

## Summary files ##
network_results_path = 'outputs/network/network_results.csv'
iz_vol_path = 'outputs/network/iz_vol.csv'
transit_line_path = 'outputs/transit/transit_line_results.csv'
transit_node_path = 'outputs/transit/transit_node_results.csv'
transit_segment_path = 'outputs/transit/transit_segment_results.csv'
boardings_by_agency_path = 'outputs/transit/daily_boardings_by_agency.csv'
special_routes_path = 'outputs/transit/daily_boardings_special_routes.csv'
boardings_by_tod_agency_path = 'outputs/transit/boardings_by_tod_agency.csv'
boardings_by_stop_path = 'outputs/transit/boardings_by_stop.csv'
light_rail_boardings_path = 'outputs/transit/light_rail_boardings.csv'
job_access_by_transit_file = 'outputs/transit/jobs_by_transit_access.xlsx'
transit_transfer_file = 'outputs/transit/transit_transfers.csv'
bkr_network_summary_path = 'outputs/network/network_summary.xlsx'
