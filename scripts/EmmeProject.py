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

import inro.emme.desktop.app as app
import inro.modeller as _m
import os, sys
import time
import toml
import pandas as pd
import json
import numpy as np
import h5py
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"inputs"))
import input_configuration as input_config
import emme_configuration as emme_config

# 10/25/2021
# modified to be compatible with python 3

class EmmeProject:
    def __init__(self, filepath):
        self.desktop = app.start_dedicated(True, input_config.modeller_initial, filepath)
        self.m = _m.Modeller(self.desktop)
        pathlist = filepath.split("/")
        self.fullpath = filepath
        self.filename = pathlist.pop()
        self.dir = "/".join(pathlist) + "/"
        self.bank = self.m.emmebank
        self.tod = self.bank.title
        self.current_scenario = list(self.bank.scenarios())[0]
        self.data_explorer = self.desktop.data_explorer()

    def network_counts_by_element(self, element):
        network = self.current_scenario.get_network()
        d = network.element_totals
        count = d[element]
        return count

    def change_active_database(self, database_name):
        for database in self.data_explorer.databases():
            #print database.title()
            if database.title() == database_name:
                # self.bank.dispose()                
                database.open()
                self.bank = self.m.emmebank
                self.tod = self.bank.title
                self.current_scenario = list(self.bank.scenarios())[0]

    def process_modes(self, mode_file):
        NAMESPACE = "inro.emme.data.network.mode.mode_transaction"
        process_modes = self.m.tool(NAMESPACE)
        process_modes(transaction_file = mode_file,
              revert_on_error = True,
              scenario = self.current_scenario)
                
    def create_scenario(self, scenario_number, scenario_title = 'test'):
        NAMESPACE = "inro.emme.data.scenario.create_scenario"
        create_scenario = self.m.tool(NAMESPACE)
        create_scenario(scenario_id=scenario_number,
                        scenario_title= scenario_title)
   
    def delete_links(self):
        if self.network_counts_by_element('links') > 0:
            NAMESPACE = "inro.emme.data.network.base.delete_links"
            delete_links = self.m.tool(NAMESPACE)
            delete_links(condition="cascade")

    def delete_nodes(self):
        if self.network_counts_by_element('regular_nodes') > 0:
            NAMESPACE = "inro.emme.data.network.base.delete_nodes"
            delete_nodes = self.m.tool(NAMESPACE)
            delete_nodes(condition="cascade")

    def delete_all_functions(self):
        NAMESPACE = "inro.emme.data.function.delete_function"
        delete_function = self.m.tool(NAMESPACE)
        for i in range(1,99):
            for ftype in ['fd', 'ft', 'fp']:
                fid = ftype + str(i)
                func = self.m.emmebank.function(fid)
                if func is not None:
                    delete_function(func)

    def process_vehicles(self,vehicle_file):
          NAMESPACE = "inro.emme.data.network.transit.vehicle_transaction"
          process = self.m.tool(NAMESPACE)
          process(transaction_file = vehicle_file,
            revert_on_error = True,
            scenario = self.current_scenario)

    def process_base_network(self, basenet_file):
        NAMESPACE = "inro.emme.data.network.base.base_network_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = basenet_file,
              revert_on_error = True,
              scenario = self.current_scenario)
    def process_turn(self, turn_file):
        NAMESPACE = "inro.emme.data.network.turn.turn_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = turn_file,
            revert_on_error = False,
            scenario = self.current_scenario)

    def process_transit(self, transit_file):
        NAMESPACE = "inro.emme.data.network.transit.transit_line_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = transit_file,
            revert_on_error = True,
            scenario = self.current_scenario)
    def process_shape(self, linkshape_file):
        NAMESPACE = "inro.emme.data.network.base.link_shape_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = linkshape_file,
            revert_on_error = True,
            scenario = self.current_scenario)

    def change_scenario(self, scen):
        self.current_scenario = scen

    def delete_matrix(self, matrix):
        NAMESPACE = "inro.emme.data.matrix.delete_matrix"
        process = self.m.tool(NAMESPACE)
        process(matrix, self.bank)

    def delete_matrices(self, matrix_type):
        NAMESPACE = "inro.emme.data.matrix.delete_matrix"
        process = self.m.tool(NAMESPACE)
        for matrix in self.bank.matrices():
            if matrix_type == "ALL":
                process(matrix, self.bank)
            elif matrix.type == matrix_type:
                process(matrix, self.bank)

    def create_matrix (self, matrix_name, matrix_description, matrix_type):
        NAMESPACE = "inro.emme.data.matrix.create_matrix"
        process = self.m.tool(NAMESPACE)
        process (matrix_id= self.bank.available_matrix_identifier(matrix_type),
                          matrix_name= matrix_name,
                          matrix_description= matrix_description,
                          default_value=0,
                          overwrite=True,
                          scenario=self.current_scenario)

    def matrix_calculator(self, **kwargs):
        spec = json_to_dictionary('matrix_calc_spec')
        for name, value in kwargs.items():
            if name == 'aggregation_origins':
                spec['aggregation']['origins'] = value
            elif name == 'aggregation_destinations':
                spec['aggregation']['destinations'] = value
            elif name == 'constraint_by_value':
                spec['constraint']['by_value'] = value
            elif name == 'constraint_by_zone_origins':
                spec['constraint']['by_zone']['origins'] = value
            elif name == 'constraint_by_zone_destinations':
                spec['constraint']['by_zone']['destinations'] = value
            else:
                spec[name] = value
        #print spec
        NAMESPACE = "inro.emme.matrix_calculation.matrix_calculator"
        process = self.m.tool(NAMESPACE)
        report = process(spec) 
        return report

    def matrix_transaction(self, transactionFile):
        NAMESPACE="inro.emme.data.matrix.matrix_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = transactionFile,
                       throw_on_error = True,
                       scenario = self.current_scenario)

    def initialize_zone_partition(self, partition_name):
        NAMESPACE="inro.emme.data.zone_partition.init_partition"
        process = self.m.tool(NAMESPACE)
        process(partition=partition_name)
        
    def process_zone_partition(self, transactionFile):
        NAMESPACE="inro.emme.data.zone_partition.partition_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = transactionFile,
                       throw_on_error = True,
                       scenario = self.current_scenario)

    def create_extra_attribute(self, type, name, description, overwrite, default_value = 0, series = None):
        NAMESPACE="inro.emme.data.extra_attribute.create_extra_attribute"
        process = self.m.tool(NAMESPACE)
        if series == None:        
            process(extra_attribute_type=type,
                          extra_attribute_name= name,
                          extra_attribute_description= description, overwrite=overwrite, 
                          extra_attribute_default_value = default_value)
        else:
            process(extra_attribute_type=type,
                          extra_attribute_name= name,
                          extra_attribute_description= description, overwrite=overwrite, 
                          extra_attribute_default_value = default_value, series = series)

    def delete_extra_attribute(self, name):
        NAMESPACE="inro.emme.data.extra_attribute.delete_extra_attribute"
        process = self.m.tool(NAMESPACE)
        process(name)

    def network_calculator(self, type, **kwargs):
        spec = json_to_dictionary(type)
        for name, value in kwargs.items():
            if name == 'selections_by_link':
                spec['selections']['link'] = value
            elif name == 'selections_by_node':
                spec['selections']['node'] = value
            else:
                spec[name] = value
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.network_calc_result = network_calc(spec)

    def process_function_file(self, file_name):
        NAMESPACE="inro.emme.data.function.function_transaction"
        process = self.m.tool(NAMESPACE)
        process(file_name ,throw_on_error = True)

    def matrix_balancing(self, **kwargs):
        spec = json_to_dictionary('matrix_balancing_spec')
        for name, value in kwargs.items():
            if name == 'results_od_balanced_values':
                spec['results']['od_balanced_values'] = value
            elif name == 'constraint_by_value':
                spec['constraint']['by_value'] = value
            elif name == 'constraint_by_zone_origins':
                spec['constraint']['by_zone']['origins'] = value
            elif name == 'constraint_by_zone_destinations':
                spec['constraint']['by_zone']['destinations'] = value
            else:
                spec[name] = value
        NAMESPACE = "inro.emme.matrix_calculation.matrix_balancing"
        compute_matrix = self.m.tool(NAMESPACE)
        report = compute_matrix(spec) 

    def import_matrices(self, matrix_name):
        NAMESPACE = "inro.emme.data.matrix.matrix_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = matrix_name,
            throw_on_error = False,
            scenario = self.current_scenario)

    def transit_line_calculator(self, **kwargs):
        spec = json_to_dictionary("transit_line_calculation")
        for name, value in kwargs.items():
            spec[name] = value
        
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.transit_line_calc_result = network_calc(spec)

    def transit_segment_calculator(self, **kwargs):
        spec = json_to_dictionary("transit_segment_calculation")
        for name, value in kwargs.items():
            spec[name] = value
        
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.transit_segment_calc_result = network_calc(spec)

    # flag: link selector (only one flag can be used for now)
    # flag_value: selector = ?
    # scen_id: scenario id
    def calculate_VHT_subarea(self, flag, flag_value, scen_id):
        scen = self.bank.scenario(scen_id)
        if scen == None:
            print('scen_id ', scen_id, 'is not in the databank ', self.fullpath)
            return None
        
        links = scen.get_network().links()
        VMT = 0
        VHT = 0
        VDT = 0
        total_vol = 0
        total_length = 0
        for link in links:
            if link[flag] == flag_value:
                total_vol = total_vol + link.auto_volume
                total_length = total_length + link.length
                VMT = VMT + link.auto_volume * link.length
                VHT = VHT + link.auto_volume * link.auto_time / 60
                VDT = VDT + link.auto_volume * (link.auto_time / 60 - link.length / link.data2)
                ret = {'VMT': VMT, 'VHT': VHT, 'VDT': VDT, 'TotalVol':total_vol, 'LinkLength':total_length}

        return ret
    
    def export_omx_matrices(self, output_mat_file):
        matrix_dict = text_to_dictionary('demand_matrix_dictionary')
        uniqueMatrices = set(matrix_dict.values())
        NAMESPACE = "inro.emme.data.matrix.export_to_omx"
        export_to_omx = self.m.tool(NAMESPACE)
        export_to_omx(uniqueMatrices, output_mat_file, append_to_file=False,
                      scenario=self.current_scenario,
                      omx_key = 'NAME')

    def export_matrix(self, matrix, matrix_path_name):
        NAMESPACE = "inro.emme.data.matrix.export_matrices"
        process = self.m.tool(NAMESPACE)
        process(matrices=matrix,
                export_file=matrix_path_name, 
                field_separator=' ',
                export_format="PROMPT_DATA_FORMAT",
                skip_default_values=True,
                full_matrix_line_format="ONE_ENTRY_PER_LINE")

    def closeDesktop(self):
        self.bank.dispose()
        self.desktop.close()

    def import_attribute_values(self, file_path, revert_on_error, import_definitions = False):
        NAMESPACE = "inro.emme.data.extra_attribute.import_extra_attributes"
        import_values = self.m.tool(NAMESPACE)
        import_values(file_path, scenario = self.current_scenario, column_labels = 'FROM_HEADER',revert_on_error = revert_on_error, import_definitions = import_definitions)

    def emme_nodes_to_df(self):
        '''
            load emme nodes to dataframe.         
        '''
        network = self.current_scenario.get_network()
        network.create_attribute('NODE', 'numIn')
        network.create_attribute('NODE', 'numOut')
        for node in network.nodes():
            node.numIn = len(list(node.incoming_links()))        
            node.numOut = len(list(node.outgoing_links()))
        
        node_data = {'id':[]}
        node_data.update({k: [] for k in network.attributes('NODE')})        
        for node in network.nodes():
            for k in network.attributes('NODE'):
                node_data[k].append(node[k])  

            node_data['id'].append(node.number)  

        nodes_df = pd.DataFrame(node_data)
        return nodes_df                                                

    def emme_links_to_df(self):
        '''
            load emme links to dataframe. Add a few boolean variables to the links_df. These boolean variables are:
                isAuto, isConnector, isOneWay, isTransit
        '''
        network = self.current_scenario.get_network()
        network.create_attribute('NODE', 'numIn')
        network.create_attribute('NODE', 'numOut')
        for node in network.nodes():
            node.numIn = len(list(node.incoming_links()))        
            node.numOut = len(list(node.outgoing_links()))

        network.create_attribute('LINK', 'isAuto')
        network.create_attribute('LINK', 'isTransit')
        network.create_attribute('LINK', 'isConnector')
        network.create_attribute('LINK', 'isOneWay')
        auto_mode = set([m for m in network.modes() if m.type == 'AUTO'])
        transit_mode = set([m for m in network.modes() if m.type == 'TRANSIT'])

        link_data = {'i_node':[], 'j_node': []}
        link_data.update({k: [] for k in network.attributes('LINK')})
        for link in network.links():
            link.isAuto = bool(link.modes.intersection(auto_mode))
            link.isTransit = bool(link.modes.intersection(transit_mode))
            link.isConnector = (link.i_node.is_centroid or link.j_node.is_centroid)
            link.isOneWay = network.link(link.j_node, link.i_node) is None

            for k in network.attributes('LINK'):
                link_data[k].append(link[k])

            link_data['i_node'].append(link.i_node.number)
            link_data['j_node'].append(link.j_node.number)
        links_df = pd.DataFrame(link_data)

        return links_df

    def set_primary_scenario(self, scen_id):
        scen = self.bank.scenario(scen_id)
        if scen is not None:
            self.data_explorer.replace_primary_scenario(scen)
            self.current_scenario = scen            
        else:
            from colorama import Fore, init
            init(autoreset = True)
            print(f'scenario {scen_id} does not exist in {self.tod}.') 
            exit(-1)
            
    def create_extra_attributes(self, attr_dict):
        for attrname, desc in attr_dict.items():
            if attrname in self.current_scenario.extra_attributes():
                self.delete_extra_attribute(attrname)
            self.create_extra_attribute('LINK', attrname, desc, 'True')

    def calc_total_vehicles(self):
         '''calculate link level volume, store as extra attribute on the link'''
    
         #medium trucks
         self.network_calculator("link_calculation", result = '@mveh', expression = '@metrk/1.5')
     
         #heavy trucks:
         self.network_calculator("link_calculation", result = '@hveh', expression = '@hvtrk/2.0')
     
         #busses:
         self.network_calculator("link_calculation", result = '@bveh', expression = '@trnv3/2.0')

         ###################################################################  
         # Need to ensure delivery truck is included in the model (supplemental module)  
         # delivery truck/light truck is no longer explicitly modeled. They are now treated as SOV         
         if input_config.include_delivery:
             self.network_calculator("link_calculation", result='@dveh', expression='@lttrk/1.5') # delivery trucks       
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
         self.network_calculator("link_calculation", result = '@tveh', expression = str_expression)

    def calculate_transit_alighting_by_segment(self, spec = None):
        for name, desc in input_config.transit_segment_extra_attributes_dict.items():
            self.create_extra_attribute('TRANSIT_SEGMENT', name, desc, True)    
        self.create_extra_attribute('TRANSIT_SEGMENT', 'temp', 'temporary segment attribute', True, 0, [1,6])                 

        ns = "inro.emme.transit_assignment.extended.network_results"
        network_results = self.m.tool(ns)
        if spec == None:
            # import spec from skim_param/transit_network_results.json
            spec = json_to_dictionary('transit_network_results')
            # spec['on_segments']['total_alightings'] = '@talight'  
            # spec['on_segments']['transfer_alightings'] = '@transalight'
            # spec['on_segments']['final_alightings'] = '@finalight'  
            # spec['on_segments']['total_boardings'] = '@tboard'
            # spec['on_segments']['initial_boardings'] = '@iboard'
            # spec['on_segments']['transfer_boardings'] = '@trsboard'
            
            spec['on_segments']['total_alightings'] = '@temp1'  
            spec['on_segments']['transfer_alightings'] = '@temp2'
            spec['on_segments']['final_alightings'] = '@temp3'  
            spec['on_segments']['total_boardings'] = '@temp4'
            spec['on_segments']['initial_boardings'] = '@temp5'
            spec['on_segments']['transfer_boardings'] = '@temp6'
         
        network = self.current_scenario.get_partial_network(["TRANSIT_LINE", "TRANSIT_SEGMENT"], include_attributes=True) 
            
        for class_name in ['trnst','commuter_rail','ferry','litrat','passenger_ferry']:
            network_results(spec, class_name = class_name)  
            # be careful. Below network and scenario are not consistent. We are directly working on network elements. 
            # After that we need to set changes to scenario. Bentley support #CS0228290            
            kind, attrs = "TRANSIT_SEGMENT", ["@temp1", "@temp2", "@temp3", "@temp4", "@temp5", "@temp6"]            
            values = self.current_scenario.get_attribute_values(kind, attrs)
            network.set_attribute_values(kind, attrs, values)  

            for line in network.transit_lines():
                for seg in line.segments(True):
                    seg['@talight'] += seg['@temp1']
                    seg['@transalight'] += seg['@temp2']
                    seg['@finalight'] += seg['@temp3']
                    seg['@tboard'] += seg['@temp4']
                    seg['@iboard'] += seg['@temp5']
                    seg['@trsboard'] += seg['@temp6']

        kind, attrs = "TRANSIT_SEGMENT", ["@talight", "@transalight", "@finalight", "@tboard", "@iboard", "@trsboard"]
        values = network.get_attribute_values(kind, attrs)
        self.current_scenario.set_attribute_values(kind, attrs, values)        

    def transit_summary(self, node_attr_study_area = '@ndmma'):
        """Export transit line, segment, and mode attributes"""

        # Extract Transit Node Data
        transit_node_data = []
        if self.current_scenario.extra_attribute(node_attr_study_area) == None:
            from colorama import Fore, init
            init(autoreset = True)
            print(f'The study area node attribute {node_attr_study_area} is not defined in EMME {self.tod} databank. {Fore.GREEN} @ndmma is used instead.')            
            self.create_extra_attribute('NODE', '@ndmma', 'flag for subarea', True)
            self.import_attribute_values(os.path.join(input_config.project_folder, 'inputs/extra_attributes/@ndmma.txt'), False)  
            node_attr_study_area = '@ndmma'
         
        network = self.current_scenario.get_network()
        tod = self.tod

        # Extract Transit Line Data
        transit_line_data = []
        for line in network.transit_lines():
            transit_line_data.append({'line_id': int(line.id), 
                                      'route_code': line.id, # line name
                                      'mode': str(line.mode),
                                      'description': line.description,
                                      'boardings': line['@board'], 
                                      'time': line['@timtr']})
        _df_transit_line = pd.DataFrame(transit_line_data)
        _df_transit_line['tod'] = tod
   
        for node in network.nodes():
            transit_node_data.append({'node_id': int(node.id), 
                                      'node_subarea': node[node_attr_study_area]})

        _df_transit_node = pd.DataFrame(transit_node_data)
        _df_transit_node['tod'] = tod
    
        # Extract Transit Segment Data
        transit_segment_data = []

        for tseg in network.transit_segments():
            bus_vehs = float(60/tseg.line.headway * emme_config.hwy_tod[emme_config.sound_cast_net_dict[self.tod]])            
            if tseg.j_node is None:
                transit_segment_data.append({'line_id': int(tseg.line.id), 
                                      'segment_boarding': float(tseg.transit_boardings), 
                                      'segment_initial_boarding': float(tseg['@iboard']), 
                                      'segment_transfer_boarding': float(tseg['@trsboard']), 
                                      'segment_volume': float(tseg.transit_volume), 
                                      'segment_alighting': float(tseg['@talight']),                                      
                                      'segment_transfer_alighting': float(tseg['@transalight']),                                      
                                      'segment_final_alighting': float(tseg['@finalight']),    
                                      'length': 0,                                                                         
                                      'ul2':  np.nan,
                                      'transit_travel_time': tseg.transit_time,
                                      'bus_vehicles': bus_vehs,   
                                      'isHidden': True,                                                                             
                                      'i_node': int(tseg.i_node.number),
                                      'j_node': np.nan})
            else:
                transit_segment_data.append({'line_id': int(tseg.line.id), 
                                      'segment_boarding': float(tseg.transit_boardings), 
                                      'segment_initial_boarding': float(tseg['@iboard']), 
                                      'segment_transfer_boarding': float(tseg['@trsboard']), 
                                      'segment_volume': float(tseg.transit_volume), 
                                      'segment_alighting': float(tseg['@talight']),                                      
                                      'segment_transfer_alighting': float(tseg['@transalight']),                                      
                                      'segment_final_alighting': float(tseg['@finalight']),
                                      'length':tseg.link.length,
                                      'ul2':  tseg.link.data2,
                                      'transit_travel_time': float(tseg.transit_time), 
                                      'bus_vehicles': bus_vehs,                                                                            
                                      'isHidden': False,                                                                            
                                      'i_node': int(tseg.i_node.number),
                                      'j_node': int(tseg.j_node.number)})
    
        _df_transit_segment = pd.DataFrame(transit_segment_data)
        _df_transit_stops = _df_transit_segment[['i_node', 'segment_boarding', 'segment_initial_boarding', 'segment_transfer_boarding', 'segment_alighting', 'segment_final_alighting', 'segment_transfer_alighting']].groupby('i_node').sum()
        _df_transit_node = _df_transit_node.merge(_df_transit_stops, left_on = 'node_id', right_index = True, how = 'left').fillna(0)
        _df_transit_node = _df_transit_node.rename(columns = {'segment_boarding':'total_boarding', 'segment_initial_boarding':'initial_boarding', 'segment_transfer_boarding': 'transfer_boarding', 
                                 'segment_alighting':'total_alighting', 'segment_final_alighting':'final_alighting', 'segment_transfer_alighting':'transfer_alighting'})                
        _df_transit_node['tod'] = tod 
                              
        _df_transit_segment['tod'] = tod        
        _df_transit_segment = _df_transit_segment.merge(_df_transit_node[['node_id', 'node_subarea']], left_on = 'i_node', right_on = 'node_id', how = 'left') 
        _df_transit_segment.drop(columns = ['node_id'], inplace = True)
        _df_transit_segment.rename(columns = {'node_subarea':'i_node_subarea'}, inplace = True) 

        _df_transit_segment['PMT'] = _df_transit_segment['segment_volume'] * _df_transit_segment['length']
        _df_transit_segment['PHT'] = _df_transit_segment['segment_volume'] * _df_transit_segment['transit_travel_time'] / 60 
        _df_transit_segment['PHD'] = _df_transit_segment['segment_volume'] * (_df_transit_segment['transit_travel_time'] - _df_transit_segment['length'] / _df_transit_segment['ul2'] * 60) / 60                                            

        _df_transit_segment['VMT'] = _df_transit_segment['bus_vehicles'] * _df_transit_segment['length']
        _df_transit_segment['VHT'] = _df_transit_segment['bus_vehicles'] * _df_transit_segment['transit_travel_time'] / 60 
        _df_transit_segment['VHD'] = _df_transit_segment['bus_vehicles'] * (_df_transit_segment['transit_travel_time'] - _df_transit_segment['length'] / _df_transit_segment['ul2'] * 60) / 60                                            

        return _df_transit_line, _df_transit_node, _df_transit_segment
         
    def create_partition(self, partition_id, p_descr, dicts_of_val_zones):
        # if partition exists in the databank, print a warning message, then delete it.
        partition = self.bank.partition(partition_id)        
        if partition == None:
            print(f'partition {partition_id} does not exist. ')

        partition.initialize()
        partition.description = p_descr
        partition_val = partition.get_data()

        # set value for each taz
        for val, list_zones in dicts_of_val_zones.items():
            for taz in list_zones:
                partition_val.set(taz, val)

        partition.set_data(partition_val)  

    def matrix_to_emme(self, numpy_matrix, mfname, description, matrix_type):
        matrix_name_list = [matrix.name for matrix in self.bank.matrices()]
        if mfname not in matrix_name_list:
            self.create_matrix(mfname, description, matrix_type) 
    
        matrix_id = self.bank.matrix(mfname).id    
        self.bank.matrix(matrix_id).set_numpy_data(numpy_matrix, self.current_scenario)

    def load_supplemental_trips(self, matrix_name):
        ''' Load externals, special generator, and group quarters trips
            from the supplemental trip model. Supplemental trips are assumed
            only on Income Class 2, so only these income class modes are modified here. '''

        tod = self.tod
        zonesDim = len(self.current_scenario.zone_numbers)    
        # Create empty array to fill with trips
        demand_matrix = np.zeros((zonesDim,zonesDim), np.float64)
        hdf_file = h5py.File(emme_config.supplemental_loc + tod + '.h5', "r")
        # Call correct mode name by removing income class value when needed
        if matrix_name in ['svtl2', 'h2tl2', 'h3tl2']:
            mode_name = matrix_name[:-1]
        else:
            mode_name = matrix_name

        # Open mode-specific array for this TOD and mode
        hdf_array = hdf_file[mode_name]
    
        # Extract specified array size and store as NumPy array 
        sub_demand_matrix = hdf_array[0:zonesDim, 0:zonesDim]
        sub_demand_array = (np.asarray(sub_demand_matrix))
        demand_matrix[0:len(sub_demand_array), 0:len(sub_demand_array)] = sub_demand_array

        return demand_matrix
                      
    def calc_bus_pce(self):
     total_hours = emme_config.transit_tod[self.tod]['num_of_hours']
     my_expression = str(total_hours) + ' * vauteq * (60/hdw)'
     self.transit_segment_calculator(result = "@trnv3", expression = my_expression, aggregation = "+")

                                            
def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
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


