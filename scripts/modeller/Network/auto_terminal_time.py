import inro.modeller as _modeller
import inro.emme.database.emmebank as _eb
import inro.emme.datatable as _dt
import traceback as _traceback
import numpy as np
import pandas as pd
import os
from datetime import datetime
import jenkspy

'''
   11/30/2023   
   This tool is used to import auto terminal time (origin and destination) to mo'prodtt' and md'attrtt' and then create worksheets with appropriate color rendering.   
   Two worksheets are saved in terminal_time folder under Worksheet.    
'''

class BKRCastAutoTerminalTime(_modeller.Tool()):
    tool_run_message = str()
    
    def __init__(self):
        self.tool_run_message = ''
        self.default_path = os.getcwd()   
        
    def page(self):

        pb = _modeller.ToolPageBuilder(self, title="BKRCast Auto Terminal Time",
            description="Auto Terminal Time",
            branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")

        if self.tool_run_message != "":
            pb.tool_run_status(self.tool_run_msg_status)
        
        return pb.render()
    
    def run(self):
        self.tool_run_message = ""
        try:
            self.__call__()
            self.tool_run_message += _modeller.PageBuilder.format_info('auto terminal time is imported and worksheets are created.')
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)

    @_modeller.method(return_type=str)
    def tool_run_msg_status(self):
        return self.tool_run_message

    @_modeller.logbook_trace(name="BKRCast auto terminal time", save_arguments=True)
    def __call__(self):
        bank = _modeller.Modeller().emmebank

        template = pd.DataFrame({'BKRCastTAZ':range(1, 1531)})        
        origin_tt_file = r'..\..\..\inputs\IntraZonals\origin_tt.in'
        dest_tt_file = r'..\..\..\inputs\IntraZonals\destination_tt.in'

        # import terminal time to mo and md.
        ns = "inro.emme.data.matrix.matrix_transaction"
        process = _modeller.Modeller().tool(ns)
        process(transaction_file=origin_tt_file,
                throw_on_error=True,
                scenario=_modeller.Modeller().scenario)
        process(transaction_file=dest_tt_file,
                throw_on_error=True,
                scenario=_modeller.Modeller().scenario)
        
        moprodtt = bank.matrix('moprodtt')
        mdattrtt = bank.matrix('mdattrtt')

        # create a subfolder for worksheets.
        desktop = _modeller.Modeller().desktop  
        project_dir = os.path.dirname(desktop.project_file_name())        
        output_folder = os.path.join(project_dir, 'Worksheets', 'terminal_time')
        if not os.path.exists(os.path.join(output_folder)):
            os.makedirs(output_folder)
            _modeller.logbook_write(f'{output_folder} was created.')   
            
        # create worksheet for origin terminal time and destination terminal time.
        self.create_worksheet('Origin Terminal Time', 'Multivalues', moprodtt, output_folder)
        self.create_worksheet('Destination Terminal Time', 'Multivalues', mdattrtt, output_folder)
        _modeller.Modeller().desktop.refresh_data()
        
    def create_worksheet(self, worksheet_title, color_name, mo, output_folder):
        ws_path = ['General', 'General worksheet'] 
        desktop = _modeller.Modeller().desktop  
        project_dir = os.path.dirname(desktop.project_file_name())        

        root_ws_f = desktop.root_worksheet_folder()
        ws = root_ws_f.find_item(ws_path).open()
        ws.par('Name').set(worksheet_title)     
           
        backgroundlayer = ws.layer(layer_name = 'Background layer(s)') 
        node_polygon = ws.add_layer_over(backgroundlayer, 'Node polygon') 
        node_polygon.par('PolygonFile').set(os.path.join(project_dir, 'Media', 'BKRCast_TAZ.shp'))
        node_polygon.par('NodeID').set('TAZNUM')   
        node_polygon.par('NodeValue').set(mo.id)    
        node_polygon.par('NodeFilter').set('isZone')
        node_polygon.par('NodeValues').set(True)         

        color_style = desktop.project.style(color_name).listval
        style_legend = node_polygon.style_legend()  
        style_legend.style.set_size(len(color_style))
        style_legend.style.set(color_style) 
        style_legend.style_index.set(mo.id)
        style_legend.use_breaks.set(True)
        style_legend.discrete_breaks.set(True)        
        style_legend.break_decimals.set(0)
        style_legend.break_method.set('QUANTILE')        
        style_legend.compute_breaks.set(True)    

        # do not use 'Links' layer, because it is actually a configuration layer which includes multiple 'regular' layers.
        link_layer = ws.layer(layer_name = 'Link base')
        link_layer.par('LinkFilter').set('isAuto && not(isConnector)')      
        link_layer.par('Offset').set(0.0) # has to be 0.0 (float type 

        node_layer = ws.layer(layer_name = 'Nodes')
        node_layer.par('SFlag').set(False)        
                    
        ws.save(os.path.join(output_folder, worksheet_title + '.emw'))  
        ws.close()   
        _modeller.logbook_write(f'Worksheet {worksheet_title} was created.')                                                                                                   