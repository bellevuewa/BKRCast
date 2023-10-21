import inro.modeller as _modeller
import inro.emme.database.emmebank as _eb
import traceback as _traceback
import pml as _html
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import os

'''
   This tool is used to compare two full matrices and show the linear regression. One full matrices resides in the current 
   databank. The other one resides in different (external) databank. User needs to select the external databank and the list of
   full matrices will be populated. 
   The scatter plot is saved in png format in selected folder (default is under script folder.)

   10/20/2023      
'''

class BKRCastMatrixCompare(_modeller.Tool()):

    
    externaldatabase = _modeller.Attribute(str)
    externalmatrix = _modeller.Attribute(str)
    internalmatrix = _modeller.Attribute(str)
    destination_folder = _modeller.Attribute(str)    
    external_matrix_dict = {}
    tool_run_message = str()
    
    def __init__(self):
        self.external = ''
        self.externalmatrix = ''
        self.internalmatrix = ''
        self.tool_run_message = ''
        self.default_path = os.getcwd()        
                
    
    def page(self):

        pb = _modeller.ToolPageBuilder(self, title="BKRCast Matrix Comparison",
        description="Matrix Comparison",
        branding_text="Modeling and Analysis Group -- City of Bellevue Transportation")

        pb.add_select_file("externaldatabase", "file", "", title = "External database file:")

        pb.add_select('externalmatrix', keyvalues = self.external_matrix_dict, title = 'Select external matrix')

        pb.add_select_matrix('internalmatrix', filter = ['FULL'], id = True, title = 'Select internal matrix')

        pb.add_select_file('destination_folder', 'directory', '', self.default_path, title = 'Select the directory for output file')
        if self.tool_run_message != "":
            pb.tool_run_status(self.tool_run_msg_status)
        
        pb.add_html("""
<script type="text/javascript">
    $(document).ready( function()
    {
        var t = new inro.modeller.util.Proxy(%s) ;
       
        // remove items from token_select when database or zone_sys is changed
        var clear_external_matrices = function()
        {
            var jq_obj = $("#externalmatrix");
            jq_obj.siblings(".ui-token-parent")
                .children(".ui-token-list").empty();
            jq_obj.empty().trigger('change');
        };
        
        // Population matrix selector with external matrices options
        var set_list_external_matrices = function()
        {
            $("#externalmatrix")
                .append(t.get_options_list())
                //.data('token_select')._refresh_width();
        };
        
        $("#externaldatabase").bind('change', function()
        {
            $(this).commit();
            clear_external_matrices();
            set_list_external_matrices();
        });
    });
</script>""" % pb.tool_proxy_tag)
        return pb.render()
    
    # Function called from GUI to update the list of matrices
    @_modeller.method(argument_types=[], return_type=str)
    def get_options_list(self):
        with _eb.Emmebank(self.externaldatabase, read_only=True) as src_emmebank:
            external_matrices = [('','')]
            for matrix in src_emmebank.matrices():
                if matrix.type == 'FULL':                
                    # tuple (matrix identifier, text representing the matrix in the GUI)
                    external_matrices.append((matrix.id, ','.join([matrix.id, matrix.name, matrix.description])))
        print(self.external_matrix_dict)
        #generate option list:
        try:
            options = _html.HTML()
            options.meta(charset="utf-8")
            for k, v in external_matrices:
                options.option(v, value=k, escape=False)
            
            external_matrix_list = str(options)
            return external_matrix_list
        except Exception as e:
            print(str(e), _traceback.format_exc(chain=False))
            return ""
            
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

    @_modeller.logbook_trace(name="BKRCast Matrix Comparison", save_arguments=True)
    def __call__(self):
        print(self.internalmatrix) 
        print('external: ' + self.externalmatrix)                     
        this_bank = _modeller.Modeller().emmebank
        external_bank = _eb.Emmebank(self.externaldatabase)
                                
        internal_matrix = this_bank.matrix(self.internalmatrix)  
        external_matrix = external_bank.matrix(self.externalmatrix)       

        # to make scatter plot of full matrices, we need to convert 2-dimensional to 1D
        internal_array = internal_matrix.get_numpy_data().flatten()
        external_array = external_matrix.get_numpy_data().flatten()

        # this linear regression is consistent with Excel 
        m, b, r, p, se = stats.linregress(internal_array, external_array)
        r2 = r ** 2
        ypred = m * internal_array + b  

        fig, ax = plt.subplots()
        ax.scatter(internal_array, external_array)   
        ax.plot(internal_array, ypred, label = f'y = {m:.3f}x {b:+.3f}   R^2 = {r2: .3f}')     
        ax.grid(True, which = 'both', axis = 'both')   
        figsize = fig.gca()
        size = max(figsize.get_xlim()[1], figsize.get_ylim()[1])
        print(str(size))    
        # print paths to the footer            
        ax.annotate('internal:' + this_bank.path, xy = (-0.1, -0.20), xycoords = 'axes fraction', ha = 'left', va = 'center', fontsize = 6)
        ax.annotate('external:' + self.externaldatabase, xy = (-0.1, -0.25), xycoords = 'axes fraction', ha = 'left', va = 'center', fontsize = 6)
        ax.axis([0, size, 0, size], 'square')
        ax.set_xlabel('Internal ' + internal_matrix.id)
        ax.set_ylabel('External ' + external_matrix.id)
        ax.set_title('Scatter Plot of Two Matrices')
        fig.legend(bbox_to_anchor=(0.2, 0.9), loc="upper left")
        fig.tight_layout()   
        if (self.destination_folder != None):
            self.default_path = self.destination_folder 
        fig.savefig(os.path.join(self.default_path, 'matrix_comparison_' + self.internalmatrix + '.png'))
        plt.close()        