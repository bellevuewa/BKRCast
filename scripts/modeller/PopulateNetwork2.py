import sys
import inro.modeller as _modeller
import inro.emme.desktop.app as _app
import inro.emme.core.exception as _exception
import itertools as _itertools
import datetime
import os
from shutil import copyfile
import pandas as pd

class BKRCastExportNetwork(_modeller.Tool()):
    '''
    this tool is to populate AM, MD and PM peak hour network and their associated network
    input files in EMME punch file format.
    Files will be produced:
      base network file, link shape file, turn file, and transit lines for AM, MD, PM and NI.
    1.1.0: populate vdf functions for four TOD.
    1.1.1: populate sc_headway.csv
    1.1.2: remove future bike links with modes == "wk" and @biketype == 0
    1.2:   create network for a horizon year directly from the master network and punch out all network inputs files.
    1.2.1  remove links with vdf24. otherwise ped/bike would use these facilities.
    1.2.2  add scenario selection and overwrite feature.
    1.2.3  remove links modes including w and vdf=24. Otherwise transit only links would be removed. This is still a temporary fix. Eventually we need to add 
            @exist_modes and @imp_modes 
    1.3.0 upgrade to python 3.7, compatible with EMME4.5.1
    1.3.1 add existing and improved turn penalty, turn lane, and turn adjustment factor. @exist_tpf, @imp_tpf, @exist_turn_lane, @imp_turn_lane, @exist_turn_factor, @imp_turn_factor
    1.3.2 export bus stop file.
    1.3.3 export vehicle file. 
    1.3.4 export zone partition
    '''
    version = "1.3.4" # this is the version
    default_path = ""
    tool_run_message = ""
    outputFolder = _modeller.Attribute(object)
    horizon_year = _modeller.Attribute(int)
    new_scen_id = _modeller.Attribute(int)
    new_scen_title = _modeller.Attribute(str)
    current_scen = _modeller.Attribute(object)
    overwrite_scen = _modeller.Attribute(bool)

    def __init__(self):
        '''
        Constructor
        '''
        self.overwrite_scen = False

    def page(self):
        pb = _modeller.ToolPageBuilder(self, title="BKRCast Network Interface",
                     description="Populate networks from master network",
                     branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")
        pb.add_select_file("outputFolder", "directory", "", self.default_path, title = "Select the directory for output files")
        if not self.current_scen:
            self.current_scen = self.current_scenario
        pb.add_select_scenario("current_scen", title="Scenario:")
        pb.add_text_box("new_scen_id", 5, title = "Enter the new scenario ID", note = "Number between 1 and 99999.")
        pb.add_checkbox('overwrite_scen', title = 'Overwrite existing scenario?')
        pb.add_text_box("new_scen_title", 60, title = 'New scenario title', note = 'Maximum 60 characters.')
        pb.add_text_box("horizon_year", 4, title = "Enter the horizon year", note = "4-digit integer only")
        self.horizon_year = ''
        self.new_scen_title = str(self.horizon_year) + ' network built from scen ' + self.current_scen.id
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
            run_message = "Network exported"
            self.tool_run_message += _modeller.PageBuilder.format_info(run_message)
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)

    @_modeller.logbook_trace(name="BKRCast Export Network", save_arguments=True)
    def __call__(self):

        ## total number of scenarios allowed
        tot_scn_spaces = self.current_emmebank.dimensions['scenarios']
        scens = self.current_emmebank.scenarios()
        _modeller.logbook_write("Version", self.version)
        self.new_scen_title = str(self.horizon_year) + ' network built from scen ' + self.current_scen.id

        num_scns = 0;
        for scen in scens:
           num_scns = num_scns + 1
        print("Total allowed scenarios " + str(tot_scn_spaces))
        print("Total scenarios " + str(num_scns))

        if tot_scn_spaces < num_scns + 5:
            self.tool_run_message += _modeller.PageBuilder.format_info("Does not have enough space for scenarios. Please increase dimension to accommodate at least three more scenarios")
            exit(1)

        notes = 'Create network for horizon year ' + str(self.horizon_year)
        print(notes)
        with _modeller.logbook_trace(name = notes, value = ""):
            # copy master scenario to horizon year and set the new network as primary
            horizon_scen = self.copyScenario(self.current_scen, self.new_scen_id, self.new_scen_title, True, True, self.overwrite_scen, True)

            # set network to existing condition
            self.copyAttribute('@exist_lanes', 'lanes', horizon_scen)
            self.copyAttribute('@exist_lanecap', 'ul1', horizon_scen)
            self.copyAttribute('@exist_vdf', 'vdf', horizon_scen)
            self.copyAttribute('@exist_speed', 'ul2', horizon_scen)
            self.copyAttribute('@exist_hot', '@tolllane', horizon_scen)
            self.copyAttribute('@exist_biketype', '@biketype', horizon_scen)
            self.copyAttribute('@exist_tpf', 'tpf', horizon_scen)
            self.copyAttribute('@exist_turn_lanes', 'up1', horizon_scen)
            self.copyAttribute('@exist_turn_factor', 'up2', horizon_scen)

            # copy improved networks for active projects
            selection = {}
            selection['link'] = '@project_year=0,' + str(self.horizon_year)
            self.copyAttribute('@imp_lanes', 'lanes', horizon_scen, selection)
            self.copyAttribute('@imp_lanecap', 'ul1', horizon_scen, selection)
            self.copyAttribute('@imp_vdf', 'vdf', horizon_scen, selection)
            self.copyAttribute('@imp_speed', 'ul2', horizon_scen, selection)
            selection['link'] = '@project_year=2000,' + str(self.horizon_year)
            self.copyAttribute('@imp_hot', '@tolllane', horizon_scen, selection)
            selection['link'] = '@bike_year = 0,' + str(self.horizon_year)
            self.copyAttribute('@imp_biketype', '@biketype', horizon_scen, selection)

            expression = '(@turn_project_year > 2000 && @turn_project_year <= ' + str(self.horizon_year)+ ') * @imp_tpf + (@turn_project_year > ' + str(self.horizon_year)+ ') * @exist_tpf + (@turn_project_year < 2000) * @exist_tpf' 
            self.turnNetCalculator('tpf', expression) 
            expression = '(@turn_project_year > 2000 && @turn_project_year <= ' + str(self.horizon_year)+ ') * @imp_turn_lanes + (@turn_project_year > ' + str(self.horizon_year)+ ') * @exist_turn_lanes + (@turn_project_year < 2000) * @exist_turn_lanes' 
            self.turnNetCalculator('up1', expression) 
            expression = '(@turn_project_year > 2000 && @turn_project_year <= ' + str(self.horizon_year)+ ') * @imp_turn_factor + (@turn_project_year > ' + str(self.horizon_year)+ ') * @exist_turn_factor + (@turn_project_year < 2000) * @exist_turn_factor' 
            self.turnNetCalculator('up2', expression) 

            # set link modes for HOV if @tolllane==5 HOT 2 Plus if @tolllane=6, HOT 3 Plus if @tolllane=1..4
            NAMESPACE = "inro.emme.data.network.base.change_link_modes"
            change_link_mode = _modeller.Modeller().tool(NAMESPACE)
            test = self.linkNetCalculator(None, '1', '@tolllane=5')
            if test['num_evaluations'] > 0:
                change_link_mode(modes = 'ahdimjgbp', action = 'SET', selection = '@tolllane=5')
            test = self.linkNetCalculator(None, '1', '@tolllane=6')
            if test['num_evaluations'] > 0:
                change_link_mode(modes = 'asehdimjgvbp', action = 'SET', selection = '@tolllane=6')
            test = self.linkNetCalculator(None, '1', '@tolllane=1,4')
            if test['num_evaluations'] > 0:
                change_link_mode(modes = 'asehdimjgvbp', action = 'SET', selection = '@tolllane=1,4')

            # backup active transit lines
            self.tLineNetCalculator('@tactive', '0', "*")
            selection = '@tstart=0,' + str(self.horizon_year) + ' and @tend = ' + str(self.horizon_year + 1) + ', 9999'
            self.tLineNetCalculator('@tactive', '1', selection)
            temptransitname = 'TRANactive_' + str(self.horizon_year) + '.dat'
            temptransitname = os.path.join(self.outputFolder, temptransitname)
            self.exportTransit(temptransitname, horizon_scen, "@tactive=1")
            NAMESPACE = "inro.emme.data.extra_attribute.export_extra_attributes"
            export_attribute = _modeller.Modeller().tool(NAMESPACE)
            export_attribute(extra_attributes = '@nihdwy', export_path = self.outputFolder, scenario=horizon_scen)

            # import active transit lines
            self.deleteTransitLines(horizon_scen, "all")
            self.loadTransitLines(horizon_scen, temptransitname, True)
            NAMESPACE = "inro.emme.data.extra_attribute.import_extra_attributes"
            import_attribute = _modeller.Modeller().tool(NAMESPACE)
            tempname = 'extra_transit_lines_' + str(self.new_scen_id) + '.txt'
            tempname = os.path.join(self.outputFolder, tempname)
            import_attribute(file_path = tempname, scenario = horizon_scen, revert_on_error = False)

        with _modeller.logbook_trace(name = 'Remove future non-motorized-only links', value = ""):
            self.removeExtraBikeLinks(horizon_scen)

        # need to remove links with vdf24, otherwise ped/bike would use them.
        with _modeller.logbook_trace(name = 'Remove future motorized links', value = ""):
            NAMESPACE = "inro.emme.data.network.base.delete_links"
            delete_links = _modeller.Modeller().tool(NAMESPACE)
            delete_links(scenario = horizon_scen, selection = 'modes=w and vdf=24', condition = 'cascade')    

        am_net_name = os.path.join(self.outputFolder, "am_roadway.in")
        md_net_name = os.path.join(self.outputFolder, "md_roadway.in")
        pm_net_name = os.path.join(self.outputFolder, "pm_roadway.in")
        ni_net_name = os.path.join(self.outputFolder, "ni_roadway.in")
        am_shape = os.path.join(self.outputFolder, "am_linkshapes.in")
        md_shape = os.path.join(self.outputFolder, "md_linkshapes.in")
        pm_shape = os.path.join(self.outputFolder, "pm_linkshapes.in")
        ni_shape = os.path.join(self.outputFolder, "ni_linkshapes.in")
        am_turn_name = os.path.join(self.outputFolder, "am_turns.in")
        md_turn_name = os.path.join(self.outputFolder, "md_turns.in")
        pm_turn_name = os.path.join(self.outputFolder, "pm_turns.in")
        ni_turn_name = os.path.join(self.outputFolder, "ni_turns.in")
        am_transit_name = os.path.join(self.outputFolder, "am_transit.in")
        md_transit_name = os.path.join(self.outputFolder, "md_transit.in")
        pm_transit_name = os.path.join(self.outputFolder, "pm_transit.in")
        ni_transit_name = os.path.join(self.outputFolder, "ni_transit.in")
        am_vdf_name = os.path.join(self.outputFolder, "vdfs6to9.txt")
        md_vdf_name = os.path.join(self.outputFolder, "vdfs9to1530.txt")
        pm_vdf_name = os.path.join(self.outputFolder, "vdfs1530to1830.txt")
        ni_vdf_name = os.path.join(self.outputFolder, "vdfs1830to6.txt")
        headway_name = os.path.join(self.outputFolder, 'sc_headways.csv')
        
        with _modeller.logbook_trace(name = "Export headway file", value = ""):
            self.exportTransitLineHeadway(horizon_scen, headway_name)

        with _modeller.logbook_trace(name = "Export temporary transit network", value = ""):
            self.tLineNetCalculator("hdw", "ut1", 'all')
            self.exportTransit(am_transit_name, horizon_scen, "not hdw = 999")
            self.tLineNetCalculator("hdw", "ut2", 'all')
            self.exportTransit(md_transit_name, horizon_scen, "not hdw = 999")
            self.tLineNetCalculator("hdw", "ut3", 'all')
            self.exportTransit(pm_transit_name, horizon_scen, "not hdw = 999")
            self.tLineNetCalculator("hdw", "@nihdwy", 'all')
            self.exportTransit(ni_transit_name, horizon_scen, "not hdw = 999")


        with _modeller.logbook_trace(name = "Create scenario for time periods", value = ""):
            today = datetime.date.today().strftime("%m%d%Y")
            amScen = self.copyScenario(horizon_scen, 224, "AMPK BKRCast " + today, True, True, True, False)
            mdScen = self.copyScenario(horizon_scen, 225, "MDPK BKRCast " + today, True, True, True, False)
            pmScen = self.copyScenario(horizon_scen, 226, "PMPK BKRCast " + today, True, True, True, False)
            niScen = self.copyScenario(horizon_scen, 227, "NIPK BKRCast " + today, True, True, True, False)

            _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(amScen)
            self.linkNetCalculator("ul1", "@revlane_cap", "@revlane = 1,4")
            self.linkNetCalculator("ul2", "0.01", "@revlane = 1,4")
            self.linkNetCalculator("ul2", "60", "@revlane = 2 or @revlane = 4 and vdf = 1")
            self.linkNetCalculator("ul2", "35", "@revlane = 2 or @revlane = 4 and vdf = 3")

            _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(mdScen)
            self.linkNetCalculator("ul1", "@revlane_cap * 0.5", "@revlane = 1,4")
            self.linkNetCalculator("ul2", "60", "@revlane = 1,4 and vdf = 1")
            self.linkNetCalculator("ul2", "35", "@revlane = 1,4 and vdf = 3")
        
            _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(pmScen)
            self.linkNetCalculator("ul1", "@revlane_cap", "@revlane = 1,4")
            self.linkNetCalculator("ul2", "0.01", "@revlane = 1,4")
            self.linkNetCalculator("ul2", "60", "@revlane = 1 or @revlane = 3 and vdf = 1")
            self.linkNetCalculator("ul2", "35", "@revlane = 1 or @revlane = 3 and vdf = 3")

            _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(niScen)
            self.linkNetCalculator("ul1", "@revlane_cap", "@revlane = 1,4")
            self.linkNetCalculator("ul2", "0.01", "@revlane = 1,4")
            self.linkNetCalculator("ul2", "60", "@revlane = 1 or @revlane = 3 and vdf = 1")
            self.linkNetCalculator("ul2", "35", "@revlane = 1 or @revlane = 3 and vdf = 3")

            _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(horizon_scen)
        
            # create transit lines for AM, MD and PM. headways are saved in ut1 ~ ut3

            self.deleteTransitLines(amScen, "all")
            self.loadTransitLines(amScen, am_transit_name, True)
            self.deleteTransitLines(mdScen, "all")
            self.loadTransitLines(mdScen, md_transit_name, True)
            self.deleteTransitLines(pmScen, "all")
            self.loadTransitLines(pmScen, pm_transit_name, True)
            self.deleteTransitLines(niScen, "all")
            self.loadTransitLines(niScen, ni_transit_name, True)

        #export base network
        with _modeller.logbook_trace(name = "Export base network", value = ""):
            self.exportBaseNetwork(amScen, "all", "all", am_net_name, False, " ", "PROMPT_DATA_FORMAT")
            self.exportBaseNetwork(mdScen, "all", "all", md_net_name, False, " ", "PROMPT_DATA_FORMAT")
            self.exportBaseNetwork(pmScen, "all", "all", pm_net_name, False, " ", "PROMPT_DATA_FORMAT")
            self.exportBaseNetwork(niScen, "all", "all", ni_net_name, False, " ", "PROMPT_DATA_FORMAT")
    
        # export link shapes
        with _modeller.logbook_trace(name = "Export link shapes", value = ""):
            self.exportLinkShapes(amScen, "all", am_shape, " ", False)
            self.exportLinkShapes(mdScen, "all", md_shape, " ", False)
            self.exportLinkShapes(pmScen, "all", pm_shape, " ", False)
            self.exportLinkShapes(niScen, "all", ni_shape, " ", False)

        # exoirt turns
        with _modeller.logbook_trace(name = "Export turns", value = ""):
            self.exportTurns(amScen, "all", am_turn_name, " ", False, "PROMPT_DATA_FORMAT")
            self.exportTurns(mdScen, "all", md_turn_name, " ", False, "PROMPT_DATA_FORMAT")
            self.exportTurns(pmScen, "all", pm_turn_name, " ", False, "PROMPT_DATA_FORMAT")
            self.exportTurns(niScen, "all", ni_turn_name, " ", False, "PROMPT_DATA_FORMAT")
        
        #export transit lines
        with _modeller.logbook_trace(name = "Export transit network", value = ""):
            self.exportTransit(am_transit_name, amScen, "not hdw = 999")
            self.exportTransit(md_transit_name, mdScen, "not hdw = 999")
            self.exportTransit(pm_transit_name, pmScen, "not hdw = 999")
            self.exportTransit(ni_transit_name, niScen, "not hdw = 999")

        #export vdf functions (all functions, overwrite if file exists)
        with _modeller.logbook_trace(name = "Export vdfs", value = ""):
            self.exportVDF(am_vdf_name)
            self.exportVDF(md_vdf_name)
            self.exportVDF(pm_vdf_name)
            self.exportVDF(ni_vdf_name)    

        # export a list of bus stop with transit submodes and coordinates.
        with _modeller.logbook_trace(name = "Export bus stops", value = ""):
            busstop_name = os.path.join(self.outputFolder, 'transit_stops' + '.csv')
            self.exportBusStop(busstop_name, horizon_scen)

        with _modeller.logbook_trace(name = "Export vehicles", value = ""):
            NAMESPACE = 'inro.emme.data.network.transit.export_vehicles'
            export_vehicle = _modeller.Modeller().tool(NAMESPACE)
            path = os.path.join(self.outputFolder, 'vehicles.txt')
            export_vehicle(scenario = horizon_scen, export_file = path, field_separator = ' ') 

        # export all zone partitions
        with _modeller.logbook_trace(name = "Export zone partitions", value = ""):
            NAMESPACE = 'inro.emme.data.zone_partition.export_partitions'
            export_partitions = _modeller.Modeller().tool(NAMESPACE)
            path = os.path.join(self.outputFolder, 'zone_partitions.txt')
            emmebank = _modeller.Modeller().emmebank
            partitions = emmebank.partitions()
            p_list = []
            for p in partitions:
                p_id = p.id
                partition = emmebank.partition(p_id)
                if partition != None:
                    print(f'partition {p_id}') 
                    p_list.append(p)
            
            export_partitions(partitions = p_list, partition_output_type="ZONES_BY_GROUP", export_file = path, append_to_file = False, field_separator = ' ', line_format = 'ONE_LINE_PER_CATEGORY', export_default_group = False)
               


    def exportTransit(self, tempFileName, scen, selection):
        NAMESPACE = "inro.emme.data.network.transit.export_transit_lines"
        export_transitlines = _modeller.Modeller().tool(NAMESPACE)
        emmebank_dir = os.path.dirname(_modeller.Modeller().emmebank.path)
        line_file = os.path.join(emmebank_dir, tempFileName)
        export_transitlines(export_file = line_file, selection = selection, scenario = scen)
    
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
        for col in busstops_df.columns.values.tolist():
            busstops_df[col] = busstops_df[col].astype(int)
            busstops_df.loc[busstops_df[col] > 1, col] = 1
        
        nodes = network.nodes
        nodes_list = []
        for node in nodes():
            dict = {'node': node.id, 'x': node.x, 'y': node.y}
            nodes_list.append(dict)
        nodes_df = pd.DataFrame(nodes_list)
        busstops_df = pd.merge(busstops_df, nodes_df, left_on = 'stop', right_on = 'node', how = 'left')
        # if express is not in the transit df, add this column with all zeros.
        if 'express' not in busstops_df.columns:
            busstops_df['express'] = 0
        busstops_df.to_csv(bus_file_name, index = False)
        busstops_err_df = pd.DataFrame(busstops_err)
        busstops_err_df.to_csv('error.txt')

    def tLineNetCalculator(self, result, expression, sel):
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        specs = {
            "type": "NETWORK_CALCULATION",
            "result": result,
            "expression": expression,
            "selections": {
                "transit_line": sel }
            }
        netcalc = _modeller.Modeller().tool(NAMESPACE)
        report = netcalc(specs)

    def copyScenario(self, fromScen, toScenID, title, copyStrategy, copyShape, overwrite, set_primary):
        NAMESPACE = "inro.emme.data.scenario.copy_scenario"
        copy_scenario = _modeller.Modeller().tool(NAMESPACE)
        toScen = copy_scenario(from_scenario = fromScen, scenario_id = toScenID, scenario_title = title, copy_strategies = copyStrategy,
                               copy_linkshapes = copyShape, overwrite = overwrite, set_as_primary = set_primary)
        return toScen

    def linkNetCalculator(self, result, expression, selectors):
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        if result is None:
            specs = {
                "type": "NETWORK_CALCULATION",
                "result": None,
                "expression": expression,
                "selections": {
                    "link": selectors }
                }
        else:
            specs = {
                "type": "NETWORK_CALCULATION",
                "result": result,
                "expression": expression,
                "selections": {
                    "link": selectors }
                }

        netCalc = _modeller.Modeller().tool(NAMESPACE)
        report = netCalc(specs)
        return report

    def turnNetCalculator(self, result, expression):
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        if result is None:
            specs = {
                "type": "NETWORK_CALCULATION",
                "result": None,
                "expression": expression,
                "selections": {
                    "incoming_link": "all",
                    "outgoing_link": "all"
                    },
                }
        else:
            specs = {
                "type": "NETWORK_CALCULATION",
                "result": result,
                "expression": expression,
                "selections": {
                    "incoming_link": "all",
                    "outgoing_link": "all"
                    },
                }

        netCalc = _modeller.Modeller().tool(NAMESPACE)
        report = netCalc(specs)
        return report

    def loadTransitLines(self, scen, transitFile, revertOnError):
        NAMESPACE = "inro.emme.data.network.transit.transit_line_transaction"
        load_transit = _modeller.Modeller().tool(NAMESPACE)
        load_transit(scenario = scen, transaction_file = transitFile, revert_on_error = revertOnError)

    def exportBaseNetwork(self, scen, node_selector, link_selector, exportname, append, seperator, exportformat):
        NAMESPACE = "inro.emme.data.network.base.export_base_network"
        export_base = _modeller.Modeller().tool(NAMESPACE)
        export_base(scenario = scen, selection = {"link": link_selector,
                                       "node": node_selector}, export_file = exportname, append_to_file = append,
                    field_separator = seperator, export_format = exportformat)

    def exportLinkShapes(self, scen, selector, exportfile, seperator, append):
        NAMESPACE = "inro.emme.data.network.base.export_link_shape"
        export_shape = _modeller.Modeller().tool(NAMESPACE)
        export_shape(scenario = scen, export_file = exportfile, selection = selector, 
                     field_separator = seperator, append_to_file = append)

    def exportTurns(self, scen, selector, exportfile, seperator, append, exportformat):
        NAMESPACE = "inro.emme.data.network.turn.export_turns"
        export_turns = _modeller.Modeller().tool(NAMESPACE)
        export_turns(scenario = scen, selection = selector, export_file = exportfile, field_separator = seperator,
                     append_to_file = append, export_format = exportformat)

    def deleteTransitLines(self, scen, selector):
        NAMESPACE = "inro.emme.data.network.transit.delete_transit_lines"
        delete_tline = _modeller.Modeller().tool(NAMESPACE)
        tot = delete_tline(scenario = scen, selection = selector)
        return tot

    def exportVDF(self, exportfile):
        NAMESPACE = "inro.emme.data.function.export_functions"
        export_function = _modeller.Modeller().tool(NAMESPACE)
        export_function(export_file = exportfile, append_to_file = False)

    def exportTransitLineHeadway(self, curScen, exportfile):
        network = curScen.get_network()
        tlines = network.transit_lines()

        with open(exportfile, mode = 'w') as f:
            f.write('LineID,hdw_6to9,hdw_9to1530,hdw_1530to1830,hdw_1830to6,id\n')
            for tline in tlines:
                f.write('{0:d}, {1:.0f}, {2:.0f}, {3:.0f}, {4:.0f}, {5:d}\n'.format(int(tline.id), tline.data1, tline.data2, tline.data3, tline['@nihdwy'], int(tline.id)))

    # remove future non-motorized links with condition modes = "wk" and @biketype == 0. (if non-motorized only, @biketype has to be 1.
    def removeExtraBikeLinks(self, curScen):
        network = curScen.get_network()
        links = network.links()
        bikemodeset = set([network.mode('w'), network.mode('k')])

        emmebank_dir = os.path.dirname(_modeller.Modeller().emmebank.path)
        extraBikeLinks = os.path.join(emmebank_dir, 'removed_bike_links.dat')
        with open(extraBikeLinks, mode = 'w') as f:
            for link in links: 
                if (link.modes == bikemodeset) and (link['@biketype'] == 0):
                    print('link ', link.id, ' is removed from network')
                    f.write('link {0} is removed from network\n'.format(link.id))
                    network.delete_link(link.i_node, link.j_node)

        curScen.publish_network(network)

    def copyAttribute(self, source, target, scen, sel=''):
        NAMESPACE = "inro.emme.data.network.copy_attribute"
        copy_attribute = _modeller.Modeller().tool(NAMESPACE)
        copy_attribute(from_attribute_name = source, to_attribute_name = target, from_scenario = scen, selection = sel)
