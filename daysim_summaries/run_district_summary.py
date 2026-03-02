import logging
import os
import time
import numpy as np
import pandas as pd

from scripts.h5toDF import convert
from config import *
from input_configuration import guidefile, project_folder, base_year

# create a logger that writes to a file in the daysim_summaries folder
log_file = os.path.join(project_folder, "daysim_summaries", "daysim_summary.log")
logger = logging.getLogger("daysim_summary")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)

logger.info(f"Processing {dataset} dataset...")
logger.info(f"Have set to use {in_out_filter_type} to filter in/out BKR area.")

#####
# Note that in this analysis we can only use cloned trip data because some information exists associated with tour data
# Thus there might have total discrepency from the number of trips in this analysis and the full survey
#####

def read_data():
    """Read the survey data or the Daysim outputs

    Returns:
        Returns a list of dataframe.
    """
    #####
    # File paths
    #####
    if dataset == 'survey':
        logger.info('Processing survey files...')
        # load data
        logger.info("Reading inputs ...")
        if int(base_year) in [2013, 2014]:
            fname = os.path.join(project_folder, 'inputs', 'model', 'survey', 'survey.h5')
            file = convert(fname, guidefile, '2013Survey')
            # get the data from survey
            hhs = file['Household']
            persons = file['Person']
            person_day = file['PersonDay']
            tours = file['Tour']
            trips = file['Trip']            
            guide_trip = pd.read_excel(os.path.join(project_folder, "inputs", "model", "CatVarDict.xlsx"), sheet_name='Trip')
            guide_person = pd.read_excel(os.path.join(project_folder, "inputs", "model", "CatVarDict.xlsx"), sheet_name='Person')
            guide_tour = pd.read_excel(os.path.join(project_folder, "inputs", "model", "CatVarDict.xlsx"), sheet_name='Tour')
            
            for col in ['opurp', 'dpurp', 'oadtyp', 'dadtyp']:
                icol = guide_trip.columns.get_loc(col)
                col_df = guide_trip.iloc[:, icol:icol+2]
                col_df = col_df.dropna()
                trips[f'_{col}'] = trips[col]
                trips[col] = trips[f'_{col}'].map(dict(zip(col_df.iloc[:, 1], col_df.iloc[:, 0])))
                
        elif int(base_year) in [2023, 2024] and dataset == "survey":
            fname_full = os.path.join(project_folder, 'inputs', 'model', 'survey', 'survey_2023_full.h5')
            fname = os.path.join(project_folder, 'inputs', 'model', 'survey', 'survey_2023.h5')
            file_full = convert(fname_full, guidefile, '2023FullSurvey')
            file = convert(fname, guidefile, '2023Survey')
            # get the data from survey
            hhs = file_full['Household']
            persons = file_full['Person']
            person_day = file['PersonDay_cloned']
            trips = file['Trip_cloned']
            trips_full = file_full['Trip']
            tours = file['Tour_cloned']

            guide_trip = pd.read_excel(os.path.join(project_folder, "inputs", "model", "CatVarDict_2023.xlsx"), sheet_name='Trip')
            guide_person = pd.read_excel(os.path.join(project_folder, "inputs", "model", "CatVarDict_2023.xlsx"), sheet_name='Person')
            guide_tour = pd.read_excel(os.path.join(project_folder, "inputs", "model", "CatVarDict_2023.xlsx"), sheet_name='Tour')

            for tr in [trips, trips_full]:
                for col in ['opurp', 'dpurp', 'oadtyp', 'dadtyp', 'mode']:
                    icol = guide_trip.columns.get_loc(col)
                    col_df = guide_trip.iloc[:, icol:icol+2]
                    col_df = col_df.dropna()
                    tr[f'_{col}'] = tr[col]
                    tr[col] = tr[f'_{col}'].map(dict(zip(col_df.iloc[:, 1], col_df.iloc[:, 0])))

            trips = [trips, trips_full]
        
        for col in ['pptyp', 'pwtyp']:
            icol = guide_person.columns.get_loc(col)
            col_df = guide_person.iloc[:, icol:icol+2]
            col_df = col_df.dropna()
            persons[f'_{col}'] = persons[col]
            persons[col] = persons[f'_{col}'].map(dict(zip(col_df.iloc[:, 1], col_df.iloc[:, 0])))

        for col in ['pdpurp', 'tmodetp']:
            icol = guide_tour.columns.get_loc(col)
            col_df = guide_tour.iloc[:, icol:icol+2]
            col_df = col_df.dropna()
            tours[f'_{col}'] = tours[col]
            tours[col] = tours[f'_{col}'].map(dict(zip(col_df.iloc[:, 1], col_df.iloc[:, 0])))

    elif dataset == 'lodes':  # LODES puplic domain dataset, FIXME: leave the path here as we are using ESD file for BKRCase model
        logger.info('Processing Daysim output files (LODES)...')
        delim = '\t'
        wd = 'E:/Projects/Clients/bkr/model/bkrcast_tod_new_distbkr/outputs'
        hhs = pd.read_csv(os.path.join(wd, '_household.tsv'), sep=delim)
        persons = pd.read_csv(os.path.join(wd, '_person.tsv'), sep=delim)
        person_day = pd.read_csv(os.path.join(wd, '_person_day.tsv'), sep=delim)
        tours = pd.read_csv(os.path.join(wd, '_tour.tsv'), sep=delim)
        trips = pd.read_csv(os.path.join(wd, '_trip.tsv'), sep=delim)
    elif dataset == 'esd':  # ESD land use dataset (BKRCast model)
        logger.info('Processing Daysim output files (ESD)...')
        delim = '\t'
        hhs = pd.read_csv(os.path.join(project_folder, 'outputs', 'daysim', '_household.tsv'), sep=delim)
        persons = pd.read_csv(os.path.join(project_folder, 'outputs', 'daysim', '_person.tsv'), sep=delim)
        person_day = pd.read_csv(os.path.join(project_folder, 'outputs', 'daysim', '_person_day.tsv'), sep=delim)
        tours = pd.read_csv(os.path.join(project_folder, 'outputs', 'daysim', '_tour.tsv'), sep=delim)
        trips = pd.read_csv(os.path.join(project_folder, 'outputs', 'daysim', '_trip.tsv'), sep=delim)
    return hhs, persons, person_day, trips, tours


