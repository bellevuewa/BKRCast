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

#!python.exe
# BKRCast Model Runner
#
# 5/11/2021
# before model run starts, check if project_folder is pointing to the current directory
# if not, it is an error that has to be fixed. 
# ===========================

# 10/25/2021
# modified to be compatible with python 3

import os
import sys
import datetime
import subprocess
import json
from shutil import copy2 as shcopy
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import logcontroller
import random
import datetime
import pandas as pd
import shutil 
from input_configuration import *
from emme_configuration import *
from data_wrangling import *

@timed
def accessibility_calcs():
    copy_accessibility_files()

    if run_update_parking:
        if base_year == model_year:
            print("----- This is a base-year analysis. Parking parcels are NOT being updated! Input for 'run_update_parking' is over-ridden. -----")
        else:
            print('Starting to update UrbanSim parcel data with 4k parking data file')
            returncode = subprocess.call([sys.executable,
                                      'scripts/utils/update_parking.py', base_inputs])
            if returncode != 0 and returncode != 3221225477:
                print('Update Parking failed')
                sys.exit(1)
            print('Finished updating parking data on parcel file')

    print('Beginning Accessibility Calculations')
    returncode = subprocess.call([sys.executable, 'scripts/accessibility/accessibility.py'])
    if returncode != 0 and returncode != 3221225477:
        print('Accessibility Calculations Failed For Some Reason :(')
        sys.exit(1)
    print('Done with accessibility calculations')

 
@timed   
def modify_config(config_vals):
    script_path = os.path.abspath(__file__)
    script_dir = os.path.split(script_path)[0] #<-- absolute dir the script is in
    config_path = "daysim/daysim_configuration.properties"

    abs_config_path_template = os.path.join(script_dir, daysim_configuration_template_file)
    abs_config_path_out =os.path.join(script_dir, config_path)
    
    config_template = open(abs_config_path_template,'r')
    config = open(abs_config_path_out,'w')
  
    try:
        for line in config_template:
            for config_temp, config_update in config_vals:
                if config_temp in line:
                    line = line.replace(config_temp, str(config_update))
            config.write(line)
               
        config_template.close()
        config.close()

    except:
     config_template.close()
     config.close()
     print(' Error creating configuration template file')
     sys.exit(1)
    
def read_attribute_from_daysim_config_template(attr_name, default=""):
    """Extract RawParkAndRideNodePath from config file or fallback to default"""
    try:
        with open(daysim_configuration_template_file, 'r') as f:
            for line in f:
                if line.strip().startswith(attr_name):
                    match = re.search(r"=\s*(.*)", line)
                    if match:
                        return match.group(1).strip().replace('\\', os.sep)
    except Exception as e:
        print(f"Warning: Could not read config file ({e}). Using default path.")
    print(f"RawParkAndRideNodePath not found. Using default: {default}")
    return default


@timed
def build_shadow_only(include_tnc_mode):
     for shad_iter in range(0, len(shadow_work)):
        daysim_config_update = [("$SHADOW_PRICE", "true"), ("$INCLUDE_TNC", str(include_tnc_mode)), ("$SAMPLE", shadow_work[shad_iter]), ("$RUN_ALL", "false")]
        #use operating cost 0.36 after 2044, otherwise 0.20.
        if int(model_year) >= 2044:
            daysim_config_update.append(("$OP_COST", 0.36))
        else:
            daysim_config_update.append(("$OP_COST", 0.20))
        modify_config(daysim_config_update)
        logger.info("Start of%s iteration of work location for shadow prices", str(shad_iter))
        returncode = subprocess.call('daysim/Daysim.exe -c daysim/daysim_configuration.properties')

        if returncode != 0 and returncode != 3221225477:
            logger.info(f'Shadow pricing crashed unexpectedly. The return code is {returncode}')
            sys.exit(1)
        logger.info(f"End of {shad_iter} iteration of work location for shadow prices")

        returncode = subprocess.call([sys.executable, 'scripts/utils/shadow_pricing_check.py'])
        shadow_con_file = open('inputs/shadow_rmse.txt', 'r')
        rmse_list = shadow_con_file.readlines()
        iteration_number = len(rmse_list)

        current_rmse = float(rmse_list[iteration_number - 1].rstrip("\n"))
        if current_rmse < shadow_con:
            print("done with shadow prices")
            shadow_con_file.close()
            return

@timed
def daysim_assignment(iteration):

     ### RUN DAYSIM ################################################################
     if run_daysim:
         logger.info(f"Start of {iteration} iteration of Daysim")

         #run daysim
         returncode = subprocess.call('daysim/Daysim.exe -c daysim/daysim_configuration.properties')
         if returncode != 0 and returncode != 3221225477:
             logger.info(f"daysim crashed unexpectedly. The return code is {returncode}")
             sys.exit(1)
         logger.info(f"End of {iteration} iteration of Daysim")

