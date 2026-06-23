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

import os,sys
import subprocess
import inro.emme.desktop.app as app
import json
import re
from shutil import copy2 as shcopy
import inro.emme.database.emmebank as _eb
import shutil
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"inputs", "skim_params"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),"scripts", 'accessibility'))
import accessibility_configuration as access_config
from input_configuration import *
from logcontroller import *
from emme_configuration import *
import pandas as pd

import numpy as np
import h5py

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
        shutil.copytree(daysim_code, 'daysim', dirs_exist_ok=True)
    except Exception as ex:
        template = "An exception of type {0} occured. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)
        sys.exit(1)

@timed
def copy_accessibility_files():
    if not os.path.exists('inputs/accessibility'):
        os.makedirs('inputs/accessibility')
    

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
        emmebank.use_engineering_notation = False   # do not use engr notation     
        scenario = emmebank.create_scenario(1002)
        network = scenario.get_network()
        #need to have at least one mode defined in scenario. Real modes are imported in network_importer.py
        network.create_mode('AUTO', 'a')
        scenario.publish_network(network)
        emmebank.dispose()

@timed
def setup_emme_project_folders():
    from pathlib import Path
    tod_dict = text_to_dictionary('time_of_day')
    tod_list = list(set(tod_dict.values()))

    if os.path.exists(os.path.join('projects')):
        print('Delete Project Folder')
        shutil.rmtree('projects')

    # Create master project, associate with all tod emmebanks
    emmeproject = app.create_project('projects', master_project)
    desktop = app.start_dedicated(False, modeller_initial, emmeproject)
    data_explorer = desktop.data_explorer()
    todpath = []
    for tod in tod_list:        
        relative_emme_path = 'Banks/' + tod + '/emmebank'
        todpath.append(relative_emme_path)
        database = data_explorer.add_database(relative_emme_path)
    #open the last database added so that there is an active one
    database.open()
    desktop.project.save()
    desktop.close()

    # change absolute emmebank path to relative path
    print(f'apply relative path in {emmeproject}')
    old_emme_path = Path(project_folder) / relative_emme_path
    with open(emmeproject, 'r') as f:
        contents = f.read()

    for tod_relatice_path in todpath:
        old_emme_path = Path(project_folder) / tod_relatice_path
        relative_mbank = os.path.relpath(tod_relatice_path, start=os.path.dirname(emmeproject))
        print(relative_mbank)
        contents = contents.replace(old_emme_path.as_posix(), relative_mbank)
    with open(emmeproject, 'w') as f:
        f.write(contents)
          

    # Create time of day projects, associate with emmebank
    tod_list.append('TruckModel') 
    tod_list.append('Supplementals')
    # if daily databank folder exists, add 'Daily to tod_list
    if os.path.exists('Banks/Daily'):
        print('daily bank exists')
        tod_list.append('Daily')

    for tod in tod_list:
        emmeproject = app.create_project('projects', tod)
        desktop = app.start_dedicated(False, modeller_initial, emmeproject)
        data_explorer = desktop.data_explorer()
        relative_emme_path = 'Banks/' + tod + '/emmebank'
        database = data_explorer.add_database(relative_emme_path)
        database.open()
        desktop.project.save()
        # print(emmeproject)
        desktop.close()

        print(f'apply relative path in {emmeproject}')
        # change absolute emmebank path to relative path
        old_emme_path = Path(project_folder) / relative_emme_path
        with open(emmeproject, 'r') as f:
            contents = f.read()
        relative_mbank = os.path.relpath(relative_emme_path, start=os.path.dirname(emmeproject))
        print(relative_mbank)
        contents = contents.replace(old_emme_path.as_posix(), relative_mbank)
        with open(emmeproject, 'w') as f:
            f.write(contents)
        
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
    shutil.copytree(base_inputs+'/networks','inputs/networks', dirs_exist_ok=True)
    print('  counts..')
    shutil.copytree(base_inputs+'/observed','inputs/observed', dirs_exist_ok=True)
    print('  extra attributes..')
    shutil.copytree(base_inputs+'/extra_attributes','inputs/extra_attributes', dirs_exist_ok=True)
    print('  tolls..')
    shutil.copytree(base_inputs+'/tolls','inputs/tolls', dirs_exist_ok=True)
    print('  vdfs..')
    shutil.copytree(base_inputs+'/vdfs','inputs/vdfs', dirs_exist_ok=True)
    print('  intraZonals..')
    shutil.copytree(base_inputs+'/IntraZonals','inputs/IntraZonals', dirs_exist_ok=True)
    print('  fare..')
    shutil.copytree(base_inputs+'/Fares','inputs/Fares', dirs_exist_ok=True)
    print('  trucks..')
    shutil.copytree(base_inputs+'/trucks','inputs/trucks', dirs_exist_ok=True)
    print('  accessibility..')
    shutil.copytree(base_inputs+'/accessibility','inputs/accessibility', dirs_exist_ok=True)  
    #print('  supplemental..')
    #dir_util.copytree(base_inputs+'/supplemental','inputs/supplemental')
    print('  land use..')
    shutil.copytree(base_inputs+'/landuse','inputs/landuse', dirs_exist_ok=True)
    shutil.copytree(base_inputs+'/popsim','inputs/popsim', dirs_exist_ok=True)


