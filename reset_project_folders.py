'''
    Create project folders including emme project files so that emme databanks are appropriately linked to project files. Run this program 
    after copying a BKRCast model to a new place. Be sure the input_configuration.py is setup correctly.

    created on 9/15/2022
'''

import os, sys
import getopt
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from input_configuration import *
from emme_configuration import *
from EmmeProject import *
from data_wrangling import *
                                      

def help():
    print('  Rebuid EMME projects so that EMME databanks are correctly linked to project files. When a BKRCast model is copied from one place ')
    print('  to another, the projects are pointing to the original places of EMME databanks. Before a new model run is started, this EMME databank linkage ')
    print('  problem has to be fixed by running this script.')
    print('  The project_folder field in input_configuration.py needs to be updated first before running this script.')
    print('\n')
    print('  python reset_project_folders.py -h')
    print('      -h: help')

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h')
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        else:
            print(f'unknown option: {opt}')
            sys.exit(2)

    print('Create project folders...')
    response = input('Have you setup your input_configuration.py correctly (Y/N)?')
    if response == 'Y':
        setup_emme_project_folders()
        print('Done')
    else:
        print('Please update the input_configuration file first.')

if __name__ == '__main__':
    main()  
