import inro.modeller as _modeller
import datetime
import os

class BKRCastExportNetwork(_modeller.Tool()):
    '''
    this tool is to populate AM, MD and PM peak hour network and their associated network
    input files in EMME punch file format.
    Files will be produced:
      base network file, link shape file, turn file, and transit lines for AM, MD, PM and NI.
    1.1.0: populate vdf functions for four TOD.
    1.1.1: populate sc_headway.csv
    1.1.2: remove future bike links with modes == "wk" and @biketype == 0
    1.3.0: upgrade to python 3.7, compatible with EMME 4.5.1
    '''
    version = "1.3.0" # this is the version
    default_path = ""
    tool_run_message = ""
    outputFolder = _modeller.Attribute(object)

    def page(self):
        pb = _modeller.ToolPageBuilder(self, title="BKRCast Network Interface",
                     description="Populate networks from master network",
                     branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")
        pb.add_select_file("outputFolder", "directory", "", self.default_path, title = "Select the directory for output files")

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
        current_scen = self.current_scenario
        _modeller.logbook_write("Version", self.version)

        with _modeller.logbook_trace(name = 'Remove future non-motorized-only links', value = ""):
            self.removeExtraBikeLinks(current_scen)

        num_scns = 0;
        for scen in scens:
           num_scns = num_scns + 1
        print("Total allowed scenarios " + str(tot_scn_spaces))
        print("Total scenarios " + str(num_scns))

        if tot_scn_spaces < num_scns + 4:
            self.tool_run_message += _modeller.PageBuilder.format_info("Does not have enough space for scenarios. Please increase dimension to accommodate at least three more scenarios")
            exit(1)

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
            self.exportTransitLineHeadway(current_scen, headway_name)

        with _modeller.logbook_trace(name = "Export temporary transit network", value = ""):
            self.tLineNetCalculator("hdw", "ut1", 'all')
            self.exportTransit(am_transit_name, current_scen, "not hdw = 999")
            self.tLineNetCalculator("hdw", "ut2", 'all')
            self.exportTransit(md_transit_name, current_scen, "not hdw = 999")
            self.tLineNetCalculator("hdw", "ut3", 'all')
            self.exportTransit(pm_transit_name, current_scen, "not hdw = 999")
            self.tLineNetCalculator("hdw", "@nihdwy", 'all')
            self.exportTransit(ni_transit_name, current_scen, "not hdw = 999")


        with _modeller.logbook_trace(name = "Create scenario for time periods", value = ""):
            today = datetime.date.today().strftime("%m%d%Y")
            amScen = self.copyScenario(current_scen, 224, "AMPK BKRCast " + today, True, True, True)
            mdScen = self.copyScenario(current_scen, 225, "MDPK BKRCast " + today, True, True, True)
            pmScen = self.copyScenario(current_scen, 226, "PMPK BKRCast " + today, True, True, True)
            niScen = self.copyScenario(current_scen, 227, "NIPK BKRCast " + today, True, True, True)

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

            _modeller.Modeller().desktop.data_explorer().replace_primary_scenario(current_scen)
        
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

    def exportTransit(self, tempFileName, scen, selection):
        NAMESPACE = "inro.emme.data.network.transit.export_transit_lines"
        export_transitlines = _modeller.Modeller().tool(NAMESPACE)
        emmebank_dir = os.path.dirname(_modeller.Modeller().emmebank.path)
        line_file = os.path.join(emmebank_dir, tempFileName)
        export_transitlines(export_file = line_file, selection = selection, scenario = scen)
            
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

    def copyScenario(self, fromScen, toScenID, title, copyStrategy, copyShape, overwrite):
        NAMESPACE = "inro.emme.data.scenario.copy_scenario"
        copy_scenario = _modeller.Modeller().tool(NAMESPACE)
        toScen = copy_scenario(from_scenario = fromScen, scenario_id = toScenID, scenario_title = title, copy_strategies = copyStrategy,
                               copy_linkshapes = copyShape, overwrite = overwrite)
        return toScen

    def linkNetCalculator(self, result, expression, selectors):
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        specs = {
            "type": "NETWORK_CALCULATION",
            "result": result,
            "expression": expression,
            "selections": {
                "link": selectors }
            }

        netCalc = _modeller.Modeller().tool(NAMESPACE)
        report = netCalc(specs)

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
