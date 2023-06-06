import sys
import inro.modeller as _modeller
import inro.emme.desktop.app as _app
import os
import json
sys.path.append(os.path.normpath(os.path.join(_modeller.Modeller().emmebank.path, '..\\..\\..\\')))
sys.path.append(os.path.normpath(os.path.join(_modeller.Modeller().emmebank.path, '..\\..\\..\\scripts')))
import emme_configuration as emme_config
from data_wrangling import *

'''
   06/01/2023
    Duplicate run_transit() in skimsandpaths.py in emme modeller. Only run the transit assignment and skims on one databank through
    Modeller tool. We can use this tool to fine tune transit line settings.

'''
class BKRCastRunTransitAssignment(_modeller.Tool()):
    version = "1.0" # this is the version
    default_path = ""
    tool_run_message = ""
    scenarios_list = _modeller.Attribute(list)

    def __init__(self):
        return

    def page(self):
        pb = _modeller.ToolPageBuilder(self, title="BKRCast Transit Assignment and Skimming",
                     description="Extended Transit Assignment and Skimming",
                     branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")
        pb.add_select_scenario("scenarios_list", title = "Select scenarios")

        if self.tool_run_message != "":
            pb.tool_run_status(self.tool_run_msg_status)

        return pb.render()

    @_modeller.method(return_type=str)
    def tool_run_msg_status(self):
        return self.tool_run_message        

    def run(self):
        self.tool_run_message = ""
        try:
            self.__call__()
            run_message = "Transit assignment and skimming completed."
            self.tool_run_message += _modeller.PageBuilder.format_info(run_message)
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)

    @_modeller.logbook_trace(name="Create and update transit node attributes", save_arguments=True)
    def create_node_attribute(self, current_scenario):
        my_bank = current_scenario.emmebank
        tod = my_bank.title
        NAMESPACE = "inro.emme.data.extra_attribute.create_extra_attribute"
        create_extra = _modeller.Modeller().tool(NAMESPACE)
        print(tod)
        for key, value in emme_config.transit_node_attributes.items():
            print(key, value)
            if current_scenario.extra_attribute(value['name']) == None:
                new_att = create_extra(extra_attribute_type="NODE",
                           extra_attribute_name=value['name'],
                           extra_attribute_description=key,
                           extra_attribute_default_value = value['init_value'],
                           overwrite=True)

        network_calc = _modeller.Modeller().tool("inro.emme.network_calculation.network_calculator")  
        node_calculator_spec = self.json_to_dictionary("node_calculation")
        transit_tod = emme_config.transit_network_tod_dict[tod]
        
        if transit_tod in emme_config.transit_node_constants.keys():
            for line_id, attribute_dict in emme_config.transit_node_constants[transit_tod].items():
                for attribute_name, value in attribute_dict.items():
                    print(line_id, attribute_name, value)
                    #Load in the necessary Dictionarie
                    mod_calc = node_calculator_spec
                    mod_calc["result"] = attribute_name
                    mod_calc["expression"] = value
                    mod_calc["selections"]["node"] = "Line = " + line_id
                    network_calc(mod_calc)
        print('finished create node attributes for ' + tod)

    def json_to_dictionary(self, name):
        proj_path = os.path.normpath(os.path.join(_modeller.Modeller().emmebank.path, '..\\..\\..\\'))
        input_filename = os.path.join(proj_path, 'inputs/skim_params/', name+'.json').replace("\\","/")
        my_dictionary = json.load(open(input_filename))
        return my_dictionary

    @_modeller.logbook_trace(name="Run transit assignment", save_arguments=True)
    def transit_assignment(self, spec, keep_exisiting_volumes, class_name=None):
        print('starting transtit assignment')
   
        #Define the Emme Tools used in this function
        assign_transit = _modeller.Modeller().tool("inro.emme.transit_assignment.extended_transit_assignment")

        #Load in the necessary Dictionaries
        assignment_specification = self.json_to_dictionary(spec)
        print("modify constant for certain nodes")
    
        #modify constants for certain nodes:
        assignment_specification["waiting_time"]["headway_fraction"] = emme_config.transit_node_attributes['headway_fraction']['name'] 
        assignment_specification["waiting_time"]["perception_factor"] = emme_config.transit_node_attributes['wait_time_perception']['name'] 
        assignment_specification["in_vehicle_time"]["perception_factor"] = emme_config.transit_node_attributes['in_vehicle_time']['name']
        assign_transit(assignment_specification,  add_volumes=keep_exisiting_volumes, class_name=class_name)

        print('Transit assignment is done.')

    @_modeller.logbook_trace(name="Run transit skims", save_arguments=True)
    def transit_skims(self, spec, class_name=None):

        skim_transit = _modeller.Modeller().tool("inro.emme.transit_assignment.extended.matrix_results")
        #specs are stored in a dictionary where "spec1" is the key and a list of specs for each skim is the value
        skim_specs = self.json_to_dictionary(spec)
        my_spec_list = skim_specs["spec1"]
        for item in my_spec_list:
            skim_transit(item, class_name=class_name)

    @_modeller.logbook_trace(name="BKRCast Transit Assignment and Skimming", save_arguments=True)
    def __call__(self):

        #export extra attributes
        with _modeller.logbook_trace(name = "Extended Transit Assignment and Skimming on Multiple Scenarios", value = ""):
            for scen in self.scenarios_list:
                _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(scen)
                current_scen = _modeller.Modeller().scenario
                _modeller.logbook_write(name = 'on scenario ' + current_scen.id + ' ' + current_scen.title)
                # create transit node attributes if they do not exist
                self.create_node_attribute(current_scen)

                print("starting transit assignment and skimming...")

                count = 0
                for submode, class_name in {'bus': 'trnst', 'light_rail':'litrat','ferry':'ferry',
                        'passenger_ferry':'passenger_ferry','commuter_rail':'commuter_rail'}.items():
                    if count > 0:
                        add_volume = True
                    else:
                        add_volume = False

                    print('    for submode: ' + submode)
                    _modeller.logbook_write(name = '  for submode: ' + submode)
                    self.transit_assignment("extended_transit_assignment_" + submode, keep_exisiting_volumes = add_volume, class_name = class_name)
                    self.transit_skims("transit_skim_setup_" + submode, class_name)
                    count += 1
    
                print("finished transit assignment and skimming")
                
                #Calc Wait Times
                _app.App.refresh_data
                matrix_calculator = self.json_to_dictionary("matrix_calculation")
                matrix_calc = _modeller.Modeller().tool("inro.emme.matrix_calculation.matrix_calculator")

                #Wait time for general transit 
                with _modeller.logbook_trace(name = 'calculate wait time for general transit'):
                    bank = _modeller.Modeller().emmebank
                    total_wait_matrix = bank.matrix('twtwa').id
                    initial_wait_matrix = bank.matrix('iwtwa').id
                    transfer_wait_matrix = bank.matrix('xfrwa').id
                    mod_calc = matrix_calculator
                    mod_calc["result"] = transfer_wait_matrix
                    mod_calc["expression"] = total_wait_matrix + "-" + initial_wait_matrix
                    matrix_calc(mod_calc)

                #wait time for transit submodes
                with _modeller.logbook_trace(name = 'calculate wait time for transit submode'):
                    for submode in ['r','f','p','c']:
                        total_wait_matrix = bank.matrix('twtw' + submode).id
                        initial_wait_matrix = bank.matrix('iwtw' + submode).id
                        transfer_wait_matrix = bank.matrix('xfrw' + submode).id

                        mod_calc = matrix_calculator
                        mod_calc['result'] = transfer_wait_matrix
                        mod_calc['expression'] = total_wait_matrix + '-' + initial_wait_matrix
                        matrix_calc(mod_calc)

                print("finished run_transit")