@timed          
def clean_up():
    delete_files = ['working\\household.bin', 'working\\household.pk', 'working\\parcel.bin',
                   'working\\parcel.pk', 'working\\parcel_node.bin', 'working\\parcel_node.pk', 'working\\park_and_ride.bin',
                   'working\\park_and_ride_node.pk', 'working\\person.bin', 'working\\person.pk', 'working\\zone.bin',
                   'working\\zone.pk']

    if (delete_parcel_data):
        delete_files.extend(['inputs\\accessibility\\'+ access_config.parcels_file_name, access_config.output_parcels])
    
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

@timed
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

    if not include_rec_bike:
        keywords.append('recb')                
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
    rows_to_be_removed = []
    for idx, row in enumerate(user_class['Bike']):
        for keyword in keywords:
            if keyword in row['Name']:
                rows_to_be_removed.append(idx)
    user_class['Bike'] = [row for idx, row in enumerate(user_class['Bike']) if idx not in rows_to_be_removed]


    with open(os.path.join(root_path, 'user_classes.json'), 'w') as file:
        file.write(json.dumps(user_class, indent = 4))

    ## SC will create a few json files for skimming, because SC will run TNC trip tables explicitly on network and save TNC
    #  link volumes in extra attributes. At this moment, we do not see the need for such detailed information. 
    # So we decide to run the TNC assignment combined with regular auto mode. 
    # therefore, origional json files for skimming still work for this purpose.

@timed
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
        branch_match = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], stderr = subprocess.DEVNULL).decode().strip()
    except:
        branch_match = 'no git is found.'  
  
    if branch_match == "HEAD":
            return None
    else:
        return os.path.basename(branch_match) 
    
def get_current_computer_name():
    import socket
    return socket.gethostname()

def update_taz_accessibility_file(horizon_year):
    df = pd.read_csv(r'inputs/model/templates/TAZIndex_template.txt', sep ='\t')
    if int(horizon_year) > 2023:
        taz_subarea_df = pd.read_csv(r'inputs/subarea_definition/TAZ_subarea.csv')
        df = df.merge(taz_subarea_df[['BKRCastTAZ', 'Jurisdiction']], left_on = 'Zone_id', right_on = 'BKRCastTAZ', how = 'left')
        df.loc[df['Jurisdiction'] == 'BELLEVUE', 'Dest_eligible'] = 1
        df.drop(columns = ['BKRCastTAZ', 'Jurisdiction'], inplace = True)   
    
    df.to_csv(r'inputs/model/TAZIndex.txt', index = False, sep = '\t')      

