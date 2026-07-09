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
import random, getopt
import datetime
import pandas as pd
import shutil
from pathlib import Path
from input_configuration import *
from emme_configuration import *
from data_wrangling import *

@timed
def accessibility_calcs():
    copy_accessibility_files()

    print('Beginning Accessibility Calculations')
    env = os.environ.copy()
    env['RUN_CONTEXT'] = 'chained'
    returncode = subprocess.call([sys.executable, 'scripts/accessibility/accessibility.py'], env=env)
    if returncode != 0 and returncode != 3221225477:
        print('Accessibility Calculations Failed For Some Reason :(')
        sys.exit(1)
    print('Done with accessibility calculations')

@timed    
def build_seed_skims(max_iterations):
    print("Processing skims and paths.")
    time_copy = datetime.datetime.now()
    env = os.environ.copy()
    env['RUN_CONTEXT'] = 'chained'
    returncode = subprocess.call([sys.executable,
        'scripts/skimming/SkimsAndPaths.py', '-i',
        str(max_iterations),
        'build_free_flow_skims'], env=env)
    if returncode != 0 and returncode != 3221225477:
        sys.exit(1)
         
    time_skims = datetime.datetime.now()
    print('###### Finished skimbuilding:', str(time_skims - time_copy))
 
@timed
def import_synthetic_population_from_outside(outside_folder_path: str):
    # This function imports synthetic population data from an outside folder path
    # copy the files from outside_folder_path to inputs/synthetic_population_outside, make the file structure 
    # compatible with the expected input for daysim, and update the daysim template to point to the new paths for synthetic population data. 
    # It also creates a metadata.txt file in the synthetic_population_outside folder to document the source of the data and when it was imported.
    logger.info(f"Synthetic population data from outside folder: {outside_folder_path} is being used. ")
    input_path = Path("inputs/synthetic_population_outside")
    files_to_copy = ['_household.tsv', '_person.tsv']
    for file_name in files_to_copy:
        source_path = Path(outside_folder_path) / file_name
        destination_path = input_path / file_name
        if source_path.exists():
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source_path, destination_path)
            print(f"Copied {file_name} to synthetic_population_outside.")
        else:
            print(f"File {file_name} not found in {outside_folder_path}.")

    # process _household.tsv and _person.tsv to create _household_reordered.tsv and _person_reordered.tsv
    hhs_df = pd.read_csv(input_path / "_household.tsv", sep='\t')
    parcelid = hhs_df.pop('hhparcel')
    hhs_df.pop('zone_id')
    hhs_df.pop('fraction_with_jobs_outside')
    hhs_df.insert(15, 'hhparcel', parcelid) # very important. this column is hard coded in daysim.
    hhs_df.to_csv(input_path / "_household_reordered.tsv", sep = '\t', index = False) 

    persons_df = pd.read_csv(input_path / "_person.tsv", sep='\t')
    first_cols = ['hhno', 'pno']
    persons_df.pop('id')
    rest_cols = [col for col in persons_df.columns if col not in first_cols]
    persons_df[first_cols + rest_cols].to_csv(input_path / "_person_reordered.tsv", sep = '\t', index = False)   

    with open(input_path / "metadata.txt", "w") as metadata_file:
        metadata_file.write(datetime.datetime.now().strftime("Date: %Y-%m-%d %H:%M:%S\n"))
        metadata_file.write(f"Source: {outside_folder_path}\n")
        metadata_file.write("This folder contains synthetic population data imported from an outside source.\n")   
        metadata_file.write("Files:\n")
        metadata_file.write("- _household_reordered.tsv: Reordered household data for Daysim input.\n")
        metadata_file.write("- _person_reordered.tsv: Reordered person data for Daysim input.\n") 

    # Lines to insert
    household_lines = [
        "RawHouseholdPath =  ..\\inputs\\synthetic_population_outside\\_household_reordered.tsv\n",
        "InputHouseholdPath = ..\\outputs\\daysim\\_household_new_input.tsv\n",
        "InputHouseholdDelimiter = 9\n",
        "RawHouseholdDelimiter = 9\n",
    ]

    person_lines = [
        "RawPersonPath = ..\\inputs\\synthetic_population_outside\\_person_reordered.tsv\n",
        "InputPersonPath= ..\\outputs\\daysim\\_person_new_input.tsv\n",
        "InputPersonDelimiter = 9\n",
        "RawPersonDelimiter = 9\n",
    ]

    master_template_path = Path('inputs/model/templates') / "master_daysim_configuration_template.properties"
    template_path = Path('daysim_configuration_template.properties')
    # Read file
    lines = master_template_path.read_text().splitlines(keepends=True)
    
    # update the daysim template with the new paths for synthetic population data
    attr_dict = {
        "ReadHDF5": "false",
        "ShouldRunHouseholdModels": "false",
        "ShouldRunPersonModels": "false"
    }

    new_lines = []
    for line in lines:
        for attr, value in attr_dict.items():
            if line.startswith(attr):
                line = f"{attr} = {value}\n"
                break

        if "ImportHouseholds" in line:
            new_lines.extend(household_lines)

        if "ImportPersons" in line:
            new_lines.extend(person_lines)

        new_lines.append(line)

    with open(template_path, "w") as template_file:
        template_file.write("".join(new_lines))

    logger.info(f"Synthetic population data are saved in {input_path} and daysim template is updated accordingly.")

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
def build_shadow_only(include_tnc_mode, include_wfh_mode):
     wfh_constant = calculate_daysim_WFH_constant(WFH_Percent)
     for shad_iter in range(0, len(shadow_work)):
        daysim_config_update = [("$SHADOW_PRICE", "true"), ("$INCLUDE_TNC", str(include_tnc_mode)), ("$INCLUDE_WFH", str(include_wfh_mode)), ("$WFH_CONSTANT", str(wfh_constant)), ("$SAMPLE", shadow_work[shad_iter]), ("$RUN_ALL", "false")]
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

        returncode = subprocess.call([sys.executable, 'scripts/utils/shadow_pricing_check.py'])
        shadow_con_file = open('inputs/shadow_rmse.txt', 'r')
        rmse_list = shadow_con_file.readlines()
        iteration_number = len(rmse_list)
        current_rmse = float(rmse_list[iteration_number - 1].rstrip("\n"))
        logger.info(f"End of {shad_iter} iteration of work location for shadow prices. RMSE is {current_rmse}.")

        if current_rmse < shadow_con:
            print("done with shadow prices")
            shadow_con_file.close()
            return
        

