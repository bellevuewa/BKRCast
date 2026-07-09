import array as _array
import datetime
import inro.emme.matrix as ematrix
import json
import numpy as np
import pandas as pd
import os,sys
import h5py
import toml

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import * 
import emme_configuration as emme_config
import input_configuration as bkr_config                                   
import accessibility.accessibility_configuration as access_config
import data_wrangling

def find_closest_horizon_year(list_years,input_year):
    if not list_years:
        return None

    horizon_year = min(list_years, key = lambda x: abs(x - input_year))

    return horizon_year                      

def calc_fric_fac(cost_skim, dist_skim, _coeff_df, selected_zones):
    ''' Calculate friction factors for all trip purposes '''
    friction_fac_dic = {}
    for index, row in _coeff_df.iterrows():
        friction_fac_dic[row['purpose']] = np.exp((row['coefficient_value'])*((cost_skim + dist_skim) / 10))
        
    return friction_fac_dic

def load_matrices_to_emme(trip_table_in, home_based_flag, trip_purps, fric_facs, my_project):
    ''' Loads data to Emme matrices: Ps and As and friction factor by trip purpose.
        Also initializes empty trip distribution and O-D result tables. '''

    # Create Emme matrices if they don't already exist
    for purpose in trip_purps:
        print(purpose)

        for p_a in ['pro', 'att']:
            trips = np.array(trip_table_in[home_based_flag + purpose + p_a])
            my_project.matrix_to_emme(trips, home_based_flag + str(purpose)+ p_a , home_based_flag + str(purpose) + p_a, "ORIGIN")            
            np.savetxt(os.path.join(emme_config.supplemental_loc, f'{home_based_flag}+{purpose}{p_a}.csv'), trips, delimiter = ',', fmt = '%.2f')            

        # Load friction factors by trip purpose
        fri_fac = fric_facs[purpose]
        my_project.matrix_to_emme(fri_fac, home_based_flag + purpose + "fri", home_based_flag + str(purpose) + "friction factors", 'FULL')        

def calculate_daily_rec_bike_trips(trip_purps, home_based_flag, my_project):
    for purp in trip_purps:
        my_project.matrix_calculator(result = f'mf{home_based_flag}{purp}od', expression = f"mf{home_based_flag}{purp}dis + mf{home_based_flag}{purp}dis'")            

def balance_matrices(trip_purps, home_based_flag, my_project, partition):
    ''' Balances productions and attractions by purpose for all internal zones '''

    for purpose in trip_purps:
        # For friction factors, set 0s to TAZs other than the park list provided in rec prod/attr list. Also set 0 to the matrix diagnoal.
        my_project.matrix_calculator(result = 'mf' + home_based_flag + purpose + 'fri', expression = '0', 
                                 constraint_by_zone_origins = 'all',
                                 constraint_by_zone_destinations = f'{partition}0') 
        my_project.matrix_calculator(result = 'mf' + home_based_flag + purpose + 'fri', expression = '0', 
                                 constraint_by_zone_origins = f'{partition}0',
                                 constraint_by_zone_destinations = 'all') 
        
        my_project.matrix_calculator(result = 'mf' + home_based_flag + purpose + 'fri', expression = 'mf' + home_based_flag + purpose + 'fri' + '* (p!=q)') 
        print("create P-A table, for purpose: " + str(purpose))
        my_project.matrix_balancing(results_od_balanced_values = 'mf' + home_based_flag + purpose + 'dis', 
                                    od_values_to_balance = 'mf' + home_based_flag + purpose + 'fri', 
                                    origin_totals = 'mo' + home_based_flag + purpose + 'pro', 
                                    destination_totals = 'md' + home_based_flag + purpose + 'att', 
                                    constraint_by_zone_destinations = f'{partition}1', 
                                    constraint_by_zone_origins = 'all')
        # replace NaN with o in the matrix
        nparray = my_project.bank.matrix(f'mf{home_based_flag}{purpose}dis').get_numpy_data()
        nparray[np.isnan(nparray)] = 0
        my_project.bank.matrix(f'mf{home_based_flag}{purpose}dis').set_numpy_data(nparray)
        

