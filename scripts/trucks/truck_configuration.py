import os, sys
sys.path.append(os.getcwd())
from input_configuration import *

#################################### TRUCK MODEL ####################################

truck_model_project = 'Projects/TruckModel/TruckModel.emp'
districts_file = 'districts19_ga.ens'
truck_trips_h5_filename = 'outputs/trucks/truck_trips.h5'
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

operating_cost_rate = 0.015