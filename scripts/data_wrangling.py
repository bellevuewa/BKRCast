#Copyright [2014] [Puget Sound Regional Council]

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os,sys,datetime,re
import subprocess
import inro.emme.desktop.app as app
import json
from shutil import copy2 as shcopy
from distutils import dir_util
import re
import inro.emme.database.emmebank as _eb
import random
import shutil
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"inputs"))
from input_configuration import *
from logcontroller import *
from emme_configuration import *
from accessibility.accessibility_configuration import *
import input_configuration
import emme_configuration
import pandas as pd
import numpy as np
import h5py

import glob

# 10/25/2021
# modified to be compatible with python 3


def multipleReplace(text, wordDict):
    for key in wordDict:
        text = text.replace(key, wordDict[key])
    return text

@timed
def copy_daysim_code():
    print('Copying Daysim executables...')
    if not os.path.exists(os.path.join(os.getcwd(), 'daysim')):
       os.makedirs(os.path.join(os.getcwd(), 'daysim'))
    try:
        dir_util.copy_tree(daysim_code, 'daysim')
    except Exception as ex:
        template = "An exception of type {0} occured. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)
        sys.exit(1)

@timed
def copy_accessibility_files():
    if not os.path.exists('inputs/accessibility'):
        os.makedirs('inputs/accessibility')
    
    print('Copying Hourly and Daily Parking Files')
    if run_update_parking: 
        try:
            shcopy(base_inputs+'/landuse/hourly_parking_costs.csv','inputs/accessibility')
            shcopy(base_inputs+'/landuse/daily_parking_costs.csv','inputs/accessibility')
        except:
            print('error copying parking file at' + base_inputs+'/landuse/' + ' either hourly or daily parking costs')
            sys.exit(1)

def text_to_dictionary(dict_name):

    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_file=open(input_filename)
    my_dictionary = {}

    for line in my_file:
        k, v = line.split(':')
        my_dictionary[eval(k)] = v.strip()

    return(my_dictionary)

def json_to_dictionary(dict_name, subdir = ''):
    """
    Import JSON-formatted input as dictionary. Expects file extension .json.
    """
    input_filename = os.path.join('inputs/skim_params/',subdir, dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)
    
@timed    
def setup_emme_bank_folders():
    tod_dict = text_to_dictionary('time_of_day')
    emmebank_dimensions_dict = json_to_dictionary('emme_bank_dimensions')
    
    if not os.path.exists('Banks'):
        os.makedirs('Banks')
    else:
        # remove it
        print('deleting Banks folder')
        shutil.rmtree('Banks')

    #gets time periods from the projects folder, so setup_emme_project_folder must be run first!
    time_periods = list(set(tod_dict.values()))
    time_periods.append('TruckModel')
    time_periods.append('Supplementals')
    for period in time_periods:
        print(period)
        print("creating bank for time period %s" % period)
        os.makedirs(os.path.join('Banks', period))
        path = os.path.join('Banks', period, 'emmebank')
        emmebank = _eb.create(path, emmebank_dimensions_dict)
        emmebank.title = period
        emmebank.unit_of_length = unit_of_length
        emmebank.coord_unit_length = coord_unit_length  
        scenario = emmebank.create_scenario(1002)
        network = scenario.get_network()
        #need to have at least one mode defined in scenario. Real modes are imported in network_importer.py
        network.create_mode('AUTO', 'a')
        scenario.publish_network(network)
        emmebank.dispose()

@timed
def setup_emme_project_folders():

    tod_dict = text_to_dictionary('time_of_day')
    tod_list = list(set(tod_dict.values()))

    if os.path.exists(os.path.join('projects')):
        print('Delete Project Folder')
        shutil.rmtree('projects')

    # Create master project, associate with all tod emmebanks
    project = app.create_project('projects', master_project)
    desktop = app.start_dedicated(False, modeller_initial, project)
    data_explorer = desktop.data_explorer()
    for tod in tod_list:
        database = data_explorer.add_database('Banks/' + tod + '/emmebank')
    #open the last database added so that there is an active one
    database.open()
    desktop.project.save()
    desktop.close()

    # Create time of day projects, associate with emmebank
    tod_list.append('TruckModel') 
    tod_list.append('Supplementals')
    for tod in tod_list:
        project = app.create_project('projects', tod)
        desktop = app.start_dedicated(False, modeller_initial, project)
        data_explorer = desktop.data_explorer()
        database = data_explorer.add_database('Banks/' + tod + '/emmebank')
        database.open()
        desktop.project.save()
        desktop.close()
        
        #copy worksheets
        wspath = os.path.join('inputs/model/worksheets/', tod)
        destpath = os.path.join('projects/', tod, 'Worksheets')
        copyfiles(wspath, destpath)
        # copy media files
        destpath = os.path.join('projects/', tod, 'Media')
        copyfiles('inputs/model/Media/', destpath)

        
def copyfiles(sourceFolder, destFolder):
    for filename in os.listdir(sourceFolder):
        src = os.path.join(sourceFolder, filename)
        dest = os.path.join(destFolder, filename)
        if (os.path.isfile(src)):
            shutil.copyfile(src, dest)