def initialize_matrix(home_based, trip_purps, my_project):
    matrix_name_list = [matrix.name for matrix in my_project.bank.matrices()]
    zones = my_project.current_scenario.zone_numbers
    for purpose in trip_purps:
        if f'{home_based+purpose}pro' in matrix_name_list:
            my_project.delete_matrix(f'{home_based+purpose}pro')
        my_project.create_matrix(f'{home_based+purpose}pro', f'{home_based + purpose} productions', "ORIGIN")                               

        if f'{home_based+purpose}att' in matrix_name_list:
            my_project.delete_matrix(f'{home_based+purpose}att')
        my_project.create_matrix(f'{home_based+purpose}att', f'{home_based+purpose} attractions', "DESTINATION")                               

        if f'{home_based+purpose}fri' in matrix_name_list:
            my_project.delete_matrix(f'{home_based+purpose}fri')
        my_project.create_matrix(f'{home_based+purpose}fri', f'{home_based+purpose} friction factors', "FULL")                               

        if f'{home_based+purpose}dis' in matrix_name_list:
            my_project.delete_matrix(f'{home_based+purpose}dis')
        my_project.create_matrix(f'{home_based+purpose}dis', f'{home_based+purpose} P-A table', "FULL")                               

        if f'{home_based+purpose}od' in matrix_name_list:
            my_project.delete_matrix(f'{home_based+purpose}od')
        my_project.create_matrix(f'{home_based+purpose}od', f'{home_based+purpose} O-D trip table', "FULL")     

        if f'{purpose}od' in matrix_name_list:  
            my_project.delete_matrix(f'{purpose}od')
        my_project.create_matrix(f'{purpose}od', f'{purpose} O-D trip table (hb + nhb)', "FULL")                        

def split_rec_bike_by_tod(recb_tod_factors, home_based_flag, daily_recb_matrix_name, my_project):
    ''' Split daily rec bike trips to different time periods based on factors in recb_tod_factors '''
    # recb_tod_factors: dataframe with columns 'time_of_day' and 'value'
    # home_based_flag: 'hb' or 'nhb'
    # daily_recb_matrix_name: name of the daily rec bike trip matrix, without 'mf' prefix
    matrix_dict = {}
    recb_daily_od_np = my_project.bank.matrix(daily_recb_matrix_name).get_numpy_data()

    for tod in recb_tod_factors['time_of_day'].unique():
        tod_fac = recb_tod_factors.loc[recb_tod_factors['time_of_day'] == tod, 'value'].values[0]
        recb_tod_np = recb_daily_od_np * tod_fac
        matrix_dict[f'{tod}'] = recb_tod_np 
        my_project.matrix_to_emme(recb_tod_np, f'{home_based_flag}recb_{tod}', f'{home_based_flag} rec bike od at {tod}', 'FULL')    
    
    return matrix_dict                                    

def export_recb_trips(path, matrix_dict):
    mode_lookup = {'recb': 'recb'}    
    for tod in matrix_dict.keys():
        print(f'exporting rec bike trips for time period: {tod}') 
        with h5py.File(os.path.join(path, f'{tod}.h5'), 'a') as my_store:
            table_name = mode_lookup['recb']
            if table_name in my_store:
                del my_store[table_name]                                        
            my_store.create_dataset(mode_lookup['recb'], data = matrix_dict[tod], compression = 'gzip')                         
    
def calculate_daily_bike_trips():
   # calculate daily inbound and outbound bike trips
    daily_bike_array_initialized = False
    my_project = EmmeProject(emme_config.project)
    for key, value in emme_config.sound_cast_net_dict.items():
        my_project.change_active_database(key)
        my_project.set_primary_scenario('1002')
        # use zone numbers of pm databank as zone size to create numpy array
        if daily_bike_array_initialized == False:
            zones = my_project.current_scenario.zone_numbers # list of zone numbers
            zonesDim = len(zones)
            daily_bike_array = np.zeros((zonesDim, zonesDim), dtype = np.float64)
            daily_bike_array_initialized = True
        # calculate mo and md of bike trip table mf23 'bike'
        bike_array = my_project.bank.matrix('mfbike').get_numpy_data()
        daily_bike_array += bike_array

    my_project.closeDesktop()
    return daily_bike_array, zones

