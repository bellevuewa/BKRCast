#Copyright [2014] [Puget Sound Regional Council]

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os, sys, shutil
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
import inro.emme.database.emmebank as _eb
import pandas as pd
import json
import h5py
import datetime
from colorama import Fore, init
from EmmeProject import EmmeProject
import data_wrangling
import accessibility.accessibility_configuration as access_config
import input_configuration as input_config
import emme_configuration as emme_config

# 3/7/2024
# imported to BKRCast. Revised to focus on Bellevue, Kirkland and Redmond area. 
# Calculation is limited to King County. Links outside of King County are not included. 

def get_intrazonal_vol(emmeproject, df_vol):
    """Calculate intrazonal volumes for all modes"""

    iz_uc_list = ['svtl1', 'svtl2', 'svtl3', 'svnt1', 'svnt2', 'svnt3', 'h2tl1', 'h2tl2', 'h2tl3', 'h2nt1', 'h2nt2', 'h2nt3', 'h3tl1', 'h3tl2', 'h3tl3', 'h3nt1', 'h3nt2', 'h3nt3']
    # so far BKRCast does not have av    
    # if config['include_av']:
    #     iz_uc_list += 'av_sov_inc','av_hov2_inc','av_hov3_inc'
    
    # in BKRCast tnc implementation, when include_tnc is True, tnc matrices will be merged into trip tables in regular mode before assignment. 
    # there is no need to add tnc matrix to the list otherwise it will be double counted.     
    # if config['include_tnc']:
    #     iz_uc_list += ['tnc_1tl', 'tnc_1nt', 'tnc_2tl', 'tnc_2nt', 'tnc_3tl', 'tnc_3nt']
    if input_config.include_delivery:
        iz_uc_list += ['lttrk']
    iz_uc_list += ['metrk','hvtrk']

    for uc in iz_uc_list:
        df_vol[uc+'_'+emmeproject.tod] = emmeproject.bank.matrix(uc).get_numpy_data().diagonal()

    return df_vol

def calc_total_vehicles(my_project):
    """For a given time period, calculate link level volume, store as extra attribute on the link."""

    my_project.network_calculator("link_calculation", result='@mveh', expression='@metrk/1.5') # medium trucks       
    my_project.network_calculator("link_calculation", result='@hveh', expression='@hvtrk/2.0') #heavy trucks     
    my_project.network_calculator("link_calculation", result='@bveh', expression='@trnv3/2.0') # buses

    # Calculate total vehicles as @tveh, depending on which modes are included
    str_base = '@svtl1 + @svtl2 + @svtl3 + @svnt1 +  @svnt2 + @svnt3 + @h2tl1 + @h2tl2 + @h2tl3 + @h2nt1 + @h2nt2 + @h2nt3 + @h3tl1\
                                + @h3tl2 + @h3tl3 + @h3nt1 + @h3nt2 + @h3nt3 + @mveh + @hveh + @bveh'
                                
    ###################################################################  
    # Need to ensure delivery truck is included in the model (supplemental module)  
    if input_config.include_delivery:
        # need to make sure @dveh is created.        
        my_project.network_calculator("link_calculation", result='@dveh', expression='@lttrk/1.5') # delivery trucks   
        str_base = str_base + ' + @dveh'            
    #####################################################################        
     

    str_expression = str_base                                
    # AV is not active in BKRCast
    #                            
    # av_str = '+ @av_sov_inc1 + @av_sov_inc2 + @av_sov_inc3 + @av_hov2_inc1 + @av_hov2_inc2 + @av_hov2_inc3 + ' + \
    #                   '@av_hov3_inc1 + @av_hov3_inc2 + @av_hov3_inc3 '
    
    # there is no tnc related volumes in assignment, even though tnc mode is on. The TNC trip tables will be added to general trip tables before assignment.
    # so str_base includes tnc volumes if the tnc mode is on.

    my_project.network_calculator("link_calculation", result='@tveh', expression=str_expression)
    
