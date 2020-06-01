import pandas as pd  
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
from input_configuration import *
from emme_configuration import *

# This tool is to create a list of extra attributes, defined in extra_attributes, in
# all four TOD databanks. Values are also imported.

extra_attributes = [{'type':'LINK', 'name': '@studyarea', 'description': 'flag for study area', 'overwrite': True, 'file_name':'inputs/extra_attributes/@studyarea.txt'},
                       {'type':'LINK', 'name': '@studyarea405', 'description': 'flag for I405 and ramps in study area', 'overwrite': True, 'file_name':'inputs/extra_attributes/@studyarea405.txt'}]

def main():
    print network_summary_project
    my_project = EmmeProject(network_summary_project)

    for flag, val in sound_cast_net_dict.iteritems():
        my_project.change_active_database(flag)
        print 'TOD: ', flag
        for attr in extra_attributes:
            print '  ', attr['name'], ' is created'
            my_project.create_extra_attribute(attr['type'], attr['name'], attr['description'], attr['overwrite'])
            filepath = os.path.join(project_folder, attr['file_name']).replace('\\','/')
            if os.path.isfile(filepath) == True:
                my_project.import_attribute_values(filepath, '1002', ' ', False)
                print '      value is imported.'
            else:
                print '    ', attr['file_name'], ' is not a valid file.'

    print 'Done'

if __name__ == '__main__':
    main()
