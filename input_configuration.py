from input_configuration_simple import *

# This file contains model input parameters imported by BKRCast scripts.   

# If you are using the simple configuration, in the file input_configuration_simple, you will set use_simple_configuration = True, and
# the values of variables to run will be set in that file.  Otherwise the values can be over-ridden below.

# CONFIGURATION TO RUN SOUNDCAST
# Note there are many other configuration files for specific model steps in their respective directories, such as Daysim, or skimming.

#################################### PRIMARY SETTINGS  ####################################

#for a new setup, update the four settings below
project_folder = r'D:\2018baseyear\BKR0V1-02'
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

if not(use_simple_configuration):
    
    # For Overriding the simple configuration, when you want to run things in more detail:
    run_update_parking = False #Only update parking for future-year analysis!
    run_accessibility_calcs = True
    run_copy_daysim_code = True
    run_copy_input_files = True
    run_setup_emme_project_folders = False
    run_setup_emme_bank_folders = False
    run_copy_seed_supplemental_trips = True  #generally set to True unless you already have trips under 'outputs/supplemental'
    run_import_networks = False

    # if run copy seed skims is tru (intentional typo for find and replace), you don't need to run skims and paths seed trips
    # the model run will start with daysim
    run_copy_seed_skims = True   # usually True
    create_no_toll_network = True
    run_skims_and_paths_seed_trips = False  # usually False

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
    delete_parcel_data = True

    # DaySim - household sampling rate input
    pop_sample = [1, 1, 1]
    
    # Assignment Iterations:
    max_iterations_list = [50, 100, 100]
    min_pop_sample_convergence_test = 10
    
    # start building shadow prices - only run work locations
    shadow_work = [1, 1, 1]
    shadow_con = 30 #%RMSE for shadow pricing to consider being converged

else:
    create_no_toll_network = False
    run_ben_cost = False
    run_tableau_db = False
    min_pop_sample_convergence_test = 10
    
    if run_setup:
        if base_year == scenario_name:
            run_update_parking = False
        else:
            run_update_parking = True

        run_accessibility_calcs = True
        run_accessibility_summary = True
        run_copy_daysim_code = True
        run_setup_emme_project_folders = True
        run_setup_emme_bank_folders = True
        run_landuse_summary = True
    else:
        run_update_parking = False
        run_accessibility_calcs = False
        run_accessibility_summary = False
        run_copy_daysim_code = False
        run_setup_emme_project_folders = False
        run_setup_emme_bank_folders = False
        run_landuse_summary = False

    if run_daysim:
        run_soundcast_summary = True
        run_daysim_report = True
        run_day_pattern_report = True
        run_mode_choice_report = True
        run_dest_choice_report = True
        run_long_term_report = True
        run_time_choice_report = True
        run_district_summary_report = True
    else:
        run_soundcast_summary = False
        run_daysim_report = False
        run_day_pattern_report = False
        run_mode_choice_report = False
        run_dest_choice_report = False
        run_long_term_report = False
        run_time_choice_report = False
        run_district_summary_report = True

    if should_build_shadow_price:
        shadow_work = [1, 1]
        shadow_con = 30 #%RMSE for shadow pricing to consider being converged
        feedback_iterations = feedback_iterations - 1 # when building shadow prices a final iteration happens automatically

    if start_with_seed_skims:
        run_copy_seed_skims = True
        run_skims_and_paths_seed_trips = False
    else:
        run_copy_seed_skims = False
        run_skims_and_paths_seed_trips = True
        run_import_networks = True
        run_truck_model = True
        run_supplemental_trips = True
        run_create_daily_bank = True

    if run_skims_and_paths:
            run_import_networks = True
            run_truck_model = True
            run_supplemental_trips = True
            run_create_daily_bank = True
    else:
            run_import_networks = False
            run_truck_model = False
            run_supplemental_trips = False
            run_create_daily_bank = False

    pop_sample = []
    max_iterations_list = []

    while feedback_iterations > 0:
        # feedback iterations remaining
        if feedback_iterations == 1:
            pop_sample.append(2)
            max_iterations_list. append(100)
        elif feedback_iterations == 2:
            pop_sample.append(5)
            max_iterations_list.append(100)
        else:
            pop_sample.append(20)
            max_iterations_list.append(10)

        feedback_iterations -=1 

#################################### LOG FILES  ####################################

# run daysim and assignment in feedback until convergence
main_log_file = 'bkrcast_log.txt'

#This is what you get if the model runs cleanly, but it's random:
good_thing = ["cookie", "run", "puppy", "seal sighting",  "beer", "snack", "nap","venti cinnamon dolce latte"]

#################################### ACCESSIBILITY ####################################

parcels_file_name = 'parcels_urbansim.txt'
buffered_parcels = 'buffered_parcels.dat'
output_parcels = 'inputs/' + buffered_parcels
buffered_parcels_csv = 'inputs/' + 'buffered_parcels.csv'
transit_stops_name = 'inputs/accessibility/transit_stops_2014.csv'
nodes_file_name = 'inputs/accessibility/all_streets_nodes_2014.csv'
links_file_name = 'inputs/accessibility/all_streets_links_2014.csv'
military_file = "inputs\\accessibility\\parcels_military.csv"
jblm_file = "inputs\\accessibility\\\distribute_jblm_jobs.csv"
daily_parking_cost = "inputs\\accessibility\\daily_parking_costs.csv"
hourly_parking_cost = "inputs\\accessibility\\hourly_parking_costs.csv"
input_ensemble = "inputs\\parking_gz.csv"