def freeflow_skims(my_project, dictZoneLookup):
    """ Attach "freeflow" (20to5) SOV skims to daysim_outputs """

    # Load daysim_outputs as dataframe
    daysim = h5py.File('outputs/daysim/daysim_outputs.h5', 'r+')
    df = pd.DataFrame()
    for field in ['travtime','otaz','dtaz']:
        df[field] = daysim['Trip'][field][:]
    df['od']=df['otaz'].astype('str')+'-'+df['dtaz'].astype('str')

    skim_vals = h5py.File(r'inputs/model/roster/20to5.h5', 'r')['Skims']['sov_inc3t'][:]

    skim_df = pd.DataFrame(skim_vals)
    # Reset index and column headers to match zone ID
    skim_df.columns = [dictZoneLookup[i] for i in skim_df.columns]
    skim_df.index = [dictZoneLookup[i] for i in skim_df.index.values]

    skim_df = skim_df.stack().reset_index()
    skim_df.columns = ['otaz','dtaz','ff_travtime']
    skim_df['od'] = skim_df['otaz'].astype('str')+'-'+skim_df['dtaz'].astype('str')
    skim_df.index = skim_df['od']

    df = df.join(skim_df,on='od', lsuffix='_cong',rsuffix='_ff')

    # Write to h5, create dataset if 
    if 'sov_ff_time' in daysim['Trip'].keys():
        del daysim['Trip']['sov_ff_time']
    try:
        daysim['Trip'].create_dataset("sov_ff_time", data=df['ff_travtime'].values, compression='gzip')
    except:
        print('could not write freeflow skim to h5')
    daysim.close()

    # Write to TSV files
    trip_df = pd.read_csv(r'outputs/daysim/_trip.tsv', delim_whitespace=True)
    trip_df['od'] = trip_df['otaz'].astype('str')+'-'+trip_df['dtaz'].astype('str')
    skim_df['sov_ff_time'] = skim_df['ff_travtime']
    # Delete sov_ff_time if it already exists
    if 'sov_ff_time' in trip_df.columns:
        trip_df.drop('sov_ff_time', axis=1, inplace=True)
    skim_df = skim_df.reset_index(drop=True)
    trip_df = pd.merge(trip_df, skim_df[['od','sov_ff_time']], on='od', how='left')
    trip_df.to_csv(r'outputs/daysim/_trip.tsv', sep='\t', index=False)

