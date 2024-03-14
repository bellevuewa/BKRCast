import os, sys, shutil
from weakref import finalize
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
import pandas as pd
from colorama import Fore, init
import input_configuration as input_config
import emme_configuration as emme_config
import datetime
import getopt

# 3/12/2024
# incorporated into BKRCast. Originally from Soundcast.
# customized to focus on B.K.R area. 

def grams_to_tons(value):
	""" Convert grams to tons."""

	value = value/453.592
	value = value/2000

	return value

def calculate_interzonal_vmt():
    """ Calcualte inter-zonal running emission rates from network outputs
    """

    # List of vehicle types to include in results; note that bus is included here but not for intrazonals
    vehicle_type_list = ['sov','hov2','hov3','bus','medium_truck','heavy_truck']

    # Load link-level volumes by time of day and network county flags
    df = pd.read_csv(input_config.network_results_path)

    df['Jurisdiction'] = df['@bkrlink'].map(input_config.bkrlink_dict)

    # Remove links with @bkrlink = 0 from the calculation
    # @bkrlink > 0: all links inside King County    
    df = df[df['@bkrlink'] > 0]
    df['county'] = 'King'    

    # Calculate VMT by bus, SOV, HOV2, HOV3+, medium truck, heavy truck
    df['sov_vol'] = df['@svtl1'] + df['@svtl2'] + df['@svtl3'] + df['@svnt1'] + df['@svnt2'] + df['@svnt3']
    df['sov_vmt'] = df['sov_vol'] * df['length']
    df['hov2_vol'] = df['@h2tl1'] + df['@h2tl2'] + df['@h2tl3'] + df['@h2nt1'] + df['@h2nt2'] + df['@h2nt3']
    df['hov2_vmt'] = df['hov2_vol'] * df['length']
    df['hov3_vol'] = df['@h3tl1'] + df['@h3tl2'] + df['@h3tl3'] + df['@h3nt1'] + df['@h3nt2'] + df['@h3nt3']
    df['hov3_vmt'] = df['hov3_vol'] * df['length']

    df['bus_vmt'] = df['@bveh'] * df['length']
    df['medium_truck_vmt'] = df['@mveh'] * df['length']
    df['heavy_truck_vmt'] = df['@hveh'] * df['length']

    # Convert TOD periods into hours used in emission rate files
    df['hourId'] = df['tod'].map(input_config.emission_tod_lookup).astype('int')

    # Calculate congested speed to separate time-of-day link results into speed bins
    df['congested_speed'] = (df['length']/df['auto_time']) * 60
    df['avgspeedbinId'] = pd.cut(df['congested_speed'], input_config.auto_speed_bins, labels=range(1, len(input_config.auto_speed_bins))).astype('int')

    # Relate soundcast facility types to emission rate definitions (e.g., minor arterial, freeway)
    # @facility_moves: facility type compatible with EPA MOVES roadway definition    
    df['roadtypeId'] = df['@facility_moves'].astype('int')

    # Take total across columns where distinct emission rate are available
    # This calculates total VMT, by vehicle type (e.g., HOV3 VMT for hour 8, freeway, King County, 55-59 mph)
    join_cols = ['avgspeedbinId','roadtypeId','hourId','Jurisdiction', 'county']
    df = df.groupby(join_cols).sum()
    df = df[['sov_vmt','hov2_vmt','hov3_vmt','bus_vmt','medium_truck_vmt','heavy_truck_vmt']]
    df = df.reset_index()

    # Write this file for calculation with different emission rates
    df.to_csv(r'outputs/emissions/interzonal_vmt_grouped.csv', index=False)

    return df

def finalize_emissions(df, col_suffix=""):
    """ 
    Compute PM10 and PM2.5 totals, sort index by pollutant value, and pollutant name.
    For total columns add col_suffix (e.g., col_suffix='intrazonal_tons')
    """

    pm10 = df[df['pollutantID'].isin([100,106,107])].groupby('veh_type').sum().reset_index()
    pm10['pollutantID'] = 200
    pm10['county'] = 'King'
    pm10['Jurisdiction'] = 'All'
    pm25 = df[df['pollutantID'].isin([110,116,117])].groupby('veh_type').sum().reset_index()
    pm25['pollutantID'] = 201
    pm25['county'] = 'King'
    pm25['Jurisdiction'] = 'All'
    df = df.append(pm10)
    df = df.append(pm25)

    return df

