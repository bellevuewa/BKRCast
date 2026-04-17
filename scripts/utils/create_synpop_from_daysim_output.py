import os
import pandas as pd
import sys
import getopt
sys.path.append(os.getcwd())
import input_configuration as input_config

def help():
    print('This script is used to create synthetic population files from the output of the DaySim model.')
    print('It reads the household and person files located in the folder specified by the "report_output_location" variable in the input configuration file.' \
    ' reorders the columns, and saves them as new TSV files.')
    print('The output files will be used by run_bkrcast.py with the "-s" flag.')

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h")
    except getopt.GetoptError as err:
        print(str(err))
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            print('Usage: run_bkrcast.py -s <path_to_synthetic_population_folder>')
            sys.exit()

    hh_person_folder = input_config.report_output_location

    hhs_name = r'_household.tsv'
    persons_name = r'_person.tsv'

    # if the files do not exist, print an error message and exit
    if not os.path.exists(os.path.join(hh_person_folder, hhs_name)):
        print(f'Error: {hhs_name} file not found in {hh_person_folder}. Please check the path and try again.')
        sys.exit(1)
    if not os.path.exists(os.path.join(hh_person_folder, persons_name)):
        print(f'Error: {persons_name} file not found in {hh_person_folder}. Please check the path and try again.')
        sys.exit(1)

    hhs_df = pd.read_csv(os.path.join(hh_person_folder, hhs_name), sep = '\t', low_memory=False)
    persons_df = pd.read_csv(os.path.join(hh_person_folder, persons_name), sep = '\t', low_memory=False)

    parcelid = hhs_df.pop('hhparcel')
    hhs_df.pop('zone_id')
    hhs_df.pop('fraction_with_jobs_outside')
    hhs_df.insert(15, 'hhparcel', parcelid)
    hhs_df.to_csv(os.path.join(hh_person_folder, '_household_reordered.tsv'), sep = '\t', index = False)
    print('Household file processed and saved as _household_reordered.tsv')

    first_cols = ['hhno', 'pno']
    persons_df.pop('id')
    rest_cols = [col for col in persons_df.columns if col not in first_cols]
    persons_df[first_cols + rest_cols].to_csv(os.path.join(hh_person_folder, '_person_reordered.tsv'), sep = '\t', index = False)
    print('Person file processed and saved as _person_reordered.tsv')

    # person_day = "_person_day.tsv"
    # person_day_df = pd.read_csv(os.path.join(hh_person_folder, person_day), sep = '\t')
    # person_day_df.pop('id')
    # person_day_df.pop('household_day_id')
    # person_day_df.pop('person_id')
    # first_cols = ['hhno', 'pno', 'day']
    # rest_cols = [col for col in person_day_df.columns if col not in first_cols]
    # person_day_df[first_cols + rest_cols].to_csv(os.path.join(hh_person_folder, '_person_day_reordered.tsv'), sep = '\t', index = False)

    # household_day = "_household_day.tsv"
    # household_day_df = pd.read_csv(os.path.join(hh_person_folder, household_day), sep = '\t')
    # household_day_df.pop('id')
    # first_cols = ['hhno', 'day']
    # rest_cols = [col for col in household_day_df.columns if col not in first_cols]  
    # household_day_df[first_cols + rest_cols].to_csv(os.path.join(hh_person_folder, '_household_day_reordered.tsv'), sep = '\t', index = False)

    # tours = "_tour.tsv"
    # tours_df = pd.read_csv(os.path.join(hh_person_folder, tours), low_memory=False, sep = '\t')
    # tours_df.pop('id')
    # tours_df.pop('person_day_id')
    # tours_df.pop('person_id')
    # first_cols = ['hhno', 'pno',  'day', 'tour']
    # rest_cols = [col for col in tours_df.columns if col not in first_cols]
    # tours_df[first_cols + rest_cols].to_csv(os.path.join(hh_person_folder, '_tour_reordered.tsv'), sep = '\t', index = False)

    # trips = "_trip.tsv"
    # trips_df = pd.read_csv(os.path.join(hh_person_folder, trips), low_memory=False, sep = '\t')
    # trips_df.pop('id')
    # trips_df.pop('tour_id')
    # trips_df.pop('vot')
    # first_cols = ['hhno', 'pno',  'day', 'tour']
    # rest_cols = [col for col in trips_df.columns if col not in first_cols]
    # trips_df[first_cols + rest_cols].to_csv(os.path.join(hh_person_folder, '_trip_reordered.tsv'), sep = '\t', index = False)

    print('Done')


if __name__ == "__main__":
    main()