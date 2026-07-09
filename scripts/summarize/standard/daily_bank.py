import inro.emme.database.emmebank as _emmebank
import inro.emme.desktop.app as app
import os, sys
from pathlib import Path
import numpy as np
import pandas as pd
import json
import shutil
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from input_configuration import *
import emme_configuration as emme_config
from EmmeProject import *
from data_wrangling import *

# 10/25/2021
# modified to be compatible with python 3

# 11/16/2022
# export daily network to shape file.

# 5/28/2023
# export daily transit boarding by transit line to external file
# create LINK extra attribute @voltransit_daily
# Create node extra attribute @daily_boarding and @daily_alighting at each transit stop

# 7/22/2025
# create daily transit network by merging all time of day transit lines.
# add transit boarding and alighting by TOD and daily (segment data) to the daily bank.
# now we can look into segment level boarding and alighting by TOD and daily inside the daily bank.

print(os.getcwd())

daily_network_fname = 'outputs/network/daily_network_results.csv'
daily_transit_boarding_fname = 'outputs/network/daily_boarding_by_transit_line.csv'
keep_atts = ['@type']
def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    skim_params_loc = os.path.abspath(os.path.join(os.getcwd(),"inputs\\skim_params")) 
    input_filename = os.path.join(skim_params_loc,dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)

def text_to_dictionary(dict_name):

    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_file=open(input_filename)
    my_dictionary = {}

    for line in my_file:
        k, v = line.split(':')
        my_dictionary[eval(k)] = v.strip()

    return(my_dictionary)


def create_emmebank(dir_name):
    
    #tod_dict = text_to_dictionary('time_of_day')
    emmebank_dimensions_dict = json_to_dictionary('emme_bank_dimensions')
    
    path = os.path.join('Banks', dir_name)
    if os.path.exists(path):
        shutil.rmtree(path)
    
    os.makedirs(path)
    path = os.path.join(path, 'emmebank')
    emmebank = _emmebank.create(path, emmebank_dimensions_dict)
    emmebank.title = dir_name
    scenario = emmebank.create_scenario(1002)
    network = scenario.get_network()
    #need to have at least one mode defined in scenario. Real modes are imported in network_importer.py
    network.create_mode('AUTO', 'a')
    scenario.publish_network(network)
    emmebank.dispose()

def copy_emmebank(from_dir, to_dir):
    if os.path.exists(to_dir):
        shutil.rmtree(to_dir)
    os.makedirs(to_dir)
    shutil.copytree(from_dir, to_dir, dirs_exist_ok = True)

def merge_networks(master_network, merge_network):
    for node in merge_network.nodes():
        if not master_network.node(node.id):
            new_node = master_network.create_regular_node(node.id)
            new_node.x = node.x
            new_node.y = node.y
            new_node.is_intersection = node.is_intersection
      
    for link in merge_network.links():
        if not master_network.link(link.i_node, link.j_node):
            new_link = master_network.create_link(link.i_node, link.j_node, link.modes)
            new_link.vertices = link.vertices
            new_link.shape = link.shape
            new_link.num_lanes = link.num_lanes
            new_link.length = link.length
            new_link.shape_length = link.shape_length
            new_link.type = link.type
            new_link.volume_delay_func = link.volume_delay_func
            new_link.data1 = link.data1
            new_link.data2 = link.data2
            new_link.data3 = link.data3

    for line in merge_network.transit_lines():
        if not master_network.transit_line(line.id):
            print(f'Adding transit line {line.id}, {line.description} to master network')
            newline = master_network.create_transit_line(line.id, line.vehicle.id, line.itinerary())
            newline.description = line.description
            newline.headway = line.headway
            newline.speed = line.speed
            newline.layover_time = line.layover_time
            newline.data1 = line.data1
            newline.data2 = line.data2
            newline.data3 = line.data3

            # update segments of the newly added line
            new_segments = newline.segments()
            seq = 0
            for segment in new_segments:
                segment.allow_alightings = line.segment(seq).allow_alightings
                segment.allow_boardings = line.segment(seq).allow_boardings
                segment.dwell_time = line.segment(seq).dwell_time
                segment.factor_dwell_time_by_length = line.segment(seq).factor_dwell_time_by_length
                segment.transit_time_func = line.segment(seq).transit_time_func
                segment.data1 = line.segment(seq).data1
                segment.data2 = line.segment(seq).data2
                segment.data3 = line.segment(seq).data3
                seq += 1
    return master_network

