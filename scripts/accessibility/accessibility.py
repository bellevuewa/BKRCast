import pandana as pdna
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import pandas as pd
import numpy as np
import re
from pyproj import Proj, transform
import accessibility_configuration as access_config
from input_configuration import *
from emme_configuration import *
import data_wrangling


# 10/25/2021
# modified to be compatible with python 3

# def assign_nodes_to_dataset(dataset, network, column_name, x_name, y_name):
#     """Adds an attribute node_ids to the given dataset."""
#     dataset[column_name] = network.get_node_ids(dataset[x_name].values, dataset[y_name].values)
   
def reproject_to_wgs84(longitude, latitude, ESPG = "+init=EPSG:2926", conversion = 0.3048006096012192):
    '''
    Converts the passed in coordinates from their native projection (default is state plane WA North-EPSG:2926)
    to wgs84. Returns a two item tuple containing the longitude (x) and latitude (y) in wgs84. Coordinates
    must be in meters hence the default conversion factor- PSRC's are in state plane feet.  
    '''    #print longitude, latitude
    # Remember long is x and lat is y!
    prj_wgs = Proj(init='epsg:4326')
    prj_sp = Proj(ESPG)

    # Need to convert feet to meters:
    longitude = longitude * conversion
    latitude = latitude * conversion
    x, y = transform(prj_sp, prj_wgs, longitude, latitude)

    return x, y

# def process_net_attribute(network, attr, fun):
#     print("Processing %s" % attr)
#     newdf = None
#     for dist_index, dist in distances.items():        
#         res_name = "%s_%s" % (re.sub("_?p$", "", attr), dist_index) # remove '_p' if present
#         aggr = network.aggregate(dist, type=fun, decay="exp", name=attr)
#         if newdf is None:
#             newdf = pd.DataFrame({res_name: aggr, "node_ids": aggr.index.values})
#         else:
#             newdf[res_name] = aggr
#     return newdf

def process_dist_attribute(parcels, network, name, x, y):
    network.set_pois(name, x, y)
    res = network.nearest_pois(access_config.max_dist, name, num_pois=1, max_distance=999)
    res[res != 999] = (res[res != 999]/5280.).astype(res.dtypes) # convert to miles
    res_name = "dist_%s" % name
    parcels[res_name] = res.loc[parcels.node_ids].values
    return parcels

def process_parcels(parcels, transit_df, net, intersections_df):
    
    # Add a field so you can compute the weighted average number of spaces later
    parcels['daily_weighted_spaces'] = parcels['PARKDY_P']*parcels['PPRICDYP']
    parcels['hourly_weighted_spaces'] = parcels['PARKHR_P']*parcels['PPRICHRP']

    # Start processing attributes
    newdf = None
    for fun, attrs in access_config.parcel_attributes.items():    
        for attr in attrs:
            net.set(parcels.node_ids, variable=parcels[attr], name=attr)    
            res = data_wrangling.process_net_attribute(net, attr, fun)
            if newdf is None:
                newdf = res
            else:
                newdf = pd.merge(newdf, res, on="node_ids", copy=False)

    # sum of bus stops in buffer
    for name in access_config.transit_attributes:    
        net.set(transit_df['node_ids'].values, transit_df[name], name=name)
        newdf = pd.merge(newdf, data_wrangling.process_net_attribute(net, name, "sum"), on="node_ids", copy=False)
    
    # sum of intersections in buffer
    for name in access_config.intersections:
        net.set(intersections_df['node_ids'].values, intersections_df[name],  name=name)
        newdf = pd.merge(newdf, data_wrangling.process_net_attribute(net, name, "sum"), on="node_ids", copy=False)

    # Parking prices are weighted average, weighted by the number of spaces in the buffer, divided by the total spaces
    newdf['PPRICDYP_1'] = newdf['daily_weighted_spaces_1']/newdf['PARKDY_P_1']
    newdf['PPRICDYP_2'] = newdf['daily_weighted_spaces_2']/newdf['PARKDY_P_2']
    newdf['PPRICHRP_1'] = newdf['hourly_weighted_spaces_1']/newdf['PARKHR_P_1']
    newdf['PPRICHRP_2'] = newdf['hourly_weighted_spaces_2']/newdf['PARKHR_P_2']

    parcels.reset_index(level=0, inplace=True)
    parcels = pd.merge(parcels, newdf, on="node_ids", copy=False)

    # set the number of pois on the network for the distance variables (transit + 1 for parks)
    net.init_pois(len(transit_modes)+1, access_config.max_dist, 1)
  
    # calc the distance from each parcel to nearest transit stop by type
    for new_name, attr in transit_modes.items():
        print(new_name)
        # get the records/locations that have this type of transit:
        transit_type_df = transit_df.loc[(transit_df[attr] == 1)]
        if transit_type_df[attr].sum() > 0:
            parcels=process_dist_attribute(parcels, net, new_name, transit_type_df["x"], transit_type_df["y"])
        else:
            parcels['dist_%s' % new_name] = 999 # use max dist if no stops exist for this submode
        # some parcels share the same network node and therefore have 0 distance. Recode this to 0.01
        field_name = 'dist_%s' % new_name
        parcels.loc[parcels[field_name] == 0, field_name] = 0.01

    # distance to park
    #parcel_idx_park = np.where(parcels.NPARKS > 0)[0]
    #parcels=process_dist_attribute(parcels, net, "park", parcels.XCOORD_P[parcel_idx_park], parcels.YCOORD_P[parcel_idx_park])
    parcels['dist_park'] = 999.0
    return parcels