def calculate_tod_rec_bike_trips_in_parallel(parallel_instances, hb_rec_bike_prod_attr_df, nhb_recb_prod_attr_df):
    '''
        EMME modeller can only be opened oncce in one session. To avoid unexpected crash, we need to run distribution, and TOD in
        a separate process.

    '''
    from multiprocessing import Pool 
    with Pool(processes=parallel_instances) as pool:
        pool.starmap(calculate_tod_rec_bike_trips, zip([hb_rec_bike_prod_attr_df.copy()], [nhb_recb_prod_attr_df.copy()]))

def calculate_tod_rec_bike_trips(hb_rec_bike_prod_attr_df, nhb_rec_bike_prod_attr_df):
    ### Distribution ####
    coeff_df = pd.read_csv(os.path.join(bkr_config.input_folder_for_supplemental, 'rec_bike_gravity_model_coefficients.csv'))
    trip_purpose_list = ['recb']

    # skims
    am_bkat_skim = data_wrangling.load_skims(emme_config.am_skim_file_loc, mode_name = 'mfbkat', divide_by_100 = True)# regular bike actual time
    pm_bkat_skim = data_wrangling.load_skims(emme_config.pm_skim_file_loc, mode_name = 'mfbkat', divide_by_100 = True) 
    am_bdist_skim = data_wrangling.load_skims(emme_config.am_skim_file_loc, mode_name = 'mfbdist', divide_by_100 = True) # regular bike distance
    pm_bdist_skim = data_wrangling.load_skims(emme_config.pm_skim_file_loc, mode_name = 'mfbdist', divide_by_100 = True)

    bkat_skim = (am_bkat_skim + pm_bkat_skim) * 0.5
    bdist_skim = (am_bdist_skim + pm_bdist_skim) * 0.5

    # TAZs where home based rec bike trips will destine to
    hbattr_tazs = hb_rec_bike_prod_attr_df.loc[hb_rec_bike_prod_attr_df['hbrecbatt'] > 0, 'BKRCastTAZ'].to_list()
    complement_hbattr_tazs =  hb_rec_bike_prod_attr_df.loc[hb_rec_bike_prod_attr_df['hbrecbatt'] == 0, 'BKRCastTAZ'].to_list()
    hbprod_tazs = hb_rec_bike_prod_attr_df.loc[hb_rec_bike_prod_attr_df['hbrecbpro'] > 0, 'BKRCastTAZ'].to_list()
    # Compute friction factors by trip purpose
    fric_facs = calc_fric_fac(bkat_skim, bdist_skim, coeff_df.loc[coeff_df['purpose'] == 'recb'], hb_rec_bike_prod_attr_df['BKRCastTAZ'].to_numpy())

    print('Split daily rec bike to different TOD')
    tod_fac = pd.read_csv(os.path.join(input_config.input_folder_for_supplemental, 'rec_bike_tod_factors.csv'))
    recb_tod_fac = tod_fac[tod_fac['mode'] == 'recb']    

    my_project = EmmeProject(emme_config.supplemental_project)

    # process home based rec bikes
    print('Processing home based rec bike trips...')
    # initialize matrices
    initialize_matrix('hb', trip_purpose_list, my_project)

    # create a partition gd housing tazs in which parks will generate rec bike trips    
    my_project.create_partition('gd', 'TAZ for home based rec bike', {1:hbattr_tazs})    

    load_matrices_to_emme(hb_rec_bike_prod_attr_df, 'hb', trip_purpose_list, fric_facs, my_project)
    my_project.matrix_to_emme(bkat_skim, "bkat", 'bike actual time (avg of am and pm)', 'FULL')
    my_project.matrix_to_emme(bdist_skim, "bdist", 'bike travel distance (avg of am and pm)', 'FULL')
            
    balance_matrices(trip_purpose_list, 'hb', my_project, 'gd')
    calculate_daily_rec_bike_trips(trip_purpose_list, 'hb', my_project)    

    #### process non-home based rec bikes
    print('processing non-home based rec bike trips...')
    initialize_matrix('nhb', trip_purpose_list, my_project)
    nhbattr_tazs = nhb_rec_bike_prod_attr_df.loc[nhb_rec_bike_prod_attr_df['nhbrecbatt'] > 0, 'BKRCastTAZ'].to_list()
    my_project.create_partition('ge', 'TAZ for non-home based rec bike', {1:nhbattr_tazs})
    load_matrices_to_emme(nhb_rec_bike_prod_attr_df, 'nhb', trip_purpose_list, fric_facs, my_project)
    balance_matrices(trip_purpose_list, 'nhb', my_project, 'ge')
    calculate_daily_rec_bike_trips(trip_purpose_list, 'nhb', my_project)

    # mf'recbod' = mf'hbrecbod' + mf'nhbrecbod'
    my_project.matrix_calculator(result = 'mfrecbod', expression = 'mfhbrecbod + mfnhbrecbod')

    # split rec bike trips by time of day factors
    recb_tod_matrices_dict = split_rec_bike_by_tod(recb_tod_fac, '', 'recbod', my_project)
    
    export_recb_trips(emme_config.supplemental_loc, recb_tod_matrices_dict)

    my_project.closeDesktop()

