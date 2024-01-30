import sys
import inro.modeller as _modeller
import inro.emme.desktop.app as _app
import inro.emme.core.exception as _exception
import itertools as _itertools
import datetime
import os
import json as _json

class BKRCastSOLAAssignments(_modeller.Tool()):
    '''
    1.1: upgrade to python 3.7, compatible with EMME 4.5.1
    1.2  now the assignment setting is consistent with SkimsAndPaths.py.    
    '''
    version = "1.2" # this is the version
    default_path = ""
    tool_run_message = ""
    scenarios_list = _modeller.Attribute(list)
    sola_spec_file = _modeller.Attribute(str)
    user_class_file = _modeller.Attribute(str)        

    def page(self):
        pb = _modeller.ToolPageBuilder(self, title="BKRCast Network Interface",
                     description="SOLA Assignment on Multiple Scenarios",
                     branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")
        pb.add_select_scenario("scenarios_list", title = "Select scenarios")
        pb.add_select_file("sola_spec_file", 'file', title = "Select SOLA assignment specs")
        pb.add_select_file('user_class_file', 'file', title = 'Select user class file')    
        self.sola_spec_file = '../../../inputs/skim_params/SOLA_assignment.json' 
        self.user_class_file = '../../../inputs/skim_params/user_classes.json'            
        print(os.getcwd())
        if self.tool_run_message != "":
            pb.tool_run_status(self.tool_run_msg_status)

        return pb.render()

    @_modeller.method(return_type=str)
    def tool_run_msg_status(self):
        return self.tool_run_message

    @property
    def current_scenario(self):
        return _modeller.Modeller().desktop.data_explorer().primary_scenario.core_scenario

    @property
    def current_emmebank(self):
        return self.current_scenario.emmebank

    def set_primary_scenario(self, scenarioID):
        '''set the scenario identified by scenarioID to the primary scenario.
        '''
        scenario = self.current_emmebank.scenario(scenarioID)
        _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(scenario)

    def run(self):
        self.tool_run_message = ""
        try:
            self.__call__(self.scenarios_list, self.sola_spec_file, self.user_class_file)
            run_message = "All assignments are done."
            self.tool_run_message += _modeller.PageBuilder.format_info(run_message)
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)
            
    def create_spec(self, sola_spec_file, user_class_file):
        # build SOLA based assignment specs based on template, match the code in SkimsAndPaths.py   
        sola_specs = _json.load(open(sola_spec_file))
        user_class = _json.load(open(user_class_file))   

        sola_specs["stopping_criteria"]["max_iterations"]= 5
        sola_specs["stopping_criteria"]["best_relative_gap"]= 0.001 
        sola_specs["stopping_criteria"]["relative_gap"]= 0.001

        for x in range (0, len(sola_specs["classes"])):
            vot = ((1/float(user_class["Highway"][x]["Value of Time"]))*60)    # reciprocol of VOT converted to cents/minute.
            sola_specs["classes"][x]["generalized_cost"]["perception_factor"] = vot
            sola_specs["classes"][x]["generalized_cost"]["link_costs"] = user_class["Highway"][x]["Toll"]
            sola_specs["classes"][x]["demand"] = "mf"+ user_class["Highway"][x]["Name"]
            sola_specs["classes"][x]["mode"] = user_class["Highway"][x]["Mode"]

        return sola_specs
                
    @_modeller.logbook_trace(name="BKRCast SOLA Assignments", save_arguments=True)
    def __call__(self, scenarios_list, sola_spec_file, user_class_file):

        current_scen = self.current_scenario
        sola_specs = self.create_spec(sola_spec_file, user_class_file)
        with _modeller.logbook_trace(name = "SOLA Assignment on Multiple Scenarios", save_arguments = True, value = ""):
            NAMESPACE = 'inro.emme.traffic_assignment.sola_traffic_assignment'
            sola_assign = _modeller.Modeller().tool(NAMESPACE)
            assign_extras = _modeller.Modeller().tool("inro.emme.traffic_assignment.set_extra_function_parameters")
            assign_extras(el1 = "@rdly", el2 = "@trnv3")
            
            for scen in scenarios_list:
                _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(scen)
                sola_assign(sola_specs)
 