def jobs_transit():
    # should produce access by BKR area
    if os.path.exists(access_config.output_parcels) == False:
        print('bufferred parcel file is not found. Please rerun accessibility first.') 
        return
                      
    buf = pd.read_csv(access_config.output_parcels, sep=' ')
    lookup_parcels_df = pd.read_csv(os.path.join(input_config.main_inputs_folder, 'model', 'parcel_TAZ_2014_lookup.csv'), low_memory = False)

    # distance to any transit stop
    lu_list = ['hh_p', u'stugrd_p', u'stuhgh_p', u'stuuni_p', u'empedu_p', u'empfoo_p', u'empgov_p', u'empind_p', u'empmed_p', u'empofc_p', u'empret_p', u'empsvc_p', u'empoth_p', u'emptot_p']
    dist_list = ['dist_lbus','dist_crt','dist_fry','dist_lrt']
    all_attr_list = ['parcelid'] + dist_list + lu_list   
    df = buf[all_attr_list]

    df = df.merge(lookup_parcels_df[['PSRC_ID', 'Jurisdiction', 'BKRCastTAZ']], left_on = 'parcelid', right_on = 'PSRC_ID', how = 'left')    
    df.index = df['parcelid']
    df.drop(columns = ['PSRC_ID'], inplace = True)    

    # Use minimum distance to any transit stop
    newdf = pd.DataFrame(df[dist_list].min(axis=1))
    newdf = newdf.reset_index()
    df = df.reset_index(drop=True)
    newdf.rename(columns={0:'nearest_transit'}, inplace=True)
    df = pd.merge(df, newdf[['parcelid','nearest_transit']], on='parcelid')

    # only sum for parcels closer than quarter mile to stop
    quarter_mile_jobs = pd.DataFrame(df[df['nearest_transit'] <= 0.25].sum())
    quarter_mile_jobs.rename(columns={0:'quarter_mile_transit'}, inplace=True)
    # all_jobs = pd.DataFrame(df.sum())
    all_jobs = df[lu_list + ['Jurisdiction']].groupby('Jurisdiction').sum()  
    quarter_mile_jobs = df.loc[df['nearest_transit'] <= 0.25, lu_list + ['Jurisdiction']].groupby('Jurisdiction').sum()  

    with pd.ExcelWriter(input_config.job_access_by_transit_file,  engine='xlsxwriter') as writer:
        wksheet = writer.book.add_worksheet('readme')
        wksheet.write(0, 0, str(datetime.datetime.now()))
        wksheet.write(1, 0, 'model folder')
        wksheet.write(1, 1, input_config.project_folder)
        wksheet.write(2, 0, 'parcel file')
        wksheet.write(2, 1, input_config.parcels_file_folder)

        all_jobs.to_excel(writer, sheet_name = 'job_access', startrow = 1)
        job_access_sheet = writer.sheets['job_access']
        job_access_sheet.write(0, 0, 'Total Jobs/Hhs by Jurisdiction')   

        srow = all_jobs.shape[0] + 5                     
        quarter_mile_jobs.to_excel(writer, sheet_name = 'job_access', startrow = srow)  
        job_access_sheet.write(srow - 1, 0, 'Jobs/Hhs within 1/4 mile radius of Transit Stops')         
           

def export_network_attributes(network):
    """ Calculate link-level results by time-of-day, append to csv """

    _attribute_list = network.attributes('LINK')  

    network_data = {k: [] for k in _attribute_list}
    i_node_list = []
    j_node_list = []
    network_data['modes'] = []
    for link in network.links():
        for colname, array in network_data.items():
            if colname != 'modes':
                try:
                    network_data[colname].append(link[colname])  
                except:
                    network_data[colname].append(0)
        i_node_list.append(link.i_node.id)
        j_node_list.append(link.j_node.id)
        network_data['modes'].append(link.modes)

    network_data['i_node'] = i_node_list
    network_data['j_node'] = j_node_list
    df = pd.DataFrame.from_dict(network_data)
    df['modes'] = df['modes'].apply(lambda x: ''.join(list([j.id for j in x])))    
    df['modes'] = df['modes'].astype('str').fillna('')
    df['ij'] = df['i_node'].astype('str') + '-' + df['j_node'].astype('str')

    df['speed'] = df['length']/df['auto_time']*60
    df['congestion_index'] = df['speed']/df['data2']
    df['congestion_index'] = df['congestion_index'].clip(0,1)
    df['congestion_category'] = pd.cut(df['congestion_index'], bins=[0,.25,.5,.7,1], labels=['Severe','Heavy','Moderate','Light'])
   
    return df
    
def sort_df(df, sort_list, sort_column_list):
    """ Sort a dataframe based on user-defined list of indices """
    for col in sort_column_list:
        df[col] = df[col].astype('category')
        df[col].cat.set_categories(sort_list, inplace=True)
    df = df.sort_values(sort_column_list)

    return df