def data_filter(hhs, persons, person_day, trips_, tours):
    """_summary_

    Args:
        hhs (pd.DataFrame): output from read_data().
        persons (pd.DataFrame): output from read_data().
        person_day (pd.DataFrame): output from read_data().
        trips (pd.DataFrame): output from read_data().
        tours (pd.DataFrame): output from read_data().
    """
    logger.info("Running creation of in/out datasets...")
    start_filter = time.time()

    ext_in = '_inbkr'
    ext_out = '_outbkr'
    taz_corr = pd.read_csv(os.path.join(project_folder, 'inputs', 'model', 'TAZ_District_CrossWalk.csv'))

    #####
    # Filtering and write trips
    #####    
    # preprocess the hhno in the trip and tour dataframe
    if int(base_year) in [2023, 2024] and dataset == "survey":
        trips = trips_[0]
        trips_full = trips_[1]
        trips_full['hhno_'] = trips_full['hhno']
        trips_full['pno_'] = trips_full['pno']
        trips_full['pno'] = trips_full['pno'] - trips_full['hhno']*100
        trips_full = trips_full[trips_full['travdist']<200].copy(deep=True)
        trips['hhno_'] = trips['hhno'].astype(str)
        trips['hhno_'] = trips['hhno_'].str[:-1].astype('int64')
        tours['hhno_'] = tours['hhno'].astype(str)
        tours['hhno_'] = tours['hhno_'].str[:-1].astype('int64')
    else:
        trips = trips_
        trips['hhno_'] = trips['hhno']

    # save bkrcast_all data
    if int(base_year) in [2023, 2024] and dataset == "survey":
        trips_full.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips_full_all.csv"), 
                index=False)    
    trips.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips_all.csv"), 
                index=False)
    tours.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"tours_all.csv"), 
                 index=False)
    person_day.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"person_day_all.csv"), 
                 index=False)
    persons.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"persons_all.csv"), 
                 index=False)
    hhs.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"hhs_all.csv"), 
                 index=False)

    if in_out_filter_type == "trip":
        logger.info("Use trip OD to filter trips inside and outside of BKR area")
        
        trips_bkr = trips.merge(taz_corr, how='left', left_on='otaz', right_on='zone_id').\
            rename(columns={'district': 'o_district'})
        trips_bkr = trips_bkr.merge(taz_corr, how='left', left_on='dtaz', right_on='zone_id').\
            rename(columns={'district': 'd_district'})
        
        if int(base_year) in [2023, 2024] and dataset == "survey":
            trips_full_bkr = trips_full.merge(taz_corr, how='left', left_on='otaz', right_on='zone_id').\
                rename(columns={'district': 'o_district'})
            trips_full_bkr = trips_full_bkr.merge(taz_corr, how='left', left_on='dtaz', right_on='zone_id').\
                rename(columns={'district': 'd_district'})

        logger.info("Filtering trips ...")
        # outside BKR
        trips_out = trips_bkr[(trips_bkr["o_district"] != "BKR") & (trips_bkr["d_district"] != "BKR")]
        trips_out.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips{ext_out}.csv"), 
                         index=False)
                       

        # inside BKR
        trips_in = trips_bkr[(trips_bkr["o_district"] == "BKR") | (trips_bkr["d_district"] == "BKR")]
        trips_in.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips{ext_in}.csv"), 
                        index=False)
        
        if int(base_year) in [2023, 2024] and dataset == "survey":
            trips_full_out = trips_full_bkr[(trips_full_bkr["o_district"] != "BKR") & 
                                            (trips_full_bkr["d_district"] != "BKR")]
            trips_full_in = trips_full_bkr[(trips_full_bkr["o_district"] == "BKR") | 
                                           (trips_full_bkr["d_district"] == "BKR")]
            trips_full_out.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips_full{ext_out}.csv"), 
                            index=False)
            trips_full_in.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips_full{ext_in}.csv"), 
                            index=False)
        
    elif in_out_filter_type == "hh":
        logger.info("Use household to filter trips inside and outside of BKR area")

        hhs_mrg = hhs.merge(taz_corr, how="left", left_on="hhtaz", right_on="zone_id")
        hh_bkr = hhs_mrg[hhs_mrg["district"] == "BKR"]

        # filter trips by hhno
        logger.info("Filtering trips ...")

        # inside BKR
        trips_in = trips[trips["hhno_"].isin(hh_bkr['hhno'])]
        trips_in[trips.columns].to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips{ext_in}.csv"), 
                                       index=False)

        # outside BKR
        trips_out = trips[~trips["hhno_"].isin(hh_bkr['hhno'])]
        trips_out[trips.columns].to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips{ext_out}.csv"), 
                                        index=False)
        
        if int(base_year) in [2023, 2024] and dataset == "survey":
            trips_full_in = trips_full[trips_full["hhno_"].isin(hh_bkr['hhno'])]
            trips_full_in[trips_full.columns].to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips_full{ext_in}.csv"), 
                                        index=False)            
            trips_full_out = trips_full[~trips_full["hhno_"].isin(hh_bkr['hhno'])]
            trips_full_out[trips_full.columns].to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips_full{ext_out}.csv"), 
                                        index=False)

    #####
    # Filter and write tours
    #####
    logger.info("Filtering tours ...")
    # inside BKR
    tours_in = tours[tours['hhno'].isin(trips_in['hhno'])]
    tours_in.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"tours{ext_in}.csv"), 
                    index=False)
    # outside BKR
    tours_out = tours[tours['hhno'].isin(trips_out['hhno'])]
    tours_out.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"tours{ext_out}.csv"), 
                    index=False)

    #####
    # Filter and write households
    #####
    logger.info("Filtering households ...")
    # inside BKR
    hhs_in = hhs[hhs['hhno'].isin(trips_in['hhno_'])]
    hhs_in.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"hhs{ext_in}.csv"), 
                  index=False)
    # outside BKR
    hhs_out = hhs[hhs['hhno'].isin(trips_out['hhno_'])]
    hhs_out.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"hhs{ext_out}.csv"), 
                  index=False)

    #####
    # Filter and write persons
    #####
    logger.info("Filtering persons ...")
    # inside BKR
    persons_in = persons[persons['hhno'].isin(trips_in['hhno_'])]
    persons_in.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"persons{ext_in}.csv"), 
                  index=False)
    # outside BKR
    persons_out = persons[persons['hhno'].isin(trips_out['hhno_'])]
    persons_out.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"persons{ext_out}.csv"), 
                  index=False)
    
    #####
    # Filter and write person_day
    #####
    logger.info("Filtering person days ...")
    # inside BKR
    person_day_in = person_day[person_day['hhno'].isin(trips_in['hhno'])]
    person_day_in.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"person_day{ext_in}.csv"), 
                         index=False)
    # outside BKR
    person_day_out = person_day[person_day['hhno'].isin(trips_out['hhno'])]
    person_day_out.to_csv(os.path.join(project_folder, "daysim_summaries", "data", f"person_day{ext_out}.csv"), 
                  index=False)
    
    logger.info("Data processing completed in %.2f seconds total.", time.time() - start_filter)
    logger.info("Finished creating in/out bkr datasets...")


