import pandas as pd  
import os, sys
import getopt
import json
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
from input_configuration import *
from emme_configuration import *


def help():
    print(' Create extra attributes in designated scenarios of each databank. Values are imported from external files as well.')
    print(' User can create multiple attributes through a dict file, or one attribute through command line.')
    print('')
    print('  create_extra_attributes.py -h -s scenario_id -d dict_file -f attribute_file_exported_from_emme')
    print('     where: ')
    print('        -h: help')
    print('        -s: scenario_id: which scenario should receive the extra attributes')
    print('        -d: dict_file in which multple. An example is below.')  
    print('        -f: an attribute file exported from EMME, including the attribute definition. ') 
    print('')
    print('  dict_file example:')  
    print("  [{'type':'LINK', 'name': '@studyarea', 'description': 'flag for study area', 'overwrite': 'True', 'file_name':'inputs/extra_attributes/@studyarea.txt'},")
    print("   {'type':'LINK', 'name': '@studyarea405', 'description': 'flag for I405 and ramps in study area', 'overwrite': 'True', 'file_name':'inputs/extra_attributes/@studyarea405.txt'}]")
    print('')       
    
def main():
    extra_attr_dict_file_path = None
    attribute_file_path = None  # node extra attribute file exported from emme, with attribute definition in head  
    scen = '1002'    
    exter_attributes_dict = None    
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hs:d:f:') 
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt =='-s': # scenario in which extra attributes are to be imported, 
            scen = str(arg)                       
        elif opt == '-d': # dict file of extra attributes
            extra_attr_dict_file_path = str(arg) #absolute file path   
            exter_attributes_dict = json.load(open(extra_attr_dict_file_path.replace('\\', '/'), "r"))                     
        elif opt == '-f': # extra attribute file with attribute definition
            attribute_file_path = str(arg)
        else:
            print('Invalid option: ' + opt)
            print('Use -h to display help.')
            exit(2)
    
    print(network_summary_project)
    my_project = EmmeProject(network_summary_project)


    for flag, val in sound_cast_net_dict.items():
        my_project.change_active_database(flag)
        my_project.set_primary_scenario(int(scen))                    
        print('TOD: ', flag)
        if exter_attributes_dict != None:        
            for attr in exter_attributes_dict:
                print('  ', attr['name'], ' is created')
                my_project.create_extra_attribute(attr['type'], attr['name'], attr['description'], attr['overwrite'])
                filepath = os.path.join(project_folder, attr['file_name']).replace('\\','/')
                if os.path.isfile(filepath) == True:
                    my_project.import_attribute_values(filepath, False, False)
                    print('      value is imported.')
                else:
                    print('    ', attr['file_name'], ' is not a valid file.')
        elif attribute_file_path != None:
            my_project.import_attribute_values(attribute_file_path, False, True)
            print(f'{attribute_file_path} is imported.')            
            
    my_project.closeDesktop()        
    print('Done')

if __name__ == '__main__':
    main()