def export_link_values(my_project):
    ''' Extract link attribute values for a given scenario and emmebank (i.e., time period) '''

    network = my_project.current_scenario.get_network()
    link_type = 'LINK'

    # list of all link attributes
    link_attr = network.attributes(link_type)

    # Initialize a dataframe to store results
    df = pd.DataFrame()
    for attr in link_attr:
        print("processing: " + str(attr))
        
        # store values and node id for a single attr in a temp df 
        df_attr = pd.DataFrame([network.get_attribute_values(link_type, [attr])[1].keys(),
                          network.get_attribute_values(link_type, [attr])[1].values()]).T
        df_attr.columns = ['nodes', 'value']
        df_attr['measure'] = str(attr)
        df = pd.concat([df, df_attr], ignore_index = True)
        
    df = df.pivot(index='nodes',columns='measure',values='value').reset_index()
    df.to_csv(daily_network_fname)

    # Export shapefile
    shapefile_dir = r'outputs/network/daily_shapefile'
    if not os.path.exists(shapefile_dir):
        os.makedirs(shapefile_dir)
    network_to_shapefile = my_project.m.tool('inro.emme.data.network.export_network_as_shapefile')
    network_to_shapefile(export_path=shapefile_dir, scenario=my_project.current_scenario)

def main():
    print('creating daily bank')
    #Use a copy of an existing bank for the daily bank
    copy_emmebank('Banks/1530to1830', 'Banks/Daily')

    daily_emmebank =_emmebank.Emmebank(r'Banks\Daily\emmebank')
    # Set the emmebank title
    daily_emmebank.title = 'daily'
    daily_scenario = daily_emmebank.scenario(1002)
    daily_network = daily_scenario.get_network()

    # delete all other scenarios 
    scens = daily_emmebank.scenarios()
    for s in scens:
        if s.id != '1002':
            s.modify_protected = False
            s.delete_protected = False
            daily_emmebank.delete_scenario(s.id)                        

    # if demand_matrix_dictionary.json is missing create one
    user_class_dict_file = Path('inputs/skim_params/user_classes.json')    
    if user_class_dict_file.is_file() == False:
        update_skim_parameters()        
    matrix_dict = json_to_dictionary('user_classes')

    ################## delete all matrices #################

    for matrix in daily_emmebank.matrices():
        daily_emmebank.delete_matrix(matrix.id)
       
    ################ create new matrices in daily emmebank for trip tables only ##############
    for x in range(0, len(emme_config.emme_matrix_subgroups)):
        for y in range(0, len(matrix_dict[emme_config.emme_matrix_subgroups[x]])):
            daily_matrix = daily_emmebank.create_matrix(daily_emmebank.available_matrix_identifier('FULL'))
            daily_matrix.name = matrix_dict[emme_config.emme_matrix_subgroups[x]][y]['Name']
            daily_matrix.description = matrix_dict[emme_config.emme_matrix_subgroups[x]][y]['Description']
            
    daily_matrix_dict = {}
    for matrix in daily_emmebank.matrices():
        daily_arr = matrix.get_numpy_data()
        daily_matrix_dict[matrix.name] = daily_arr
        print(matrix.name)

    time_period_list = []


    for tod, time_period in sound_cast_net_dict.items():
        path = os.path.join('Banks', tod, 'emmebank')
        print(path)
        bank = _emmebank.Emmebank(path)
        scenario = bank.scenario(1002)
        network = scenario.get_network()
        # Trip  table stuff:
        for matrix in bank.matrices():
            if matrix.name in daily_matrix_dict:
                hourly_arr = matrix.get_numpy_data()
                daily_matrix_dict[matrix.name] = daily_matrix_dict[matrix.name] + hourly_arr
      
        # Network stuff:    
        if time_period != 'pm':
             daily_network = merge_networks(daily_network, network)           

    daily_scenario.publish_network(daily_network, resolve_attributes=True)

    # Write daily trip tables:
    for matrix in daily_emmebank.matrices():
        matrix.set_numpy_data(daily_matrix_dict[matrix.name])


    for extra_attribute in daily_scenario.extra_attributes():
        print(f'{extra_attribute} is removed from daily databank')
        if extra_attribute not in keep_atts:
            daily_scenario.delete_extra_attribute(extra_attribute)
            
    daily_volume_attr = daily_scenario.create_extra_attribute('LINK', '@tveh')
    daily_volume_attr.description = 'daily vehicle volume'
    daily_bike_vol_attr = daily_scenario.create_extra_attribute('LINK', '@bvoldaily')
    daily_bike_vol_attr.description = 'daily bike volume'
    if input_config.include_rec_bike:    
        daily_bike_vol_attr = daily_scenario.create_extra_attribute('LINK', '@recbvoldaily')
        daily_bike_vol_attr.description = 'daily rec bike volume'
    
    daily_network = daily_scenario.get_network()

    segments = []
    templates = []
    for tod, time_period in sound_cast_net_dict.items():
        path = os.path.join('Banks', tod, 'emmebank')
        print(path)
        bank = _emmebank.Emmebank(path)
        scenario = bank.scenario(1002)
        if daily_scenario.extra_attribute('@v' + tod):
            daily_scenario.delete_extra_attribute('@v' + tod)
        if daily_scenario.extra_attribute('@bvol' + tod):
            daily_scenario.delete_extra_attribuet('@bvol' + tod)
        if daily_scenario.extra_attribute('@tv' + tod):
            daily_scenario.delete_extra_attribute('@tv' + tod)
        if daily_scenario.extra_attribute('@recbvol' + tod):
            daily_scenario.delete_extra_attribute('@recbvol' + tod)
        if daily_scenario.extra_attribute('@bveh' + tod):
            daily_scenario.delete_extra_attribute('@bveh' + tod)
        if daily_scenario.extra_attribute('@mveh' + tod):
            daily_scenario.delete_extra_attribute('@mveh' + tod)
        if daily_scenario.extra_attribute('@hveh' + tod):
            daily_scenario.delete_extra_attribute('@hveh' + tod)
        if daily_scenario.extra_attribute('@volax' + tod):
            daily_scenario.delete_extra_attribute('@volax' + tod)
        

        # copy auto volume in each tod to daily bank
        attr = daily_scenario.create_extra_attribute('LINK', '@v' + tod)
        attr.description = 'vehicle volume ' + tod
        values = scenario.get_attribute_values('LINK', ['@tveh'])
        daily_scenario.set_attribute_values('LINK', [attr], values)

        # copy bus vehicle volume in each tod to daily bank
        attr = daily_scenario.create_extra_attribute('LINK', '@bveh' + tod)
        attr.description = 'bus vehicle volume ' + tod
        values = scenario.get_attribute_values('LINK', ['@bveh'])
        daily_scenario.set_attribute_values('LINK', [attr], values)

        # copy medium truck vehicle volume in each tod to daily bank
        attr = daily_scenario.create_extra_attribute('LINK', '@mveh' + tod)
        attr.description = 'medium truck vehicle volume ' + tod
        values = scenario.get_attribute_values('LINK', ['@mveh'])
        daily_scenario.set_attribute_values('LINK', [attr], values)

        # copy heavy truck vehicle volume in each tod to daily bank
        attr = daily_scenario.create_extra_attribute('LINK', '@hveh' + tod)
        attr.description = 'heavy vehicle volume ' + tod
        values = scenario.get_attribute_values('LINK', ['@hveh'])
        daily_scenario.set_attribute_values('LINK', [attr], values)

        attr = daily_scenario.create_extra_attribute('LINK', '@volax' + tod)
        attr.description = 'transit walk access volume ' + tod
        values = scenario.get_attribute_values('LINK', ['aux_transit_volume']) #volax
        daily_scenario.set_attribute_values('LINK', [attr], values)

        # copy transit volume (on link) in each tod to daily bank
        attr = daily_scenario.create_extra_attribute('LINK', '@tv' + tod)
        attr.description = 'transit volume on link ' + tod
        if scenario.extra_attribute('@voltr_l'):
            scenario.delete_extra_attribute('@voltr_l')

        # calculate transit volume on each link in each tod, by looping through all transit segments on each link
        # be aware that create_attribute() only creates an attribute in memory. 
        network = scenario.get_network()
        network.create_attribute('LINK', 'voltr_l', default_value = 0)
        for link in network.links():
            sum_voltr = 0
            for seg in link.segments():
                sum_voltr += seg.transit_volume
            link['voltr_l'] = sum_voltr
        values = network.get_attribute_values('LINK', ['voltr_l'])
        daily_scenario.set_attribute_values('LINK', [attr], values)

        # create bike volume for each TOD
        attr = daily_scenario.create_extra_attribute('LINK', '@bvol' + tod)
        attr.description = 'bike volume ' + tod
        values = scenario.get_attribute_values('LINK', ['@bvol'])
        daily_scenario.set_attribute_values('LINK', [attr], values)

        # create rec bike volume for each TOD
        if input_config.include_rec_bike:        
            attr = daily_scenario.create_extra_attribute('LINK', '@recbvol' + tod)
            attr.description = 'rec bike volume ' + tod
            values = scenario.get_attribute_values('LINK', ['@recbvol'])
            daily_scenario.set_attribute_values('LINK', [attr], values)

        # load transit segment boarding into dataframe
        # we now have daily transit network.load segment boarding / alighting 
        segment_df = get_transit_segment_data(scenario)
        segment_df.rename(columns =  {'transit_boardings':'board_'+ tod}, inplace = True)
        segments.append(segment_df[['id', 'board_'+ tod]])
        templates.append(segment_df[['id', 'line']])

        attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@tboard_seg_' + time_period)
        attr.description = 'total segment boardings ' + time_period
        values = scenario.get_attribute_values('TRANSIT_SEGMENT', ['@tboard']) 
        daily_scenario.set_attribute_values('TRANSIT_SEGMENT', [attr], values)

        attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@iboard_seg_' + time_period)
        attr.description = 'initial segment boardings ' + time_period
        values = scenario.get_attribute_values('TRANSIT_SEGMENT', ['@iboard']) 
        daily_scenario.set_attribute_values('TRANSIT_SEGMENT', [attr], values) 

        attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@trsboard_seg_' + time_period)
        attr.description = 'transfer segment boardings ' + time_period
        values = scenario.get_attribute_values('TRANSIT_SEGMENT', ['@trsboard']) 
        daily_scenario.set_attribute_values('TRANSIT_SEGMENT', [attr], values)      

        attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@talight_seg_' + time_period)
        attr.description = 'total segment alightings ' + time_period
        values = scenario.get_attribute_values('TRANSIT_SEGMENT', ['@talight']) 
        daily_scenario.set_attribute_values('TRANSIT_SEGMENT', [attr], values)

        attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@finalight_seg_' + time_period)
        attr.description = 'final segment alightings ' + time_period
        values = scenario.get_attribute_values('TRANSIT_SEGMENT', ['@finalight']) 
        daily_scenario.set_attribute_values('TRANSIT_SEGMENT', [attr], values)

        attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@trsalight_seg_' + time_period)
        attr.description = 'transfer segment alightings ' + time_period
        values = scenario.get_attribute_values('TRANSIT_SEGMENT', ['@transalight']) 
        daily_scenario.set_attribute_values('TRANSIT_SEGMENT', [attr], values)

        ## copy boarding alighting at transit stop in each tod to daily bank.
        # calculate daily boarding/alighting at each stop.
        # to be done.
        attr = daily_scenario.create_extra_attribute('NODE', '@tboard_' + time_period)
        attr.description = 'total boardings at stop ' + time_period
        values = scenario.get_attribute_values('NODE', ['@tboard_nde'])
        daily_scenario.set_attribute_values('NODE', [attr], values)

        attr = daily_scenario.create_extra_attribute('NODE', '@tiboard_' + time_period)
        attr.description = 'total init boardings at stop ' + time_period
        values = scenario.get_attribute_values('NODE', ['@tiboard_nde'])
        daily_scenario.set_attribute_values('NODE', [attr], values)

        attr = daily_scenario.create_extra_attribute('NODE', '@trsboard_' + time_period)
        attr.description = 'tot trsfer boardings at stop ' + time_period
        values = scenario.get_attribute_values('NODE', ['@trsboard_nde'])
        daily_scenario.set_attribute_values('NODE', [attr], values)

        attr = daily_scenario.create_extra_attribute('NODE', '@talight_'+time_period)
        attr.description = 'total alightings at stop ' + time_period
        values = scenario.get_attribute_values('NODE', ['@talight_nde'])
        daily_scenario.set_attribute_values('NODE', [attr], values)

        attr = daily_scenario.create_extra_attribute('NODE', '@falight_'+time_period)
        attr.description = 'total final alightings at stop ' + time_period
        values = scenario.get_attribute_values('NODE', ['@finalight_nde'])
        daily_scenario.set_attribute_values('NODE', [attr], values)

        attr = daily_scenario.create_extra_attribute('NODE', '@trsalight_'+time_period)
        attr.description = 'tot trsfer alightings at stop ' + time_period
        values = scenario.get_attribute_values('NODE', ['@trsalight_nde'])
        daily_scenario.set_attribute_values('NODE', [attr], values)

    # assemble transit segment dataframe by TOD in one dataframe
    # calculate daily boarding by transit line
    # export the dataframe to an external file.
    assembled_segment_df = pd.concat(templates)
    assembled_segment_df = assembled_segment_df.drop_duplicates(subset = ['id'])
    for df in segments:
        assembled_segment_df = assembled_segment_df.merge(df, on = 'id', how = 'left')
    
    transit_line_df = assembled_segment_df.groupby('line').sum()
    transit_line_df['daily_boarding'] = 0
    for tod in load_transit_tod:
        transit_line_df['daily_boarding'] += transit_line_df['board_' + tod]
        transit_line_df['board_' + tod] = transit_line_df['board_' + tod].astype(int)

    transit_line_df['daily_boarding'] = transit_line_df['daily_boarding'].astype(int)
    transit_line_df.to_csv(daily_transit_boarding_fname)
    print(f"Daily transit boarding is exported to {daily_transit_boarding_fname}")

    attr = daily_scenario.create_extra_attribute('LINK', '@voltransit_daily')
    attr.description = 'daily transit volume'

    attr = daily_scenario.create_extra_attribute('LINK', '@bveh_daily')
    attr.description = 'daily bus vehicle volume'

    attr = daily_scenario.create_extra_attribute('LINK', '@mveh_daily')
    attr.description = 'daily medium truck vehicle volume'

    attr = daily_scenario.create_extra_attribute('LINK', '@hveh_daily')
    attr.description = 'daily heavy truck vehicle volume'

    attr = daily_scenario.create_extra_attribute('LINK', '@volax_daily')
    attr.description = 'daily transit walk access volume'

    attr = daily_scenario.create_extra_attribute('NODE', '@daily_boarding')
    attr.description = 'daily total boarding at stop'
    attr = daily_scenario.create_extra_attribute('NODE', '@daily_iboarding')
    attr.description = 'daily initial boarding at stop'
    attr = daily_scenario.create_extra_attribute('NODE', '@daily_trsboarding')
    attr.description = 'daily transfer boarding at stop'

    attr = daily_scenario.create_extra_attribute('NODE', '@daily_alighting')
    attr.description = 'daily total alighting at stop'
    attr = daily_scenario.create_extra_attribute('NODE', '@daily_falighting')
    attr.description = 'daily final alighting at stop'
    attr = daily_scenario.create_extra_attribute('NODE', '@daily_trsalighting')
    attr.description = 'daily transfer alighting at stop'


    attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@daily_seg_board')
    attr.description = 'daily total boarding at segment'
    attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@daily_seg_iboard')
    attr.description = 'daily initial boarding at segment'
    attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@daily_seg_trsboard')
    attr.description = 'daily transfer boarding at segment'

    attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@daily_seg_alight')
    attr.description = 'daily total alighting at segment'
    attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@daily_seg_falight')
    attr.description = 'daily final alighting at segment'
    attr = daily_scenario.create_extra_attribute('TRANSIT_SEGMENT', '@daily_trsalight')
    attr.description = 'daily transfer alighting at segment'


    daily_network = daily_scenario.get_network()

    attr_list = ['@v' + x for x in tods]
    attr_list.extend(['@bvol' + x for x in tods])
    attr_list.extend(['@tv' + x for x in tods])
    attr_list.extend(['@bveh' + x for x in tods])
    attr_list.extend(['@mveh' + x for x in tods])
    attr_list.extend(['@hveh' + x for x in tods])
    attr_list.extend(['@volax' + x for x in tods])

    if input_config.include_rec_bike:    
        attr_list.extend(['@recbvol' + x for x in tods])
        # calculate daily volumes: auto, bike, and transit
        for link in daily_network.links():
            for item in tods:
                link['@tveh'] = link['@tveh'] + link['@v' + item]
                link['@bvoldaily'] = link['@bvoldaily'] + link['@bvol' + item]
                link['@voltransit_daily'] = link['@voltransit_daily'] + link['@tv' + item]
                link['@recbvoldaily']  = link['@recbvoldaily'] + link['@recbvol' + item]
                link['@bveh_daily'] = link['@bveh_daily'] + link['@bveh' + item]
                link['@mveh_daily'] = link['@mveh_daily'] + link['@mveh' + item]
                link['@hveh_daily'] = link['@hveh_daily'] + link['@hveh' + item]
                link['@volax_daily'] = link['@volax_daily'] + link['@volax' + item]
    else: 
        for link in daily_network.links():
            for item in tods:
                link['@tveh'] = link['@tveh'] + link['@v' + item]
                link['@bvoldaily'] = link['@bvoldaily'] + link['@bvol' + item]
                link['@voltransit_daily'] = link['@voltransit_daily'] + link['@tv' + item]
                link['@bveh_daily'] = link['@bveh_daily'] + link['@bveh' + item]
                link['@mveh_daily'] = link['@mveh_daily'] + link['@mveh' + item]
                link['@hveh_daily'] = link['@hveh_daily'] + link['@hveh' + item]
                link['@volax_daily'] = link['@volax_daily'] + link['@volax' + item]

    # calculate daily boarding and alightings at transit stops
    for node in daily_network.nodes():
        for tod in sound_cast_net_dict.values():
            node['@daily_boarding'] += node['@tboard_' + tod]
            node['@daily_iboarding'] += node['@tiboard_' + tod]
            node['@daily_trsboarding'] += node['@trsboard_' + tod]
            node['@daily_alighting'] += node['@talight_' + tod]
            node['@daily_falighting'] += node['@falight_' + tod]
            node['@daily_trsalighting'] += node['@trsalight_' + tod]

    for segment in daily_network.transit_segments():
        for tod in sound_cast_net_dict.values():
            segment['@daily_seg_board'] += segment['@tboard_seg_' + tod]
            segment['@daily_seg_iboard'] += segment['@iboard_seg_' + tod]
            segment['@daily_seg_trsboard'] += segment['@trsboard_seg_' + tod]
            segment['@daily_seg_alight'] += segment['@talight_seg_' + tod]
            segment['@daily_seg_falight'] += segment['@finalight_seg_' + tod]
            segment['@daily_trsalight'] += segment['@trsalight_seg_' + tod]

    daily_scenario.publish_network(daily_network, resolve_attributes=True)

    print('The following extra attributes are updated: ')
    print(str(attr_list))
    print('daily bank created')

    create_daily_project_folder()  
    # Write daily link-level results
    my_project = EmmeProject('projects/daily/daily.emp')

    export_link_values(my_project)

