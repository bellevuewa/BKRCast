#####
# Configuration for create_bkr_dataset, district_summary_purp
#####
dataset = 'survey'  # the dataset you want to process for summary, can be 'survey', 'lodes' or 'esd'. 'esd' is the daysim output data
in_out_filter_type = 'hh'  # "hh" or "trip". hh or trip. if hh - households in/outside bkr will filtered. if trip - households with trips in/outside bkr will be filtered.

#####
# Configuration for main_validation
#####
runWrkSchLocationChoice                   = True
runVehAvailability                        = True
runDayPattern                             = True
runTripDestination                        = True  # TODO: each purpose
runTourDestination                        = True  # TODO: check again needed
runTourMode                               = True
runTourTOD                                = True
runTripMode                               = True
runTripTOD                                = True

suff = {0: "Home", 
        1: "Work", 
        2: "School", 
        3: "Escort", 
        4: "PerBus", 
        5: "Shop", 
        6: "Meal", 
        7: "SocRec"}  # purpose you want to include in trips and tours