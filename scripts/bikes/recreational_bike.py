import pandas as pd
import numpy as np
import os, sys
import h5py
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
import input_configuration  as input_config
import  emme_configuration as emme_config


trip_file = os.path.join(input_config.report_output_location, '_trip.tsv')
trip_df = pd.read_csv(trip_file, sep = '\t')
bike_trips_df = trip_df.loc[trip_df['mode'] == 2].copy()
bike_by_dpurp_df = bike_trips_df[['dpurp', 'trexpfac']].groupby('dpurp').sum().reset_index()
bike_by_dpurp_df['purp_name'] = bike_by_dpurp_df['dpurp']
bike_by_dpurp_df.replace({'purp_name': input_config.purp_trip_dict}, inplace = True)

tour_file = os.path.join(input_config.report_output_location, '_tour.tsv')
tour_df = pd.read_csv(tour_file, sep = '\t')
bike_tour_df = tour_df.loc[(tour_df['tmodetp'] == 2) & (tour_df['parent'] == 0)].copy()
bike_tour_pdpurp_df = bike_tour_df[['pdpurp', 'toexpfac']].groupby('pdpurp').sum().reset_index()
bike_tour_pdpurp_df['purp_name'] = bike_tour_pdpurp_df['pdpurp']
bike_tour_pdpurp_df.replace({'purp_name':input_config.tour_purpose_dict}, inplace = True)

bike_social_tours_df = bike_tour_df.loc[bike_tour_df['pdpurp'] == 7].copy()
bike_social_tours_by_destparcel = bike_social_tours_df[['tdpcl', 'toexpfac']].groupby('tdpcl').sum().reset_index()

social_trips_df = trip_df.loc[trip_df['dpurp'] == 7].copy()
social_trips_by_destparcel_df = social_trips_df[['dpcl', 'trexpfac']].groupby('dpcl').sum().reset_index()
social_trips_by_destparcel_df.to_csv(os.path.join(input_config.report_bikes_output_location, 'all_social_trips_by_destparcel.csv'), index = False)
social_trips_by_destTAZ_df = social_trips_df[['dtaz', 'trexpfac']].groupby('dtaz').sum().reset_index()
social_trips_by_destTAZ_df.to_csv(os.path.join(input_config.report_bikes_output_location, 'all_social_trips_by_destTAZ.csv'), index = False)

with open(os.path.join(input_config.report_bikes_output_location, 'recreational_bike_trips.txt'), 'w') as writer:
    writer.write('bike trips by purpose, region-wide\n')
    writer.write(bike_by_dpurp_df.to_string())
    writer.write('\n\n')
    
    writer.write('bike tours by purpose, region-wide\n')
    writer.write(bike_tour_pdpurp_df.to_string())
    writer.write('\n\n')

    writer.write('bike social tours by destination parcel\n')
    writer.write(bike_social_tours_by_destparcel.to_string())
    writer.write('\n\n') 

           
bike_social_tours_by_destparcel.to_csv(os.path.join(input_config.report_bikes_output_location, 'social_bike_tours_by_destparcel.csv'), index = False)
print('Done')