def calculate_rec_bike_prod_attr(daily_outbound_bike, rec_bike_type, rec_bike_rate, emme_taz_list):
    ''' Calculate recreational bike productions and attractions for home based and non-home based trips 
    daily_outbound_bike: daily outbound bike trips from TAZ
    rec_bike_type: 'home_based' or 'non_home_based'
    rec_bike_rate: ratio of rec bike trips over regular bike trips
    emme_taz_list: list of TAZs in Emme
    '''
    # load accessibility by TAZ file
    accessibility_df = pd.read_csv(os.path.join(access_config.report_bikes_output_location, 'TAZ_bike_accessibility.csv'))
    

    recbike_df = pd.DataFrame({'BKRCastTAZ': emme_taz_list})

    # county_lookup_df = pd.read_csv(os.path.join(bkr_config.project_folder, bkr_config.districtfile))
    # pierce_kitsap_county_df = county_lookup_df.loc[(county_lookup_df['County'] == 'Pierce') | (county_lookup_df['County'] == 'Kitsap')]

    if rec_bike_type == 'home_based':
        home_based_flag = 'hb'
        # calculate factored recreational bike production for home based (daily)
        daily_rec_bike_prod_sries = daily_outbound_bike * rec_bike_rate * 0.5
        daily_rec_bike_prod_df = pd.DataFrame(daily_rec_bike_prod_sries, columns = [f'{home_based_flag}recbpro'])
        # daily_rec_bike_prod_df.loc[daily_rec_bike_prod_df.index.isin(pierce_kitsap_county_df['TAZ']), f'{home_based_flag}recbpro'] = 0
        total_daily_rec_bike_prod = daily_rec_bike_prod_df[f'{home_based_flag}recbpro'].sum()

        # calculate hhs by TAZ,
        parcels_df = data_wrangling.load_parcel_data_without_JBLM_jobs(os.path.join(bkr_config.parcels_file_folder, access_config.parcels_file_name))
        daily_rec_bike_prod = parcels_df[['TAZ_P', 'HH_P']].groupby('TAZ_P').sum()
        # remove TAZ for Pierce and Kitsap counties
        # daily_rec_bike_prod.loc[daily_rec_bike_prod.index.isin(pierce_kitsap_county_df['TAZ']), 'HH_P'] = 0
        daily_rec_bike_prod['hhshare'] = daily_rec_bike_prod['HH_P'] / daily_rec_bike_prod['HH_P'].sum()
        daily_rec_bike_prod[f'{home_based_flag}recbpro'] = total_daily_rec_bike_prod * daily_rec_bike_prod['hhshare']
        daily_rec_bike_prod.fillna(0, inplace = True)

        # calculate rec bike attraction for home based
        daily_rec_bike_attr = accessibility_df[['BKRCastTAZ', 'share']].copy()
        daily_rec_bike_attr[f'{home_based_flag}recbatt'] = total_daily_rec_bike_prod * daily_rec_bike_attr['share']
        daily_rec_bike_attr.fillna(0, inplace = True)
    else:
        home_based_flag = 'nhb'
        # calculate factored recreational bike production for non-home based (daily)
        total_daily_rec_bike_prod = (daily_outbound_bike * rec_bike_rate * 0.5).sum()
        daily_rec_bike_prod = accessibility_df[['BKRCastTAZ', 'share']].copy().set_index('BKRCastTAZ')
        daily_rec_bike_prod[f'{home_based_flag}recbpro'] = total_daily_rec_bike_prod * daily_rec_bike_prod['share']
        daily_rec_bike_prod.fillna(0, inplace = True)
        # rec bike attractions are the same as productions, all from park to park based on their share of accessibility
        # we could imrpove the accessibility calculation later        
        daily_rec_bike_attr = accessibility_df[['BKRCastTAZ', 'share']].copy()
        daily_rec_bike_attr[f'{home_based_flag}recbatt'] = total_daily_rec_bike_prod * daily_rec_bike_attr['share']
        daily_rec_bike_attr.fillna(0, inplace = True)

    recbike_df = recbike_df.merge(daily_rec_bike_prod, left_on = 'BKRCastTAZ', right_index = True, how = 'left')
    recbike_df = recbike_df.merge(daily_rec_bike_attr, left_on = 'BKRCastTAZ', right_on = 'BKRCastTAZ', how = 'left')
    recbike_df.fillna(0, inplace = True)
    print(f'total daily {rec_bike_type} rec bike production: {total_daily_rec_bike_prod}')
    recbike_df.to_csv(os.path.join(emme_config.supplemental_loc, f'{rec_bike_type}_daily_rec_bike_prod_attr.csv'), index = False)

    return recbike_df


