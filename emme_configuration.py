import math
import sys
HORIZON_YEAR = 2018   ## range = [2014, 2040]

###### Distance-based pricing######
add_distance_pricing = False # usually set to False unless we want to test VMT tax
# rate below includes 3.5 cent carbon tax, PSRC
distance_rate_dict = {'am' : 13.5, 'md' : 8.5, 'pm' : 13.5, 'ni' : 8.5}

# HOT Lane 
add_hot_lane_tolls = True
#HOT_rate_dict = {'am' : 35, 'md' : 10, 'pm' : 35, 'ni' : 10}    # PSRC


# HOT lane rate per mile
# @tolllane
# 1: I405 toll lane, north section, leaving Bellevue
# 2: I405 toll lane, north section, going Bellevue
# 3: I405 toll lane, south section, leaving Bellevue
# 4: I405 toll lane, south section, going Bellevue
# 6: HOT2+ (for SR167)
HOT_rate_dict = {'am' : {1: 10, 2: 35, 3: 10, 4: 35, 6: 35},
                  'md' : {1: 10, 2: 10, 3: 10, 4: 10, 6: 10},
                  'pm' : {1: 35, 2: 10, 3: 35, 4: 10, 6: 35},
                  'ni' : {1: 10, 2: 10, 3: 10, 4: 10, 6: 10}}

##################################### NETWORK IMPORTER ####################################
master_project = 'LoadTripTables'
project = 'Projects/LoadTripTables/LoadTripTables.emp'
network_summary_project = project
tod_networks = ['am', 'md', 'pm', 'ni']
sound_cast_net_dict = {'6to9' : 'am', '9to1530' : 'md', '1530to1830' : 'pm', '1830to6' : 'ni'}
load_transit_tod = ['6to9', '9to1530', '1530to1830', '1830to6']

mode_file = 'modes.txt'
transit_vehicle_file = 'vehicles.txt' 
base_net_name = '_roadway.in'
turns_name = '_turns.in'
transit_name = '_transit.in'
shape_name = '_linkshapes.in'
no_toll_modes = ['s', 'h']  
unit_of_length = 'mi'    # units of miles in Emme
coord_unit_length = 0.0001894    # network links measured in feet, converted to miles (1/5280)
headway_file = 'sc_headways.csv'