max_dist = 24140.2 # 3 miles in meters

distances = { # in meters; 
              # keys correspond to suffices of the resulting parcel columns
              # ORIGINAL VALUES !!
             1: 2640, # 0.5 mile
             2: 5280 # 1 mile
             }

# These will be disaggregated from the parcel data to the network.
# Keys are the functions applied when aggregating over buffers.

parcel_attributes = {
              "sum": ["HH_P", "STUGRD_P", "STUHGH_P", "STUUNI_P", 
                      "EMPMED_P", "EMPOFC_P", "EMPEDU_P", "EMPFOO_P", "EMPGOV_P", "EMPIND_P", 
                      "EMPSVC_P", "EMPOTH_P", "EMPTOT_P", "EMPRET_P",
                      "PARKDY_P", "PARKHR_P", "NPARKS", "APARKS", "daily_weighted_spaces", "hourly_weighted_spaces"],
              "ave": [ "PPRICDYP", "PPRICHRP"],
              }

col_order =[u'parcelid', u'xcoord_p', u'ycoord_p', u'sqft_p', u'taz_p', u'lutype_p', u'hh_p',
       u'stugrd_p', u'stuhgh_p', u'stuuni_p', u'empedu_p', u'empfoo_p',
       u'empgov_p', u'empind_p', u'empmed_p', u'empofc_p', u'empret_p',
       u'empsvc_p', u'empoth_p', u'emptot_p', u'parkdy_p', u'parkhr_p',
       u'ppricdyp', u'pprichrp', u'hh_1', u'stugrd_1', u'stuhgh_1',
       u'stuuni_1', u'empedu_1', u'empfoo_1', u'empgov_1', u'empind_1',
       u'empmed_1', u'empofc_1', u'empret_1', u'empsvc_1', u'empoth_1',
       u'emptot_1', u'parkdy_1', u'parkhr_1', u'ppricdy1', u'pprichr1',
       u'nodes1_1', u'nodes3_1', u'nodes4_1', u'tstops_1', u'nparks_1',
       u'aparks_1', u'hh_2', u'stugrd_2', u'stuhgh_2', u'stuuni_2',
       u'empedu_2', u'empfoo_2', u'empgov_2', u'empind_2', u'empmed_2',
       u'empofc_2', u'empret_2', u'empsvc_2', u'empoth_2', u'emptot_2',
       u'parkdy_2', u'parkhr_2', u'ppricdy2', u'pprichr2', u'nodes1_2',
       u'nodes3_2', u'nodes4_2', u'tstops_2', u'nparks_2', u'aparks_2',
       u'dist_lbus', u'dist_ebus', u'dist_crt', u'dist_fry', u'dist_lrt',
       u'dist_park']

# These are already on network (from add-ons).
# Keys correspond to the resulting parcel columns (minus suffix).
# Values correspond the names in the add-on dataset.
transit_attributes = ["tstops"]
intersections = ["nodes1", "nodes3", "nodes4"]

transit_modes = {"lbus": "bus", "ebus": "express", 
       "fry": "ferry", "crt": "commuter_rail", "lrt": "light_rail"} # will compute nearest distance to these

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
aadt_bins = [0,10000,20000,30000,9999999]
aadt_labels = [0,1,2,3] # Corresponding "bucket" labels for AADT segmentation for aadt_dict

# Crosswalk of bicycle facilities from geodatabase to a 2-tier typology - premium, standard (and none)
# premium (@biketype=1) - Trail/Separated bike lane
# standard (@biketype=2,3,4) - bike lane striped, Bike shoulder, and Wider lane/shared shoulder (Redmond does not have this category)
bike_facility_crosswalk = {'@bkfac': {  0:'none', 1:'premium', 2:'standard', 
                                        3:'standard', 4:'standard'}}

# Perception factor values corresponding to these tiers, from Broch et al., 2012
facility_dict = {'facility_wt': {	'premium': -0.160,
                                    'standard': -0.108, 
                                    'none': 0}}

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

#################################### TRUCK MODEL ####################################

truck_model_project = 'Projects/TruckModel/TruckModel.emp'
districts_file = 'districts19_ga.ens'
truck_trips_h5_filename = 'inputs/4k/auto.h5'
truck_base_net_name = 'am_roadway.in'

#TOD to create Bi-Dir skims (AM/EV Peak)
truck_generalized_cost_tod = {'6to9' : 'am', '1530to1830' : 'pm'}

# External Magic Numbers
LOW_STATION = 1511
HIGH_STATION = 1528
EXTERNAL_DISTRICT = 'ga08'

truck_adjustment_factor = {'ltpro': 0.544,
							'mtpro': 0.545,
							'htpro': 0.530,
							'ltatt': 0.749,
							'mtatt': 0.75,
							'htatt': 1.0}

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
