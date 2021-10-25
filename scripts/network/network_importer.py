import pandas as pd
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import os, sys
import re 
import multiprocessing as mp
import subprocess
import json
from multiprocessing import Pool, pool
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"inputs"))
from emme_configuration import *
from input_configuration import *

# 10/25/2021
# modified to be compatible with python 3

class EmmeProject:
    def __init__(self, filepath):
        self.desktop = app.start_dedicated(True, modeller_initial, filepath)
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
                
                database.open()
                print('changed')
                self.bank = self.m.emmebank
                self.tod = self.bank.title
                print(self.tod)
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
    def network_calculator(self, type, **kwargs):
        spec = json_to_dictionary(type)
        for name, value in kwargs.items():
            if name == 'selections_by_link':
                spec['selections']['link'] = value
            else:
                spec[name] = value
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.network_calc_result = network_calc(spec)

   
    def delete_links(self):
        if self.network_counts_by_element('links') > 0:
            NAMESPACE = "inro.emme.data.network.base.delete_links"
            delete_links = self.m.tool(NAMESPACE)
            #delete_links(selection="@dist=9", condition="cascade")
            delete_links(condition="cascade")

    def delete_nodes(self):
        if self.network_counts_by_element('regular_nodes') > 0:
            NAMESPACE = "inro.emme.data.network.base.delete_nodes"
            delete_nodes = self.m.tool(NAMESPACE)
            delete_nodes(condition="cascade")
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
    def change_scenario(self):

        self.current_scenario = list(self.bank.scenarios())[0]


    
def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)


          
def import_tolls(emmeProject):
    #create extra attributes:
    create_extras = emmeProject.m.tool("inro.emme.data.extra_attribute.create_extra_attribute")
    t23 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@toll1",extra_attribute_description="SOV Tolls",overwrite=True)
    t24 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@toll2",extra_attribute_description="HOV 2 Tolls",overwrite=True)
    t25 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@toll3",extra_attribute_description="HOV 3+ Tolls",overwrite=True)
    t26 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@trkc1",extra_attribute_description="Light Truck Tolls",overwrite=True)
    t27 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@trkc2",extra_attribute_description="Medium Truck Tolls",overwrite=True)
    t28 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@trkc3",extra_attribute_description="Heavy Truck Tolls",overwrite=True)
    t28 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@brfer",extra_attribute_description="Bridge & Ferrry Flag",overwrite=True)
    t28 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@rdly",extra_attribute_description="Intersection Delay",overwrite=True)
    t30 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@count",extra_attribute_description="count",overwrite=True)

    import_attributes = emmeProject.m.tool("inro.emme.data.network.import_attribute_values")

    #add general extra attributes input by user in emme_configuration.py
    load_extra_attributes(emmeProject, extra_attributes)

    tod_4k = sound_cast_net_dict[emmeProject.tod]

    attr_file= ['inputs/tolls/' + tod_4k + '_roadway_tolls.in', 'inputs/tolls/ferry_vehicle_fares.in', 'inputs/networks/rdly/' + tod_4k + '_rdly.txt']

    # set tolls
    #for file in attr_file:
    import_attributes(attr_file[0], scenario = emmeProject.current_scenario,
              column_labels={0: "inode",
                             1: "jnode",
                             2: "@toll1",
                             3: "@toll2",
                             4: "@toll3",
                             5: "@trkc1",
                             6: "@trkc2",
                             7: "@trkc3"},
              revert_on_error=False)

    import_attributes(attr_file[1], scenario = emmeProject.current_scenario,
              column_labels={0: "inode",
                             1: "jnode",
                             2: "@toll1",
                             3: "@toll2",
                             4: "@toll3",
                             5: "@trkc1",
                             6: "@trkc2",
                             7: "@trkc3"},
              revert_on_error=True)

    
    #@rdly:
    import_attributes(attr_file[2], scenario = emmeProject.current_scenario,
             revert_on_error=True)
   
    # set TOD specific extra attributes
    print("import screenline counts and local counts for period: ") + tod_4k
    if (tod_4k == 'am'):	
        load_extra_attributes(emmeProject, AM_extra_attributes)
    elif (tod_4k == 'md'):
        load_extra_attributes(emmeProject, MD_extra_attributes)
    elif (tod_4k == 'pm'):
        load_extra_attributes(emmeProject, PM_extra_attributes)
    else: # (tod_4k == "ni")
        load_extra_attributes(emmeProject, NI_extra_attributes)
    
    print('update capacity for period: ' + tod_4k) #capacities in the original network are per hour
    cap_period = str(hwy_tod[tod_4k]) + ' * ul1' 
    emmeProject.network_calculator("link_calculation", result = "ul1", expression = cap_period, selections_by_link = "all")
    

def load_extra_attributes(emmeProject, attribute_list):
    create_extras = emmeProject.m.tool("inro.emme.data.extra_attribute.create_extra_attribute")
    import_attributes = emmeProject.m.tool("inro.emme.data.network.import_attribute_values")
    #add extra attributes input by user in emme_configuration.py
    for attribute in attribute_list:
        create_extras(extra_attribute_type=attribute["type"],extra_attribute_name=attribute["name"],extra_attribute_description=attribute["description"],overwrite=attribute["overwrite"])
        if(os.path.isfile(attribute["file_name"])):
            import_attributes(attribute["file_name"], scenario = emmeProject.current_scenario)


