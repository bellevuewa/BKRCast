import pandas as pd
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
from input_configuration import *
from emme_configuration import *

## Configuration
start_time = 0
end_time = 0
time_location = 'DEPARTURE'  # 'DEPARTURE' or 'ARRIVAL'
## end configuration

# aggregate trip ends by TAZ and 
# taz: 'otaz' or 'dtaz'
def aggregate_trips_by_taz(df, taz):
    aggregated = pd.DataFrame(df.groupby(taz)['trexpfac'].sum())
    aggregated.reset_index(inplace = True)
    return aggregated   

# Create trip ends by TAZ
def calculate_person_trips_by_taz(df):
    orig_df = aggregate_trips_by_taz(df, 'otaz')
    orig_df.rename(columns = {'trexpfac':'outbound', 'otaz':'taz'}, inplace = True)
    dest_df = aggregate_trips_by_taz(df, 'dtaz')
    dest_df.rename(columns = {'trexpfac':'inbound', 'dtaz':'taz'}, inplace = True)
    person_trips = orig_df.merge(dest_df, on = 'taz', how = 'outer')
    person_trips.fillna(0, inplace = True)
    person_trips.to_csv(os.path.join(project_folder, report_output_location, 'aggregated_person_trips_by_taz.csv'), sep = ',')
    return person_trips

def main():

    trippath = os.path.join(project_folder, report_output_location, '_trip.tsv')
    print 'open ' + trippath
    trips_df = pd.read_csv(trippath, sep = '\t', low_memory = False)
    if (start_time == 0 and end_time == 0):
        selected_trips_df = trips_df
    else:
        if time_location == 'DEPARTURE':
            querystring = 'deptm >= ' + str(start_time) + ' and deptm < ' + str(end_time)
        elif time_location == 'ARRIVAL':
            querystring = 'arrtm >= ' + str(start_time) + ' and arrtm < ' + str(end_time)
        else:
            print "time_location can be only 'DEPARTURE' or 'ARRIVAL'"
            sys.exit(-1)
        selected_trips_df = trips_df.query(querystring)
        print selected_trips_df.shape

    calculate_person_trips_by_taz(selected_trips_df)
    print 'Done'


if __name__ == '__main__':
    main()

