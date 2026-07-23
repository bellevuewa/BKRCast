import os, sys
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
import pandas as pd
import json
import datetime
import getopt
from EmmeProject import EmmeProject
import data_wrangling
import input_configuration as input_config
import emme_configuration as emme_config

'''
 7/22/2026
 This script is used to calculate transit travel time for each line segment defined in the input json file.
 The output file is saved in outputs/summary/{scenario_name}_transit_travel_time_results.xlsx.
 The default input json file is inputs/skim_params/transit_travel_time_selection.json, which contains the line segments to be processed.

'''

def help():
    print(' This script is used to calculate transit travel time for each line segment defined in the input json file.')
    print(' The output file is saved in outputs/summary/{scenario_name}_transit_travel_time_results.xlsx.')
    print(' The default input json file is inputs/skim_params/transit_travel_time_selection.json, which contains the line segments to be processed.')
    print(' The stop location lookup file is inputs/skim_params/stop_location_lookup.csv, which contains the stop id and stop name mapping.')
    print()
    print(' python transit_travel_time_calculation.py -h -s scenario_id -i transit_line_file')
    print('    -h: help')
    print('    -s: scenario id, default is 1002')
    print('    -i: transit line json file, default is inputs/skim_params/transit_travel_time_selection.json')

def main():
    scenario_id = 1002    
    tod = "PM"
    transit_line_file = os.path.join(os.getcwd(), "inputs/skim_params", 'transit_travel_time_selection.json')
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hs:i:')
    except getopt.GetoptError:
        help()
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-i':
            transit_line_file = str(arg) # need to be an absolute path
        elif opt == '-s':
            scenario_id = int(arg)        

    # Load the input json file and stop location lookup file
    input_dicts = json.load(open(transit_line_file))
    stops_df = pd.read_csv('inputs/skim_params/stop_location_lookup.csv')

    tod_results = []
    my_project = EmmeProject(emme_config.network_summary_project)
    for key, value in emme_config.sound_cast_net_dict.items(): 
        my_project.change_active_database(key)
        my_project.set_primary_scenario(scenario_id)

        print(f"Processing {value} scenario {scenario_id}...")
        for route, line_segs in input_dicts.items():
            if route == 'metadata':
                continue

            for segment in line_segs:
                start_node = segment["start_id"]
                end_node = segment["end_id"]
                line_id, travel_time = my_project.find_transit_travel_time_by_route_and_node_pair(route, start_node, end_node)
                if line_id is not None:
                    tod_results.append({
                        'route': route,
                        'line_id': line_id,
                        'start_node': start_node,
                        'end_node': end_node,
                        'travel_time': travel_time,
                        'tod': value
                    })
                else:
                    print(f'No line found for route: {route}, Start Node: {start_node}, End Node: {end_node}')

    results_df = pd.DataFrame(tod_results)
    # Pivot the results to have separate columns (travel time) for each time of day
    results_wide = results_df.pivot_table(index=['route', 'line_id', 'start_node', 'end_node'], columns='tod', 
                                          values='travel_time', aggfunc="first").reset_index()
    results_wide.columns.name = None

    # Merge the stop names into the results dataframe
    results_wide = results_wide.merge(stops_df[['stop_id', 'stop_name']], left_on='start_node', right_on='stop_id', how='left')
    results_wide.rename(columns={'stop_name': 'start'}, inplace=True)
    results_wide.drop(columns=['stop_id'], inplace=True)
    results_wide = results_wide.merge(stops_df[['stop_id', 'stop_name']], left_on='end_node', right_on='stop_id', how='left')
    results_wide.rename(columns={'stop_name': 'end'}, inplace=True)
    results_wide.drop(columns=['stop_id'], inplace=True)

    my_project.closeDesktop()

    with pd.ExcelWriter(os.path.join(input_config.report_summary_output_location, f'{input_config.scenario_name}_transit_travel_time_results_{scenario_id}.xlsx'), engine='xlsxwriter') as writer:
        workbook = writer.book
        wksheet = workbook.add_worksheet('readme')
        wksheet.write(0, 0, str(datetime.datetime.now()))
        wksheet.write(1, 0, 'model folder')
        wksheet.write(1, 1, input_config.project_folder)
        wksheet.write(2, 0, f'scenario id')
        wksheet.write(2, 1, f'{scenario_id}')
        wksheet.write(3, 0, f'Line travel time selection file')
        wksheet.write(3, 1, f'{transit_line_file}')

        results_wide.to_excel(writer, index=False, sheet_name='transit_travel_times')

if __name__ == "__main__":
    run_context = os.getenv('RUN_CONTEXT') # chained if this script is called from another script, otherwise it is standalone
    if run_context == 'chained':
        meta_data = False
    else:
        meta_data = True

    logger, start_time = data_wrangling.open_main_logger(meta_data, 'Data Processing')
    logger.info(f"Running script: {os.path.basename(__file__)} %s", " ".join(sys.argv[1:]))
    main()
    end_time = datetime.datetime.now()
    elapsed_total = end_time - start_time
    logger.info(f'Total run time: {elapsed_total}')