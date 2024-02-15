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
import numpy as np
import json
import h5py
from sqlalchemy import create_engine
from EmmeProject import EmmeProject
from input_configuration import *
import toml
import data_wrangling

config = toml.load(os.path.join(os.getcwd(), 'configuration/input_configuration.toml'))
network_config = toml.load(os.path.join(os.getcwd(), 'configuration/network_configuration.toml'))
emme_config = toml.load(os.path.join(os.getcwd(), 'configuration/emme_configuration.toml'))
sum_config = toml.load(os.path.join(os.getcwd(), 'configuration/summary_configuration.toml'))

def get_intrazonal_vol(emmeproject, df_vol):
    """Calculate intrazonal volumes for all modes"""

    iz_uc_list = ['svtl', 'svnt', 'h2tl','h2nt', 'h3tl', 'h3nt']
    # so far BKRCast does not have av    
    # if config['include_av']:
    #     iz_uc_list += 'av_sov_inc','av_hov2_inc','av_hov3_inc'
    iz_uc_list = [uc+str(1+i) for i in range(3) for uc in iz_uc_list]
    if config['include_tnc']:
        iz_uc_list += ['tnc_1tl', 'tnc_1nt', 'tnc_2tl', 'tnc_2nt', 'tnc_3tl', 'tnc_3nt']
    if config['include_delivery']:
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

    ###################################################################  
    # Need to ensure delivery truck is included in the model (supplemental module)  
    if config['include_delivery']:
        my_project.network_calculator("link_calculation", result='@dveh', expression='@lttrk/1.5') # delivery trucks       
    #####################################################################        
     
    # Calculate total vehicles as @tveh, depending on which modes are included
    str_base = '@svtl1 + @svtl2 + @svtl3 + @svnt1 +  @svnt2 + @svnt3 + @h2tl1 + @h2tl2 + @h2tl3 + @h2nt1 + @h2nt2 + @h2nt3 + @h3tl1\
                                + @h3tl2 + @h3tl3 + @h3nt1 + @h3nt2 + @h3nt3 + @lttrk + @mveh + @hveh + @bveh'

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

def jobs_transit(output_path):
    buf = pd.read_csv(r'outputs/landuse/buffered_parcels.txt', sep=' ')

    # distance to any transit stop
    df = buf[['parcelid','dist_lbus','dist_crt','dist_fry','dist_lrt',
              u'hh_p', u'stugrd_p', u'stuhgh_p', u'stuuni_p', u'empedu_p',
           u'empfoo_p', u'empgov_p', u'empind_p', u'empmed_p', u'empofc_p',
           u'empret_p', u'empsvc_p', u'empoth_p', u'emptot_p']]
    df.index = df['parcelid']

    # Use minimum distance to any transit stop
    newdf = pd.DataFrame(df[['dist_lbus','dist_crt','dist_fry','dist_lrt']].min(axis=1))
    newdf = newdf.reset_index()
    df = df.reset_index(drop=True)
    newdf.rename(columns={0:'nearest_transit'}, inplace=True)
    df = pd.merge(df, newdf[['parcelid','nearest_transit']], on='parcelid')

    # only sum for parcels closer than quarter mile to stop
    quarter_mile_jobs = pd.DataFrame(df[df['nearest_transit'] <= 0.25].sum())
    quarter_mile_jobs.rename(columns={0:'quarter_mile_transit'}, inplace=True)
    all_jobs = pd.DataFrame(df.sum())
    all_jobs.rename(columns={0:'total'}, inplace=True)

    df = pd.merge(all_jobs,quarter_mile_jobs, left_index=True, right_index=True)
    df.drop(['parcelid','dist_lbus','dist_crt','dist_fry','dist_lrt','nearest_transit'], inplace=True)

    df.to_csv(output_path)

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
    
def sort_df(df, sort_list, sort_column):
    """ Sort a dataframe based on user-defined list of indices """

    df[sort_column] = df[sort_column].astype('category')
    df[sort_column].cat.set_categories(sort_list, inplace=True)
    df = df.sort_values(sort_column)

    return df