#extra attribute - add to the list in dictionary format
#format = {'type':'LINK', 'name': '@test', 'description': 'desc1', 'overwrite': True}}
#'type' is one of 'NODE', 'LINK', 'TURN', 'TRANSIT_LINE', or 'TRANSIT_SEGMENT'
#'name' should start with '@', for ex. '@toll1'
#'desc1' could be any string describing the attributes
#'overwrite' is True or False
#'file_name' is path (within the BKRCast directory) of the file with attribute value - format should be inode, jnode, attr
extra_attributes = [{'type':'LINK', 'name': '@count', 'description': 'counts', 'overwrite': True, 'file_name':'inputs/counts/screenline_cnts.txt'},
                    {'type':'NODE', 'name': '@bkrnode', 'description': 'flag for BKR internal nodes', 'overwrite': True, 'file_name':'inputs/extra_attributes/@bkrnode.txt'},
                    {'type':'NODE', 'name': '@elevation', 'description': 'elevation (from ArcGIS, KC 5ft contour)', 'overwrite': True, 'file_name':'inputs/extra_attributes/@elevation.txt'},
                    {'type':'LINK', 'name': '@biketype', 'description': 'bike lane type for BKR area', 'overwrite': True, 'file_name':'inputs/extra_attributes/@biketype.txt'},
                    {'type':'LINK', 'name': '@bkrlink', 'description': 'flag for BKR internal links', 'overwrite': True, 'file_name':'inputs/extra_attributes/@bkrlink.txt'},
                    {'type':'LINK', 'name': '@class', 'description': 'Functional classification', 'overwrite': True, 'file_name':'inputs/extra_attributes/@class.txt'},
                    {'type':'LINK', 'name': '@htoll', 'description': 'HOV toll', 'overwrite': True, 'file_name':'inputs/extra_attributes/@htoll.txt'},
                    {'type':'LINK', 'name': '@ltoll', 'description': 'LOV toll', 'overwrite': True, 'file_name':'inputs/extra_attributes/@ltoll.txt'},
                    {'type':'LINK', 'name': '@stoll', 'description': 'SOV toll', 'overwrite': True, 'file_name':'inputs/extra_attributes/@stoll.txt'},
                    {'type':'LINK', 'name': '@revlane', 'description': 'reversible lane tag', 'overwrite': True, 'file_name':'inputs/extra_attributes/@revlane.txt'},
                    {'type':'LINK', 'name': '@revlane_cap', 'description': 'full capacity for reversible lane', 'overwrite': True, 'file_name':'inputs/extra_attributes/@revlane_cap.txt'},
                    {'type':'LINK', 'name': '@slid', 'description': 'Screen line ID', 'overwrite': True, 'file_name':'inputs/extra_attributes/@slid.txt'},
                    {'type':'LINK', 'name': '@slope', 'description': 'splope (calculated in GIS from KC 5ft)', 'overwrite': True, 'file_name':'inputs/extra_attributes/@slope.txt'},
                    {'type':'LINK', 'name': '@subarea', 'description': 'BKR Subarea', 'overwrite': True, 'file_name':'inputs/extra_attributes/@subarea.txt'},
                    {'type':'LINK', 'name': '@kirkland_slid', 'description': 'Screenlines for Kirkland only', 'overwrite': True, 'file_name':'inputs/extra_attributes/@kirkland_slid.txt'},
                    {'type':'LINK', 'name': '@belcbd', 'description': 'Flag for Bellevue CBD', 'overwrite': True, 'file_name':'inputs/extra_attributes/@belcbd.txt'},
                    {'type':'LINK', 'name': '@tolllane', 'description': 'Flag for toll lane', 'overwrite': True, 'file_name':'inputs/extra_attributes/@tolllane.txt'}]
AM_extra_attributes = [{'type':'LINK', 'name': '@local_cnts_am_2014', 'description': 'Local counts AMPK 2014', 'overwrite': True, 'file_name':'inputs/observed/@local_cnts_am_2014.txt'},
                       {'type':'LINK', 'name': '@slcnt_am_2014', 'description': 'Screenline counts AMPK 2014', 'overwrite': True, 'file_name':'inputs/observed/@slcnt_am_2014.txt'}]
MD_extra_attributes = [{'type':'LINK', 'name': '@local_cnts_md_2014', 'description': 'Local counts MDPK 2014', 'overwrite': True, 'file_name':'inputs/observed/@local_cnts_md_2014.txt'},
                       {'type':'LINK', 'name': '@slcnt_md_2014', 'description': 'Screenline counts MDPK 2014', 'overwrite': True, 'file_name':'inputs/observed/@slcnt_md_2014.txt'}]
PM_extra_attributes = [{'type':'LINK', 'name': '@local_cnts_pm_2014', 'description': 'Local counts PMPK 2014', 'overwrite': True, 'file_name':'inputs/observed/@local_cnts_pm_2014.txt'},
                       {'type':'LINK', 'name': '@slcnt_pm_2014', 'description': 'Screenline counts PMPK 2014', 'overwrite': True, 'file_name':'inputs/observed/@slcnt_pm_2014.txt'}]
NI_extra_attributes = [{'type':'TRANSIT_LINE', 'name': '@nihdwy', 'description': 'headway at night', 'overwrite': True, 'default_value': '999', 'file_name':'inputs/extra_attributes/@nihdwy.txt'} ]

################################### SKIMS AND PATHS ####################################
log_file_name = 'skims_log.txt'
STOP_THRESHOLD = 0.015
parallel_instances = 4   # Number of simultaneous parallel processes. Must be a factor of 4.
max_iter = 50             # Assignment Convergence Criteria
best_relative_gap = 0.01  # Assignment Convergence Criteria
relative_gap = .0001
normalized_gap = 0.01