def summarize_network(df):
    """ Calculate VMT, VHT, and Delay from link-level results """
    """ BKR area only """    

    # @bkrlink = 0 are links outside of King County  1: Bel, 2: Kirk, 3: Red, 4: BKR fringe, 5: rest of KC
    kc_df = df[(df['@bkrlink'] > 0)].copy()  

    # calculate total link VMT and VHT
    kc_df['VMT'] = kc_df['@tveh'] * kc_df['length']
    kc_df['VHT'] = kc_df['@tveh'] * kc_df['auto_time'] / 60

    # Define facility type
    kc_df.loc[kc_df['@class'].isin([1]), 'facility_type'] = 'freeway'
    kc_df.loc[kc_df['@class'].isin([10,20]), 'facility_type'] = 'arterial'
    kc_df.loc[kc_df['@class'].isin([30]), 'facility_type'] = 'connector'
    kc_df.loc[kc_df['@class'].isin([40]), 'facility_type'] = 'local'

    # Calculate delay
    # Select links from overnight time of day
    kc_df['freeflow_time']  = (kc_df['length'] / kc_df['data2']) * 60

    # Calcualte hourly delay
    kc_df['VHD'] = ((kc_df['auto_time'] - kc_df['freeflow_time']) * kc_df['@tveh']) / 60    # sum of (volume)*(travtime diff from freeflow)
    # calulate lane miles.    
    kc_df['lane_miles'] = kc_df['length'] * kc_df['num_lanes']

    # Add time-of-day group (AM, PM, etc.)
    tod_df = pd.read_json(r'inputs/skim_params/time_of_day_crosswalk_ab_4k_dictionary.json', orient='index')
    tod_df = tod_df[['TripBasedTime']].reset_index()
    tod_df.columns = ['tod','period']
    kc_df = pd.merge(kc_df,tod_df,on='tod',how='left')

    with pd.ExcelWriter(r'outputs/network/network_summary.xlsx', engine='xlsxwriter') as writer:
        wksheet = writer.book.add_worksheet('readme')
        wksheet.write(0, 0, str(datetime.datetime.now()))
        wksheet.write(1, 0, 'model folder')
        wksheet.write(1, 1, input_config.project_folder)
        wksheet.write(2, 0, 'parcel file')
        wksheet.write(2, 1, input_config.parcels_file_folder)
        wksheet.write(4, 0, 'notes')
        wksheet.write(5, 0, 'Facility type is defined by @class')
        wksheet.write(6, 0, 'BKR area is defined by @bkrlink. Links outside of King County are not included in the calculation.')    

        
        lane_miles = kc_df[kc_df['tod']=='6to9'].copy()
        lane_miles = pd.pivot_table(lane_miles, values='lane_miles', index='@bkrlink',columns='facility_type', aggfunc='sum').reset_index()
        lane_miles.rename(columns = {col:col+'_lane_miles' for col in lane_miles.columns if col in ['freeway', 'arterial', 'connector', 'local']}, inplace = True)
    
        for metric in ['VMT', 'VHT', 'VHD']:
            city_sum = pd.pivot_table(kc_df, values = metric, index = ['@bkrlink'], columns = 'facility_type', aggfunc = 'sum').reset_index()
            city_sum.rename(columns = {col:col + "_" + metric.lower() for col in city_sum.columns if col in ['freeway', 'arterial', 'connector', 'local']}, inplace = True) 
            lane_miles = lane_miles.merge(city_sum, how = 'left', on = '@bkrlink')            

        lane_miles = lane_miles.replace(input_config.bkrlink_dict)
        lane_miles = lane_miles.sort_values(by = ['@bkrlink'])             
        lane_miles.to_excel(writer, sheet_name = 'lane_miles', startrow = 2, index = False)
        wksheet = writer.sheets['lane_miles']
        wksheet.write(1, 0, 'Lane Miles and VMT/VHT/VHD by @bkrlink')    
        foot_note_start = 2 + lane_miles.shape[0] + 2
        wksheet.write(foot_note_start, 0, 'Notes')
        wksheet.write(foot_note_start + 1, 0, 'VMT/VHT/VHD: daily, including centroid connector')                              
        
        # Totals by functional classification
        startrow = 2
        sheet_name = 'BKR metric by FC'            
        _df = pd.pivot_table(kc_df, values=['VMT','VHT','VHD'], index=['@bkrlink', 'tod','period'],columns='facility_type', aggfunc='sum').reset_index()
        _df = sort_df(df=_df, sort_list=emme_config.tods , sort_column_list = ['@bkrlink', 'period'])
        _df['Jurisdiction'] = _df['@bkrlink'].map(input_config.bkrlink_dict)        
        _df.to_excel(writer, sheet_name = sheet_name, startrow = startrow)
        wksheet = writer.sheets[sheet_name]
        wksheet.write(startrow - 1, 0, 'Metric by Facility Type')  
        foot_note_start = _df.shape[0] + 4 
        wksheet.write(foot_note_start + 1, 0, 'Notes')
        wksheet.write(foot_note_start + 2, 0, 'VMT/VHT/VHD including centroid connectors')        
                        
        # Totals by user classification
        # Update uc_list based on inclusion of TNC and AVs
        new_uc_list = ['@svtl1', '@svtl2', '@svtl3', '@svnt1', '@svnt2', '@svnt3', '@h2tl1', '@h2tl2', '@h2tl3', '@h2nt1', '@h2nt2', '@h2nt3', '@h3tl1', '@h3tl2', '@h3tl3', '@h3nt1', '@h3nt2', '@h3nt3', '@mveh', '@hveh', '@bveh']

        if input_config.include_delivery:
            new_uc_list.append('@dveh')	

        # calculate vmt, vht vhd by user class
        for uc in new_uc_list:
            kc_df[uc+'_vmt'] = kc_df[uc] * kc_df['length']                    
            kc_df[uc+'_vht'] = kc_df[uc] * kc_df['auto_time'] / 60
            kc_df[uc+'_vhd'] = ((kc_df['auto_time'] - kc_df['freeflow_time']) * kc_df[uc])/60

        attr_list = [item + '_vmt' for item in new_uc_list] + [item + '_vht' for item in new_uc_list] + [item + '_vhd' for item in new_uc_list]
        
        _df = pd.pivot_table(kc_df, values=attr_list, index=['@bkrlink', 'tod','period'], aggfunc='sum').reset_index()
        _df['Jurisdiction'] = _df['@bkrlink'].map(input_config.bkrlink_dict)        
        
        sheet_name = "BKR metric by UC"
        head_list = ['@bkrlink', 'Jurisdiction', 'tod', 'period']  
        startrow = 2            
        for metric in ['_vmt', '_vht', '_vhd']:
            metric_list = [item for item in _df.columns if metric in item]
            sub_df = _df[head_list + metric_list]
            sub_df.to_excel(excel_writer = writer, sheet_name = sheet_name, startrow = startrow, index = False)
            wksheet = writer.sheets[sheet_name]
            wksheet.write(startrow - 1, 0, metric[1:].upper())            
            startrow += sub_df.shape[0] + 2
            wksheet.write(startrow, 0, 'Notes')
            wksheet.write(startrow + 1, 0, metric[1:].upper() + ': including centroid connectors')
            startrow += 5                                                           
            
    
        kc_df['city_name'] = kc_df['@bkrlink'].map(input_config.bkrlink_dict)
        _df = kc_df.groupby('city_name').sum()[['VMT','VHT','VHD']].reset_index()
        wksheet.write(startrow + 1, 0, 'VMT/VHT/VHD by City') 
        startrow += 1        
        _df.to_excel(excel_writer=writer, sheet_name = sheet_name, startrow = startrow)
        startrow += _df.shape[0] + 2
        wksheet.write(startrow + 1, 0, 'Notes')
        wksheet.write(startrow + 2, 0, 'VMT/VHT/VHD including centroid connectors')                        


