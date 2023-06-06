import inro.modeller as _modeller
from inro.emme.desktop import worksheet as _worksheet
import pandas as pd
import os

'''
    05/25/2023
    Export intersection nodes in batch mode.
'''
class BKRCastExportIntVolumes(_modeller.Tool()):
    version = "1.0" # this is the version
    default_path = ""
    tool_run_message = ""
    outputFolder = _modeller.Attribute(object)
    intputFilename = _modeller.Attribute(object)
    vol_factor = _modeller.Attribute(float)
    general_notes = _modeller.Attribute(str)

    def page(self):
        pb = _modeller.ToolPageBuilder(self, title="BKRCast Network Interface",
                     description="Export Intersection Volumes",
                     branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")

        pb.add_select_file("outputFolder", "directory", "", self.default_path, title = "Select the directory for output files")
        pb.add_select_file("intputFilename", "file", "", self.default_path, title = "Select the intersection node list", note = 'file has only one column, use <b>node</b> as column name.')
        pb.add_text_box("general_notes", 60, title = 'General Description', note = 'Maximum 60 characters.')
        pb.add_text_box('vol_factor', 4, title = 'Peak Hour Factor', note = 'decimal only')

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
            run_message = "All intersections are exported."
            self.tool_run_message += _modeller.PageBuilder.format_info(run_message)
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)

    @_modeller.logbook_trace(name="BKRCast Export Intersection Volumes", save_arguments=True)
    def __call__(self):
        nodes_df = pd.read_csv(self.intputFilename)
        node_list = nodes_df['node'].tolist()

        #export extra attributes
        with _modeller.logbook_trace(name = "Export Intersection Volumes", value = ""):
            self.exportIntersectionVolumes(self.outputFolder, node_list)


    def exportIntersectionVolumes(self, folder, nodes):
        print(f'current dir: {os.getcwd()}')
        modeller = _modeller.Modeller()
        desktop = modeller.desktop
        ws_folder = desktop.root_worksheet_folder()
        wspath = ['Traffic volumes at intersections']
        int_ws = ws_folder.find_item(wspath).open()
        intersection_layer = int_ws.layer(layer_type = 'Configurable control', layer_name = 'Intersection')
        if self.vol_factor != None:
            expression = f'pvolau * {self.vol_factor}'
            intersection_layer.par('Expression0').set(expression)

        intersection_legend = int_ws.layer(layer_name = 'Legend')
        intersection_legend.add_legend_item('TextItem')
        seqid = intersection_legend.get_legend_item_count() - 1
        intersection_legend.set_legend_coordinates(seqid, _worksheet.LegendLayer.Coordinate.BottomLeftPixel)
        intersection_legend.set_legend_anchor_pos(seqid, _worksheet.LegendLayer.Anchor.BottomLeft)
        # below numbers have to float
        intersection_legend.par("TextXPos").set(6.0, index = seqid)
        intersection_legend.par("TextYPos").set(6.0, index = seqid)
        intersection_legend.par("TextString").set(self.general_notes, index = seqid)

        for node_id in nodes:
            intersection_layer.par('Filter0').set("i=={}".format(node_id))
            fn = os.path.join(folder, str(node_id) + '.pdf')
            int_ws.save_as_pdf(fn)
        
        int_ws.close()


            
        

        