def calculate_interzonal_emissions(df, df_rates):
    """ Calculate link emissions using rates unique to speed, road type, hour, county, and vehicle type. """

    df.rename(columns={'avgspeedbinId': 'avgSpeedBinID', 'roadtypeId': 'roadTypeID', 'hourId': 'hourID'}, inplace=True)

    # Calculate total VMT by vehicle group
    df['light'] = df['sov_vmt'] + df['hov2_vmt'] + df['hov3_vmt']
    df['medium'] = df['medium_truck_vmt']
    df['heavy'] = df['heavy_truck_vmt']
    df['transit'] = df['bus_vmt']
    # What about buses??
    df.drop(['sov_vmt','hov2_vmt','hov3_vmt','medium_truck_vmt','heavy_truck_vmt','bus_vmt'], inplace=True, axis=1)

    # Melt to pivot vmt by vehicle type columns as rows
    df = pd.melt(df, id_vars=['avgSpeedBinID','roadTypeID','hourID', 'Jurisdiction', 'county'], var_name='veh_type', value_name='vmt')
    df = pd.merge(df, df_rates, on=['avgSpeedBinID','roadTypeID','hourID','county','veh_type'], how='left', left_index=False)
    # Calculate total grams of emission 
    df['grams_tot'] = df['grams_per_mile']*df['vmt']
    df['tons_tot'] = grams_to_tons(df['grams_tot'])

    return df

def capitalize_first_letter(input_string):
    if not input_string:
        return input_string

    return input_string[0].upper() + input_string[1:].lower()                      
     
def calculate_intrazonal_vmt():

    df_iz = pd.read_csv(r'outputs/network/iz_vol.csv')

    # Map each zone to county
    subarea_df = pd.read_csv('inputs/subarea_definition/TAZ_subarea.csv')
    subarea_df.loc[subarea_df['Jurisdiction'] == 'BELLEVUE', 'Jurisdiction'] = 'Bellevue'
    subarea_df.loc[subarea_df['Jurisdiction'] == 'KIRKLAND', 'Jurisdiction'] = 'Kirkland'
    subarea_df.loc[subarea_df['Jurisdiction'] == 'REDMOND', 'Jurisdiction'] = 'Redmond'
    subarea_df.loc[subarea_df['Jurisdiction'].isin(['BellevueFringe', 'KirklandFringe', 'RedmondFringe']), 'Jurisdiction'] = 'Rest of KC'
     
    # remove anything outside of King County.              
    df_iz = pd.merge(df_iz, subarea_df, how='left', left_on='BKRCastTAZ', right_on = 'BKRCastTAZ')
    df_iz = df_iz.loc[df_iz['County'] == 'King']    

    # Sum up SOV, HOV2, and HOV3 volumes across user classes 1, 2, and 3 by time of day
    # Calcualte VMT for these trips too; rename truck volumes for clarity
    for tod in input_config.emission_tod_lookup.keys():
        df_iz['sov_' + tod + '_vol'] = df_iz['svtl1_' + tod] + df_iz['svtl2_' + tod] + df_iz['svtl3_' + tod] + df_iz['svnt1_' + tod] + df_iz['svnt2_' + tod] + df_iz['svnt3_' + tod]
        df_iz['hov2_' + tod + '_vol'] = df_iz['h2tl1_' + tod] + df_iz['h2tl2_' + tod] + df_iz['h2tl3_' + tod] + df_iz['h2nt1_' + tod] + df_iz['h2nt2_' + tod] + df_iz['h2nt3_' + tod]
        df_iz['hov3_' + tod + '_vol'] = df_iz['h3tl1_' + tod] + df_iz['h3tl2_' + tod] + df_iz['h3tl3_' + tod] + df_iz['h3nt1_' + tod] + df_iz['h3nt2_' + tod] + df_iz['h3nt3_' + tod]
        df_iz['mediumtruck_' + tod+'_vol'] = df_iz['metrk_' + tod]
        df_iz['heavytruck_' + tod+'_vol'] = df_iz['hvtrk_' + tod]

        # Calculate VMT as intrazonal distance times volumes 
        df_iz['sov_' +tod +'_vmt'] = df_iz['sov_' + tod+'_vol'] * df_iz['izdist']
        df_iz['hov2_' +tod +'_vmt'] = df_iz['hov2_' + tod+'_vol'] * df_iz['izdist']
        df_iz['hov3_' +tod +'_vmt'] = df_iz['hov3_' + tod+'_vol'] * df_iz['izdist']
        df_iz['mediumtruck_' + tod +'_vmt'] = df_iz['mediumtruck_' + tod + '_vol'] * df_iz['izdist']
        df_iz['heavytruck_' + tod +'_vmt'] = df_iz['heavytruck_' + tod + '_vol'] * df_iz['izdist']
	
    # Group totals by vehicle type, time-of-day, and county
    df = df_iz.groupby(['County', 'Jurisdiction']).sum().T
    df.reset_index(inplace=True)
    df = df[df['index'].apply(lambda row: 'vmt' in row)]

    # Calculate total VMT by time of day and vehicle type
    # Ugly dataframe reformatting to unstack data
    df['tod'] = df['index'].apply(lambda row: row.split('_')[1])
    df['vehicle_type'] = df['index'].apply(lambda row: row.split('_')[0])
    df.drop('index', axis=1,inplace=True)
    df.index = df[['tod','vehicle_type']]
    df.drop(['tod','vehicle_type'],axis=1,inplace=True)
    df = pd.DataFrame(df.unstack()).reset_index()
    df['tod'] = df['level_2'].apply(lambda row: row[0])
    df['vehicle_type'] = df['level_2'].apply(lambda row: row[1])
    df.drop('level_2', axis=1, inplace=True)
    df.columns = ['county', 'Jurisdiction', 'VMT','tod','vehicle_type']

    # Use hourly periods from emission rate files
    df['hourId'] = df['tod'].map(input_config.emission_tod_lookup).astype('int')

    # Export this file for use with other rate calculations
    # Includes total VMT for each group for which rates are available
    df.to_csv(r'outputs/emissions/intrazonal_vmt_grouped.csv', index=False)

    return df