def line_to_line_transfers(emme_project, tod):
    emme_project.create_extra_attribute('TRANSIT_LINE', '@ln2ln', description = 'line to line', overwrite = True)
    emme_project.network_calculator("transit_line_calculation", result='@ln2ln', expression='index1')
    with open('inputs/skim_params/transit_traversal.json') as f:
        spec = json.load(f)
    NAMESPACE = "inro.emme.transit_assignment.extended.traversal_analysis"
    process = emme_project.m.tool(NAMESPACE)

    transit_line_list = []
    network = emme_project.current_scenario.get_network()

    for line in network.transit_lines():
        transit_line_list.append({'line':line.id, 'mode':line.mode.id})
    transit_lines = pd.DataFrame(transit_line_list)
    transit_lines['lindex'] = transit_lines.index + 1
    transit_lines=transit_lines[['lindex', 'line', 'mode']]

    df_list = []
    
    for class_name in ['trnst','commuter_rail','ferry','litrat','passenger_ferry']:
        report = process(spec, class_name = class_name, output_file = 'outputs/transit/traversal_results.txt') 
        traversal_df = pd.read_csv('outputs/transit/traversal_results.txt', skiprows=16, skipinitialspace=True, sep = ' ', names = ['from_line', 'to_line', 'boardings'])
    
        traversal_df = traversal_df.merge(transit_lines, left_on= 'from_line', right_on='lindex')
        traversal_df = traversal_df.rename(columns={'line':'from_line_id', 'mode':'from_mode'})
        traversal_df.drop(columns=['lindex'], inplace = True)

        traversal_df = traversal_df.merge(transit_lines, left_on= 'to_line', right_on='lindex')
        traversal_df = traversal_df.rename(columns={'line':'to_line_id', 'mode':'to_mode'})
        traversal_df.drop(columns=['lindex'], inplace = True)
        df_list.append(traversal_df)
        os.remove('outputs/transit/traversal_results.txt')
        
    df = pd.concat(df_list)
    df = df.groupby(['from_line', 'to_line']).agg({'from_line_id' : min, 'to_line_id' : min, 'from_mode' : min, 'to_mode' : min, 'boardings' : sum, })
    df.reset_index(inplace = True)
    df['tod'] = tod
    return df

