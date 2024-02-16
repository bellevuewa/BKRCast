import inro.modeller as _modeller
import inro.emme.database.emmebank as _eb
import traceback as _traceback
import matplotlib.pyplot as plt
from scipy import stats
import os
from datetime import datetime

'''
   This tool is used to produce trip table (matrix) comparison between current databank and an external databank. Each trip table is compared
   and scatterplot is drawn and ploted to a big figure. 
   User selects an external databank for comparison, and selects a directory for the output file. If destination directory is not selected,
   default folder of script subfolder is used.

      
   10/21/2023      
'''

class BKRCastTripTableCompare(_modeller.Tool()):

    
    externaldatabase = _modeller.Attribute(str)
    destination_folder = _modeller.Attribute(str)    
    tool_run_message = str()
    
    def __init__(self):
        self.external = ''
        self.tool_run_message = ''
        self.default_path = os.getcwd()        
                
    
    def page(self):

        pb = _modeller.ToolPageBuilder(self, title="BKRCast Trip Table Comparison",
        description="Trip Table Comparison",
        branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")

        pb.add_select_file("externaldatabase", "file", "", title = "External database file:")

        pb.add_select_file('destination_folder', 'directory', '', self.default_path, title = 'Select the directory for output file')
        if self.tool_run_message != "":
            pb.tool_run_status(self.tool_run_msg_status)
        
        return pb.render()
    
    def run(self):
        self.tool_run_message = ""
        try:
            self.__call__()
            if self.destination_folder != None:
                run_message = 'Comparison exported to the selected folder.'
            else:
                run_message = 'Comparison exported to the default folder.'                                                                          
                            
            self.tool_run_message += _modeller.PageBuilder.format_info(run_message)
        except Exception as e:
            self.tool_run_message += _modeller.PageBuilder.format_exception(exception = e, chain = False)

    @_modeller.method(return_type=str)
    def tool_run_msg_status(self):
        return self.tool_run_message

    @_modeller.logbook_trace(name="BKRCast Comparison of All Trip Tables", save_arguments=True)
    def __call__(self):
        this_bank = _modeller.Modeller().emmebank
        external_bank = _eb.Emmebank(self.externaldatabase)
        
        # produce 7 x 4 grid of subplots, make the figure size 32 x 50 inches
        fig, ax = plt.subplots(7, 4, figsize = (32, 50))
        # set margin. Do not use plt.tight_layout() as it is not compatible with margin        
        plt.subplots_adjust(top=0.96, bottom=0.04, left = 0.02, right = 0.98)        
        for mfid in range(1, 26):
            # find out plot location            
            col = (mfid - 1) % 4
            row = (mfid - 1) // 4                        
            mf = f'mf{mfid}'        
            print(f'{mf} {row} {col}')                                       
            internal_matrix = this_bank.matrix(mf)  
            external_matrix = external_bank.matrix(mf) 

            if external_matrix != None:            
                internal_name = internal_matrix.name
                external_name = external_matrix.name                              

                # to make scatter plot of full matrices, we need to convert 2-dimensional to 1D
                internal_array = internal_matrix.get_numpy_data().flatten()
                external_array = external_matrix.get_numpy_data().flatten()

                # this linear regression is consistent with Excel 
                m, b, r, p, se = stats.linregress(internal_array, external_array)
                r2 = r ** 2
                ypred = m * internal_array + b  

                ax[row, col].scatter(internal_array, external_array)   
                # add regression line                
                ax[row, col].plot(internal_array, ypred, label = f'y = {m:.3f}x {b:+.3f}   R^2 = {r2: .3f}')     
                ax[row, col].grid(True, which = 'both', axis = 'both')   
                ax[row, col].set_xlabel(f'Internal {internal_matrix.id} {internal_name}')
                ax[row, col].set_ylabel(f'External {external_matrix.id} {external_name}')
                # ax[row, col].autoscale(tight = True)            
                
                ax[row, col].set_title('Scatter Plot of Two Matrices')
                ax[row, col].legend(bbox_to_anchor=(0.2, 0.9), loc="upper left")

                # make x and y axis have the same scale.
                resize_right = max(ax[row, col].get_xlim()[1], ax[row, col].get_ylim()[1])
                resize_left = min(ax[row, col].get_xlim()[0], ax[row, col].get_ylim()[0])                
                ax[row, col].set_xlim((resize_left, resize_right))
                ax[row, col].set_ylim((resize_left, resize_right))
                               
            else:
                self.tool_run_message += f'{mf} is not valid in external bank.'
        
        print('Exporting...')                                                        
        # add figure title
        fig.suptitle('Trip Table Comparison', fontsize = 32, color = 'black', y = 0.99)   
        # add databank paths and print date to the footer        
        fig.text(0.02, 0.018, 'internal:' + this_bank.path, fontsize = 10)   
        fig.text(0.02, 0.014, 'external:' + self.externaldatabase, fontsize = 10)
        fig.text(0.02, 0.010, datetime.now().strftime('%m-%d-%Y %H:%M:%S'), fontsize = 10) 
                                   
        if (self.destination_folder != None):
            self.default_path = self.destination_folder 
   
        plt.savefig(os.path.join(self.default_path, 'matrix_comparison.png'))
        print('Comparison file is exported.')        
        plt.close(fig)        