def summarize_network(df, writer):
    """ Calculate VMT, VHT, and Delay from link-level results """

    # @class = 0 are links outside of BKR area
    bkr_df = df[df['@class'] != 0].copy()   

    # calculate total link VMT and VHT
    bkr_df['VMT'] = bkr_df['@tveh'] * bkr_df['length']
    bkr_df['VHT'] = bkr_df['@tveh'] * bkr_df['auto_time'] / 60

    # Define facility type
    bkr_df.loc[bkr_df['@class'].isin([1]), 'facility_type'] = 'highway'
    bkr_df.loc[bkr_df['@class'].isin([10,20,30,40]), 'facility_type'] = 'arterial'
    bkr_df.loc[bkr_df['@class'].isin([50]), 'facility_type'] = 'connector'

    # Calculate delay
    # Select links from overnight time of day
    delay_df = bkr_df.loc[bkr_df['tod'] == '20to5', ['ij','auto_time']].copy()
    delay_df.rename(columns={'auto_time':'freeflow_time'}, inplace=True)

    # Merge delay field back onto network link df
    bkr_df = pd.merge(bkr_df, delay_df, on='ij', how='left')

    # Calcualte hourly delay
    bkr_df['delay'] = ((bkr_df['auto_time'] - bkr_df['freeflow_time']) * bkr_df['@tveh']) / 60    # sum of (volume)*(travtime diff from freeflow)

    # Add time-of-day group (AM, PM, etc.)
    tod_df = pd.read_json(r'inputs/skim_params/time_of_day_crosswalk_ab_4k_dictionary.json', orient='index')
    tod_df = tod_df[['TripBasedTime']].reset_index()
    tod_df.columns = ['tod','period']
    bkr_df = pd.merge(bkr_df,tod_df,on='tod',how='left')

    # Totals by functional classification
    for metric in ['VMT','VHT','delay']:
        _df = pd.pivot_table(bkr_df, values=metric, index=['tod','period'],columns='facility_type', aggfunc='sum').reset_index()
        _df = sort_df(df=_df, sort_list=network_config['tods'] , sort_column='tod')
        _df = _df.reset_index(drop=True)
        _df.to_excel(writer, sheet_name=metric+' by FC')
        _df.to_csv(r'outputs/network/' + metric.lower() +'_facility.csv', index=False)

    bkr_df['lane_miles'] = bkr_df['length'] * bkr_df['num_lanes']
    lane_miles = bkr_df[bkr_df['tod']=='6to9'].copy()
    lane_miles = pd.pivot_table(lane_miles, values='lane_miles', index='@bkrlink',columns='facility_type', aggfunc='sum').reset_index()
    lane_miles['@bkrlink'] = lane_miles['@bkrlink'].astype(int).astype(str)
    lane_miles = lane_miles.replace({'@bkrlink': sum_config['bkrlink_map']})
    lane_miles = lane_miles[lane_miles['@bkrlink'].isin(sum_config['bkrlink_map'].values())]
    lane_miles.rename(columns = {col:col+'_lane_miles' for col in lane_miles.columns if col in ['highway', 'arterial', 'connector']}, inplace = True)
    

    city_vmt = pd.pivot_table(bkr_df, values='VMT', index=['@bkrlink'],columns='facility_type', aggfunc='sum').reset_index()
    city_vmt['@bkrlink'] = city_vmt['@bkrlink'].astype(int).astype(str)
    city_vmt = city_vmt.replace({'@bkrlink': sum_config['bkrlink_map']})
    city_vmt.rename(columns = {col:col+'_vmt' for col in city_vmt.columns if col in ['highway', 'arterial', 'connector']}, inplace = True)
    lane_miles = lane_miles.merge(city_vmt, how='left', on ='@bkrlink')
    lane_miles.to_csv(r'outputs/network/bkr_vmt_lane_miles.csv', index=False)
    # Totals by user classification

    # Update uc_list based on inclusion of TNC and AVs
    new_uc_list = []

    if config['include_delivery']:
        new_uc_list.append('@dveh')	

    # av is not implemented in BKRCast
    # tnc is implemented but tnc volume is not separated from general class. Before assignment, tnc matrices are merged with general matrices.
    # if (not config['include_tnc']) & (not config['include_av']):
    #     for uc in sum_config['uc_list']:
    #         if ('@tnc' not in uc) & ('@av' not in uc):
    #             new_uc_list.append(uc)
                
    # if (config['include_tnc']) & (not config['include_av']):
    #     for uc in sum_config['uc_list']:
    #         if '@av' not in uc:
    #             new_uc_list.append(uc)
                
    # if (not config['include_tnc']) & (config['include_av']):
    #     for uc in sum_config['uc_list']:
    #         if '@tnc' not in uc:
    #             new_uc_list.append(uc)
                
    # VMT
    _df = bkr_df.copy()
    for uc in new_uc_list:
        _df[uc] = _df[uc] * _df['length']
    _df = _df[new_uc_list+['tod']].groupby('tod').sum().reset_index()
    _df = sort_df(df=_df, sort_list=network_config['tods'], sort_column='tod')
    _df.to_excel(excel_writer=writer, sheet_name="VMT by UC")
    _df.to_csv(r'outputs/network/vmt_user_class.csv', index=False)

    # VHT
    _df = bkr_df.copy()
    for uc in new_uc_list:
        _df[uc] = _df[uc] * _df['auto_time'] / 60
    _df = _df[new_uc_list+['tod']].groupby('tod').sum().reset_index()
    _df = sort_df(df=_df, sort_list=network_config['tods'], sort_column='tod')
    _df = _df.reset_index(drop=True)
    _df.to_excel(excel_writer=writer, sheet_name="VHT by UC")
    _df.to_csv(r'outputs/network/vht_user_class.csv', index=False)

    # Delay
    _df = bkr_df.copy()
    for uc in new_uc_list:
        _df[uc] = ((_df['auto_time']-_df['freeflow_time'])*_df[uc])/60
    _df = _df[new_uc_list+['tod']].groupby('tod').sum().reset_index()
    _df = sort_df(df=_df, sort_list=network_config['tods'], sort_column='tod')
    _df = _df.reset_index(drop=True)
    _df.to_excel(excel_writer=writer, sheet_name="Delay by UC")
    _df.to_csv(r'outputs/network/delay_user_class.csv', index=False)

    # Results by County
    
    bkr_df['city_name'] = bkr_df['@bkrlink'].map(sum_config['bkrlink_map'])
    bkr_df['city_name'].fillna('Outside BKR', inplace=True)
    _df = bkr_df.groupby('city_name').sum()[['VMT','VHT','delay']].reset_index()
    _df.to_excel(excel_writer=writer, sheet_name='City Results')
    _df.to_csv(r'outputs/network/city_network.csv', index=False)

    writer.save()

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

