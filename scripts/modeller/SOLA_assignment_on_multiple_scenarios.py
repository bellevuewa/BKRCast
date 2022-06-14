import sys
import inro.modeller as _modeller
import inro.emme.desktop.app as _app
import inro.emme.core.exception as _exception
import itertools as _itertools
import datetime
import os
import json as _json

class BKRCastExportAllAttributes(_modeller.Tool()):
    '''
    1.1: upgrade to python 3.7, compatible with EMME 4.5.1
    '''
    version = "1.1" # this is the version
    default_path = ""
    tool_run_message = ""
    scenarios_list = _modeller.Attribute(list)
    sola_specs_box = _modeller.Attribute(str)

    def page(self):
        pb = _modeller.ToolPageBuilder(self, title="BKRCast Network Interface",
                     description="SOLA Assignment on Multiple Scenarios",
                     branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")
        pb.add_select_scenario("scenarios_list", title = "Select scenarios")
        pb.add_sola_traffic_assignment_spec("sola_specs_box", title = "Select specs")

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
            self.__call__()
            run_message = "All attributes exported"
            self.tool_run_message += _modeller.PageBuilder.format_info(run_message)
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)

    @_modeller.logbook_trace(name="BKRCast Export All Attributes", save_arguments=True)
    def __call__(self):

        current_scen = self.current_scenario
        specs = _json.loads(self.sola_specs_box)
        with _modeller.logbook_trace(name = "SOLA Assignment on Multiple Scenarios", value = ""):
            NAMESPACE = 'inro.emme.traffic_assignment.sola_traffic_assignment'
            sola_assign = _modeller.Modeller().tool(NAMESPACE)
            for scen in self.scenarios_list:
                _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(scen)
                sola_assign(specs)
 