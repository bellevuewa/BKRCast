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

def select_residents_by_taz(taz_subarea_df):
    taz_subarea_df.reset_index(inplace = True)
    hhpath = os.path.join(project_folder, report_output_location, '_household.tsv')
    personpath = os.path.join(project_folder, report_output_location, '_person.tsv')
    hhs = pd.read_csv(hhpath, sep = '\t', low_memory = True)
    persons = pd.read_csv(personpath, sep = '\t', low_memory = True)
    selected_hhs = hhs.merge(taz_subarea_df, how = 'inner', left_on = 'hhtaz', right_on = 'TAZ')

    selected_persons = persons.merge(selected_hhs, how = 'inner', left_on = 'hhno', right_on = 'hhno')
    selected_persons['person_id'] = selected_persons['hhno'].astype('string') + '-' + selected_persons['pno'].astype('string')    
    print "residents selected: %d" % selected_persons.shape[0]
    return selected_hhs, selected_persons

def select_workers_by_taz(taz_subarea_df):
    taz_subarea_df.reset_index(inplace = True)
    hhpath = os.path.join(project_folder, report_output_location, '_household.tsv')
    personpath = os.path.join(project_folder, report_output_location, '_person.tsv')
    hhs = pd.read_csv(hhpath, sep = '\t', low_memory = True)
    persons = pd.read_csv(personpath, sep = '\t', low_memory = True)
    selected_persons = persons[persons['pwtaz'].isin(taz_subarea_df['TAZ'])]
    selected_persons['person_id'] = selected_persons['hhno'].astype('string') + '-' + selected_persons['pno'].astype('string')    
    selected_hhs = hhs[hhs['hhno'].isin(selected_persons['hhno'].unique())]
    print "workers selected: %d" % selected_persons.shape[0]
    return selected_hhs, selected_persons

def select_residents_in_Bellevue():
    hhpath = os.path.join(project_folder, report_output_location, '_household.tsv')
    personpath = os.path.join(project_folder, report_output_location, '_person.tsv')
    hhs = pd.read_csv(hhpath, sep = '\t', low_memory = True)
    persons = pd.read_csv(personpath, sep = '\t', low_memory = True)
    selected_hhs = hhs[hhs['hhtaz'] <= 616]
    selected_persons = persons.merge(selected_hhs, how = 'inner', left_on = 'hhno', right_on = 'hhno')
    selected_persons['person_id'] = selected_persons['hhno'].astype('string') + '-' + selected_persons['pno'].astype('string')    
    print "residents selected: %d" % selected_persons.shape[0]
    return selected_hhs, selected_persons

def select_workers_in_Bellevue():
    hhpath = os.path.join(project_folder, report_output_location, '_household.tsv')
    personpath = os.path.join(project_folder, report_output_location, '_person.tsv')
    hhs = pd.read_csv(hhpath, sep = '\t', low_memory = True)
    persons = pd.read_csv(personpath, sep = '\t', low_memory = True)
    selected_persons = persons[(persons['pwtaz'] <= 616) & (persons['pwtaz'] > 0)]
    selected_hhs = hhs[hhs['hhno'].isin(selected_persons['hhno'].unique())]
    selected_persons['person_id'] = selected_persons['hhno'].astype('string') + '-' + selected_persons['pno'].astype('string')    
    
    print "workers selected: %d" % selected_persons.shape[0]
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
    commute_trips = trips_df[(((trips_df['half'] == 1) & (trips_df['dpurp'] == 1)) | ((trips_df['half'] == 2) & (trips_df['opurp'] == 1))) & (trips_df['otaz'] != trips_df['dtaz'])]
    return commute_trips

def remove_trips_within_same_TAZ(trips_df):
    selected = trips_df[trips_df['otaz'] != trips_df['dtaz']]
    return selected

def remove_very_short_trips(trips_df, minTravTime):
    selected = trips_df[trips_df['travdist'] > 0.1]
    return selected

def remove_non_toll_network_trips(trips_df):
    selected = trips_df[trips_df['pathtype'] != 2]
    return selected