@timed
def run_all_summaries():

   if run_bkrcast_summary:
      if int(model_year) <= 2023:
        subprocess.call([sys.executable, 'scripts/summarize/calibration/SCsummary_2013.py'])
      else:
        subprocess.call([sys.executable, 'scripts/summarize/calibration/SCsummary_2023.py'])

def clean_output_folder():
    folders_kept = ['landuse', 'bike'] # subfolders inside outputs
    output_folder = os.path.join(project_folder, 'outputs')

    if not os.path.exists(output_folder):
        print(f"Output folder does not exist: {output_folder}")
        return

    list_directory = os.listdir('outputs')
    for item in list_directory:
        full_path = os.path.join(output_folder, item)
        if os.path.isfile(full_path):
            os.remove(full_path)
        elif os.path.isdir(full_path) and (not(item in folders_kept)):
            shutil.rmtree(full_path)
                
                
##################################################################################################### ###################################################################################################### 
# Main Script:
def main():
    norm_proj_dir = os.path.normcase(project_folder)
    cur_dir = os.getcwd()
    if norm_proj_dir != os.path.normcase(cur_dir):
        print('***Warning***')
        print('The project_folder is ' + project_folder)
        print('The current directory is ' + cur_dir)
        print('They do not match. Please reconcile the difference first.')
        exit(-1)

## SET UP INPUTS ##########################################################

    if not os.path.exists('outputs'):
        os.makedirs('outputs')

    if include_tnc and run_daysim:
        include_tnc_mode = 'true'
    else:
        include_tnc_mode = 'false'


    # delete everything inside outputs/ folder, except accessibility outputs which resides in landuse subfolder.
    clean_output_folder()    
    build_output_dirs()
    update_daysim_modes()
    update_skim_parameters()
    update_taz_accessibility_file(model_year)    

    # generate the master park and ride file
    pnr_name = read_attribute_from_daysim_config_template('RawParkAndRideNodePath', 'inputs/pnr/p_r_nodes.csv')
    generate_pr_node_file(master_PnR_file, pnr_name, int(model_year))

    print('adding military jobs to regular jobs')
    print('adding JBLM workers to external workers')
    print('adjusting non-work externals')
    print('creating ixxi file for Daysim')
    returncode = subprocess.call([sys.executable, 'scripts/supplemental/create_ixxi_work_trips.py'])
    if returncode != 0 and returncode != 3221225477:
        print('Military Job loading failed')
        sys.exit(1)
    print('military jobs loaded')

    if run_accessibility_calcs:
        accessibility_calcs()

    if run_cumulative_slopes:
        logger.info('Running culmulative slope calculation')
        returncode = subprocess.call([sys.executable, 'scripts/bikes/calculate_cumulative_slopes_for_bike.py']) 
        if returncode != 0 and returncode != 3221225477:
            print('Cumulative slope calculation failed')
            sys.exit(1)
            
    # Check all inputs have been created or copied
    check_inputs()

    logger.info(("Run Daysim Only: %s" % str(model_year)))
    time_start = datetime.datetime.now()
    logger.info("starting run %s" % str((time_start)))

    # IF BUILDING SHADOW PRICES, UPDATING WORK AND SCHOOL SHADOW PRICES
    # 3 daysim iterations
    build_shadow_only(include_tnc_mode)

    daysim_config_update = [("$SHADOW_PRICE" ,"true"), ("$INCLUDE_TNC", str(include_tnc_mode)), ("$SAMPLE", 1), ("$RUN_ALL", "true")]
    # use new operating cost 0.36 after 2044, otherwise use 0.2 
    if int(model_year) >= 2044:
        daysim_config_update.append(("$OP_COST", 0.36))
    else:
        daysim_config_update.append(("$OP_COST", 0.20))

    modify_config(daysim_config_update)

    daysim_assignment('1st')
            
### SUMMARIZE
### ##################################################################
    run_all_summaries()

#### ALL DONE
#### ##################################################################
    clean_up()

    print('###### OH HAPPY DAY!  ALL DONE. GO GET A ' + random.choice(good_thing))

if __name__ == "__main__":
    logger = logcontroller.setup_custom_logger('main_logger')
    logger.info('------------------------Run Daysim Only----------------------------------------------')
    start_time = datetime.datetime.now()
    branch = get_current_branch()
    commit_hash = get_current_commit_hash()
    commit_info = f'BKRCast commit: {commit_hash}'
    branch_info = f'BKRCast Branch: {branch}'
    logger.info(branch_info)
    logger.info(commit_info)

    main()

    end_time = datetime.datetime.now()
    elapsed_total = end_time - start_time
    logger.info('------------------------RUN ENDING_----------------------------------------------')
    logger.info('TOTAL RUN TIME %s'  % str(elapsed_total))
