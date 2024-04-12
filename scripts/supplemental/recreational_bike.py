import array as _array
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import json
import numpy as np
import pandas as pd
import os,sys
import h5py

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

def matrix_to_emme(matrix, mfname, description, matrix_type, my_project):
    matrix_name_list = [matrix.name for matrix in my_project.bank.matrices()]
    if mfname not in matrix_name_list:
        my_project.create_matrix(mfname, description, matrix_type) 
    
    matrix_id = my_project.bank.matrix(mfname).id    
    my_project.bank.matrix(matrix_id).set_numpy_data(matrix, my_project.current_scenario)
    
def load_matrices_to_emme(trip_table_in, trip_purps, fric_facs, my_project):
    ''' Loads data to Emme matrices: Ps and As and friction factor by trip purpose.
        Also initializes empty trip distribution and O-D result tables. '''

    # Create Emme matrices if they don't already exist
    for purpose in trip_purps:
        print(purpose)

        for p_a in ['pro', 'att']:
            trips = np.array(trip_table_in[purpose + p_a])
            matrix_to_emme(trips, str(purpose)+ p_a , str(purpose) + p_a, "ORIGIN", my_project)            
            np.savetxt(os.path.join(emme_config.supplemental_loc, f'{purpose}{p_a}.csv'), trips, delimiter = ',', fmt = '%.2f')            

        # Load friction factors by trip purpose
        fri_fac = fric_facs[purpose]
        matrix_to_emme(fri_fac, purpose + "fri", str(purpose) + "friction factors", 'FULL', my_project)        

def calculate_daily_rec_bike_trips(trip_purps,  my_project):
    for purp in trip_purps:
        my_project.matrix_calculator(result = f'mf{purp}od', expression = f"mf{purp}dis + mf{purp}dis'")            

def balance_matrices(trip_purps, my_project):
    ''' Balances productions and attractions by purpose for all internal zones '''

    for purpose in trip_purps:
        # For friction factors, set 0s to TAZs other than the park list provided in rec prod/attr list. Also set 0 to the matrix diagnoal.
        my_project.matrix_calculator(result = 'mf' + purpose + 'fri', expression = '0', 
                                 constraint_by_zone_origins = 'all',
                                 constraint_by_zone_destinations = 'gd0') 
        my_project.matrix_calculator(result = 'mf' + purpose + 'fri', expression = '0', 
                                 constraint_by_zone_origins = 'gd0',
                                 constraint_by_zone_destinations = 'all') 
        
        my_project.matrix_calculator(result = 'mf' + purpose + 'fri', expression = 'mf' + purpose + 'fri' + '* (p!=q)') 
        print("create P-A table, for purpose: " + str(purpose))
        my_project.matrix_balancing(results_od_balanced_values = 'mf' + purpose + 'dis', 
                                    od_values_to_balance = 'mf' + purpose + 'fri', 
                                    origin_totals = 'mo' + purpose + 'pro', 
                                    destination_totals = 'md' + purpose + 'att', 
                                    constraint_by_zone_destinations = 'gd1', 
                                    constraint_by_zone_origins = 'gd1')

def initialize_matrix(trip_purps, my_project):
    matrix_name_list = [matrix.name for matrix in my_project.bank.matrices()]
    zones = my_project.current_scenario.zone_numbers
    for purpose in trip_purps:
        if f'{purpose}pro' in matrix_name_list:
            my_project.delete_matrix(f'{purpose}pro')
        my_project.create_matrix(f'{purpose}pro', f'{purpose} productions', "ORIGIN")                               

        if f'{purpose}att' in matrix_name_list:
            my_project.delete_matrix(f'{purpose}att')
        my_project.create_matrix(f'{purpose}att', f'{purpose} attractions', "DESTINATION")                               

        if f'{purpose}fri' in matrix_name_list:
            my_project.delete_matrix(f'{purpose}fri')
        my_project.create_matrix(f'{purpose}fri', f'{purpose} friction factors', "FULL")                               

        if f'{purpose}dis' in matrix_name_list:
            my_project.delete_matrix(f'{purpose}dis')
        my_project.create_matrix(f'{purpose}dis', f'{purpose} P-A table', "FULL")                               

        if f'{purpose}od' in matrix_name_list:
            my_project.delete_matrix(f'{purpose}od')
        my_project.create_matrix(f'{purpose}od', f'{purpose} O-D trip table', "FULL")                               

def split_rec_bike_by_tod(recb_tod_factors, my_project):
    matrix_dict = {}
    recb_daily_od_np = my_project.bank.matrix('recbod').get_numpy_data()

    for tod in recb_tod_factors['time_of_day'].unique():
        tod_fac = recb_tod_factors.loc[recb_tod_factors['time_of_day'] == tod, 'value'].values[0]
        recb_tod_np = recb_daily_od_np * tod_fac
        matrix_dict[f'{tod}'] = recb_tod_np 
        matrix_to_emme(recb_tod_np, f'recb_{tod}', f'rec bike od at {tod}', 'FULL', my_project)    
    
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
    