def calculate_intrazonal_emissions(df_running_rates, df_intra_vmt):
    """ Summarize intrazonal emissions by vehicle type. """

    df_intra_vmt.rename(columns={'vehicle_type':'veh_type', 'VMT': 'vmt', 'hourId': 'hourID'},inplace=True)
    df_intra_vmt.drop('tod', axis=1, inplace=True)

    df_intra_light = df_intra_vmt[df_intra_vmt['veh_type'].isin(['sov','hov2','hov3'])]
    df_intra_light = df_intra_light.groupby(['county', 'Jurisdiction', 'hourID']).sum()[['vmt']].reset_index()
    df_intra_light.loc[:,'veh_type'] = 'light'

    df_intra_vmt.loc[df_intra_vmt['veh_type'] == 'mediumtruck', 'veh_type'] = 'medium'
    df_intra_vmt.loc[df_intra_vmt['veh_type'] == 'heavytruck', 'veh_type'] = 'heavy'
    
    df_intra_medium = df_intra_vmt[df_intra_vmt['veh_type'] == 'medium']
    df_intra_heavy = df_intra_vmt[df_intra_vmt['veh_type'] == 'heavy']

    df_intra = pd.concat([df_intra_light, df_intra_medium, df_intra_heavy], ignore_index = True)
    df_intra = df_intra.reset_index(drop = True)    

    # For intrazonals, assume standard speed bin and roadway type for all intrazonal trips
    speedbin = 4
    roadtype = 5

    iz_rates = df_running_rates[(df_running_rates['avgSpeedBinID'] == speedbin) &
	                    (df_running_rates['roadTypeID'] == roadtype)].copy()
    iz_rates['county'] = iz_rates['county'].apply(lambda x: capitalize_first_letter(x))     

    iz_rates.to_csv('outputs/emissions/intrazonal_emission_rates.csv')  

    df_intra = pd.merge(df_intra, iz_rates, on=['hourID','county','veh_type'], how='left', left_index=False)

    # Calculate total grams of emission 
    df_intra['grams_tot'] = df_intra['grams_per_mile']*df_intra['vmt']
    df_intra['tons_tot'] = grams_to_tons(df_intra['grams_tot'])

    return df_intra