@timed
def run_truck_supplemental(iteration):

    ### RUN Supplemental Trips
    ##########################################################
    ### Adds external, special generator, and group quarters trips to DaySim
    env = os.environ.copy()
    env['RUN_CONTEXT'] = 'chained'
    if run_supplemental_trips:
        # Only run generation script once - does not change with feedback
        if iteration == 0:
            returncode = subprocess.call([sys.executable,'scripts/supplemental/generation.py'], env=env)
            if returncode != 0 and returncode != 3221225477:
                logger.info(f'Supplemental trip generation crashed unexpectedly. The return code is {returncode}')
                sys.exit(1)

        #run distribution
        returncode = subprocess.call([sys.executable,'scripts/supplemental/distribute_non_work_ixxi.py'], env=env)
        if returncode != 0 and returncode != 3221225477:
            logger.info(f'Distribute_non_work_ixxi.py crashed unexpectedly. The return code is {returncode}')
            sys.exit(1)

        returncode = subprocess.call([sys.executable, 'scripts/supplemental/create_airport_trips.py'], env=env)
        if returncode != 0 and returncode != 3221225477:
            logger.info(f'Airport model crashed unexpectedly. The return code is {returncode}')
            sys.exit(1)


    ### RUN Truck Model ################################################################
    if run_truck_model:
        returncode = subprocess.call([sys.executable,'scripts/trucks/truck_model.py'], env=env)
        if returncode != 0 and returncode != 3221225477:
            logger.info(f'Truck model crashed unexpectedly. The return code is {returncode}')
            sys.exit(1)

                           
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
    
     ### ADD SUPPLEMENTAL TRIPS ####################################################
     run_truck_supplemental(iteration)
    
     #### ASSIGNMENTS ##############################################################
     if run_skims_and_paths:
        logger.info(f"Start of {iteration} iteration of Skims and Paths")
        env = os.environ.copy()
        env['RUN_CONTEXT'] = 'chained'
        returncode = subprocess.call([sys.executable, 'scripts/skimming/SkimsAndPaths.py', '-i', str(iteration)], env=env)
         
        if returncode != 0 and returncode != 3221225477:
            logger.info(f'Skims crashed unexpectedly. The return code from skims and paths is {returncode}')
            sys.exit(1)

        # no need to run recreational bike here. It is run after the last iteration of skims and paths
        returncode = subprocess.call([sys.executable,'scripts/bikes/bike_model.py'], env=env)
        if returncode != 0 and returncode != 3221225477:
            logger.info(f'Bike model crashed unexpectedly. The return code from skims and paths is {returncode}')
            sys.exit(1)

        logger.info(f"End of {iteration} iteration of Skims and Paths")        

