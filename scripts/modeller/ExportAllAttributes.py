import sys
import inro.modeller as _modeller
import inro.emme.desktop.app as _app
import inro.emme.core.exception as _exception
import itertools as _itertools
import datetime
import os
from shutil import copyfile

class BKRCastExportAllAttributes(_modeller.Tool()):
    '''
    this tool is to export all extra attributes from current scenario.
    1.0.1: export all extra attributes
    1.0.2: 
        export @nihdwy for all @nihdwy < 999. It can be directly loaded into the model.
        export @rdly to four time periods. No need to mannually copy and rename to different time periods.
    1.03:
        export @biketype and @slope to emme_attr.in
    1.1.0: upgrade to python 3.7, compatible with EMME 4.5.1
    '''
    version = "1.0.3" # this is the version
    default_path = ""
    tool_run_message = ""
    outputFolder = _modeller.Attribute(object)

    def page(self):
        pb = _modeller.ToolPageBuilder(self, title="BKRCast Network Interface",
                     description="Export all extra attributes from current scenario",
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
            run_message = "All attributes exported"
            self.tool_run_message += _modeller.PageBuilder.format_info(run_message)
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)

    @_modeller.logbook_trace(name="BKRCast Export All Attributes", save_arguments=True)
    def __call__(self):

        current_scen = self.current_scenario
        #export extra attributes
        with _modeller.logbook_trace(name = "Export extra attributes", value = ""):
            for f in os.listdir(self.outputFolder):
                os.remove(os.path.join(self.outputFolder, f))
            
            self.exportExtraAttributeDefinition(self.outputFolder, current_scen)
            for extra_attr in current_scen.extra_attributes():
                self.exportExtraAttribute(extra_attr.name, self.outputFolder, current_scen)

            # export @nihdwy to @nihdwy.txt. This will overwrite the same file exported earlier.
            self.exportnihdwy(self.outputFolder, current_scen)

            ## copy @rdly.txt to am_rdly.txt, md_rdly.txt, pm_rdly.txt, ni_rdly.txt
            copyfile(os.path.join(self.outputFolder, '@rdly.txt'), os.path.join(self.outputFolder, 'am_rdly.txt'))
            copyfile(os.path.join(self.outputFolder, '@rdly.txt'), os.path.join(self.outputFolder, 'md_rdly.txt'))
            copyfile(os.path.join(self.outputFolder, '@rdly.txt'), os.path.join(self.outputFolder, 'pm_rdly.txt'))
            os.rename(os.path.join(self.outputFolder, '@rdly.txt'), os.path.join(self.outputFolder, 'ni_rdly.txt'))

    def exportExtraAttribute(self, attr, path, scen):
        attribute = scen.extra_attribute(attr)
        if (attribute == None):
            return

        NAMESPACE = "inro.emme.data.extra_attribute.export_extra_attributes"
        export_attribute = _modeller.Modeller().tool(NAMESPACE)
        export_attribute(extra_attributes = attr, export_path = path, scenario=scen)
        type = attribute.type
        print(type)
        default_name = ""
        if type == "NODE":
            default_name = "extra_nodes_" + scen.id + ".txt"
        elif type == "LINK":
            default_name = "extra_links_" + scen.id + ".txt"
        elif type == "TURN":
            default_name = "extra_turns_" + scen.id + ".txt"
        elif type == "TRANSIT_LINE":
            default_name = "extra_transit_lines_" + scen.id + ".txt"
        elif type == "TRANSIT_SEGMENT":
            default_name = "extra_segments_" + scen.id + ".txt"
        else:
            default_name = "extra_unknowns_" + scen.id + ".txt"
        
        default_name = os.path.join(path, default_name)
        new_name = attr + ".txt"
        new_name = os.path.join(path, new_name)
        os.rename(default_name, new_name)
        print(attr + " exported")
    
    def exportExtraAttributeDefinition(self, path, scen):
        filename = "extra_attribute_definitions.txt"
        outputfile = os.path.join(path, filename)
        file = open(outputfile, 'w')
        for extra_attr in scen.extra_attributes():
            record = extra_attr.type + "," + extra_attr.name + "," + extra_attr.description + "," + str(extra_attr.default_value)
            print(record)
            file.write(record)
            file.write("\n")

        file.close()

    def exportnihdwy(self, path, scen):
        network = scen.get_network()
        tlines = network.transit_lines()

        fn = os.path.join(path, '@nihdwy.txt')
        with open(fn, mode = 'w') as f:
            f.write('line @nihdwy\n')
            for tline in tlines:
                if tline['@nihdwy'] < 999:
                    f.write('{0:d} {1:.0f}\n'.format(int(tline.id), tline['@nihdwy']))

       
 