import os
import logging
import time

import pandas as pd

from config import *
from input_configuration import project_folder
from daysim_summaries.validation_utility import write_tables
from validation_helper import *


#####
# Creating a logger
#####

def create_logger(logfile='log.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(logfile, mode='w'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger()
    logging.info("Running Daysim validation...")
    return logger


def main():
    start_time = time.time()
    logger = create_logger(logfile=os.path.join(project_folder, "daysim_summaries", f"daysim_validation.log"))

    # run tabulations
    zone_district = pd.read_csv(os.path.join(project_folder, "inputs", "subarea_definition", "TAZ_subarea.csv"))
    working_folder = os.path.join(os.getcwd(), "daysim_summaries")

    #####
    # This script generates summaries for DaySim Usual Work and School Locations
    # Distributions of home-work/school distances and times by persontype are produced
    #####
    if runWrkSchLocationChoice:
        logging.info("Summarizing work location choice...")
        start_time_wrkschloc = time.time()

        for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
            perdata = pd.read_csv(os.path.join(working_folder, "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
            hhdata = pd.read_csv(os.path.join(working_folder, "data", f"hhs_{bkrcast_folder.split('_')[1]}.csv"))
            perdata_new = prep_wrkschloc(perdata, hhdata, zone_district)
        
            write_tables("WrkLocation", 
                        perdata_new, bkrcast_folder,
                        os.path.join(working_folder, "templates", "WrkLocation.csv"), 
                        dataset)
            write_tables("SchLocation", 
                        perdata_new, bkrcast_folder, 
                        os.path.join(working_folder, "templates", "SchLocation.csv"), 
                        dataset)

            logging.info(f"Work/School Location Summary for BKRCast {bkrcast_folder}...Finished")
        logging.info(f"Total run time: {round((time.time() - start_time_wrkschloc) / 60, 2)} minutes")

    #####
    # This script generates summaries for DaySim vehicle availability models
    # Distributions of vehicle ownership by drivers, income and county are produced
    #####
    if runVehAvailability:
        logging.info("Summarizing vehicle ownership choice...")
        start_time_vehavailability = time.time()
        for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
            perdata = pd.read_csv(os.path.join(working_folder, "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
            hhdata = pd.read_csv(os.path.join(working_folder, "data", f"hhs_{bkrcast_folder.split('_')[1]}.csv"))
            hhdata_new = prep_vehavail(perdata, hhdata, zone_district)
            
            write_tables("VehAvailability", 
                        hhdata_new, bkrcast_folder,
                        os.path.join(working_folder, "templates", "VehAvailability.csv"), 
                        dataset)

            logging.info(f"Vehicle Availability Summary for BKRCast {bkrcast_folder}...Finished")
        logging.info(f"Total run time: {round((time.time() - start_time_vehavailability) / 60, 2)} minutes")

    #####
    # This script generates Day Patterns from DaySim run outputs
    #####
    if runDayPattern:
        logging.info("Summarizing Day pattern...")
        start_time_daypattern = time.time()
        for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
            perdata = pd.read_csv(os.path.join(working_folder, "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
            hhdata = pd.read_csv(os.path.join(working_folder, "data", f"hhs_{bkrcast_folder.split('_')[1]}.csv"))

            # person
            perdata_new = prep_perdata(perdata, hhdata, zone_district)
            perdata_new = perdata_new[["hhno", "pno", "pptyp", "hhcounty", "inccat", "vehsuf", "psexpfac"]]

            # person day
            pdaydata = pd.read_csv(os.path.join(working_folder, "data", f"person_day_{bkrcast_folder.split('_')[1]}.csv"))
            pdaydata_new = prep_pdaydata(pdaydata, perdata_new, excludeChildren5=False)
            write_tables("DayPattern", 
                        pdaydata_new, bkrcast_folder,
                        os.path.join(working_folder, "templates", "DayPattern_pday.csv"), 
                        dataset)
            # tour
            tourdata = pd.read_csv(os.path.join(working_folder, "data", f"tours_{bkrcast_folder.split('_')[1]}.csv"))
            tourdata_new = prep_tourdata(tourdata, 
                                         perdata_new, 
                                         zone_district, 
                                         work_tours_only=False,
                                         excludeChildren5=False)
            write_tables("DayPattern", 
                        tourdata_new, bkrcast_folder,
                        os.path.join(working_folder, "templates", "DayPattern_tour.csv"), 
                        dataset)

            # trip
            tripdata = pd.read_csv(os.path.join(working_folder, "data", f"trips_full_{bkrcast_folder.split('_')[1]}.csv"))
            tripdata_new = prep_tripdata(tripdata, perdata_new, zone_district, excludeChildren5=False)
            write_tables("DayPattern", 
                        tripdata_new, bkrcast_folder,
                        os.path.join(working_folder, "templates", "DayPattern_trip.csv"), 
                        dataset)

            logging.info(f"Summarizing Destination Choice for BKRCast {bkrcast_folder}...Finished")
        logging.info(f"Total run time: {round((time.time() - start_time_daypattern) / 60, 2)} minutes")
    
    #####
    # This script generates Trip Destination Summaries from DaySim run outputs
    #####
    if runTripDestination:
        logging.info("Summarizing Trip Destination Choice...")
        start_time_tripdest = time.time()
        for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
            perdata = pd.read_csv(os.path.join(working_folder, "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
            hhdata = pd.read_csv(os.path.join(working_folder, "data", f"hhs_{bkrcast_folder.split('_')[1]}.csv"))
            perdata_new = prep_perdata(perdata, hhdata, zone_district)
            perdata_new = perdata_new[["hhno","pno","pptyp","hhtaz","hhcounty","pwtaz","psexpfac"]]

            tripdata = pd.read_csv(os.path.join(working_folder, "data", f"trips_full_{bkrcast_folder.split('_')[1]}.csv"))
            tripdata_new = prep_tripdata(tripdata, perdata_new, zone_district, excludeChildren5=False)

            write_tables("TripDestination", 
                        tripdata_new, bkrcast_folder,
                        os.path.join(working_folder, "templates", "TripDestination.csv"), 
                        dataset)
            
            logging.info(f"Summarizing Trip Destination for BKRCast {bkrcast_folder}...Finished")
        logging.info(f"Total run time: {round((time.time() - start_time_tripdest) / 60, 2)} minutes")

    #####
    # This script generates Day Patterns from DaySim run outputs
    #####
    logging.info("Summarizing Tour Destination Choice...")
    if runTourDestination:
        start_time_tourdest = time.time()
        for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
            perdata = pd.read_csv(os.path.join(working_folder, "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
            hhdata = pd.read_csv(os.path.join(working_folder, "data", f"hhs_{bkrcast_folder.split('_')[1]}.csv"))
            perdata_new = prep_perdata(perdata, hhdata, zone_district)
            perdata_new = perdata_new[["hhno","pno","pptyp","hhtaz","hhcounty","pwtaz","psexpfac"]]
            
            tourdata = pd.read_csv(os.path.join(working_folder, "data", f"tours_{bkrcast_folder.split('_')[1]}.csv"))
            tourdata_new = prep_tourdata(tourdata, 
                                         perdata_new, 
                                         zone_district, 
                                         work_tours_only=False,
                                         excludeChildren5=False)

            for purp_id, purp_label in suff.items():
                if 3 <= purp_id < 8:
                    fname = f"TourDestination_{purp_label}"
                    write_tables(fname, 
                                 tourdata_new[tourdata_new["pdpurp2"] == purp_id], bkrcast_folder,
                                 os.path.join(working_folder, "templates", "TourDestination.csv"), 
                                 dataset)

            write_tables("TourDestination_WrkBased", 
                         tourdata_new[tourdata_new["pdpurp2"] == 8], bkrcast_folder,
                         os.path.join(working_folder, "templates", "TourDestination_wkbased.csv"), 
                         dataset)
            logging.info(f"Summarizing Tour Destination for BKRCast {bkrcast_folder}...Finished")
        logging.info(f"Total run time: {round((time.time() - start_time_tourdest) / 60, 2)} minutes")

    #####
    # This script generates summaries for DaySim Tour mode models
    # Distributions of tour modes by purpose are produced
    #####
    if runTourMode:
        logging.info("Summarizing Tour Mode Choice...")
        start_time_tourmode = time.time()
        for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
            perdata = pd.read_csv(os.path.join(working_folder, "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
            hhdata = pd.read_csv(os.path.join(working_folder, "data", f"hhs_{bkrcast_folder.split('_')[1]}.csv"))
            perdata_new = prep_perdata(perdata, hhdata, zone_district)
            perdata_new = perdata_new[["hhno", "vehcat","pno","pptyp","hhtaz","hhcounty","pwtaz","psexpfac"]]
        
            tourdata = pd.read_csv(os.path.join(working_folder, "data", f"tours_{bkrcast_folder.split('_')[1]}.csv"))
            # default is NHTS, prep_modedata_DaySim is only for Tampa/JAX
            if dataset == "survey":
                tourdata_new = prep_modedata_NHTS(tourdata)
            elif dataset in ["esd", "daysim"]:
                tourdata_new = prep_modedata_DaySim(tourdata)
            tourdata_new = prep_tourdata(tourdata_new, 
                                         perdata_new, 
                                         zone_district, 
                                         work_tours_only=True,
                                         excludeChildren5=False)

            write_tables("TourMode", 
                         tourdata_new, bkrcast_folder,
                         os.path.join(working_folder, "templates", "TourMode.csv"), 
                         dataset)

            logging.info(f"Summarizing Tour Mode Choice for BKRCast {bkrcast_folder}...Finished")
        logging.info(f"Total run time: {round((time.time() - start_time_tourmode) / 60, 2)} minutes")

    #####
    # This script generates summaries for NHTS and DaySim Tour Time fo Day models
    # Distributions of tour arrival and departure times along with those of durations at tour destinations are produced
    #####
    if runTourTOD:
        logging.info("Summarizing Tour Time of Day Choice...")
        start_time_tourtod = time.time()
        for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
            perdata = pd.read_csv(os.path.join(working_folder, "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
            tourdata = pd.read_csv(os.path.join(working_folder, "data", f"tours_{bkrcast_folder.split('_')[1]}.csv"))
            tourdata_new = prep_tourdata(tourdata, 
                                perdata, 
                                zone_district, 
                                work_tours_only=False,
                                excludeChildren5=True)
            write_tables("TourTOD", 
                         tourdata_new, bkrcast_folder,
                         os.path.join(working_folder, "templates", "TourTOD.csv"), 
                         dataset)
            
            logging.info(f"Summarizing Tour Time of Day for BKRCast {bkrcast_folder}...Finished")
        logging.info(f"Total run time: {round((time.time() - start_time_tourtod) / 60, 2)} minutes")

    #####
    # This script generates summaries for DaySim Trip mode models
    # Distributions of trip mode by tour mode are produced
    #####
    if runTripMode:
        logging.info("Summarizing Trip Mode Choice...")
        start_time_tripmode = time.time()
        for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
            perdata = pd.read_csv(os.path.join(working_folder, "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
            tourdata = pd.read_csv(os.path.join(working_folder, "data", f"tours_{bkrcast_folder.split('_')[1]}.csv"))
            tripdata = pd.read_csv(os.path.join(working_folder, "data", f"trips_{bkrcast_folder.split('_')[1]}.csv"))
            tourdata_new = prep_tourdata(tourdata, 
                                         perdata, 
                                         zone_district, 
                                         work_tours_only=False,
                                         excludeChildren5=True)
            # default is NHTS, prep_modedata_DaySim is only for Tampa/JAX
            if dataset == "survey":
                tourdata_new = prep_modedata_NHTS(tourdata_new)
                tripdata = prep_trmode_NHTS(tripdata)
            elif dataset in ["esd", "daysim"]:
                tourdata_new = prep_modedata_DaySim(tourdata)
                tripdata = prep_trmode_NHTS(tripdata)

            tripdata = tripdata.merge(tourdata_new[['hhno', 'pno', 'tour', 'tourmode', 'pdpurp2', 'pptyp', 'psexpfac']], 
                                      on=['hhno', 'pno', 'tour'], 
                                      how='left')

            # Fix PRS trips to have proper tourmode
            tripdata.loc[(tripdata['tripmode'] == 12) & (tripdata['dorp'] == 11), 'tourmode'] = 2
            tripdata.loc[(tripdata['tripmode'] == 12) & (tripdata['dorp'].isin([12, 13])), 'tourmode'] = 3
            tripdata.loc[(tripdata['tripmode'] == 13) & (tripdata['dorp'] == 21), 'tourmode'] = 1
            tripdata.loc[(tripdata['tripmode'] == 13) & (tripdata['dorp'] == 22), 'tourmode'] = 2
            tripdata.loc[(tripdata['tripmode'] == 13) & (tripdata['dorp'] == 23), 'tourmode'] = 3
            
            tripdata = tripdata[tripdata['pptyp'] < 8]
            write_tables("TripMode", 
                         tripdata, bkrcast_folder,
                         os.path.join(working_folder, "templates", "TripMode.csv"), 
                         dataset)

            logging.info(f"Summarizing Trip Mode Choice for BKRCast {bkrcast_folder}...Finished")
        logging.info(f"Total run time: {round((time.time() - start_time_tripmode) / 60, 2)} minutes")

    #####
    # This script generates summaries for DaySim Trip Time fo Day models
    # Distributions of trip arrival and departure times along with those of durations at trip destinations are produced
    #####
    if runTripTOD:
        logging.info("Summarizing Trip Time of Day Choice...")
        start_time_triptod = time.time()
        for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
            perdata = pd.read_csv(os.path.join(working_folder, "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
            tripdata = pd.read_csv(os.path.join(working_folder, "data", f"trips_{bkrcast_folder.split('_')[1]}.csv"))
            tripdata_new = prep_tripdata(tripdata, perdata, zone_district, excludeChildren5=True)
            write_tables("TripTOD", 
                         tripdata_new, bkrcast_folder,
                         os.path.join(working_folder, "templates", "TripTOD.csv"), 
                         dataset)

            logging.info(f"Summarizing Trip Time of Day for BKRCast {bkrcast_folder}...Finished")
        logging.info(f"Total run time: {round((time.time() - start_time_triptod) / 60, 2)} minutes")


    elapsed_minutes = round((time.time() - start_time) / 60, 2)
    logging.info(f"Total run time: {elapsed_minutes} minutes")
    logger.info("All processing completed in %.2f seconds total.", time.time() - start_time)


if __name__ == '__main__':
    main()