import inro.modeller as _modeller
import inro.emme.database.emmebank as _eb
import inro.emme.datatable as _dt
import traceback as _traceback
import numpy as np
import pandas as pd
import os
from datetime import datetime

'''
   11/30/2023   
   This tool is used to import land use by TAZ to mo matrices and create worksheets to highlight them. .
   The following mo matrices are created:
    mo'total_jobs', mo'total_households',  
    mo'job_density', mo'household_density'
    
   A data table named 'Land Use by BKRCastTAZ' is also created.   
.
   Four worksheets are created highlight land use data Worksheets are saved in Landuse folder under Worksheet.    
'''

class BKRCastLandUseDensity(_modeller.Tool()):
    tool_run_message = str()
    input_file = _modeller.Attribute(str)   
     
    def __init__(self):
        self.tool_run_message = ''
        self.default_path = os.getcwd()   
        
    def page(self):

        pb = _modeller.ToolPageBuilder(self, title="BKRCast Import Land Use",
            description="Import Land Use",
            branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")

        pb.add_select_file('input_file', 'file', '', self.default_path, title = 'Select the input land use summary file')
              
        if self.tool_run_message != "":
            pb.tool_run_status(self.tool_run_msg_status)
        
        return pb.render()
    
    def run(self):
        self.tool_run_message = ""
        try:
            self.__call__()
            self.tool_run_message += _modeller.PageBuilder.format_info('land use is imported and worksheets are created.')
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)

    @_modeller.method(return_type=str)
    def tool_run_msg_status(self):
        return self.tool_run_message

    # create a matrix based on matrix type, name, and numpy data.
    def create_matrix(self, matrix_type, matrix_name, description, numpy_data, overwrite = True):
        ns = 'inro.emme.data.matrix.create_matrix'                        
        create_matrix = _modeller.Modeller().tool(ns)
        bank = _modeller.Modeller().emmebank
        matrix = bank.matrix(matrix_type + matrix_name)
        if matrix == None:                       
            matrix = create_matrix(matrix_id = matrix_type, matrix_name = matrix_name, matrix_description = description, overwrite = overwrite)

        matrix.set_numpy_data(numpy_data) 
        _modeller.logbook_write(f'{matrix.id, matrix.name} is updated.')                   
        return matrix
        
    @_modeller.logbook_trace(name="BKRCast import land use", save_arguments=True)
    def __call__(self):
        bank = _modeller.Modeller().emmebank

        lu_df = pd.read_csv(self.input_file)
        template = pd.DataFrame({'BKRCastTAZ':range(1, 1531)})        
        # save everything to dataframe and calculate trip ends per sq mile
        taz_subarea_df = pd.read_csv(r'..\..\..\inputs\subarea_definition\TAZ_subarea.csv')
        lu_df = pd.merge(template, lu_df[['TAZ_P', 'EMPTOT_P', 'HH_P']], left_on = 'BKRCastTAZ', right_on = 'TAZ_P', how = 'left')
        lu_df = lu_df.merge(taz_subarea_df[['BKRCastTAZ', 'Area']], on = 'BKRCastTAZ', how = 'left')
        lu_df['job_density'] = lu_df['EMPTOT_P'] / (lu_df['Area'] /(5280 * 5280))
        lu_df['hh_density'] = lu_df['HH_P'] / (lu_df['Area'] /(5280 * 5280))
        lu_df = lu_df.fillna(0)                        
   
        # save total_prod, total_attr, and total_trip_ends to mo
        mototjobs = self.create_matrix('mo', 'total_jobs', 'total jobs', lu_df['EMPTOT_P'].to_numpy(), True)
        motothhs = self.create_matrix('mo', 'total_hhs', 'total households', lu_df['HH_P'].to_numpy(), True)
        mojobden = self.create_matrix('mo', 'job_den', 'job density', lu_df['job_density'].to_numpy(), True)        
        mohhden = self.create_matrix('mo', 'hh_den', 'household density', lu_df['hh_density'].to_numpy(), True)        

        # save dataframe df to a data table in emme 
        dt_Data = _dt.Data()
        for col in lu_df.columns:
            attribute = _dt.Attribute(col, lu_df[col].values)
            dt_Data.add_attribute(attribute)
        data_table_db = _modeller.Modeller().desktop.project.data_tables()
        table_name = 'Land Use by BKRCastTAZ'        
        if data_table_db.table(table_name) != None:
            data_table_db.delete_table(table_name)  
            _modeller.logbook_write(f'Old data table {table_name} was deleted')                      
                                
        data_table_db.create_table(table_name, dt_Data)  
        _modeller.logbook_write(f'New data table{table_name} was created.')   

        # create land use folder under Worksheet folder
        desktop = _modeller.Modeller().desktop  
        project_dir = os.path.dirname(desktop.project_file_name())        
        output_folder = os.path.join(project_dir, 'Worksheets', 'Landuse')
        if not os.path.exists(os.path.join(output_folder)):
            os.makedirs(output_folder)
            _modeller.logbook_write(f'{output_folder} was created.')   
        # create worksheet for total jobs, total hhs, job density, and hh density.
        self.create_worksheet('Total_jobs', 'Bugn', mototjobs, output_folder)
        self.create_worksheet('Total_householdss', 'Ylgn', motothhs, output_folder)
        self.create_worksheet('Job_density', 'Blues', mojobden, output_folder)
        self.create_worksheet('Household_density', 'Purples', mohhden, output_folder)
        _modeller.Modeller().desktop.refresh_data()
        
    def create_worksheet(self, worksheet_title, style_name, mo, output_folder):
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
        node_polygon.par('NodeValues').set(False)         

        color_style = desktop.project.style(style_name).listval
        style_legend = node_polygon.style_legend()  
        style_legend.style.set_size(len(color_style))
        style_legend.style.set(color_style) 
        style_legend.style_index.set(mo.id)
        style_legend.use_breaks.set(True)
        style_legend.break_decimals.set(0)
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