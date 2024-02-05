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
sys.path.append(os.path.join(os.getcwd(),"inputs", "skim_params"))
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
    #print('  supplemental..')
    #dir_util.copy_tree(base_inputs+'/supplemental','inputs/supplemental')
    print('  land use..')
    dir_util.copy_tree(base_inputs+'/landuse','inputs/landuse')
    dir_util.copy_tree(base_inputs+'/popsim','inputs/popsim')
    print('  park and ride capacity..')
    dir_util.copy_tree(base_inputs+'/pnr','inputs/pnr')

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

def update_skim_parameters():
    """
    Generate skim parameter spec files from templates.
    """

    # Based on toggles from input_configuration, remove modes if not used
    # from user_class and demand matrix list in skim_parameters input folder.

    keywords = []
    # AV is not implemented yet
    #if not include_av:
    #    keywords.append('av_')
    if not include_tnc:  ##########################################################################################
        keywords.append('tnc_')
    # delivery truck not included (Light truck)
    #if not include_delivery:
    #    keywords.append('delivery_')

    root_path = os.path.join(os.getcwd(),r'inputs/skim_params')

    # Remove unused modes from demand_matrix_dictionary
    with open(os.path.join(root_path, 'templates/demand_matrix_dictionary_template.json')) as template_file, open(os.path.join(root_path, 'demand_matrix_dictionary.json'), 'w') as newfile: 
        for line in template_file:
            if not any(keyword in line for keyword in keywords):
                newfile.write(line)

    user_class = json.load(open(os.path.join(root_path, 'templates/user_classes_template.json')))
    rows_to_be_removed = []
    # never modify a list while enumerating it through. Keep the indexes first.
    for idx, row in enumerate(user_class['Highway']):
        for keyword in keywords:
            if keyword in row['Name']:
                rows_to_be_removed.append(idx)

    # instead of deleting what we do not need, update the list with what we need
    user_class['Highway'] = [row for idx, row in enumerate(user_class['Highway']) if idx not in rows_to_be_removed]

    with open(os.path.join(root_path, 'user_classes.json'), 'w') as file:
        file.write(json.dumps(user_class, indent = 4))

    ## SC will create a few json files for skimming, because SC will run TNC trip tables explicitly on network and save TNC
    #  link volumes in extra attributes. At this moment, we do not see the need for such detailed information. 
    # So we decide to run the TNC assignment combined with regular auto mode. 
    # therefore, origional json files for skimming still work for this purpose.


def update_daysim_modes():
    """
    Apply settings in input_configuration to daysim_configuration and roster files:

    include_tnc: PaidRideShareModeIsAvailable,
    include_av: AV_IncludeAutoTypeChoice,
    tnc_av: AV_PaidRideShareModeUsesAVs 
    """

    # Store values from input_configuration in a dictionary:
    # av_settings = ['include_av', 'include_tnc', 'tnc_av']
    #av_settings = ['include_tnc']

    #daysim_dict = {
    #    'AV_IncludeAutoTypeChoice': 'include_av',
    #    'AV_UseSeparateAVSkimMatricesByOccupancy': 'include_av',    # Must be updated or causes issues with roster 
    #    'PaidRideShareModeIsAvailable':'include_tnc',
    #    'AV_PaidRideShareModeUsesAVs': 'tnc_av',
    #}

    #daysim_dict = {
    #    'PaidRideShareModeIsAvailable':'include_tnc'
    #}

    #mode_config_dict = {}    
    #for setting in av_settings:
    #    mode_config_dict[setting] = globals()[setting]
  
    ## Copy temp file to use 
    #daysim_config_path = os.path.join(os.getcwd(),'daysim_configuration_template.properties')
    #new_file_path = os.path.join(os.getcwd(),'daysim_configuration_template_tmp.properties')

    #with open(daysim_config_path) as template_file, open(new_file_path, 'w') as newfile:
    #    for line in template_file:
    #        if any(value in line for value in daysim_dict.keys()):
    #            var = line.split(" = ")[0]
    #            line = var + " = " + str(mode_config_dict[daysim_dict[var]]).lower() + "\n"
    #            newfile.write(line)
    #        else:
    #            newfile.write(line)

    ## Replace the original daysim_configuration_template file with the updated version
    #try:
    #    os.remove(daysim_config_path)
    #    os.rename(new_file_path, daysim_config_path)
    #except OSError as e:  ## if failed, report it back to the user ##
    #    print('Error: ' + e.filename + ' - ' + e.strerror)

    # Write Daysim roster and roster-combination files from template
    # Exclude AV alternatives if not included in scenario

    df = pd.read_csv(r'inputs/model/templates/bkr_roster_template.csv')
    # AV is not implemented yet.
    #if not include_av:     # Remove AV from mode list
    #    df = df[-df['mode'].isin(['av1','av2','av3'])]
    if not include_tnc_to_transit:    # remove TNC-to-transit from potential path types
        df = df[-df['path-type'].isin(filter(lambda x: 'tnc' in x, df['path-type'].unique()))]
    #if not include_knr_to_transit:
    #    df = df[-df['path-type'].isin(filter(lambda x: 'knr' in x, df['path-type'].unique()))]
    df.fillna('null').to_csv(r'inputs/model/bkr_roster.csv',index=False)

    df = pd.read_csv(r'inputs/model/templates/bkr-roster.combinations_template.csv', index_col='#')
    # AV is not implemented yet
    #if not include_av:
    #    df[['av1','av2','av3']] = 'FALSE'
    if not include_tnc:
        df = df[~df.index.str.contains('-tnc')]

    # Adjust KNR path types
    # KNR is not implemented yet
    #if not include_knr_to_transit:
    #    df.loc[['ferry-knr'],'transit'] = 'FALSE'
    if include_tnc and (not include_tnc_to_transit):
        df.loc[['local-bus-tnc','light-rail-tnc'],'transit'] = 'FALSE'
    df.to_csv(r'inputs/model/bkr-roster.combinations.csv')


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

def get_current_branch():  
    try:
        branch_match = subprocess.check_output(['git', 'rev-parse', '--symbolic-full-name', 'HEAD']).decode().strip()
    except:
        branch_match = 'no git is found.'  
  
    if branch_match == "HEAD":
            return None
    else:
        return os.path.basename(branch_match) 

def update_taz_accessibility_file(horizon_year):
    df = pd.read_csv(r'inputs/model/templates/TAZIndex_template.txt', sep ='\t')
    if int(horizon_year) > 2023:
        taz_subarea_df = pd.read_csv(r'inputs/subarea_definition/TAZ_subarea.csv')
        df = df.merge(taz_subarea_df[['BKRCastTAZ', 'Jurisdiction']], left_on = 'Zone_id', right_on = 'BKRCastTAZ', how = 'left')
        df.loc[df['Jurisdiction'] == 'BELLEVUE', 'Dest_eligible'] = 1
        df.drop(columns = ['BKRCastTAZ', 'Jurisdiction'], inplace = True)   
    
    df.to_csv(r'inputs/model/TAZIndex.txt', index = False, sep = '\t')                                             