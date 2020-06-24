import pandas as pd
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from input_configuration import *
from emme_configuration import *
import h5py
import data_wrangling


## Configuration
# studyarea.txt should be placed in the project folder. 
subarea_taz_file = r'Studyarea.txt'

## end configuration

#stime and etime: time in number of minutes after midnight. so 1530 is 930
#time_location = 'DEPARTURE'  # use time as 'DEPARTURE' or 'ARRIVAL'
def select_trips_by_time(trips_df, stime, etime, time_location):
    if (stime == 0 and etime == 0):
        selected_trips_df = trips_df
    else:
        if time_location == 'DEPARTURE':
            querystring = 'deptm >= ' + str(stime) + ' and deptm < ' + str(etime)
        elif time_location == 'ARRIVAL':
            querystring = 'arrtm >= ' + str(stime) + ' and arrtm < ' + str(etime)
        else:
            print "time_location can be only 'DEPARTURE' or 'ARRIVAL'"
            sys.exit(-1)
        selected_trips_df = trips_df.query(querystring)
        print selected_trips_df.shape
    return selected_trips_df

# select trips by persons
# persons_df is required to have an column named 'person_id', in the format of hhno-pno
# person_id will be created in trips_df
def select_trips_by_persons(trips_df, persons_df):
    trips_df['person_id'] = trips_df['hhno'].astype('string') + '-' + trips_df['pno'].astype('string')   
    selected_trips_df = trips_df.merge(persons_df[['person_id']], how = 'inner', on = 'person_id')
    return selected_trips_df

def select_pop_by_taz(taz_subarea_df):
    taz_subarea_df.reset_index(inplace = True)
    hhs, persons = data_wrangling.get_hhs_df_from_synpop()
    selected_hhs = hhs.merge(taz_subarea_df, how = 'inner', left_on = 'hhtaz', right_on = 'TAZ')

    selected_persons = persons.merge(selected_hhs, how = 'inner', left_on = 'hhno', right_on = 'hhno')
    selected_persons['person_id'] = selected_persons['hhno'].astype('string') + '-' + selected_persons['pno'].astype('string')    
    return selected_hhs, selected_persons

def select_trips_by_querystring(trips_df, querystring):
    selected_trips_df = trips_df.query(querystring)
    print selected_trips_df.shape
    return selected_trips_df

def select_auto_and_transit_trips(trips_df):  
    # mode 1 walk 2 bike
    selected_trips = trips_df[trips_df['mode'] >=3]
    return selected_trips

def select_commute_trips(trips_df):
    commute_trips = trips_df[((trips_df['half'] == 1) & (trips_df['dpurp'] == 1)) | ((trips_df['half'] == 2) & (trips_df['opurp'] == 1))]
    return commute_trips

def calculate_trip_metrics(trips_df):
    totaltrips = trips_df['trexpfac'].sum()
    avgtime = trips_df['travtime'].mean()
    mintravtime = trips_df['travtime'].min()
    maxtravtime = trips_df['travtime'].max()
    avgdist = trips_df['travdist'].mean()
    mintravdist = trips_df['travdist'].min()
    maxtravdist = trips_df['travdist'].max()
    output = {'Total Trips': totaltrips, 'Avg TT' : avgtime, 'Min TT' : mintravtime, 'Max TT' : maxtravtime, 'Avg Travel Dist' : avgdist, 'Min Travel Dist' : mintravdist, 'Max Travel Dist' : maxtravdist}
    print output
    return output

def exportTofile(file, dict):
    for key, val in dict.iteritems():
        file.write('%s: %.2f\n'% (key, val))
    
def main():
    trippath = os.path.join(project_folder, report_output_location, '_trip.tsv')
    print 'open ' + trippath
    trips_df = pd.read_csv(trippath, sep = '\t', low_memory = True)
    studyarea_filepath = os.path.join(project_folder, subarea_taz_file)
    taz_subarea_df = pd.read_csv(studyarea_filepath, sep = ',')
    taz_subarea_df = taz_subarea_df.loc[~taz_subarea_df['TAZ'].duplicated()]

    # select hhs and persons who live in the study area
    selected_hhs, selected_persons = select_pop_by_taz(taz_subarea_df)
    # select trips made by selected_persons
    selected_daily_person_trips_df = select_trips_by_persons(trips_df, selected_persons)
    selected_daily_person_auto_transit_trips = select_auto_and_transit_trips(selected_daily_person_trips_df)
    selected_daily_person_auto_transit_commute_trips = select_commute_trips(selected_daily_person_auto_transit_trips)
    
    outputs = {}
    daily_all_metrics = calculate_trip_metrics(selected_daily_person_trips_df)
    outputs.update({'Daily all trips':daily_all_metrics})
    print 'Daily Commute'
    daiy_commute_metrics = calculate_trip_metrics(selected_daily_person_auto_transit_commute_trips)
    outputs.update({'Daily commute trips' : daiy_commute_metrics})
    selected_pm_trips_df = select_trips_by_time(selected_daily_person_trips_df, 930,1110,'DEPARTURE')
    print 'pm peak period'
    pm_all_metrics = calculate_trip_metrics(selected_pm_trips_df)
    outputs.update({'PM all trips' : pm_all_metrics})
    selected_pm_person_auto_transit_commute_trips = select_commute_trips(selected_pm_trips_df)
    pm_commute_metrics = calculate_trip_metrics(selected_pm_person_auto_transit_commute_trips)
    outputs.update({'PM commute trips' : pm_commute_metrics})

    outputfilepath = os.path.join(project_folder, report_output_location, 'metris_from_trip_table.txt')
    with open(outputfilepath, 'w') as f:
        f.write('All non-motorized trips are excluded from calculation.\n\n')
        for key, val in outputs.iteritems():
            f.write('%s\n' % key)
            for key2, val2 in val.iteritems():
                f.write('   %s: %.2f\n'% (key2, val2))

    print 'Done'

if __name__ == '__main__':
    main()