# return two objects
# a dict with min, max, avg of tt and distance
# a df of avg tt and avg dist by purpose
def calculate_trip_metrics(trips_df):
    newtrips_df = trips_df.copy()
    newtrips_df['sumtt'] = newtrips_df['travtime'] * newtrips_df['trexpfac']
    newtrips_df['sumdist'] = newtrips_df['travdist'] * newtrips_df['trexpfac']
    
    metrics = newtrips_df[['sumtt', 'sumdist', 'trexpfac', 'dpurp']].groupby('dpurp').sum()
    metrics['avgtt'] = (metrics['sumtt'] / metrics['trexpfac']).round(2)
    metrics['avgdist'] = (metrics['sumdist'] / metrics['trexpfac']).round(2)

    avgtt_all = round((metrics['sumtt'].sum() / metrics['trexpfac'].sum()), 2)
    avgdist_all = round((metrics['sumdist'].sum() / metrics['trexpfac'].sum()), 2)
    purp_dic = {0: 'home', 1: 'work', 2: 'school', 3: 'escort', 4: 'personal biz', 5: 'shopping', 6: 'meal', 7: 'social', 8: 'rec', 9: 'medical', 10: 'change'}
    metrics.reset_index(inplace = True)
    metrics.replace({'dpurp': purp_dic}, inplace = True)
    row_all = pd.Series(data={'dpurp':'all', 'avgtt': avgtt_all, 'avgdist':avgdist_all, 'trexpfac': metrics['trexpfac'].sum(), 'sumtt':metrics['sumtt'].sum(), 'sumdist':metrics['sumdist'].sum()})
    metrics = metrics.append(row_all, ignore_index = True)

    totaltrips = newtrips_df['trexpfac'].sum()
    avgtime = newtrips_df['travtime'].mean()
    mintravtime = newtrips_df['travtime'].min()
    maxtravtime = newtrips_df['travtime'].max()
    avgdist = newtrips_df['travdist'].mean()
    mintravdist = newtrips_df['travdist'].min()
    maxtravdist = newtrips_df['travdist'].max()
    output = {'Total Trips': totaltrips, 'Avg TT' : avgtime, 'Min TT' : mintravtime, 'Max TT' : maxtravtime, 'Avg Travel Dist' : avgdist, 'Min Travel Dist' : mintravdist, 'Max Travel Dist' : maxtravdist}
    print output
    return output, metrics

def exportTofile(file, dict):
    for key, val in dict.iteritems():
        file.write('%s: %.2f\n'% (key, val))

def exportWeirdTrips(trips_df):
    filepath = os.path.join(project_folder, report_output_location, 'weird_trips.csv')
    
    selected = trips_df[(trips_df['travtime'] < 1) | (trips_df['travtime'] > 190)]
    selected.to_csv(filepath, sep = ',')

def calculate_person_travel(hhs_df, persons_df, trips_df, outputfile):
    selected_daily_person_trips_df = select_trips_by_persons(trips_df, persons_df)
    selected_daily_person_trips_df = remove_very_short_trips(selected_daily_person_trips_df, 2)
    selected_daily_person_commute_trips = select_commute_trips(selected_daily_person_trips_df)

    outputs = {}
    daily_all_metrics, daily_by_purp = calculate_trip_metrics(selected_daily_person_trips_df)
    outputs.update({'Daily all trips':daily_all_metrics})
    outputfile.write('Daily all trips:\n')
    daily_by_purp.to_csv(outputfile, sep = '\t', float_format = '%.1f')
    print 'Daily Commute'
    daiy_commute_metrics, daily_commute_by_purp = calculate_trip_metrics(selected_daily_person_commute_trips)
    outputs.update({'Daily commute trips' : daiy_commute_metrics})
    print 'pm peak period'
    selected_pm_trips_df = select_trips_by_time(selected_daily_person_trips_df, 930 ,1110,'DEPARTURE')
    pm_all_metrics, pm_by_purp = calculate_trip_metrics(selected_pm_trips_df)
    outputs.update({'PM all trips' : pm_all_metrics})

    outputfile.write('PM all trips:\n')
    pm_by_purp.to_csv(outputfile, sep = '\t',  float_format = '%.1f')
    selected_pm_person_commute_trips = select_commute_trips(selected_pm_trips_df)
    pm_commute_metrics, pm_commute_by_purp = calculate_trip_metrics(selected_pm_person_commute_trips)
    outputs.update({'PM commute trips' : pm_commute_metrics})

    for key, val in outputs.iteritems():
        outputfile.write('%s\n' % key)
        for key2, val2 in val.iteritems():
            outputfile.write('   %s: %.2f\n'% (key2, val2))  
  
    return outputs
            
def main():
    trippath = os.path.join(project_folder, report_output_location, '_trip.tsv')
    print 'open ' + trippath
    trips_df = pd.read_csv(trippath, sep = '\t', low_memory = True)
    trips_df['vmt'] = trips_df['travtime']
    studyarea_filepath = os.path.join(project_folder, subarea_taz_file)
    taz_subarea_df = pd.read_csv(studyarea_filepath, sep = ',')
    taz_subarea_df = taz_subarea_df.loc[~taz_subarea_df['TAZ'].duplicated()]

    outputfilepath = os.path.join(project_folder, report_output_location, 'metris_from_trip_table.txt')
    with open(outputfilepath, 'w') as f:
        f.write('Below are for residents\n')
        # select hhs and persons who live in the study area
        selected_hhs, selected_persons = select_residents_in_Bellevue()
        calculate_person_travel(selected_hhs, selected_persons, trips_df, f)
        f.write('\n\n')

        f.write('Below are for workers\n')
        # select hhs and persons who work in the study area
        selected_hhs, selected_persons = select_workers_in_Bellevue()
        calculate_person_travel(selected_hhs, selected_persons, trips_df, f)
        f.write('\n\n')

    print 'Done'

if __name__ == '__main__':
    main()
