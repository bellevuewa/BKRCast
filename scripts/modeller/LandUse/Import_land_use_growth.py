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
   This tool is used to import land use by TAZ to mo matrices and create worksheets to highlight them. .
   The following mo matrices are created:
    mo'total_jobs', mo'total_households',  
    mo'job_density', mo'household_density'
    
   A data table named 'Land Use by BKRCastTAZ' is also created.   
.
   Four worksheets are created highlight land use data Worksheets are saved in Landuse folder under Worksheet.    
'''

class BKRCastLandUseGrowth(_modeller.Tool()):
    tool_run_message = str()
    future_input_file = _modeller.Attribute(str)  
    base_input_file = _modeller.Attribute(str)     
    bkr_only = _modeller.Attribute(bool)    
    
    def __init__(self):
        self.tool_run_message = ''
        self.default_path = os.getcwd()   
        
    def page(self):

        pb = _modeller.ToolPageBuilder(self, title="BKRCast Import Land Use Growth",
            description="Import Land Use Growth",
            branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")

        pb.add_select_file('future_input_file', 'file', '', self.default_path, title = 'Select the future land use summary file')
        pb.add_select_file('base_input_file', 'file', '', self.default_path, title = 'Select the base land use summary file')

        pb.add_checkbox('bkr_only', title = 'Show BKR only?')        
                      
        if self.tool_run_message != "":
            pb.tool_run_status(self.tool_run_msg_status)
        
        return pb.render()
    
    def run(self):
        self.tool_run_message = ""
        try:
            self.__call__()
            self.tool_run_message += _modeller.PageBuilder.format_info('land use growth is imported and worksheets are created.')
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
        
    @_modeller.logbook_trace(name="BKRCast import land use growth", save_arguments=True)
    def __call__(self):
        bank = _modeller.Modeller().emmebank

        future_lu_df = pd.read_csv(self.future_input_file)
        base_lu_df = pd.read_csv(self.base_input_file)        
        template = pd.DataFrame({'BKRCastTAZ':range(1, 1531)})        
        # save everything to dataframe and calculate trip ends per sq mile
        taz_subarea_df = pd.read_csv(r'..\..\..\inputs\subarea_definition\TAZ_subarea.csv')
        future_lu_df = pd.merge(template, future_lu_df[['TAZ_P', 'EMPTOT_P', 'HH_P']], left_on = 'BKRCastTAZ', right_on = 'TAZ_P', how = 'left')
        future_lu_df.rename(columns = {'EMPTOT_P':'Future_Jobs', 'HH_P':'Future_Hhs'}, inplace = True)        

        base_lu_df = pd.merge(template, base_lu_df[['TAZ_P', 'EMPTOT_P', 'HH_P']],  left_on = 'BKRCastTAZ', right_on = 'TAZ_P', how = 'left')        
        base_lu_df.rename(columns = {'EMPTOT_P':'Base_Jobs', 'HH_P':'Base_Hhs'}, inplace = True) 

        combined_lu_df = pd.merge(future_lu_df, base_lu_df, on = 'BKRCastTAZ', how = 'inner')               
        combined_lu_df = combined_lu_df.merge(taz_subarea_df[['BKRCastTAZ', 'Jurisdiction']], on = 'BKRCastTAZ', how = 'left')
        combined_lu_df.fillna(0, inplace = True)
        combined_lu_df['job_growth'] = combined_lu_df['Future_Jobs'] - combined_lu_df['Base_Jobs']
        combined_lu_df['hh_growth'] = combined_lu_df['Future_Hhs'] - combined_lu_df['Base_Hhs']

        # save dataframe df to a data table in emme 
        dt_Data = _dt.Data()
        for col in combined_lu_df.columns:
            attribute = _dt.Attribute(col, combined_lu_df[col].values)
            dt_Data.add_attribute(attribute)
        data_table_db = _modeller.Modeller().desktop.project.data_tables()
        table_name = 'Land Use Growth by BKRCastTAZ'        
        if data_table_db.table(table_name) != None:
            data_table_db.delete_table(table_name)  
            _modeller.logbook_write(f'Old data table {table_name} was deleted')                      
                                
        data_table_db.create_table(table_name, dt_Data)  
        _modeller.logbook_write(f'New data table{table_name} was created.')   

        if self.bkr_only:
            combined_lu_df.loc[(combined_lu_df['Jurisdiction'] != 'BELLEVUE') & (combined_lu_df['Jurisdiction'] != 'KIRKLAND') & (combined_lu_df['Jurisdiction'] != 'REDMOND'), ['Future_Jobs', 'Future_Hhs', 'Base_Jobs', 'Base_Hhs', 'job_growth', 'hh_growth']] = 0

        # save total_prod, total_attr, and total_trip_ends to mo
        moftotjobs = self.create_matrix('mo', 'future_jobs', 'future total jobs', combined_lu_df['Future_Jobs'].to_numpy(), True)
        moftothhs = self.create_matrix('mo', 'future_hhs', 'future total households', combined_lu_df['Future_Hhs'].to_numpy(), True)
        mobtotjobs = self.create_matrix('mo', 'base_jobs', 'base total jobs', combined_lu_df['Base_Jobs'].to_numpy(), True)
        mobtothhs = self.create_matrix('mo', 'base_hhs', 'base total households', combined_lu_df['Base_Hhs'].to_numpy(), True)
        mojobgrowth = self.create_matrix('mo', 'job_growth', 'job growth', combined_lu_df['job_growth'].to_numpy(), True)        
        mohhgrowth = self.create_matrix('mo', 'hh_growth', 'hh growth', combined_lu_df['hh_growth'].to_numpy(), True)        

        # create land use folder under Worksheet folder
        desktop = _modeller.Modeller().desktop  
        project_dir = os.path.dirname(desktop.project_file_name())        
        output_folder = os.path.join(project_dir, 'Worksheets', 'Landuse Growth')
        if not os.path.exists(os.path.join(output_folder)):
            os.makedirs(output_folder)
            _modeller.logbook_write(f'{output_folder} was created.')   
        # create worksheet for total jobs, total hhs, job density, and hh density.
        self.create_worksheet('Job Growth', 'Bugn', mojobgrowth, output_folder)
        self.create_worksheet('HH Growth', 'Bugn', mohhgrowth, output_folder)
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

        ## modify the color scheme to show negative growht in different color ramp
        # create break using natural break (jenks) 
        npdata = mo.get_data().to_numpy()
        jenks_break = jenkspy.jenks_breaks(npdata, nb_class = 13)
        for i in range(len(jenks_break) - 1):
            if jenks_break[i] < 0 and jenks_break[i + 1] > 0:
                jenks_break.insert(i + 1, -0.1)
                jenks_break.insert(i + 2, 0.1) 
                break
               
        color_style_negative = desktop.project.style('Reds').listval
        # add two color placeholders because we added two breaks in jenks_break        
        color_style.append(color_style[0].copy())        
        color_style.append(color_style[1].copy())  

        # color no change in white
        from colour import Color
        color_style[i+1].fill.color = Color('white')
                                   
        # Color all decrease in red                                                                    
        k = 0
        for j in range(i, -1, -1):
            color_style[j] = color_style_negative[k]
            k = k + 1            
 
        # color all increase in color_name             
        color_style_positive = desktop.project.style(color_name).listval
        k = 0
        for j in range(i+2, len(color_style)):
            color_style[j] = color_style_positive[k]
            k = k + 1                     

        print(f'jenks break: {jenks_break}')
        style_legend = node_polygon.style_legend()  
        style_legend.style.set_size(len(color_style))
        style_legend.style.set(color_style) 
        style_legend.style_index.set(mo.id)
        style_legend.use_breaks.set(True)
        style_legend.break_decimals.set(0)
        style_legend.breaks.breaks = jenks_break
        
        # do not use 'Links' layer, because it is actually a configuration layer which includes multiple 'regular' layers.
        link_layer = ws.layer(layer_name = 'Link base')
        link_layer.par('LinkFilter').set('isAuto && not(isConnector)')      
        link_layer.par('Offset').set(0.0) # has to be 0.0 (float type 

        node_layer = ws.layer(layer_name = 'Nodes')
        node_layer.par('SFlag').set(False)        
                    
        ws.save(os.path.join(output_folder, worksheet_title + '.emw'))  
        ws.close()   
        _modeller.logbook_write(f'Worksheet {worksheet_title} was created.')                                                                                                   