MIN_EXTERNAL = 1511      #zone of externals 
MAX_EXTERNAL = 1528      #zone of externals 
HIGH_TAZ = 1359
LOW_PNR = 1360 #external dummy is also included
HIGH_PNR = 1510

SPECIAL_GENERATORS = {"SeaTac":1356,"Tacoma Dome":1357,"exhibition center":1359, "Seattle Center":1358}
feedback_list = ['Banks/6to9/emmebank','Banks/1530to1830/emmebank']

# Time of day periods
hwy_tod = {'am':3,'md':6.5,'pm':3,'ni':11.5} #time period duration
tods = ['6to9', '9to1530', '1530to1830', '1830to6']
project_list = ['Projects/' + tod + '/' + tod + '.emp' for tod in tods]

## HDF5 Groups and Subgroups
hdf5_maingroups = ["Daysim","Emme","Truck Model","UrbanSim"]
hdf5_emme_subgroups = tods
emme_matrix_subgroups = ["Highway", "Walk", "Bike", "Transit"]
hdf5_urbansim_subgroups = ["Households","Parcels","Persons"]
hdf5_freight_subgroups = ["Inputs","Outputs","Rates"]
hdf5_daysim_subgroups = ["Household","Person","Trip","Tour"]

# Skim for time, cost
skim_matrix_designation_all_tods = ['t','c']  # Time (t) and direct cost (c) skims
skim_matrix_designation_limited = ['d']    # Distance skim

# Skim for distance for only these time periods
distance_skim_tod = ['6to9', '1530to1830']
generalized_cost_tod = ['6to9', '1530to1830']
gc_skims = {'light_trucks' : 'lttrk', 'medium_trucks' : 'metrk', 'heavy_trucks' : 'hvtrk', 'sov' : 'svtl2'}

# Bike/Walk Skims
bike_walk_skim_tod = ['6to9']

# Transit Inputs:
transit_skim_tod = load_transit_tod
transit_submodes = ['b', 'c', 'f', 'p', 'r']
transit_node_attributes = {'headway_fraction' : {'name' : '@hdwfr', 'init_value': .5}, 
                           'wait_time_perception' :  {'name' : '@wait', 'init_value': 2},
                           'in_vehicle_time' :  {'name' : '@invt', 'init_value': 1}}
transit_node_constants = {'am':{'4943':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '4944':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '4945':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '4952':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '4961':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}},
                          'pm':{'4943':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '4944':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '4945':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '4952':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '4961':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}}}

transit_network_tod_dict = sound_cast_net_dict                

transit_tod = {'6to9' : {'4k_tp' : 'am', 'num_of_hours' : 3},
               '9to1530' : {'4k_tp' : 'md', 'num_of_hours' : 6.5}, 
               '1530to1830' : {'4k_tp' : 'pm', 'num_of_hours' : 3},
               '1830to6' : {'4k_tp' : 'ni', 'num_of_hours' : 3.5}} #2 hours of service in PSRC - trying 3.5 hours in BKR, assuming service till 10pm
                
# Transit Fare:
zone_file = 'inputs/Fares/transit_fare_zones.grt'
peak_fare_box = 'inputs/Fares/am_fares_farebox.in'
peak_monthly_pass = 'inputs/Fares/am_fares_monthly_pass.in'
offpeak_fare_box = 'inputs/Fares/md_fares_farebox.in'
offpeak_monthly_pass = 'inputs/Fares/md_fares_monthly_pass.in'
fare_matrices_tod = ['6to9', '9to1530']

# Intrazonals
intrazonal_dict = {'distance' : 'izdist', 'time auto' : 'izatim', 'time bike' : 'izbtim', 'time walk' : 'izwtim'}
taz_area_file = 'inputs/intrazonals/taz_acres.in'
origin_tt_file = 'inputs/intrazonals/origin_tt.in'
destination_tt_file = 'inputs/intrazonals/destination_tt.in'