def district_summary_purp():
    time_start = time.time()

    # Read zone-district correspondence
    zone_district = pd.read_csv(os.path.join(project_folder, "inputs", "subarea_definition", "TAZ_subarea.csv"))
    file_parcel = os.path.join(project_folder, "outputs", "landuse", "buffered_parcels.txt")

    for bkrcast_folder in ['bkrcast_all', 'bkrcast_inbkr', 'bkrcast_outbkr']:
        logging.info(f"Running DaySim summaries for BKRCast ({bkrcast_folder.split('_')[1]})...")
        # set up output file paths
        outfile_district = os.path.join(project_folder, "daysim_summaries", bkrcast_folder, "district_summary.csv")
        outfile_mode = os.path.join(project_folder, "daysim_summaries", bkrcast_folder, "TL_mode.csv")
        outfile_ptype = os.path.join(project_folder, "daysim_summaries", bkrcast_folder, "summary_ptype.csv")
        if int(base_year) in [2023, 2024] and dataset == "survey":
            outfile_district_full = os.path.join(project_folder, "daysim_summaries", bkrcast_folder, "district_summary_full.csv")
            outfile_mode_full = os.path.join(project_folder, "daysim_summaries", bkrcast_folder, "TL_mode_full.csv")

        # read data
        hhs = pd.read_csv(os.path.join(project_folder, "daysim_summaries", "data", f"hhs_{bkrcast_folder.split('_')[1]}.csv"))
        persons = pd.read_csv(os.path.join(project_folder, "daysim_summaries", "data", f"persons_{bkrcast_folder.split('_')[1]}.csv"))
        tours = pd.read_csv(os.path.join(project_folder, "daysim_summaries", "data", f"tours_{bkrcast_folder.split('_')[1]}.csv"))
        trips = pd.read_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips_{bkrcast_folder.split('_')[1]}.csv"))
        if int(base_year) in [2023, 2024] and dataset == "survey":
            trips_full = pd.read_csv(os.path.join(project_folder, "daysim_summaries", "data", f"trips_full_{bkrcast_folder.split('_')[1]}.csv"))

        # preprocess
        trips = trips[(trips['travdist']>0) & (trips['travdist']<=200)].copy(deep=True)
        if int(base_year) in [2023, 2024] and dataset == "survey":
            trips['_hhno'] = trips['hhno'].astype(str)
            trips['_hhno'] = trips['_hhno'].str[:-1]
            trips['_hhno'] = trips['_hhno'].astype('int64')
            trips_full['_hhno'] = trips_full['hhno']
        else:
            trips['_hhno'] = trips['hhno']
        tours = tours[tours['hhno'].isin(trips['hhno'])].copy(deep=True)
        persons = persons[persons['hhno'].isin(trips['_hhno'])].copy(deep=True)
        hhs = hhs[hhs['hhno'].isin(trips['_hhno'])].copy(deep=True)

        persons['wrk_district'] = persons['pwtaz'].map(dict(zip(zone_district['BKRCastTAZ'], zone_district['DistrictFlowID'])))
        tours['d_district'] = tours['tdtaz'].map(dict(zip(zone_district['BKRCastTAZ'], zone_district['DistrictFlowID'])))

        if int(base_year) in [2023, 2024] and dataset == "survey":
            trips_full['temp'] = trips_full['travdist'] * trips_full['trexpfac']
            summary_mode_full = trips_full.groupby('mode')[['temp', 'trexpfac']].sum()
            summary_mode_full['avg_triplength'] = summary_mode_full['temp'] / summary_mode_full['trexpfac']
            mode_output_full = summary_mode_full[['avg_triplength']].reset_index()
            mode_output_full.columns = ['mode', 'avg_triplength']

        trips['temp'] = trips['travdist'] * trips['trexpfac']
        summary_mode = trips.groupby('mode')[['temp', 'trexpfac']].sum()        
        summary_mode['avg_triplength'] = summary_mode['temp'] / summary_mode['trexpfac']
        mode_output = summary_mode[['avg_triplength']].reset_index()
        mode_output.columns = ['mode', 'avg_triplength']

        if dataset in ['lodes', 'esd']:
            parcels = pd.read_csv(file_parcel, sep=" ")
            trips['otaz'] = trips['opcl'].map(dict(zip(parcels['parcelid'], parcels['taz_p'])))
            trips['dtaz'] = trips['dpcl'].map(dict(zip(parcels['parcelid'], parcels['taz_p'])))
            hhs['hhtaz'] = hhs['hhparcel'].map(dict(zip(parcels['parcelid'], parcels['taz_p'])))

        trips = trips.merge(hhs[['hhno', 'hhtaz']], left_on='_hhno', right_on='hhno', how='left', suffixes=('', '_hhs'))

        trips['o_district'] = trips['otaz'].map(dict(zip(zone_district['BKRCastTAZ'], zone_district['DistrictFlowID'])))
        trips['d_district'] = trips['dtaz'].map(dict(zip(zone_district['BKRCastTAZ'], zone_district['DistrictFlowID'])))
        trips = trips[(trips['opcl'] > 0) & (trips['dpcl'] > 0)]

        # define trip purpose: HBW, HBO, NHB
        trips['purp'] = np.where((trips['oadtyp'] == 1) & (trips['dpurp'] == 1) |
                                    (trips['dadtyp'] == 1) & (trips['opurp'] == 1), "HBW", "NHB")
        trips['purp'] = np.where((trips['oadtyp'] > 1) & (trips['dpurp'] == 1) |
                                    (trips['dadtyp'] > 1) & (trips['opurp'] == 1), "NBW", trips['purp'])
        trips['purp'] = np.where((trips['oadtyp'] == 1) & (trips['dpurp'] > 1) |
                                    (trips['dadtyp'] == 1) & (trips['opurp'] > 1), "HBO", trips['purp'])

        if int(base_year) in [2023, 2024] and dataset == "survey":
            trips_full['purp'] = np.where((trips_full['oadtyp'] == 1) & (trips_full['dpurp'] == 1) |
                                          (trips_full['dadtyp'] == 1) & (trips_full['opurp'] == 1), "HBW", "NHB")
            trips_full['purp'] = np.where((trips_full['oadtyp'] > 1) & (trips_full['dpurp'] == 1) |
                                          (trips_full['dadtyp'] > 1) & (trips_full['opurp'] == 1), "NBW", trips_full['purp'])
            trips_full['purp'] = np.where((trips_full['oadtyp'] == 1) & (trips_full['dpurp'] > 1) |
                                          (trips_full['dadtyp'] == 1) & (trips_full['opurp'] > 1), "HBO", trips_full['purp'])
        
            trips_full['o_district'] = trips_full['otaz'].map(dict(zip(zone_district['BKRCastTAZ'], zone_district['DistrictFlowID'])))
            trips_full['d_district'] = trips_full['dtaz'].map(dict(zip(zone_district['BKRCastTAZ'], zone_district['DistrictFlowID'])))
            trips_full = trips_full[(trips_full['opcl'] > 0) & (trips_full['dpcl'] > 0)]
            summary_district_full = trips_full.groupby(['o_district', 'd_district', 'purp'])['trexpfac'].sum().reset_index()
        
        summary_district = trips.groupby(['o_district', 'd_district', 'purp'])['trexpfac'].sum().reset_index()

        trips['trip_time'] = np.where(trips['half'] == 1, trips['arrtm'], trips['deptm'])
        trips['trip_tod'] = 'nt'
        trips.loc[(trips['trip_time'] >= 360) & (trips['trip_time'] < 540), 'trip_tod'] = 'am'  # 6-9 am
        trips.loc[(trips['trip_time'] >= 540) & (trips['trip_time'] < 930), 'trip_tod'] = 'md'  # 9-3:30 pm
        trips.loc[(trips['trip_time'] >= 930) & (trips['trip_time'] < 1110), 'trip_tod'] = 'pm'  # 3:30-6:30 pm

        trips['key'] = trips['hhno_'].astype(str) + "_" + trips['pno'].astype(str)
        persons['key'] = persons['hhno'].astype(str) + "_" + persons['pno'].astype(str)
        ptype_map = dict(zip(persons['key'], persons['pptyp']))
        trips['ptype'] = trips['key'].map(ptype_map)

        summary_stops = trips.groupby(['o_district', 'd_district', 'purp', 'trip_tod', 'ptype', 'dpurp'])['trexpfac'].sum().reset_index()

        # Save outputs
        mode_output.to_csv(outfile_mode, index=False)
        summary_stops.to_csv(outfile_ptype, index=False)
        summary_district.to_csv(outfile_district, index=False)

        if int(base_year) in [2023, 2024] and dataset == "survey":
            mode_output_full.to_csv(outfile_mode_full, index=False)
            summary_district_full.to_csv(outfile_district_full, index=False)
    
        logging.info(f"Finished summaries for BKRCast ({bkrcast_folder})...")
    logger.info("District summary completed in %.2f seconds total.", time.time() - time_start)
    

def main():
    # run the pipeflow
    start_all = time.time()
    hhs, persons, person_day, trips, tours = read_data()
    data_filter(hhs, persons, person_day, trips, tours)
    district_summary_purp()  # district_summary_purp.R and district_summary_ptype.R are equal
    logger.info("All programs completed in %.2f seconds total.", time.time() - start_all)


if __name__ == '__main__':
    main()
    