def transit_summary(emme_project, df_transit_line, df_transit_node, df_transit_segment):
    """Export transit line, segment, and mode attributes"""

    network = emme_project.current_scenario.get_network()
    tod = emme_project.tod

    # Extract Transit Line Data
    transit_line_data = []
    for line in network.transit_lines():
        transit_line_data.append({'line_id': line.id, 
                                  'route_code': line.id,
                                  'mode': str(line.mode),
                                  'description': line.description,
                                  'boardings': line['@board'], 
                                  'time': line['@timtr']})
    _df_transit_line = pd.DataFrame(transit_line_data)
    _df_transit_line['tod'] = tod
   
    # Extract Transit Node Data
    transit_node_data = []
    for node in network.nodes():
        transit_node_data.append({'node_id': int(node.id), 
                                  'initial_boardings': node.initial_boardings,
                                  'final_alightings': node.final_alightings})

    _df_transit_node = pd.DataFrame(transit_node_data)
    _df_transit_node['tod'] = tod
    
    # Extract Transit Segment Data
    transit_segment_data = []
    for tseg in network.transit_segments():
        if tseg.j_node is None:
            transit_segment_data.append({'line_id': tseg.line.id, 
                                  'segment_boarding': tseg.transit_boardings, 
                                  'segment_volume': tseg.transit_volume, 
                                  'i_node': tseg.i_node.number,
                                  'j_node': np.nan})
        else:
            transit_segment_data.append({'line_id': tseg.line.id, 
                                  'segment_boarding': tseg.transit_boardings, 
                                  'segment_volume': tseg.transit_volume, 
                                  'i_node': tseg.i_node.number,
                                  'j_node': tseg.j_node.number})
    
    _df_transit_segment = pd.DataFrame(transit_segment_data)
    _df_transit_segment['tod'] = tod

    return _df_transit_line, _df_transit_node, _df_transit_segment