@timed
def check_convergence(iteration):
    converge = "not yet"
    if iteration > 0:
        with open('inputs/converge.txt', 'r') as  con_file:
             converge = json.load(con_file)
    return converge

@timed
def run_all_summaries():
    env = os.environ.copy()
    env['RUN_CONTEXT'] = 'chained'

    if run_bkrcast_summary:
        if int(model_year) <= 2023:
            subprocess.call([sys.executable, 'scripts/summarize/calibration/SCsummary_2013.py'], env=env)
        else:
            subprocess.call([sys.executable, 'run_bkrcast_validation.py'], env=env)

    #Create a daily network with volumes. Will add counts and summary emme project. 
    if run_create_daily_bank:
        subprocess.call([sys.executable, 'scripts/summarize/standard/network_summary.py'], env=env)
        subprocess.call([sys.executable, 'scripts/summarize/standard/daily_bank.py'], env=env)

    if run_landuse_summary:
        subprocess.call([sys.executable, 'scripts/summarize/standard/landuse_summary.py'], env=env)
        
    if run_truck_summary:
        subprocess.call([sys.executable, 'scripts/summarize/standard/truck_vols.py'], env=env)

    if run_vmt_summary:
        subprocess.call([sys.executable, 'scripts/summarize/standard/calculate_daily_VMT.py'], env=env)
        
    if run_telecommute_summary:
        subprocess.call([sys.executable, 'scripts/summarize/standard/telecommute_analysis.py'], env=env)

    if run_modeshare_summary:
        for district in ['BelDT', 'Bellevue', 'Kirkland', 'Redmond']:
            subprocess.call([sys.executable, 'scripts/summarize/standard/tour_mode_share_calculator.py', district], env=env)
            subprocess.call([sys.executable, 'scripts/summarize/standard/trip_mode_share_calculator.py', district], env=env)

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
                
def run_recreational_bike():
    logger.info('Running the recreational bike model')
    print('Running the recreational bike as part of the supplemental module')
    print('Calculating accessibility for recreational bike')
    env = os.environ.copy()
    env['RUN_CONTEXT'] = 'chained'
    returncode = subprocess.call([sys.executable, 'scripts/accessibility/bike_accessibility_TAZ.py'], env=env)
    if returncode != 0 and returncode != 3221225477:    
        print('bike_accessibility is was crashed.')
        sys.exit(1)

    print('Generating recreational bike trips')
    returncode = subprocess.call([sys.executable, 'scripts/supplemental/recreational_bike.py'], env=env)
    if returncode != 0 and returncode != 3221225477:
        print('recreational bike generation is crashed.')
        sys.exit(1) 

    print('Assignment recreational bike trips')
    returncode = subprocess.call([sys.executable, 'scripts/bikes/bike_model.py', '-b'], env=env)
    if returncode != 0 and returncode != 3221225477:
        print('recreational bike assignment is crashed.')
        sys.exit(1)

    logger.info('Finished running the recreational bike model')      

def precheck():
    # Check if project_folder is pointing to the current directory
    norm_proj_dir = os.path.normcase(project_folder)
    cur_dir = os.getcwd()
    if norm_proj_dir != os.path.normcase(cur_dir):
        print('***Warning***')
        print('The project_folder is ' + project_folder)
        print('The current directory is ' + cur_dir)
        print('They do not match. Please reconcile the difference first.')
        exit(-1)

    # make sure emme lock file is not present in emme databank folder
    databank_folders = tods.copy()
    databank_folders.extend(['Suplementals', 'TruckModel'])
    for folder in databank_folders:
        emme_lock_file = os.path.join(project_folder, 'Banks', folder, 'emlocki')
        if os.path.exists(emme_lock_file):
            print(f"Error: Emme lock file found in {folder} databank. Please remove the lock file before running the model.")
            exit(-1)