def get_transit_segment_data(scenario):
    network = scenario.get_network()
    segment_data = {'i_node':[], 'j_node':[]}
    segment_data.update({k: [] for k in network.attributes('TRANSIT_SEGMENT')})
    segment_data.update({'id': [], 'line': []})

    for segment in network.transit_segments():
        segment_data['i_node'].append(segment.i_node.id)
        if segment.j_node != None:
            segment_data['j_node'].append(segment.j_node.id)
        else:
            segment_data['j_node'].append(None)

        for k in network.attributes('TRANSIT_SEGMENT'):
            segment_data[k].append(segment[k])

        segment_data['id'].append(segment.id)
        segment_data['line'].append(segment.line.id)

    segment_df = pd.DataFrame(segment_data)

    return segment_df


def create_daily_project_folder():
    if os.path.exists(os.path.join('projects/Daily')):
        print('Delete Project Folder')
        shutil.rmtree('projects/Daily')

    emmeproject = app.create_project('projects', 'Daily')
    desktop = app.start_dedicated(False, modeller_initial, emmeproject)
    data_explorer = desktop.data_explorer()
    database = data_explorer.add_database('Banks/Daily/emmebank')
    database.open()
    desktop.project.save()
    desktop.close()

    old_emme_path = Path(project_folder) / 'Banks/Daily/emmebank'
    with open(emmeproject, 'r') as f:
        contents = f.read()
    relative_mbank = os.path.relpath('Banks/Daily/emmebank', start=os.path.dirname(emmeproject))
    print(relative_mbank)
    contents = contents.replace(old_emme_path.as_posix(), relative_mbank)
    with open(emmeproject, 'w') as f:
        f.write(contents)
            
            #copy worksheets
    wspath = os.path.join('inputs/model/worksheets/', 'Daily')
    destpath = os.path.join('projects/', 'Daily', 'Worksheets')
    copyfiles(wspath, destpath)
    # copy media files
    destpath = os.path.join('projects/', 'Daily', 'Media')
    copyfiles('inputs/model/Media/', destpath)
    
    print('daily project folder is created.')

if __name__ == '__main__':
    run_context = os.getenv('RUN_CONTEXT') # chained if this script is called from another script, otherwise it is standalone
    if run_context == 'chained':
        meta_data = False
    else:
        meta_data = True

    logger, start_time = open_main_logger(meta_data, 'Data Processing')
    logger.info(f"Running script: {os.path.basename(__file__)} %s", " ".join(sys.argv[1:]))
    main()
    end_time = datetime.datetime.now()
    elapsed_total = end_time - start_time
    logger.info(f'Total run time: {elapsed_total}')
