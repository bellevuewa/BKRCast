'''
    Create project folders including emme project files so that emme databanks are appropriately linked to project files. Run this program 
    after copying a BKRCast model to a new place. Be sure the input_configuration.py is setup correctly.

    created on 9/15/2022
'''

import inro.emme.database.emmebank as _emmebank
import inro.emme.desktop.app as app
import inro.modeller as _m
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from input_configuration import *
from emme_configuration import *
from EmmeProject import *
from data_wrangling import *
                                      

def main():
    print('Create project folders...')
    response = input('Have you setup your input_configuration.py correctly (Y/N)?')
    if response == 'Y':
        setup_emme_project_folders()
        print('Done')
    else:
        print('Please update the input_configuration file first.')

if __name__ == '__main__':
    main()  