def balance_trips(df, home_based, trip_purposes, balanced_to):
    """ Balance trips to productions or attractions."""
    # home_based = 'hb' or 'nhb'
    if balanced_to == 'pro':
        to_balance = 'att'
        
    else:
        to_balance = 'pro'
        
    for purposes in trip_purposes:
        total_to_match = sum(df[home_based + purposes + balanced_to])
        total_to_balance = sum(df[home_based+ purposes + to_balance])
        ratio = total_to_match / total_to_balance
        df[home_based + purposes + to_balance] = df[home_based + purposes + to_balance] * ratio
    
    return df

def load_skims(skim_file_loc, mode_name, divide_by_100=False):
    ''' Loads H5 skim matrix for specified mode. '''
    with h5py.File(skim_file_loc, "r") as f:
        skim_file = f['Skims'][mode_name][:]
    # Divide by 100 since decimals were removed in H5 source file through multiplication
    if divide_by_100:
        return skim_file.astype(float)/100
    else:
        return skim_file

def assign_nodes_to_dataset(dataset, network, column_name, x_name, y_name):
    """Adds an attribute node_ids to the given dataset."""
    dataset[column_name] = network.get_node_ids(dataset[x_name].values, dataset[y_name].values)

def process_net_attribute(network, attr, fun):
    print("Processing %s" % attr)
    newdf = None
    for dist_index, dist in access_config.distances.items():        
        res_name = "%s_%s" % (re.sub("_?p$", "", attr), dist_index) # remove '_p' if present
        aggr = network.aggregate(dist, type=fun, decay="exp", name=attr)
        if newdf is None:
            newdf = pd.DataFrame({res_name: aggr, "node_ids": aggr.index.values})
        else:
            newdf[res_name] = aggr
    return newdf

def load_parcel_data(parcel_path):
    parcels = pd.read_csv(parcel_path, sep = " ", index_col = None )
    #capitalize field names to avoid errors
    parcels.columns = [i.upper() for i in parcels.columns]
    #check for missing data!
    for col_name in parcels.columns:
        # daysim does not use EMPRSC_P
        if col_name != 'EMPRSC_P':
            if parcels[col_name].sum() == 0:
                print(col_name + ' column sum is zero! Exiting program.')
                sys.exit(1)

    # # not using. causes bug in daysim (copied from soundcast)
    # parcels['APARKS'] = 0
    # parcels['NPARKS'] = 0
    return parcels    

def load_parcel_data_without_JBLM_jobs(parcel_path):
    """
    return a parcel file without JBLM jobs, in data frame.
    """
    parcels_df = pd.read_csv(parcel_path, sep = " ", index_col = None )
    parcels_df.columns = [i.upper() for i in parcels_df.columns]
    #check for missing data!
    for col_name in parcels_df.columns:
        # daysim does not use EMPRSC_P
        if col_name != 'EMPRSC_P':
            if parcels_df[col_name].sum() == 0:
                print(col_name + ' column sum is zero! Exiting program.')
                sys.exit(1)   

    df_psrc = pd.read_csv(os.path.join(input_folder_for_supplemental, 'BKR_zones.csv'))
    jblm_tazs = df_psrc.loc[df_psrc['jblm'] == 1, 'BKRCastTAZ'].unique().tolist()

    # remove JBLM parcels
    job_columns = [col for col in parcels_df.columns if col.startswith('EMP')]
    parcels_df.loc[parcels_df['TAZ_P'].isin(jblm_tazs), job_columns] = 0
    return parcels_df

def build_pandana_network():
    import pandana as pdna    
    # nodes must be indexed by node_id column, which is the first column
    all_street_nodes = pd.read_csv(access_config.nodes_file_name, index_col = 'node_id')
    all_street_links = pd.read_csv(access_config.links_file_name, index_col = None )
    # get rid of circular links
    all_street_links = all_street_links.loc[(all_street_links.from_node_id != all_street_links.to_node_id)]
    # assign impedance
    imp = pd.DataFrame(all_street_links.Shape_Length)
    imp = imp.rename(columns = {'Shape_Length':'distance'})

    all_street_links['from_node_id'] = all_street_links['from_node_id'].astype('int')
    all_street_links['to_node_id'] = all_street_links['to_node_id'].astype('int')

    # create pandana network
    net = pdna.network.Network(all_street_nodes.x, all_street_nodes.y, all_street_links.from_node_id, all_street_links.to_node_id, imp)
    for dist in access_config.distances:
        net.precompute(dist)

    return net, all_street_links, all_street_nodes        