def main():
    print('Calculating recreational bike trips...')    
    trip_nhb_prod = ['recbpro']    
    trip_nhb_attr = ['recbatt'] 
    balance_to_production = ['recb'] 
    # annual growth assumption, placeholder for now. will need to keep this assumption somewhere in an input file. 
    annual_nhb_rec_bike_growth_rate = 0.015
    
    df_nhb_recbike = pd.read_csv(os.path.join(bkr_config.input_folder_for_supplemental, 'recreational_bike_prod_attr.csv'))

    # calculate prod/attr for the model_year using compound rate    
    list_year = df_nhb_recbike['Year'].unique().tolist()
    nhb_recbike_year = find_closest_horizon_year(list_year, int(input_config.model_year))
    df_nhb_recbike_model_year = df_nhb_recbike.loc[df_nhb_recbike['Year'] == nhb_recbike_year].copy()
    df_nhb_recbike_model_year['Year'] = int(input_config.model_year)     
    scaling_factor = pow(1 + annual_nhb_rec_bike_growth_rate, (int(input_config.model_year) - nhb_recbike_year))             
    print(f'use rec bike prod/attr in year {nhb_recbike_year}, compounded growth rate: {scaling_factor - 1}')     
    df_nhb_recbike_model_year[trip_nhb_attr + trip_nhb_prod] *= scaling_factor
    data_wrangling.balance_trips(df_nhb_recbike_model_year, balance_to_production, 'pro')
    print('Recreational bike attractions are balanced to production.')
    df_nhb_recbike_model_year.to_csv(os.path.join(emme_config.supplemental_loc, 'recreational_bike_balanced_trip_ends.csv'), index = False)

    ### Distribution ####
    coeff_df = pd.read_csv(os.path.join(bkr_config.input_folder_for_supplemental, 'rec_bike_gravity_model_coefficients.csv'))
    trip_purpose_list = ['recb']
    my_project = EmmeProject(emme_config.supplemental_project)
    initialize_matrix(trip_purpose_list, my_project)
    # create a partition gd housing tazs in which parks will generate rec bike trips    
    my_project.create_partition('gd', 'parks for rec bike', {1:df_nhb_recbike_model_year['BKRCastTAZ'].to_list()})    
    
    # BKRCastTAZ field in trip_table is not consecutive number. Must reformat it to be compatible with EMME matrix
    zones_df = pd.DataFrame(my_project.current_scenario.zone_numbers, columns = {'BKRCastTAZ'})         
    trip_table = pd.merge(zones_df, df_nhb_recbike_model_year[['BKRCastTAZ', 'recbpro', 'recbatt']], on = 'BKRCastTAZ', how = 'left') 
    trip_table.fillna(0, inplace = True)

    am_bkat_skim = data_wrangling.load_skims(emme_config.am_skim_file_loc, mode_name = 'mfbkat', divide_by_100 = True)
    pm_bkat_skim = data_wrangling.load_skims(emme_config.pm_skim_file_loc, mode_name = 'mfbkat', divide_by_100 = True)
    am_bkpt_skim = data_wrangling.load_skims(emme_config.am_skim_file_loc, mode_name = 'mfbkpt', divide_by_100 = True)
    pm_bkpt_skim = data_wrangling.load_skims(emme_config.pm_skim_file_loc, mode_name = 'mfbkpt', divide_by_100 = True)
    
    bkat_skim = (am_bkat_skim + pm_bkat_skim) * 0.5
    bkpt_skim = (am_bkpt_skim + pm_bkpt_skim) * 0.5

    # Compute friction factors by trip purpose
    fric_facs = calc_fric_fac(bkat_skim, bkpt_skim, coeff_df.loc[coeff_df['purpose'] == 'recb'], df_nhb_recbike_model_year['BKRCastTAZ'].to_numpy())
    load_matrices_to_emme(trip_table, trip_purpose_list, fric_facs, my_project)
    matrix_to_emme(bkat_skim, "bkat", 'bike actual time (avg of am and pm)', 'FULL', my_project)
    matrix_to_emme(bkpt_skim, "bkpt", 'bike perceived time (avg of am and pm)', 'FULL', my_project)
            
    balance_matrices(trip_purpose_list, my_project)
    calculate_daily_rec_bike_trips(trip_purpose_list, my_project)    

    print('Split daily rec bike to different TOD')
    tod_fac = pd.read_csv(os.path.join(input_config.input_folder_for_supplemental, 'rec_bike_tod_factors.csv'))
    recb_tod_fac = tod_fac[tod_fac['mode'] == 'recb']    
    recb_tod_matrices_dict = split_rec_bike_by_tod(recb_tod_fac, my_project)
    
    export_recb_trips(emme_config.supplemental_loc, recb_tod_matrices_dict)
    my_project.closeDesktop()


if __name__ == "__main__":
    main()