def calculate_start_emissions(start_rates_df):
    """ Calculate start emissions based on vehicle population by county and year. """

    df_veh = pd.read_csv('inputs/model/emission/vehicle_population_bkr.csv')
    list_year = df_veh['year'].unique().tolist()
    veh_year = find_closest_horizon_year(list_year, int(input_config.base_year))        
    df_veh = df_veh.loc[df_veh['year'] == veh_year].copy()    

    # Scale all vehicles by difference between base year and model total vehicles owned from auto onwership model
    df_hh = pd.read_csv(r'outputs/daysim/_household.tsv', delim_whitespace=True, usecols=['hhvehs'])
    tot_veh = df_hh['hhvehs'].sum()

    # Scale county vehicles by total change
    tot_veh_model_base_year = 3007056
    veh_scale = 1.0+(tot_veh - tot_veh_model_base_year)/tot_veh_model_base_year
    df_veh['vehicles'] = df_veh['vehicles']*veh_scale

    # Join with rates to calculate total emissions
    # Sum total emissions across all times of day, by county, for each pollutant
    df = pd.merge(df_veh, start_rates_df, left_on=['type','county'],right_on=['veh_type','county'])
    df['start_grams'] = df['vehicles']*df['ratePerVehicle'] 
    df['start_tons'] = grams_to_tons(df['start_grams'])
    df = df.groupby(['pollutantID','veh_type','county', 'Jurisdiction']).sum().reset_index()
    df.drop(columns = ['year', 'vehicles'], axis = 1, inplace = True)    

    # Calculate bus start emissions
    # Load data taken from NTD that reports number of bus vehicles "operated in maximum service"
    df_bus_veh = pd.read_csv('inputs/model/emission/bus_vehicles_bkr.csv')
    list_year = df_bus_veh['year'].unique().tolist()
    bus_veh_year = find_closest_horizon_year(list_year, int(input_config.base_year))        
    df_bus_veh = df_bus_veh.loc[df_bus_veh['year'] == bus_veh_year].copy()   

    df_bus = start_rates_df[start_rates_df['veh_type'] == 'transit']
    df_bus = df_bus.merge(df_bus_veh[['county','Jurisdiction','bus_vehicles_in_service']], on = 'county')     
    df_bus['start_grams'] = df_bus['ratePerVehicle'] * df_bus['bus_vehicles_in_service']
    df_bus['start_tons'] = grams_to_tons(df_bus['start_grams'])
    df_bus = df_bus.groupby(['pollutantID', 'veh_type', 'county', 'Jurisdiction']).sum().reset_index()
    df_bus.drop(columns = ['bus_vehicles_in_service'], axis = 1, inplace = True)    

    df = df.append(df_bus)

    return df

def find_closest_horizon_year(list_years,input_year):
    if not list_years:
        return None

    horizon_year = min(list_years, key = lambda x: abs(x - input_year))

    return horizon_year                      
 

def assemble_emission_rates(df_rates, summer_month_id, winter_month_id):
    df_rates['county'] = df_rates['county'].apply(lambda x: capitalize_first_letter(x))    
    list_year = df_rates['year'].unique().tolist() 
    running_rate_year = find_closest_horizon_year(list_year, int(input_config.model_year))       
    df_rates = df_rates.loc[df_rates['year'] == running_rate_year].copy()
    
    # Select the month to use for each pollutant; some rates are used for winter or summer depending
    # on when the impacts are at a maximum due to temperature.
    df_summer = df_rates[df_rates['pollutantID'].isin(input_config.summer_list)]
    df_summer = df_summer[df_summer['monthID'] == summer_month_id]
    df_winter = df_rates[~df_rates['pollutantID'].isin(input_config.summer_list)]
    df_winter = df_winter[df_winter['monthID'] == winter_month_id]
    df_rates = df_winter.append(df_summer)

    return df_rates    

def help():
    print(' Calculate emissions totals for start, intrazonal, and interzonal running emissions.')
    print(' Uses different average rates for light, medium, and heavy vehicles.')
    print(' This method was originally used for GHG strategy analyses, which tested scenarios ')
    print(' of improvements by vehicle types (e.g., 5% emissions reductions for medium and heavy trucks, 25% more light EVs).')
    print('')
    print('emissions.py -h -f')
    print('   -h: help')            
    print(f'   -f: {Fore.GREEN}export (EXCEL) file name')    

