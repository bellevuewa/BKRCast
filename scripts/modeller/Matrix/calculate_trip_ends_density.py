import inro.modeller as _modeller
import inro.emme.database.emmebank as _eb
import inro.emme.datatable as _dt
import traceback as _traceback
import numpy as np
import pandas as pd
import os
from datetime import datetime

'''
   11/17/2023   
   This tool is used to calculate auto trip ends (mf1..mf21 if tnc is not activated), and density of trip ends by TAZ area.
   The following mo matrices are created:
    mo'total_prod', mo'total_attr', mo'total_trip_ends', 
    mo'prod_density', mo'attr_density', mo'pa_density'
   A data table named 'Auto trip ends' is also created.   
   The data table is also exported to an .csv file.
   A worksheet named 'Auto PA per squared mile' is created to visually show mo'pa_density'.    
'''

class BKRCastTripEndsDensity(_modeller.Tool()):
    tool_run_message = str()
    output_file = _modeller.Attribute(str)   
    tnc_mode_on = _modeller.Attribute(str)    
     
    def __init__(self):
        self.tool_run_message = ''
        self.default_path = os.getcwd()   
        
        
    def page(self):

        pb = _modeller.ToolPageBuilder(self, title="BKRCast Trip Ends Density",
            description="Trip Ends Density Calculation",
            branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")

        pb.add_select_file('output_file', 'save_file', '', self.default_path, title = 'Select the output file')
        pb.add_checkbox('tnc_mode_on', title = 'Is TNC mode on')  
              
        if self.tool_run_message != "":
            pb.tool_run_status(self.tool_run_msg_status)
        
        return pb.render()
    
    def run(self):
        self.tool_run_message = ""
        try:
            self.__call__(tnc_mode = self.tnc_mode_on)
            self.tool_run_message += _modeller.PageBuilder.format_info('trip ends are calculated.')
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
        
    @_modeller.logbook_trace(name="BKRCast Trip Ends Density Calculation", save_arguments=True)
    def __call__(self, tnc_mode = False):
        bank = _modeller.Modeller().emmebank
        if tnc_mode:
            trip_table_upper_limit = 39                    
        trip_table_upper_limit = 21

        total_prod = 0
        total_attr = 0
        total_trip_ends = 0                
        for matrix_id in range(1, trip_table_upper_limit + 1):
            matrix = bank.matrix(f'mf{matrix_id}')
            if matrix != None:
                matrix_data_numpy = matrix.get_numpy_data()
                prod = np.sum(matrix_data_numpy, axis = 1)
                attr = np.sum(matrix_data_numpy, axis = 0)
                # no need to transpose attr, because attr is 1-D array.                
                total = prod + attr 
                total_prod += prod
                total_attr += attr
                total_trip_ends += total  
                sum_ends = np.sum(matrix_data_numpy)                                                              
                print(f'mf{matrix_id}: {matrix.name}, total_trip_ends = {sum_ends}')
    
        # save total_prod, total_attr, and total_trip_ends to mo
        moprod = self.create_matrix('mo', 'total_prod', 'total auto production', total_prod, True)
        moattr = self.create_matrix('mo', 'total_attr', 'total auto attraction', total_attr, True)
        mototal = self.create_matrix('mo', 'total_trip_ends', 'total auto trip ends', total_trip_ends, True)        

        # save everything to dataframe and calculate trip ends per sq mile
        taz_subarea_df = pd.read_csv(r'..\..\..\inputs\subarea_definition\TAZ_subarea.csv')
        matrix_data_index = moprod.get_data().indices
        print(str(matrix_data_index))        
        index_series = pd.Series(matrix_data_index[0], name = 'BKRCastTAZ')
        df = pd.DataFrame({'BKRCastTAZ':matrix_data_index[0], 'prod': moprod.get_numpy_data().astype('float64'), 'attr': moattr.get_numpy_data().astype('float64'), 'total_pa':mototal.get_numpy_data().astype('float64')})        
        df = df.merge(taz_subarea_df[['BKRCastTAZ', 'Area']], on = 'BKRCastTAZ', how = 'left')
        df['prod_density'] = df['prod'] / (df['Area'] / (5280 * 5280))
        df['attr_density'] = df['attr'] / (df['Area'] / (5280 * 5280))
        df['pa_density'] = df['total_pa'] / (df['Area'] / (5280 * 5280))

        # save prod_density, attr_density and pa_density to mos
        moprod_density = self.create_matrix('mo', 'prod_density', 'auto prod per sq mile', df['prod_density'].to_numpy(), True)
        moattr_density = self.create_matrix('mo', 'attr_density', 'auto attr per sq mile', df['attr_density'].to_numpy(), True)
        mopa_density = self.create_matrix('mo', 'pa_density', 'auto PA per sq mile', df['pa_density'].to_numpy(), True) 
               
        # save dataframe df to a data table in emme 
        dt_Data = _dt.Data()
        for col in df.columns:
            attribute = _dt.Attribute(col, df[col].values)
            dt_Data.add_attribute(attribute)
        data_table_db = _modeller.Modeller().desktop.project.data_tables()
        table_name = 'Auto trip ends'        
        if data_table_db.table(table_name) != None:
            data_table_db.delete_table(table_name)  
            _modeller.logbook_write(f'Old data table {table_name} was deleted')                      
                                
        data_table_db.create_table(table_name, dt_Data)  
        _modeller.logbook_write(f'New data table{table_name} was created.')                                                          
        # create worksheet for prod_density, attr_density, and pa_density
        self.create_worksheet(mopa_density)
        _modeller.Modeller().desktop.refresh_data()
        
        # export to density to file
        with open(self.output_file, 'w') as output:
            output.write(str(datetime.now()) + '\n')
            output.write(f'{bank.path}\n')
            output.write(f'{bank.title}\n\n') 
            output.write(df.to_string(index = False)) 
            _modeller.logbook_write(f'File was saved in {self.output_file}.')                       
                       
    def create_worksheet(self, mo):
        ws_path = ['General', 'General worksheet'] 
        desktop = _modeller.Modeller().desktop  
        data_explorer = desktop.data_explorer()        
        project_dir = os.path.dirname(desktop.project_file_name())        

        root_ws_f = desktop.root_worksheet_folder()
        ws = root_ws_f.find_item(ws_path).open()
        ws.par('Name').set('Auto PA per squared mile')     
           
        backgroundlayer = ws.layer(layer_name = 'Background layer(s)') 
        node_polygon = ws.add_layer_over(backgroundlayer, 'Node polygon') 
        node_polygon.par('NodeValue').set(mo.id)    
        node_polygon.par('NodeFilter').set('isZone')
        node_polygon.par('PolygonFile').set(os.path.join(project_dir, 'Media', 'BKRCast_TAZ.shp'))
        node_polygon.par('NodeID').set('TAZNUM')   
        node_polygon.par('NodeValues').set(False)         

        rdpu_style = desktop.project.style('Rdpu').listval
        style_legend = node_polygon.style_legend()  
        style_legend.style_index.set(mo.id)
        style_legend.use_breaks.set(True)
        style_legend.break_decimals.set(0)
        style_legend.style.set_size(len(rdpu_style))
        style_legend.style.set(rdpu_style) 
        style_legend.compute_breaks.set(True)    

        # do not use 'Links' layer, because it is actually a configuration layer
        link_layer = ws.layer(layer_name = 'Link base')
        link_layer.par('LinkFilter').set('isAuto && not(isConnector)')      
        link_layer.par('Offset').set(0.0) # has to be 0.0 (float type 

        node_layer = ws.layer(layer_name = 'Nodes')
        node_layer.par('SFlag').set(False)        
                    
        ws.save(os.path.join(project_dir, 'Worksheets', 'auto_pa_density.emw'))  
        ws.close()   
        _modeller.logbook_write(f'Worksheet \"Auto PA per squared mile\" was created.')                                                                                                   