def multiwordReplace(text, replace_dict):
    rc = re.compile(r"[A-Za-z_]\w*")
    def translate(match):
        word = match.group(0)
        return replace_dict.get(word, word)
    return rc.sub(translate, text)

def update_headways(emmeProject, headways_df):
    network = emmeProject.current_scenario.get_network()
    for transit_line in network.transit_lines():
        row = headways_df.loc[(headways_df.id == int(transit_line.id))]
        if int(row['hdw_' + emmeProject.tod]) > 0:
            transit_line.headway = int(row['hdw_' + emmeProject.tod])
        else:
            network.delete_transit_line(transit_line.id)
    emmeProject.current_scenario.publish_network(network)


def distance_pricing(distance_rate, hot_rate, emmeProject):
    toll_atts = ["@toll1", "@toll2", "@toll3", "@trkc1", "@trkc2", "@trkc3"]
    network = emmeProject.current_scenario.get_network()
    tod_4k = sound_cast_net_dict[emmeProject.tod]
    for link in network.links():
        if add_distance_pricing:
            for att in toll_atts:
                link[att] = link[att] + (link.length * distance_rate)
        if add_hot_lane_tolls:
            # is the link a managed lane: 1 for I405 HOT north part; 3 is for the south part
            if (link['@tolllane'] <= 4 and link['@tolllane'] >=1):     ## toll lane option 1 (I405): free for 3+
                # get the modes allowed
                test = [i[1].id for i in enumerate(link.modes)]
                # if sov modes are allowed, they should be tolled
                if 's' in test or 'e' in test:
                    print(hot_rate)
                    link['@toll1'] = link['@toll1'] + (link.length * hot_rate[link['@tolllane']])
                    if ((tod_4k == 'am') or (tod_4k =='pm')):
                        link['@toll2'] = link['@toll2'] + (link.length * hot_rate[link['@tolllane']])
                if 'v' in test:
                    link['@trkc1'] = link['@trkc1'] + (link.length * hot_rate[link['@tolllane']])
            elif link['@tolllane'] == 6:    ## toll lane option 6 (SR167): free for 2+
                # get the modes allowed
                test = [i[1].id for i in enumerate(link.modes)]
                # if sov modes are allowed, they should be tolled
                if 's' in test or 'e' in test:
                    print(hot_rate)
                    link['@toll1'] = link['@toll1'] + (link.length * hot_rate[link['@tolllane']])
                if 'v' in test:
                    link['@trkc1'] = link['@trkc1'] + (link.length * hot_rate[link['@tolllane']])

    emmeProject.current_scenario.publish_network(network)

def change_mode_for_no_toll_traffic(emmeProject):
    # change modes on tolled network, but exclude some bridges/ferries
    if create_no_toll_network:
        network = emmeProject.current_scenario.get_network()

        for link in network.links():
            if link['@toll1'] > 0 and link['@brfer'] == 0:
                #for i in no_toll_modes:
                link.modes -= set([network.mode('s')])
            # at md or ni period, set 
            if link['@toll2'] > 0 and link['@brfer'] == 0:
                link.modes -= set([network.mode('h')])
        emmeProject.current_scenario.publish_network(network)

def run_importer(project_name):
    my_project = EmmeProject(project_name)
    headway_df = pd.DataFrame.from_csv('inputs/networks/' + headway_file)
    for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        for scenario in list(my_project.bank.scenarios()):
            my_project.bank.delete_scenario(scenario)
        
        #create scenario
        my_project.bank.create_scenario(1002)
        my_project.change_scenario()
        
        #delete existing links and nodes
        my_project.delete_links()
        my_project.delete_nodes()
        
        #import mode file
        my_project.process_modes('inputs/networks/' + mode_file)
        
        #import base network
        my_project.process_base_network('inputs/networks/' + value + base_net_name)
        #my_project.process_base_network('inputs/networks/fixes/ferries/' + value + base_net_name)

        #import linkshapes
        my_project.process_shape('inputs/networks/' + value + shape_name)

        #import turns
        my_project.process_turn('inputs/networks/' + value + turns_name)

        #import transit networks
        if my_project.tod in load_transit_tod:
           my_project.process_vehicles('inputs/networks/' + transit_vehicle_file)
           my_project.process_transit('inputs/networks/' + value + transit_name)
           update_headways(my_project, headway_df)

        #import tolls
        import_tolls(my_project)
        #time_period_headway_df = headeway_df.loc[(headway_df['hdw_' + my_project.tod])]
        #print len(time_period_headway_df)
        if add_distance_pricing or add_hot_lane_tolls:
            distance_pricing(distance_rate_dict[value], HOT_rate_dict[value], my_project)     

        if create_no_toll_network == True:
            change_mode_for_no_toll_traffic(my_project)

def main():
    print(network_summary_project)
    run_importer(network_summary_project)
    # comment out for now - nagendra.dhakar@rsginc.com
    #returncode = subprocess.call([sys.executable,'scripts/network/daysim_zone_inputs.py'])
    returncode=0
    if returncode != 0:
        sys.exit(1)
    
    print('done')

if __name__ == "__main__":
    main()