def main():

    """
    Calculate emissions totals for start, intrazonal, and interzonal running emissions.
    Uses different average rates for light, medium, and heavy vehicles. 
    This method was originally used for GHG strategy analyses, which tested scenarios
    of improvements by vehicle types (e.g., 5% emissions reductions for medium and heavy trucks, 25% more light EVs).
    """

    emission_export_file = 'emission_summary.xlsx'
    init(autoreset = True)    
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hf')
    except getopt.GetoptError:
        help()
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-f':
            emission_export_file = arg 
                
    print(f'{Fore.GREEN}You many need to rerun network_summary.py to ensure the network output files are updated.')
    print('Calculating emissions...')

    # Create output directory
    output_dir = r'outputs/emissions'
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # Load running emission rates by vehicle type, for the model year
    print('load emission rates...')    
    df_running_rates = pd.read_csv('inputs/model/emission/running_emission_rates_by_veh_type_bkr.csv')
    df_running_rates = assemble_emission_rates(df_running_rates, 7, 1)    
    df_running_rates.rename(columns={'ratePerDistance': 'grams_per_mile'}, inplace=True)

    # load start emission rate
    start_rates_df = pd.read_csv('inputs/model/emission/start_emission_rates_by_veh_type.csv')
    start_rates_df = assemble_emission_rates(start_rates_df, 7, 1)    

    # Sum total emissions across all times of day, by county, for each pollutant
    start_rates_df = start_rates_df.groupby(['pollutantID','county','veh_type']).sum()[['ratePerVehicle']].reset_index()


    # Group interzonal trips and calculate interzonal emissions
    print('calculating...')    
    df_interzonal_vmt = calculate_interzonal_vmt()
    df_interzonal = calculate_interzonal_emissions(df_interzonal_vmt, df_running_rates)
    
    # Group intrazonal trips and calculate intrazonal emissions
    df_intrazonal_vmt = calculate_intrazonal_vmt()
    df_intrazonal = calculate_intrazonal_emissions(df_running_rates, df_intrazonal_vmt)

    # Calculate start emissions by vehicle type
    start_emissions_df = calculate_start_emissions(start_rates_df)

    # Combine all rates and export as CSV
    df_inter_group = df_interzonal.groupby(['county', 'Jurisdiction', 'pollutantID', 'veh_type']).sum()[['tons_tot']].reset_index()
    df_inter_group.rename(columns={'tons_tot': 'interzonal_tons'}, inplace=True)
    df_intra_group = df_intrazonal.groupby(['county', 'Jurisdiction', 'pollutantID', 'veh_type']).sum()[['tons_tot']].reset_index()
    df_intra_group.rename(columns={'tons_tot': 'intrazonal_tons'}, inplace=True)
    df_start_group = start_emissions_df.groupby(['county', 'Jurisdiction', 'pollutantID', 'veh_type']).sum()[['start_tons']].reset_index()

    new_summary_df = pd.merge(df_inter_group, df_intra_group,  on = ['county', 'Jurisdiction', 'pollutantID', 'veh_type'], how='left')
    new_summary_df = pd.merge(new_summary_df, df_start_group, on = ['county', 'Jurisdiction', 'pollutantID', 'veh_type'], how='left').fillna(0).reset_index()
    new_summary_df = finalize_emissions(new_summary_df)   
    new_summary_df['pollutantID'] = new_summary_df['pollutantID'].astype('int')
    new_summary_df['pollutant_name'] = new_summary_df['pollutantID'].astype('int', errors='ignore').astype('str').map(input_config.pollutant_map)

    new_summary_df['total_daily_tons'] = new_summary_df['start_tons'] + new_summary_df['interzonal_tons'] + new_summary_df['intrazonal_tons']
    summary_pivot_df = pd.pivot_table(new_summary_df, index = ['Jurisdiction', 'pollutant_name'], values = ['total_daily_tons'], aggfunc = 'sum').reset_index()

    print('exporting...')
    with pd.ExcelWriter(os.path.join(output_dir, emission_export_file), engine='xlsxwriter') as writer:
        wksheet = writer.book.add_worksheet('readme')
        wksheet.write(0, 0, str(datetime.datetime.now()))
        wksheet.write(1, 0, 'model folder')
        wksheet.write(1, 1, input_config.project_folder)
        wksheet.write(2, 0, 'parcel file')
        wksheet.write(2, 1, input_config.parcels_file_folder)
        wksheet.write(4, 0, 'notes')
        wksheet.write(5, 0, 'All emission rates are from Soundcast, and saved in inputs/mode/emission. ')
        wksheet.write(6, 0, 'Emission calculation only covers King County area, with focus on Bellevue, Kirkland and Redmond.')   

        df_interzonal.to_excel(writer, sheet_name = 'interzonal', startrow = 1, index = False)
        df_intrazonal.to_excel(writer, sheet_name = 'intrazonal', startrow = 1, index = False)
        start_emissions_df.to_excel(writer, sheet_name = 'start', startrow = 1, index = False)
        new_summary_df.to_excel(writer, sheet_name = 'combined', startrow = 1, index = False)
        df_intrazonal_vmt.to_excel(writer, sheet_name = 'intrazonal vmt', startrow = 1, index = False)
        df_interzonal_vmt.to_excel(writer, sheet_name = 'interzonal vmt', startrow = 1, index = False)                
        
        juris_list = summary_pivot_df['Jurisdiction'].unique().tolist()
        startrow = 2        
        for juris in juris_list:
            df_to_export =  summary_pivot_df.loc[summary_pivot_df['Jurisdiction'] == juris]           
            df_to_export[['pollutant_name', 'total_daily_tons']].to_excel(writer, sheet_name = 'summary', startrow = startrow, index = False)
            wksheet  = writer.sheets['summary']
            wksheet.write(startrow - 1, 0, f'Daily Emission in {juris}')  
            startrow += df_to_export.shape[0] + 3

    print('Done')    

if __name__ == '__main__':
    main()