@timed
def generate_pr_node_file(input_csv, output_csv, year):
    # Load input CSV
    df = pd.read_csv(input_csv)

    # Check required columns exist
    required_columns = ['Project_Year', 'Imp_Capacity', '2023_Capacity']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing expected column from the master pnr file: {col}")

    # Apply the capacity rule
    df['Capacity'] = df.apply(
        lambda row: row['Imp_Capacity'] if year >= row['Project_Year'] else row['2023_Capacity'],
        axis=1
    )
    df['Cost'] = 0

    # Drop unwanted columns
    columns_to_drop = ['2023_Capacity', 'Project_Year', 'New_Spaces', 'Imp_Capacity', 'Source']
    df.drop(columns=[col for col in columns_to_drop if col in df.columns], inplace=True)

    """Ensure that the output path is inside a 'pnr' folder"""
    output_csv = output_csv.lstrip(".\\/")
    output_path = os.path.dirname(output_csv)
    if output_path:
        os.makedirs(output_path, exist_ok=True)

    # Save output CSV
    # the column order is important for daysim. Last two columns are not used in daysim
    # the order is: NodeID, ZoneID, XCoord, YCoord, Capacity, Cost, Description, EMME_Description
    df[['NodeID', 'ZoneID', 'XCoord', 'YCoord', 'Capacity', 'Cost', 'Description', 'EMME_Description']].to_csv(output_csv, index=False)
    print(f"PnR file for {year} is {output_csv}")

def calculate_daysim_WFH_constant(wfh_percent):
    '''
    Calculate the Daysim WFH constant based on the given WFH percentage assumption.
    The formula is derived from the relationship between WFH percentage and the constant.
    WorkAtHome_AlternativeSpecificConstant = ln(wfh_percent / 57.18%) / 0.4874
    '''
    constant = np.log(wfh_percent / 0.5718) / 0.4874
    # round to 1 decimal places to be consistent with Daysim models we have done.
    # but should be revised to three decimal places in the next round of model update.
    return float(round(constant, 1))


def od_list_to_matrix_numpy(file_path, skip_headerlines = 5, n_zones=None):
    ''' Convert an OD list in a text file to a matrix. The text file should have three columns: origin, destination, and volume.
    skip_headerlines: number of lines to skip at the beginning of the file. Default is 5.
    n_zones: number of zones in the matrix. If None, it will be determined by the maximum zone number in the origin and destination columns.
    return:
    matrix: a numpy array of shape (n_zones, n_zones) with the OD volumes.
    df: a pandas dataframe with the same data as the matrix, with zone numbers as index and columns. The index and column names start from 1 to n_zones.
    '''

    with open(file_path, 'r') as f:
        lines = f.readlines()

    if len(lines) <= skip_headerlines:
        # print(f"No data found in {file_path} after skipping {skip_headerlines} header lines.")
        return None, pd.DataFrame()
    
    data = np.loadtxt(file_path, skiprows=skip_headerlines)

    if data.size == 0:
        return None, pd.DataFrame()

    if data.ndim == 1:
        data = data.reshape(1, -1)

    origins = data[:, 0].astype(int)
    dests = data[:, 1].astype(int)
    vols = data[:, 2]

    # skip zero volumes
    mask = vols != 0
    origins = origins[mask]
    dests = dests[mask]
    vols = vols[mask]

    # determine matrix size
    if n_zones is None:
        n_zones = int(max(origins.max(), dests.max()))

    # create matrix
    matrix = np.zeros((n_zones, n_zones))

    # fill matrix
    matrix[origins - 1, dests - 1] = vols

    unique_origins = np.unique(origins)
    unique_dests = np.unique(dests)
    filtered_matrix = matrix[np.ix_(unique_origins - 1, unique_dests - 1)]
    df = pd.DataFrame(filtered_matrix, index = unique_origins, columns = unique_dests)
    return matrix, df