def summarize_transit_detail(df_transit_line, df_transit_node, df_transit_segment):
    """Sumarize various transit measures."""
    
    df_transit_line['route_code'] = df_transit_line['route_code'].astype('int')
    
    # Daily trip totals by submode
    try:    
        bank = _eb.Emmebank(os.path.join(os.getcwd(), r'Banks/daily/emmebank'))

        ## This is total transit trips in the region. 
        ## we also need to have transit trips from BKR, to BKR, and within BKR.    
        df = pd.DataFrame()
        for mode in ['commuter_rail','litrat','ferry', 'passenger_ferry', 'trnst']:
            df.loc[mode,'total_trips'] = bank.matrix(mode).get_numpy_data().sum()
        bank.dispose()
    except:
        print('cannot open daily bank. summrize_transit_detail() is terminated.') 
        return           
    
    df.to_csv(r'outputs\transit\total_transit_trips.csv')
    # Boardings for special routes
    df_special = df_transit_line[df_transit_line['route_code'].isin({int(k) for k in emme_config.special_route_lookup.keys()})].groupby('route_code').sum()[['boardings']].sort_values('boardings', ascending=False)
    df_special = df_special.reset_index()
    df_special['description'] = df_special['route_code'].map({int(k):v for k,v in emme_config.special_route_lookup.items()})
    df_special[['route_code','description','boardings']].to_csv(input_config.special_routes_path, index=False)

    # Daily Boardings by Stop
    df_transit_segment = pd.read_csv(input_config.transit_segment_path)
    df_transit_node = pd.read_csv(input_config.transit_node_path)
    df_transit_segment = df_transit_segment.groupby('i_node').sum().reset_index()
    df_transit_node = df_transit_node.groupby('node_id').sum().reset_index()
    df = pd.merge(df_transit_node, df_transit_segment, left_on='node_id', right_on='i_node')
    df.rename(columns={'segment_boarding': 'total_boardings'}, inplace=True)
    df['transfers'] = df['total_boardings'] - df['initial_boardings']
    df.to_csv(input_config.boardings_by_stop_path)

    # Light rail station boardings
    df = pd.read_csv(input_config.boardings_by_stop_path)
    # df_obs = pd.read_sql("SELECT * FROM light_rail_station_boardings", con=conn)
    # df_obs['year'] = df_obs['year'].fillna(0).astype('int')
    # df_obs = df_obs[(df_obs['year'] == int(config['base_year'])) | (df_obs['year'] == 0)]

    # Translate daily boardings to 5 to 20
    # df_line_obs = pd.read_sql("SELECT * FROM observed_transit_boardings WHERE year=" + str(config['base_year']), con=conn)
    # df_line_obs['route_id'] = df_line_obs['route_id'].astype('int')
    light_rail_list = [6025, 6026, 6039, 6040]
    # daily_factor = df_line_obs[df_line_obs['route_id'].isin(light_rail_list)]['daily_factor'].values[0]
    # df_obs['observed_5to20'] = df_obs['boardings']/daily_factor

    # df = df[df['i_node'].isin(df_obs['emme_node'])]
    df.rename(columns={'total_boardings':'modeled_5to20'},inplace=True)

    # if len(df_obs) > 0:
    #     df = df.merge(df_obs, left_on='i_node', right_on='emme_node')
    #     cols = ['observed_5to20','modeled_5to20']
    # else:
    #     cols = ['modeled_5to20']
    cols = ['modeled_5to20']
    df_total = df.copy()[cols]
    df_total.loc['Total',cols] = df[cols].sum().values
    df_total.to_csv(input_config.light_rail_boardings_path)