def summarize_transit_detail(df_transit_line, df_transit_node, df_transit_segment):
    """Sumarize various transit measures."""
    
    df_transit_line['route_code'] = df_transit_line['route_code'].astype('int')
    
    # Daily trip totals by submode
    bank = _eb.Emmebank(os.path.join(os.getcwd(), r'Banks/daily/emmebank'))

    df = pd.DataFrame()
    for mode in ['commuter_rail','litrat','ferry', 'passenger_ferry', 'trnst']:
        df.loc[mode,'total_trips'] = bank.matrix(mode).get_numpy_data().sum()
    df.to_csv(r'outputs\transit\total_transit_trips.csv')
    bank.dispose()
    
    # Boardings for special routes
    df_special = df_transit_line[df_transit_line['route_code'].isin({int(k) for k in sum_config['special_route_lookup'].keys()})].groupby('route_code').sum()[['boardings']].sort_values('boardings', ascending=False)
    df_special = df_special.reset_index()
    df_special['description'] = df_special['route_code'].map({int(k):v for k,v in sum_config['special_route_lookup'].items()})
    df_special[['route_code','description','boardings']].to_csv(sum_config['special_routes_path'], index=False)

    # Daily Boardings by Stop
    df_transit_segment = pd.read_csv(r'outputs\transit\transit_segment_results.csv')
    df_transit_node = pd.read_csv(r'outputs\transit\transit_node_results.csv')
    df_transit_segment = df_transit_segment.groupby('i_node').sum().reset_index()
    df_transit_node = df_transit_node.groupby('node_id').sum().reset_index()
    df = pd.merge(df_transit_node, df_transit_segment, left_on='node_id', right_on='i_node')
    df.rename(columns={'segment_boarding': 'total_boardings'}, inplace=True)
    df['transfers'] = df['total_boardings'] - df['initial_boardings']
    df.to_csv(sum_config['boardings_by_stop_path'])

    # Light rail station boardings
    df = pd.read_csv(sum_config['boardings_by_stop_path'])
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
    df_total.to_csv(sum_config['light_rail_boardings_path'])