def help():
    print('This is the BKRcast model runner script. It will run the entire BKRcast model from start to finish, including accessibility calculations, Daysim runs, skim building, and summaries.')
    print("")
    print('Usage: run_bkrcast.py -s <path_to_synthetic_population_folder> -h -i <number_of_iterations>')
    print("")
    print('Options:')
    print('-h: Show this help message and exit')
    print('-s: Specify the path to the synthetic population folder that contains _household.tsv and _person.tsv files. ')
    print('    The script util/create_synpop_from_daysim_output.py should be run first to process these files and create new files that are compatible with the expected input for daysim. ')
    print('    This option should be used if you want to skip long term models like auto ownership, transit pass ownership, work and school locations')
    print('    and directly use the synthetic population generated from a previous run of DaySim. If this option is not used, the model will run with the default synthetic population generation process, which includes running the long term models.')
    print('-i: number of iterations to run. Default is 3.')
##################################################################################################### ###################################################################################################### 
# Main Script:
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:s:")
    except getopt.GetoptError as err:
        print(str(err))
        sys.exit(2)

    synthetic_population_folder = ""
    number_of_iterations = 3

    for opt, arg in opts:
        if opt == '-h':
            help()
            print('Usage: run_bkrcast.py -s <path_to_synthetic_population_folder>')
            sys.exit()
        elif opt == '-s':
            synthetic_population_folder = arg
            print(f"Importing synthetic population from: {synthetic_population_folder}")
            
        elif opt == '-i':
            if not arg.isdigit() or int(arg) <= 0:
                print("Error: Number of iterations must be a positive integer.")
                sys.exit(2)
            number_of_iterations = int(arg)
        else:
            print('Unknown option. Use -h for help.')
            sys.exit(2)

    precheck()
## SET UP INPUTS ##########################################################

    if not os.path.exists('outputs'):
        os.makedirs('outputs')

    if include_tnc and run_daysim:
        include_tnc_mode = 'true'
    else:
        include_tnc_mode = 'false'
    
    if include_wfh and run_daysim:
        include_wfh_mode = 'true'
    else:
        include_wfh_mode = 'false'

    # delete everything inside outputs/ folder, except accessibility outputs which resides in landuse subfolder.
    clean_output_folder()    
    build_output_dirs()
    if synthetic_population_folder != "":
        import_synthetic_population_from_outside(synthetic_population_folder) 
    else:
        # copy master daysim template to the project root folder
        shutil.copy(Path('inputs/model/templates') / "master_daysim_configuration_template.properties", "daysim_configuration_template.properties")   
        # remove the inputs/synthetic_population_outside folder if it exists.
        synthetic_population_outside_folder = Path("inputs/synthetic_population_outside")
        if synthetic_population_outside_folder.exists() and synthetic_population_outside_folder.is_dir():
            shutil.rmtree(synthetic_population_outside_folder)
            
    update_daysim_modes()
    update_skim_parameters()
    update_taz_accessibility_file(model_year)    

    if run_copy_input_files:
        copy_large_inputs()
    
    # generate the master park and ride file
    pnr_name = read_attribute_from_daysim_config_template('RawParkAndRideNodePath', 'inputs/pnr/p_r_nodes.csv')
    generate_pr_node_file(master_PnR_file, pnr_name, int(model_year))

    if run_copy_daysim_code:
        copy_daysim_code()

    if run_setup_emme_bank_folders:
        setup_emme_bank_folders()

    if run_setup_emme_project_folders:
        setup_emme_project_folders()