@timed    
def copy_large_inputs():
    print('Copying large inputs...')
    print('  network files..')
    dir_util.copy_tree(base_inputs+'/networks','inputs/networks')
    print('  counts..')
    dir_util.copy_tree(base_inputs+'/observed','inputs/observed')
    print('  extra attributes..')
    dir_util.copy_tree(base_inputs+'/extra_attributes','inputs/extra_attributes')
    print('  tolls..')
    dir_util.copy_tree(base_inputs+'/tolls','inputs/tolls')
    print('  vdfs..')
    dir_util.copy_tree(base_inputs+'/vdfs','inputs/vdfs')
    print('  intraZonals..')
    dir_util.copy_tree(base_inputs+'/IntraZonals','inputs/IntraZonals')
    print('  fare..')
    dir_util.copy_tree(base_inputs+'/Fares','inputs/Fares')
    print('  trucks..')
    dir_util.copy_tree(base_inputs+'/trucks','inputs/trucks')
    print('  accessibility..')
    dir_util.copy_tree(base_inputs+'/accessibility','inputs/accessibility')  
    print('  bikes..')
    dir_util.copy_tree(base_inputs+'/bikes','inputs/bikes')
    print('  supplemental..')
    dir_util.copy_tree(base_inputs+'/supplemental','inputs/supplemental')
    print('  land use..')
    dir_util.copy_tree(base_inputs+'/landuse','inputs/landuse')
    dir_util.copy_tree(base_inputs+'/popsim','inputs/popsim')
    print('  survey..')
    shcopy(main_inputs_folder + '/model/survey.h5','scripts/summarize/inputs/calibration')
    print('  park and ride capacity..')
    dir_util.copy_tree(base_inputs+'/pnr','inputs/pnr')

#@timed
#def copy_seed_supplemental_trips():
#    print('Copying seed supplemental trips')
#    if not os.path.exists('outputs/supplemental'):
#       os.makedirs('outputs/supplemental')
#    for filename in glob.glob(os.path.join(project_folder+'/inputs/supplemental/trips', '*.*')):
#        shutil.copy(filename, project_folder+'/outputs/supplemental')
    
@timed
def rename_network_outs(iter):
    for summary_name in network_summary_files:
        csv_output = os.path.join(os.getcwd(), 'outputs',summary_name+'.csv')
        if os.path.isfile(csv_output):
            shcopy(csv_output, os.path.join(os.getcwd(), 'outputs',summary_name+str(iter)+'.csv'))
            os.remove(csv_output)


@timed          
def clean_up():
    delete_files = ['working\\household.bin', 'working\\household.pk', 'working\\parcel.bin',
                   'working\\parcel.pk', 'working\\parcel_node.bin', 'working\\parcel_node.pk', 'working\\park_and_ride.bin',
                   'working\\park_and_ride_node.pk', 'working\\person.bin', 'working\\person.pk', 'working\\zone.bin',
                   'working\\zone.pk']

    if (delete_parcel_data):
        delete_files.extend(['inputs\\accessibility\\'+parcels_file_name, output_parcels, buffered_parcels_csv])
    
    for file in delete_files: 
        if (os.path.isfile(file)):
            os.remove(file)
        else:
            print(file)


def find_inputs(base_directory, save_list):
    for root, dirs, files in os.walk(base_directory):
        for file in files:
            if '.' in file:
                save_list.append(file)

def check_inputs():
    ''' Warn user if any inputs are missing '''

    logger = logging.getLogger('main_logger')

    # Build list of existing inputs from local inputs
    input_list = []
    find_inputs(os.getcwd(), input_list)    # local inputs

    # Compare lists and report inconsistenies
    missing_list = []
    for f in commonly_missing_files:
        if not any(f in input for input in input_list):
            missing_list.append(f)

    # Save missing file list to soundcast log and print to console
    if len(missing_list) > 0:
        logger.info('Warning: the following files are missing and may be needed to complete the model run:')
        print('Warning: the following files are missing and may be needed to complete the model run:')
        for file in missing_list:
            logger.info('- ' + file)
            print(file)

def h5_to_df(h5_file, group_name):
    """
    Converts the arrays in a H5 store to a Pandas DataFrame. 
    """
    col_dict = {}
    h5_set = h5_file[group_name]
    for col in h5_set.keys():
        my_array = np.asarray(h5_set[col])
        col_dict[col] = my_array
    df = pd.DataFrame(col_dict)
    return df

def df_to_h5(df, h5_store, group_name):
    """
    Stores DataFrame series as indivdual to arrays in an h5 container. 
    """
    # delete store store if exists   
    if group_name in h5_store:
        del h5_store[group_name]
        my_group = h5_store.create_group(group_name)
        print("Group Skims Exists. Group deleSted then created")
        #If not there, create the group
    else:
        my_group = h5_store.create_group(group_name)
        print("Group Skims Created")
    for col in df.columns:
        h5_store[group_name].create_dataset(col, data=df[col], dtype = 'int', compression = 'gzip')

def backupScripts(source, dest):
    import os
    import shutil
    shutil.copyfile(source, dest)

def get_hhs_df_from_synpop():
    poph5 = h5py.File(os.path.join(project_folder, households_persons_file), 'r')
    hhs = h5_to_df(poph5, 'Household')
    persons = h5_to_df(poph5, 'Person')
    return hhs, persons

def get_current_commit_hash():
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    except:
        commit = '0000000'
    return commit

def build_output_dirs():
    for path in ['outputs',r'outputs/daysim','outputs/bikes','outputs/network','outputs/transit', 'outputs/landuse','outputs/emissions', r'outputs/trucks', 'outputs/supplemental', 'outputs/summary']:
        if not os.path.exists(path):
            os.makedirs(path)
