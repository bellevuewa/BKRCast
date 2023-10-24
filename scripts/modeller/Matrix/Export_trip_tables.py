import inro.modeller as _modeller
import inro.emme.database.emmebank as _eb
import traceback as _traceback
import pml as _html
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import os
from datetime import datetime
import pandas as pd

'''
   This tool is to export all trip tables from the current databank to an external excel file. Each trip table takes one tab. 
   Readme tab provides additional info regarding the model and matrices.
   If no matrix is selected, all trip tables are exported (mf1 .. mf25). mf26, mf27 and mf28 are not exported only because they are modes that 
   are irrelevant to BKR area.       
   Total trip ends, total trips, and total intrazonal trips can be exported as an option.    

   10/23/2023         
'''
class BKRCastExportTripTables(_modeller.Tool()):

    internalmatrix = _modeller.Attribute(list)
    destination_folder = _modeller.Attribute(str)    
    matrixsummary = _modeller.Attribute(bool)    
    tool_run_message = str()
    
    def __init__(self):
        self.internalmatrix = ''
        self.tool_run_message = ''
        self.default_path = os.getcwd()   
        self.trip_table_list = [f'mf{id}' for id in range(1, 26)] 
        self.matrixsummary = False               
                
    def page(self):

        pb = _modeller.ToolPageBuilder(self, title="BKRCast Trip Table Export",
        description="Export Trip Tables",
        branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")

        pb.add_select_matrix('internalmatrix', filter = ['FULL'], id = True, multiple = True, title = 'Select matrices', note = 'all trip tables are selected if no selection is made')

        pb.add_select_file('destination_folder', 'directory', '', self.default_path, title = 'Select the directory for output file')

        pb.add_checkbox('matrixsummary', title = 'Export matrix summary')        

        if self.tool_run_message != "":
            pb.tool_run_status(self.tool_run_msg_status)
        
        return pb.render()

    @_modeller.method(return_type=str)
    def tool_run_msg_status(self):
        return self.tool_run_message
                
    def run(self):
        self.tool_run_message = ""
        try:
            self.__call__(self.internalmatrix, self.destination_folder, self.matrixsummary)
            if self.destination_folder != None:
                run_message = 'Trip tables are exported to the selected folder.'
            else:
                run_message = 'Trip tables exported to the default folder.'                                                                          
                            
            self.tool_run_message += _modeller.PageBuilder.format_info(run_message)
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)
            

    def stringfilter(self, str):
        s = '[]"'
        line = str        
        for char in s: 
            line = line.replace(char, '')
        
        l = line.split(',')
        return l        
             
    @_modeller.logbook_trace(name="BKRCast Trip Tables Export", save_arguments=True)
    def __call__(self, internalmatrix, destination_folder, matrixsummary):
        # for some reason, the value self.internalmatrix is not a list, but a string. Need to parse it to list of matrices.
        # bug is reported to INRO waiting for a fix in a future update.  
        if internalmatrix == '':
            matrices = self.trip_table_list  
        else:                             
            matrices = self.stringfilter(internalmatrix)
        print(matrices) 

        cur_bank = _modeller.Modeller().emmebank
        if destination_folder != None:
            export_loc = destination_folder
        else:
            export_loc = self.default_path                                    
                
        writer = pd.ExcelWriter(os.path.join(export_loc, 'EMME_Trip_Tables.xlsx'), engine = 'xlsxwriter') 
        ### create a list of matrix to be exported
        if matrixsummary == True:
            matrix_table_columns = ['Matrix ID', 'Matrix Name', 'Description', 'Total Tripends', 'Total Trips', 'Intrazonal Trips']
        else: 
            matrix_table_columns = ['Matrix ID', 'Matrix Name', 'Description']
        matrix_list_df = pd.DataFrame(columns = matrix_table_columns)
                       
        for mfid in matrices:
            matrix = cur_bank.matrix(mfid)
            if matrix != None:            
                print(f'{matrix.id} {matrix.name}')
                matrix_data_numpy = matrix.get_numpy_data() 
                
                if matrixsummary == True:                
                    total_tripends = np.sum(matrix_data_numpy)
                    intrazonal_trips = np.trace(matrix_data_numpy)                
                    total_trips = total_tripends - intrazonal_trips 
                    newrow = {'Matrix ID': matrix.id, 'Matrix Name':matrix.name, 'Description':matrix.description, 'Total Tripends':total_tripends, 'Total Trips': total_trips, 'Intrazonal Trips': intrazonal_trips}                
                else:
                    newrow = {'Matrix ID': matrix.id, 'Matrix Name':matrix.name, 'Description':matrix.description}                
                                        
                matrix_list_df = matrix_list_df.append(newrow, ignore_index = True)  
                              
                matrix_data_indices = matrix.get_data().indices                    
                df = pd.DataFrame(matrix_data_numpy, columns = matrix_data_indices[1]) 
                index_series = pd.Series(matrix_data_indices[0], name='BKRCastTAZ')
                df.set_index(index_series, inplace = True)                
                df.to_excel(writer, sheet_name = f'{matrix.id}', index = True, startrow = 0)     
                                    
        matrix_list_df.to_excel(writer, sheet_name = 'readme', index = False, startrow = 4, startcol = 0, columns = matrix_table_columns)
        wksheet = writer.sheets['readme']
        wksheet.write(0, 0, str(datetime.now()))
        wksheet.write(1, 0, 'model folder')
        wksheet.write(1, 1, cur_bank.path)
        wksheet.write(3, 0, 'List of Trip Tables')   
        
        writer.close()
