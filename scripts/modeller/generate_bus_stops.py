import sys
import inro.modeller as _modeller
import inro.emme.desktop.app as _app
import inro.emme.core.exception as _exception
import itertools as _itertools
import pandas as pd
import datetime
import os

# 6/15/2022
# produce a list of bus stop with transit submodes and coordinates.
# the bus stop file is an input file to BKRCast, to be used in accessibility calculation.
#

class BKRCastGenerateBusStops(_modeller.Tool()):
    version = "1.0" # this is the version
    default_path = ""
    tool_run_message = ""
    outputFilename = _modeller.Attribute(object)

    def page(self):
        pb = _modeller.ToolPageBuilder(self, title="BKRCast Network Interface",
                     description="Export bus stops",
                     branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")
        self.outputFilename = "bus_stops.txt"
        pb.add_text_box("outputFilename", 30, title = "Enter output file name")

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

    def run(self):
        self.tool_run_message = ""
        try:
            self.__call__()
            run_message = "All bus stops are exported"
            self.tool_run_message += _modeller.PageBuilder.format_info(run_message)
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)

    @_modeller.logbook_trace(name="BKRCast Export All Bus Stops", save_arguments=True)
    def __call__(self):
        current_scen = self.current_scenario
        #export extra attributes
        with _modeller.logbook_trace(name = "Export bus stops", value = ""):
            self.exportBusStop(self.outputFilename, current_scen)


    def exportBusStop(self, bus_file_name, scen):
        network = scen.get_network()
        transit_segments = network.transit_segments()
        busstops = []
        busstops_err = []
        segments  = []
        for seg in transit_segments:
            mode = seg.line.mode.id
            i_node = seg.i_node.id
            i_node_x = seg.i_node.x
            i_node_y = seg.i_node.y
            if mode == 'b':
                dict = {'bus':1, 'stop': i_node}
                busstops.append(dict)
            elif mode == 'c':
                dict = {'commuter_rail':1, 'stop': i_node}
                busstops.append(dict)
            elif mode == 'r':
                dict = {'light_rail':1, 'stop': i_node}
                busstops.append(dict)
            elif mode == 'n':
                dict = {'brt':1, 'stop': i_node}
                busstops.append(dict)
            elif mode == 'f':
                dict = {'ferry':1, 'stop': i_node}
                busstops.append(dict)
            elif mode == 'p':
                dict = {'express':1, 'stop': i_node}
                busstops.append(dict)
            else:
                dict = {mode: 1, 'stop': i_node}
                busstops_err.append(dict)
            segments.append({'i':seg.i_node, 'j':seg.j_node, 'line':seg.line.id, 'mode': seg.line.mode.id})

        busstops_df = pd.DataFrame(busstops)
        busstops_df = busstops_df.groupby('stop').sum()
        for col in ['ferry', 'light_rail', 'bus', 'express', 'commuter_rail']:
            busstops_df[col] = busstops_df[col].astype(int)
            busstops_df.loc[busstops_df[col] > 1, col] = 1
        
        nodes = network.nodes
        nodes_list = []
        for node in nodes():
            dict = {'node': node.id, 'x': node.x, 'y': node.y}
            nodes_list.append(dict)
        nodes_df = pd.DataFrame(nodes_list)
        busstops_df = pd.merge(busstops_df, nodes_df, left_on = 'stop', right_on = 'node', how = 'left')
        busstops_df.to_csv(bus_file_name, index = False)
        busstops_err_df = pd.DataFrame(busstops_err)
        busstops_err_df.to_csv('error.txt')