# SUPPLEMENTAL#######################################################
#Trip-Based Matrices for External, Trucks, and Special Generator Inputs
supplemental_loc = 'outputs/supplemental/'
hdf_auto_filename = 'inputs/4k/auto.h5'
hdf_transit_filename = 'inputs/4k/transit.h5' 
group_quarters_trips = 'outputs/supplemental/group_quarters/'
ext_spg_trips = 'outputs/supplemental/ext_spg/'
supplemental_modes = ['svtl2', 'trnst', 'bike', 'h2tl2', 'h3tl2', 'walk', 'lttrk','metrk','hvtrk']
hh_trip_loc = '/supplemental/generation/rates/hh_triprates.in'
nonhh_trip_loc = '/supplemental/generation/rates/nonhh_triprates.in'
puma_taz_loc = '/supplemental/generation/ensembles/puma00.ens'
taz_data_loc = '/supplemental/generation/landuse/tazdata.in'
pums_data_loc = '/supplemental/generation/pums/' 
externals_loc = '/supplemental/generation/externals.csv'
# Special generator zones and demand (dictionary key is TAZ, value is demand)
spg_general = {1357: 1761,
               1359: 7921,
               1358: 14668} # updated on 1/10/2020, PSRC   
spg_airport = {1356: 105240} # updated on 1/10/2020, PSRC
## growth rates are provided by PSRC
## Adjust auto special generators to HORIZON_YEAR, by scaling up 2014 daily trips.
for key in spg_airport:
    spg_airport_rate = 1
    if HORIZON_YEAR > 2030 and HORIZON_YEAR <= 2040:
        spg_airport_rate = pow(1 + 2.18/100, HORIZON_YEAR - 2030) * pow(1 + 2.69/100, 2030 - 2020) * pow(1 + 3.65/100, 2020 - 2014)
    elif HORIZON_YEAR > 2020:
        spg_airport_rate = pow (1 + 2.69/100, HORIZON_YEAR - 2020) * pow(1 + 3.65/100, 2020 - 2014)
    elif HORIZON_YEAR >= 2014: 
        spg_airport_rate = pow(1 + 3.65/100, HORIZON_YEAR - 2014)
    else:
        print 'Your HORIZON_YEAR is not valid.'
        sys.exit(-1)    
    spg_airport[key] = spg_airport[key] * spg_airport_rate

for key in spg_general:
    spg_general_rate = 1
    if HORIZON_YEAR > 2025 and HORIZON_YEAR <=2040:
        spg_general_rate = pow(1 + 0.77/100, HORIZON_YEAR - 2025) * pow(1 + 1.14/100, 2025 - 2014)
    elif HORIZON_YEAR >= 2014:
        spg_general_rate = pow(1 + 1.14/100, HORIZON_YEAR - 2014)  
    else: 
        print 'Your HORIZON_YEAR is not valid'  
        sys.exit(-1)
    spg_general[key] =  spg_general[key] * spg_general_rate

# Using one AM and one PM time period to represent AM and PM skims
am_skim_file_loc = 'inputs/6to9.h5'
pm_skim_file_loc = 'inputs/1530to1830.h5'
trip_table_loc = 'outputs/prod_att.csv'
output_dir = 'outputs/supplemental/'
ext_spg_dir = 'outputs/supplemental/ext_spg'
gq_directory = 'outputs/supplemental/group_quarters'
gq_trips_loc = 'outputs/gq_prod_att.csv'
supplemental_project = 'projects/supplementals/supplementals.emp'
# Iterations for fratar process in trip distribution
bal_iters = 5
# Define gravity model coefficients
autoop = 16.75    # Auto operation costs (in hundreds of cents per mile?)
avotda = 0.0303    # VOT

# Change modes for toll links
toll_modes_dict = {'asehdimjvutbpfl' : 'aedmvutbpfl', 'asehdimjvutbpwl' :	'aedmvutbpwl', 'ahdimjbp' : 'admbp'}