def clean_up(parcels):
    # we just had these columns to get the weighted average, now drop them
    del parcels['daily_weighted_spaces']
    del parcels['hourly_weighted_spaces']
    del parcels['daily_weighted_spaces_1']
    del parcels['daily_weighted_spaces_2']
    del parcels['hourly_weighted_spaces_1']
    del parcels['hourly_weighted_spaces_2']
    
    # stupidly the naming convention suddenly changes for Daysim, so we have to be consistent
    rename = {}
    for column in parcels.columns:
        if '_P_' in column:
            new_col = re.sub('_P', '', column)
            rename[column] = new_col
    parcels = parcels.rename(columns = rename)
    parcels = parcels.rename(columns ={'PPRICDYP_1': 'PPRICDY1', 'PPRICHRP_1': 'PPRICHR1','PPRICDYP_2': 'PPRICDY2','PPRICHRP_2': 'PPRICHR2'})

    # daysim needs the column names to be lower case
    parcels.columns = map(str.lower, parcels.columns)
    parcels=parcels.fillna(0)
    parcels_final = pd.DataFrame()
    
    # currently Daysim just uses dist_lbus as actually meaning the minimum distance to transit, so we will match that setup for now.
    print('updating the distance to local bus field to actually hold the minimum to any transit because that is how Daysim is currently reading the field')
    parcels['dist_lbus'] = parcels[['dist_lbus', 'dist_ebus', 'dist_crt', 'dist_fry', 'dist_lrt']].min(axis=1)

    for col in access_config.col_order:
        parcels_final[col] = parcels[col]
    
    parcels_final[u'xcoord_p'] = parcels_final[u'xcoord_p'].astype(int)
    return parcels_final

def main():
    if run_update_parking and base_year != scenario_name:
        input_parcels = "inputs\\accessibility\\" + access_config.parcels_file_name
        print('open file ' + input_parcels)
        parcels = pd.read_csv(input_parcels, sep = " ", index_col = None )
    else: 
        # read in data
        parcels = pd.read_csv(os.path.join(parcels_file_folder, access_config.parcels_file_name), sep = " ", index_col = None )

    #capitalize field names to avoid errors
    parcels.columns = [i.upper() for i in parcels.columns]
    #check for missing data!
    for col_name in parcels.columns:
        # daysim does not use EMPRSC_P
        if col_name != 'EMPRSC_P':
            if parcels[col_name].sum() == 0:
                print(col_name + ' column sum is zero! Exiting program.')
                sys.exit(1)

    # not using. causes bug in daysim (copied from soundcast)
    parcels['APARKS'] = 0
    parcels['NPARKS'] = 0

    net, links, nodes = data_wrangling.build_pandana_network()

    # get transit stops
    transit_df = pd.read_csv(os.path.join(main_inputs_folder, 'networks', access_config.transit_stops_name),  index_col = None)
    transit_df['tstops'] = 1

    # intersections:
    # combine from and to columns
    all_nodes = pd.DataFrame(net.edges_df['from'].append(net.edges_df.to), columns = ['node_id'])

    # get the frequency of each node, which is the number of intersecting ways
    intersections_df = pd.DataFrame(all_nodes.node_id.value_counts())
    intersections_df = intersections_df.rename(columns = {'node_id' : 'edge_count'})
    intersections_df.reset_index(0, inplace = True)
    intersections_df = intersections_df.rename(columns = {'index' : 'node_ids'})

    # add a column for each way count
    intersections_df['nodes1'] = np.where(intersections_df['edge_count']==1, 1, 0)
    intersections_df['nodes3'] = np.where(intersections_df['edge_count']==3, 1, 0)
    intersections_df['nodes4'] = np.where(intersections_df['edge_count']>3, 1, 0)

    # assign network nodes to parcels, for buffer variables
    data_wrangling.assign_nodes_to_dataset(parcels, net, 'node_ids', 'XCOORD_P', 'YCOORD_P')

    # assign network nodes to transit stops, for buffer variable
    data_wrangling.assign_nodes_to_dataset(transit_df, net, 'node_ids', 'x', 'y')

    # run all accibility measures
    parcels = process_parcels(parcels, transit_df, net, intersections_df)

    # Report a raw distance to HCT and all transit before calibration
    #parcels['raw_dist_hct'] = parcels[[ 'dist_ebus', 'dist_crt', 'dist_fry', 'dist_lrt', 'dist_brt']].min(axis=1)
    #parcels['raw_dist_transit'] = parcels[['dist_lbus','dist_ebus', 'dist_crt', 'dist_fry', 'dist_lrt', 'dist_brt']].min(axis=1)
    parcels['raw_dist_hct'] = parcels[['dist_crt', 'dist_fry', 'dist_lrt']].min(axis=1)
    parcels['raw_dist_transit'] = parcels[['dist_lbus', 'dist_crt', 'dist_fry', 'dist_lrt']].min(axis=1)

    # reduce perceived walk distance for light rail and ferry. This is used to calibrate to 2014 boarding and transfer rates
    parcels.loc[parcels['dist_lrt'] <= 1, 'dist_lrt'] = parcels['dist_lrt'] * 0.5
    parcels.loc[parcels['dist_fry'] <= 2, 'dist_fry'] = parcels['dist_fry'] * 0.5
    parcels_done = clean_up(parcels)
    parcels_done.to_csv(access_config.output_parcels, index = False, sep = ' ')

if __name__ == '__main__':
    main()