def main():
    print('Calculating recreational bike trips...')    
    balance_to_production = ['recb'] 
    rec_rates = toml.load(os.path.join(bkr_config.input_folder_for_supplemental, 'rec_bike_rates.toml'))

    # rates from NHTS 2017
    home_based_rec_bike_rate = rec_rates['home_based_rec_bike']
    hbrecb_ratio_to_regular_bike = home_based_rec_bike_rate / (1 - home_based_rec_bike_rate)
    non_home_based_rec_bike_rate = rec_rates['non_home_based_rec_bike']
    nhbrecb_ratio_to_regular_bike = non_home_based_rec_bike_rate / (1 - non_home_based_rec_bike_rate)
    
    daily_bike_array, zones = calculate_daily_bike_trips()
    taz_to_index_lookup = dict((value,index) for index,value in enumerate(zones))
    index_to_taz_lookup = dict((index,value) for index,value in enumerate(zones))

    # outbound rec bike trips from home
    # change the index from 0 based to TAZ number
    daily_outbound_bike = pd.Series(daily_bike_array.sum(axis = 1)) # 0 based index
    daily_outbound_bike.index = daily_outbound_bike.index.map(index_to_taz_lookup)

    print('Calculating recreational bike productions and attractions...')
    hbrecbike_df = calculate_rec_bike_prod_attr(daily_outbound_bike, 'home_based', hbrecb_ratio_to_regular_bike, zones)
    nhbrecbike_df = calculate_rec_bike_prod_attr(daily_outbound_bike, 'non_home_based', nhbrecb_ratio_to_regular_bike, zones)
 
    print('Balancing recreational bike trips...')
    # balance recreational bike attractions to productions.
    hbrecbike_df = data_wrangling.balance_trips(hbrecbike_df, 'hb', balance_to_production, 'pro')
    nhbrecbike_df = data_wrangling.balance_trips(nhbrecbike_df, 'nhb', balance_to_production, 'pro')

    print('Calculating recreational bike daily trips and by time of day...')
    calculate_tod_rec_bike_trips_in_parallel(1, hbrecbike_df, nhbrecbike_df)


if __name__ == "__main__":
    run_context = os.getenv('RUN_CONTEXT') # chained if this script is called from another script, otherwise it is standalone
    if run_context == 'chained':
        meta_data = False
    else:
        meta_data = True

    logger, start_time = data_wrangling.open_main_logger(meta_data, 'Recreational Bike')
    logger.info(f"Running script: {os.path.basename(__file__)} %s", " ".join(sys.argv[1:]))
    main()
    end_time = datetime.datetime.now()
    elapsed_total = end_time - start_time
    logger.info(f'Total run time: {elapsed_total}')