def main():
    # Delete any existing files
    for _path in [sum_config['transit_line_path'], sum_config['transit_node_path'], sum_config['transit_segment_path'], sum_config['network_results_path']]:
        if os.path.exists(_path ):
            os.remove(_path )

    ## Access Emme project with all time-of-day banks available
    my_project = EmmeProject(network_config['network_summary_project'])
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
    df_iz_vol['taz'] = dictZoneLookup.values()
    
    dir = r'outputs/transit/line_od'
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)
    
    transit_line_od_period_list = ['6to9', '1530to1830']

    # Loop through all Time-of-Day banks to get network summaries
    # Initialize extra network and transit attributes
    for tod_hour, tod_segment in network_config['sound_cast_net_dict'].items():
        print('processing network summary for time period: ' + str(tod_hour))
        my_project.change_active_database(tod_hour)
        if tod_hour in network_config['transit_tod'].keys():
            _df_transit_transfers = line_to_line_transfers(my_project, tod_hour)
            df_transit_transfers = df_transit_transfers.append(_df_transit_transfers)
        
        for name, description in network_config['extra_attributes_dict'].items():
            my_project.create_extra_attribute('LINK', name, description, 'True')
        # Calculate transit results for time periods with transit assignment:
        if my_project.tod in network_config['transit_tod'].keys():
            for name, desc in sum_config['transit_extra_attributes_dict'].items():
                my_project.create_extra_attribute('TRANSIT_LINE', name, desc, 'True')
                my_project.transit_segment_calculator(result=name, expression=name[1:])
            _df_transit_line, _df_transit_node, _df_transit_segment = transit_summary(emme_project=my_project, 
                                                                                    df_transit_line=df_transit_line,
                                                                                    df_transit_node=df_transit_node, 
                                                                                    df_transit_segment=df_transit_segment)
            df_transit_line = df_transit_line.append(_df_transit_line)
            df_transit_node = df_transit_node.append(_df_transit_node)
            df_transit_segment = df_transit_segment.append(_df_transit_segment)
        
            # we may need to create BKR's own transit line OD table for selected lines.

            # Calculate transit line OD table for select lines
            if tod_hour in transit_line_od_period_list:         
                for line_id, name in sum_config['transit_line_dict'].items():
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
                        my_project.export_matrix('mfeline', 'outputs/transit/line_od/'+str(line_id)+'_'+class_name+'.csv')

        # Add total vehicle sum for each link (@tveh)
        my_project.calc_total_vehicles()

        # Calculate intrazonal VMT
        _df_iz_vol = pd.DataFrame(my_project.bank.matrix('izdist').get_numpy_data().diagonal(),columns=['izdist'])
        _df_iz_vol['taz'] = dictZoneLookup.values()
        _df_iz_vol = get_intrazonal_vol(my_project, _df_iz_vol)
        if 'izdist' in df_iz_vol.columns:
            _df_iz_vol = _df_iz_vol.drop('izdist', axis=1)
        df_iz_vol = df_iz_vol.merge(_df_iz_vol, on='taz', how='left')

        # Export link-level results for multiple attributes
        network = my_project.current_scenario.get_network()
        _network_df = export_network_attributes(network)
        _network_df['tod'] = my_project.tod
        network_df = network_df.append(_network_df)

    my_project.closeDesktop()
    
    output_dict = {sum_config['network_results_path']: network_df, 
                   sum_config['iz_vol_path']: df_iz_vol,
                   sum_config['transit_line_path']: df_transit_line,
                   sum_config['transit_node_path']: df_transit_node,
                   sum_config['transit_segment_path']: df_transit_segment}

    # Append hourly results to file output
    for filepath, df in output_dict.items():
       df.to_csv(filepath, index=False)

    ## Write freeflow skims to Daysim trip records to calculate individual-level delay
    # not sure why we need the FF travel time. Will put it back if we find it is useful.
    # freeflow_skims(my_project, dictZoneLookup)

    # Export number of jobs near transit stops
    jobs_transit('outputs/transit/transit_access.csv')

    # Export transit transfers
    df_transit_transfers.to_csv('outputs/transit/transit_transfers.csv')

    # Create basic spreadsheet summary of network
    with pd.ExcelWriter(r'outputs/network/network_summary.xlsx', engine='xlsxwriter') as writer:
        # need to revise summarize_network() to meet the requirements of BKRCast 
        summarize_network(network_df, writer)

    # create detailed transit summaries
    # df_transit_line = pd.read_csv(transit_line_path)
    # df_transit_node = pd.read_csv(transit_node_path)
    # df_transit_segment = pd.read_csv(transit_segment_path)
    summarize_transit_detail(df_transit_line, df_transit_node, df_transit_segment)
    print('Done')    

if __name__ == "__main__":
    main()