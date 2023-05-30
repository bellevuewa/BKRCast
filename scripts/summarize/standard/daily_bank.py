import inro.emme.database.emmebank as _emmebank
import inro.emme.desktop.app as app
import os, sys
import numpy as np
import pandas as pd
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from input_configuration import *
from emme_configuration import *
import json
import shutil
from distutils import dir_util
from EmmeProject import *

# 10/25/2021
# modified to be compatible with python 3

# 11/16/2022
# export daily network to shape file.

# 5/28/2023
# export daily transit boarding by transit line to external file
# create LINK extra attribute @voltransit_daily
# Create node extra attribute @daily_boarding and @daily_alighting at each transit stop

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
    dir_util.copy_tree(from_dir, to_dir)

def merge_networks(master_network, merge_network):
    for node in merge_network.nodes():
        if not master_network.node(node.id):
            new_node = master_network.create_regular_node(node.id)
            new_node.x = node.x
            new_node.y = node.y
            new_node.is_intersection = node.is_intersection
      
    for link in merge_network.links():
        if not master_network.link(link.i_node, link.j_node):
            master_network.create_link(link.i_node, link.j_node, link.modes)

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
        df = df.append(df_attr)
        
    df = df.pivot(index='nodes',columns='measure',values='value').reset_index()
    df.to_csv(daily_network_fname)

    # Export shapefile
    shapefile_dir = r'outputs/network/shapefile'
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

    matrix_dict = text_to_dictionary('demand_matrix_dictionary')
    uniqueMatrices = set(matrix_dict.values())

    ################## delete all matrices #################

    for matrix in daily_emmebank.matrices():
        daily_emmebank.delete_matrix(matrix.id)
       
    ################ create new matrices in daily emmebank for trip tables only ##############

    for unique_name in uniqueMatrices:
        daily_matrix = daily_emmebank.create_matrix(daily_emmebank.available_matrix_identifier('FULL')) #'FULL' means the full-type of trip table
        daily_matrix.name = unique_name

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
        if len(time_period_list) == 0:
            daily_network = network
            time_period_list.append(time_period)
        elif time_period not in time_period_list:
            time_period_list.append(time_period) #this line was repeated below
            daily_network = merge_networks(daily_network, network)
            time_period_list.append(time_period) #this line was repeated above
    daily_scenario.publish_network(daily_network, resolve_attributes=True)

    # Write daily trip tables:
    for matrix in daily_emmebank.matrices():
        matrix.set_numpy_data(daily_matrix_dict[matrix.name])


    for extra_attribute in daily_scenario.extra_attributes():
        print(f'{extra_attribute} is removed from daily databank')
        if extra_attribute not in keep_atts:
            daily_scenario.delete_extra_attribute(extra_attribute)
    daily_volume_attr = daily_scenario.create_extra_attribute('LINK', '@tveh')
    daily_volume_attr.description = 'daily auto volume'
    daily_bike_vol_attr = daily_scenario.create_extra_attribute('LINK', '@bvoldaily')
    daily_bike_vol_attr.description = 'daily bike volume'
    daily_network = daily_scenario.get_network()

    segments = []
    templates = []
    for tod, time_period in sound_cast_net_dict.items():
        path = os.path.join('Banks', tod, 'emmebank')
        print(path)
        bank = _emmebank.Emmebank(path)
        scenario = bank.scenario(1002)
        if daily_scenario.extra_attribute('@v' + tod[:4]):
            daily_scenario.delete_extra_attribute('@v' + tod[:4])
        if daily_scenario.extra_attribute('@bvol' + tod[:4]):
            daily_scenario.delete_extra_attribuet('@bvol' + tod[:4])
        if daily_scenario.extra_attribute('@tv' + tod[:4]):
            daily_scenario.delete_extra_attribute('@tv' + tod[:4])

        # copy auto volume in each tod to daily bank
        attr = daily_scenario.create_extra_attribute('LINK', '@v' + tod[:4])
        attr.description = 'auto volume ' + tod
        values = scenario.get_attribute_values('LINK', ['@tveh'])
        daily_scenario.set_attribute_values('LINK', [attr], values)

        # copy transit volume (on link) in each tod to daily bank
        attr = daily_scenario.create_extra_attribute('LINK', '@tv' + tod[:4])
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
        attr = daily_scenario.create_extra_attribute('LINK', '@bvol' + tod[:4])
        attr.description = 'bike volume ' + tod
        values = scenario.get_attribute_values('LINK', ['@bvol'])
        daily_scenario.set_attribute_values('LINK', [attr], values)

        # load transit segment boarding into dataframe
        # unlike auto network in daily bank, we do not have a daily transit network. Can only export daily boarding 
        # in dataframe.
        segment_df = get_transit_segment_data(scenario)
        segment_df.rename(columns =  {'transit_boardings':'board_'+ tod}, inplace = True)
        segments.append(segment_df[['id', 'board_'+ tod]])
        templates.append(segment_df[['id', 'line']])

        ## copy boarding alighting at transit stop in each tod to daily bank.
        # calculate daily boarding/alighting at each stop.
        # to be done.
        attr = daily_scenario.create_extra_attribute('NODE', '@board_' + tod)
        attr.description = 'boardings at transit stop ' + tod
        values = scenario.get_attribute_values('NODE', ['initial_boardings'])
        daily_scenario.set_attribute_values('NODE', [attr], values)

        attr = daily_scenario.create_extra_attribute('NODE', '@alight_'+tod)
        attr.description = 'alightings at transit stop ' + tod
        values = scenario.get_attribute_values('NODE', ['final_alightings'])
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
    attr = daily_scenario.create_extra_attribute('NODE', '@daily_boarding')
    attr.description = 'daily boarding at transit stop'
    attr = daily_scenario.create_extra_attribute('NODE', '@daily_alighting')
    attr.description = 'daily alighting at transit stop'

    daily_network = daily_scenario.get_network()

    attr_list = ['@v' + x for x in tods]
    attr_list.extend(['@bvol' + x for x in tods])
    attr_list.extend(['@tv' + x for x in tods])

    # calculate daily volumes: auto, bike, and transit
    for link in daily_network.links():
        for item in tods:
            link['@tveh'] = link['@tveh'] + link['@v' + item[:4]]
            link['@bvoldaily'] = link['@bvoldaily'] + link['@bvol' + item[:4]]
            link['@voltransit_daily'] = link['@voltransit_daily'] + link['@tv' + item[:4]]

    # calculate daily boarding and alightings at transit stops
    for node in daily_network.nodes():
        for tod in tods:
            node['@daily_boarding'] += node['@board_' + tod]
            node['@daily_alighting'] += node['@alight_' + tod]

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
    if os.path.exists(os.path.join('projects/daily')):
        print('Delete Project Folder')
        shutil.rmtree('projects/daily')

    project = app.create_project('projects', 'daily')
    desktop = app.start_dedicated(False, modeller_initial, project)
    data_explorer = desktop.data_explorer()
    database = data_explorer.add_database('Banks/daily/emmebank')
    database.open()
    desktop.project.save()
    desktop.close()
    print('daily project folder is created.')

if __name__ == '__main__':
    main()