def main():
    # Delete any existing files
    print('Delete existing output fiiles.')    
    for _path in [input_config.transit_line_path, input_config.transit_node_path, input_config.transit_segment_path, input_config.network_results_path]:
        if os.path.exists(_path ):
            os.remove(_path )

    ## Access Emme project with all time-of-day banks available
    my_project = EmmeProject(emme_config.network_summary_project)
    network = my_project.current_scenario.get_network()
    zones = my_project.current_scenario.zone_numbers
    dictZoneLookup = dict((index,value) for index,value in enumerate(zones))

        # Initialize result dataframes
    df_transit_line = pd.DataFrame()
    df_transit_node = pd.DataFrame()
    df_transit_segment = pd.DataFrame()
    df_transit_transfers = pd.DataFrame()
    network_df = pd.DataFrame()
    df_iz_vol = pd.DataFrame()
    df_iz_vol['BKRCastTAZ'] = dictZoneLookup.values()
    
    directory = r'outputs/transit/line_od'
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory)
    
    transit_line_od_period_list = ['6to9', '1530to1830']

    # Loop through all Time-of-Day banks to get network summaries
    # Initialize extra network and transit attributes
    for tod_hour, tod_segment in emme_config.sound_cast_net_dict.items():
        print('processing network summary for time period: ' + str(tod_hour))
        my_project.change_active_database(tod_hour)
        print('  create link extra attributes')        
        for name, description in input_config.extra_attributes_dict.items():
            my_project.create_extra_attribute('LINK', name, description, 'True')
        
        print('  analyze line to line transfer.')            
        if tod_hour in emme_config.transit_tod.keys():
            _df_transit_transfers = line_to_line_transfers(my_project, tod_hour)
            df_transit_transfers = df_transit_transfers.append(_df_transit_transfers)
        
        print('  summarize transit network')
        # Calculate transit results for time periods with transit assignment:
        if my_project.tod in emme_config.transit_tod.keys():
            for name, desc in input_config.transit_extra_attributes_dict.items():
                my_project.create_extra_attribute('TRANSIT_LINE', name, desc, 'True')
                my_project.transit_segment_calculator(result=name, expression=name[1:])
            _df_transit_line, _df_transit_node, _df_transit_segment = my_project.transit_summary()
            df_transit_line = df_transit_line.append(_df_transit_line)
            df_transit_node = df_transit_node.append(_df_transit_node)
            df_transit_segment = df_transit_segment.append(_df_transit_segment)
        
            # we may need to create BKR's own transit line OD table for selected lines.

            # Calculate transit line OD table for select lines
            print('  create OD table for selected transit lines')            
            if tod_hour in transit_line_od_period_list:         
                for line_id, name in emme_config.transit_line_dict.items():
                    # Calculate results for all path types
                    for class_name in ['trnst','commuter_rail','ferry','litrat','passenger_ferry']:
                        for matrix in my_project.bank.matrices():
                            if matrix.name == 'eline':
                                my_project.delete_matrix(matrix)
                                my_project.delete_extra_attribute('@eline')
                        my_project.create_extra_attribute('TRANSIT_LINE', '@eline', name, 'True')
                        my_project.create_matrix('eline', 'Demand from select transit line', "FULL")

                        # Add an identifier to the chosen line
                        my_project.network_calculator("link_calculation", result='@eline', expression='1',
                                                      selections={'transit_line': str(line_id)})

                        # Transit path analysis
                        transit_path_analysis = my_project.m.tool('inro.emme.transit_assignment.extended.path_based_analysis')
                        _spec = data_wrangling.json_to_dictionary("transit_path_analysis")
                        transit_path_analysis(_spec, class_name=class_name)
                        
                        # Write this path OD table to sparse CSV
                        my_project.export_matrix('mfeline', 'outputs/transit/line_od/' + str(line_id) + '_'+ class_name + "_" + tod_hour + '.csv')

        # Add total vehicle sum for each link (@tveh)
        print('  calculate total vehicles.')                        
        my_project.calc_total_vehicles()

        # Calculate intrazonal volume and distance
        print('  calculate intrazonal volume and distance')        
        _df_iz_vol = pd.DataFrame(my_project.bank.matrix('izdist').get_numpy_data().diagonal(),columns=['izdist'])
        _df_iz_vol['BKRCastTAZ'] = dictZoneLookup.values()
        _df_iz_vol = get_intrazonal_vol(my_project, _df_iz_vol)
        if 'izdist' in df_iz_vol.columns:
            _df_iz_vol = _df_iz_vol.drop('izdist', axis=1)
        df_iz_vol = df_iz_vol.merge(_df_iz_vol, on='BKRCastTAZ', how='left')

        # create datafrane of all links with multiple attributes
        print('  create dataframe of links')
        network = my_project.current_scenario.get_network()
        _network_df = export_network_attributes(network)
        _network_df['tod'] = my_project.tod
        network_df = network_df.append(_network_df)

    my_project.closeDesktop()
    
    ######################################## TO DO #########################
    # it would be nice to export results to xlsx fiel instead of csv. We could add additional analysis data to xlsx later.    
    output_dict = {input_config.network_results_path: network_df, 
                   input_config.iz_vol_path: df_iz_vol,
                   input_config.transit_line_path: df_transit_line,
                   input_config.transit_node_path: df_transit_node,
                   input_config.transit_segment_path: df_transit_segment}

    # Append hourly results to file output
    print('export all links, all transit lines, all transit stops, all transit segments')    
    for filepath, df in output_dict.items():
       df.to_csv(filepath, index=False)

    # Export transit transfers
    print('export transit transfer')       
    df_transit_transfers.to_csv(input_config.transit_transfer_file)

    # Export number of jobs near transit stops
    print('generate number of jobs/hhs accessible within 1/4 mile radius of transit stops.')       
    jobs_transit()

    # Create basic spreadsheet summary of network
    print('calculate VMT/VHT/VHD by facility type, by user class, and by jurisdiction')    
    summarize_network(network_df)

    # create detailed transit summaries
    init(autoreset = True)    
    print(f'summarize transit network. {Fore.GREEN}Make sure daily bank is also up-to-date.')    
    summarize_transit_detail(df_transit_line, df_transit_node, df_transit_segment)
    print('Done')    

if __name__ == "__main__":
    main()