### IMPORT NETWORKS ###############################################################
    env = os.environ.copy()
    env['RUN_CONTEXT'] = 'chained'
    if run_import_networks:
        time_copy = datetime.datetime.now()
        logger.info("Start of network importer")
        returncode = subprocess.call([sys.executable,
        'scripts/network/network_importer.py', base_inputs], env=env)
        logger.info("End of network importer")
        time_network = datetime.datetime.now()
        if returncode != 0 and returncode != 3221225477:
           sys.exit(1)

    print('adding military jobs to regular jobs')
    print('adding JBLM workers to external workers')
    print('adjusting non-work externals')
    print('creating ixxi file for Daysim')
    returncode = subprocess.call([sys.executable, 'scripts/supplemental/create_ixxi_work_trips.py'], env=env)
    if returncode != 0 and returncode != 3221225477:
        print('Military Job loading failed')
        sys.exit(1)
    print('military jobs loaded')

    if run_accessibility_calcs:
        accessibility_calcs()

    if run_cumulative_slopes:
        logger.info('Running culmulative slope calculation')
        returncode = subprocess.call([sys.executable, 'scripts/bikes/calculate_cumulative_slopes_for_bike.py'], env=env)
        if returncode != 0 and returncode != 3221225477:
            print('Cumulative slope calculation failed')
            sys.exit(1)
            
### BUILD OR COPY SKIMS ###############################################################
    if run_skims_and_paths_seed_trips:
        logger.info('Running skim seed trips')
        # run_truck_supplemental(0)
        build_seed_skims(10)
        # no need to run rec bike assignment in seeding trips
        returncode = subprocess.call([sys.executable,'scripts/bikes/bike_model.py'], env=env)
        if returncode != 0 and returncode != 3221225477:
            sys.exit(1)

    # Check all inputs have been created or copied
    check_inputs()


### RUN DAYSIM AND ASSIGNMENT TO CONVERGENCE-- MAIN LOOP ##########################################
    
    if(run_daysim or run_skims_and_paths or run_skims_and_paths_seed_trips):
        wfh_constant = calculate_daysim_WFH_constant(WFH_Percent)        
        for iteration in range(number_of_iterations):
            print("We're on iteration %d" % (iteration))
            logger.info(("We're on iteration %d\r\n" % (iteration)))
            time_start = datetime.datetime.now()
            logger.info("starting run %s" % str((time_start)))

            # IF BUILDING SHADOW PRICES, UPDATING WORK AND SCHOOL SHADOW PRICES
            # 3 daysim iterations
            build_shadow_only(include_tnc_mode, include_wfh_mode)

            daysim_config_update = [("$SHADOW_PRICE" ,"true"), ("$INCLUDE_TNC", str(include_tnc_mode)), ("$INCLUDE_WFH", str(include_wfh_mode)), ("$WFH_CONSTANT", str(wfh_constant)), ("$SAMPLE", 1), ("$RUN_ALL", "true")]
            # use new operating cost 0.36 after 2044, otherwise use 0.2 
            if int(model_year) >= 2044:
                daysim_config_update.append(("$OP_COST", 0.36))
            else:
                daysim_config_update.append(("$OP_COST", 0.20))

            modify_config(daysim_config_update)
            
            ## Run Skimming and/or Daysim
            daysim_assignment(iteration)
           
            converge=check_convergence(iteration)
            if converge == 'stop':
                print("System converged!")
                break

            print('The system is not yet converged. Daysim and Assignment will be re-run.')

    if include_rec_bike:
        run_recreational_bike()
                    
### SUMMARIZE
### ##################################################################
    run_all_summaries()

#### ALL DONE
#### ##################################################################
    clean_up()

    print('###### OH HAPPY DAY!  ALL DONE. GO GET A ' + random.choice(good_thing))

if __name__ == "__main__":
    logger = logcontroller.setup_custom_logger('main_logger')
    logger.info('------------------------NEW RUN STARTING----------------------------------------------')
    start_time = datetime.datetime.now()
    computer_name = get_current_computer_name()
    branch = get_current_branch()
    commit_hash = get_current_commit_hash()
    computer_info = f'BKRCast is running on computer: {computer_name}'
    commit_info = f'BKRCast commit: {commit_hash}'
    branch_info = f'BKRCast Branch: {branch}'
    logger.info(branch_info)
    logger.info(commit_info)
    logger.info(computer_info)

    main()

    end_time = datetime.datetime.now()
    elapsed_total = end_time - start_time
    logger.info('------------------------RUN ENDING_----------------------------------------------')
    logger.info('TOTAL RUN TIME %s'  % str(elapsed_total))
