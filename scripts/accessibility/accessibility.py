import datetime
import getopt
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
    res = network.nearest_pois(access_config.max_dist, name, num_pois=1, max_distance=999.0)
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
            parcels['dist_%s' % new_name] = 999.0 # use max dist if no stops exist for this submode
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

def transit_walk_access_to_jobs_hhs(parcels, transit_df, net, walk_time = access_config.transit_stop_walk_time, parcel_polygon_path = None):
    '''
    This function calculates the number of jobs and households that are accessible within a given walk time to transit stops.
    The walk time is in minutes and it is the walk time along the network.
    parcels includes an all streeet network node id column called node_ids, which is assigned to a parcel as the nearest network node to the parcel centroid. 
    The transit_df includes a node_ids column that is assigned to each transit stop as the nearest network node to the transit stop.
    '''
    walk_distance_ft = walk_time * access_config.ped_walk_speed * 5280 / 60 # convert to feet
    not_reachable = 999999

    net.init_pois(len(transit_df), walk_distance_ft, 1) # initialize the network with the number of transit stops and the walk distance
    # register bus stop as POIs
    net.set_pois('bus_stops', transit_df['x'], transit_df['y'])
    # distance from every all street node to the nearest transit stop
    dist_to_stops = net.nearest_pois(walk_distance_ft, 'bus_stops', num_pois=1, max_distance=not_reachable).iloc[:, 0]
    accessible_node_ids = dist_to_stops.loc[dist_to_stops <= walk_distance_ft].index

    accessible_nodes_df = net.nodes_df.loc[net.nodes_df.index.isin(accessible_node_ids)].copy()
    import geopandas as gpd
    from shapely.geometry import Point
    accessible_nodes_df['geometry'] = [Point(row.x, row.y) for row in accessible_nodes_df.itertuples()]
    nodes_gdf = gpd.GeoDataFrame(accessible_nodes_df, geometry='geometry', crs = input_config.gis_projection)
    from pathlib import Path
    output_path = Path(input_config.report_net_output_location) / Path('all_street_network') / (Path(f'{walk_time}_minutes_walk_accessible_nodes').stem + '.shp')  
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nodes_gdf.to_file(output_path, index=False)

    # export transit stops to a shape file for use in GIS. Save the shape files in ouputs/network/all_street_network folder
    transit_df['geometry'] = [Point(row.x, row.y) for row in transit_df.itertuples()]
    transit_gdf = gpd.GeoDataFrame(transit_df, geometry='geometry', crs = input_config.gis_projection)
    transit_gdf.to_file(Path(input_config.report_net_output_location) / Path('all_street_network') / (Path(access_config.transit_stops_name).stem + '.shp'), index=False)

    # get the parcels that are within the walk distance to transit stops
    # if a parcel includes any of the accessible nodes, then it is considered accessible to transit
    lookup_parcels_df = pd.read_csv(os.path.join(input_config.main_inputs_folder, 'model', 'parcel_TAZ_2014_lookup.csv'), low_memory = False)
    accessible_parcels =parcels.loc[parcels['node_ids'].isin(accessible_node_ids)]

    # create 50 ft buffer around accessible_nodes and check which parcels intersect with the buffer. 
    # union this with the parcels that are already accessible to transit based on the node_ids. 
    accessible_parcel_ids = set(parcels.loc[parcels['node_ids'].isin(accessible_node_ids), 'PARCELID'])
    if parcel_polygon_path is not None:
        parcel_polygons_gdf = gpd.read_file(parcel_polygon_path)
        parcel_polygons_gdf = parcel_polygons_gdf.to_crs(input_config.gis_projection)
        parcel_polygons_gdf['PSRC_ID'] = parcel_polygons_gdf['PSRC_ID'].astype(int)
        accessible_node_buffer = nodes_gdf[['geometry']].copy()
        accessible_node_buffer['geometry'] = accessible_node_buffer.geometry.buffer(50) # 50 ft
        intersecting = gpd.sjoin(parcel_polygons_gdf[['geometry', 'PSRC_ID']], accessible_node_buffer, how='inner', predicate='intersects')
        intersecting_parcel_ids = set(intersecting['PSRC_ID'].unique())
        accessible_parcel_ids.update(intersecting_parcel_ids)
        accessible_parcels = parcels.loc[parcels['PARCELID'].isin(accessible_parcel_ids)].copy()
        accessible_parcels = accessible_parcels.merge(lookup_parcels_df[['PSRC_ID', 'Jurisdiction', 'BKRCastTAZ']], left_on='PARCELID', right_on='PSRC_ID', how='left')
        accessible_parcels.to_csv(os.path.join(input_config.report_net_output_location, 'all_street_network',f'parcels_within_{walk_time}_minutes_walk_to_transit.csv'), index=False)
        accessible_parcels[['Jurisdiction', 'EMPTOT_P', 'HH_P']].groupby('Jurisdiction').sum().to_csv(os.path.join(input_config.report_net_output_location, 'all_street_network',f'jobs_hhs_within_{walk_time}_minutes_walk_to_transit_by_jurisdiction.csv'))

        # export the accessible parcels to a shapefile for GIS use
        accessible_parcels_gdf = parcel_polygons_gdf.loc[parcel_polygons_gdf['PSRC_ID'].isin(accessible_parcel_ids)].copy()
        accessible_parcels_gdf = accessible_parcels_gdf.merge(lookup_parcels_df[['PSRC_ID', 'Jurisdiction', 'BKRCastTAZ']], left_on='PSRC_ID', right_on='PSRC_ID', how='left')
        accessible_parcels_gdf.to_file(os.path.join(input_config.report_net_output_location, 'all_street_network',f'parcels_within_{walk_time}_minutes_walk_to_transit.shp'), index=False)

def help():
    # a short description of what this script does and how to use it. explain where the output files are saved and what they are called.
    print('This script calculates accessibility measures for parcels based on the all street network and transit stops.')
    print('It calculates the number of jobs and households that are accessible within a given walk time to transit stops.')
    print('It also calculates the distance from each parcel to the nearest transit stop by type (local bus, express bus, commuter rail, ferry, light rail).')
    print('The output files are saved in the outputs/landuse folder and outputs/network/all_street_network folder.')
    print('The output shapefiles are saved in the outputs/network/all_street_network folder and are called parcels_within_<walk_time>_minutes_walk_to_transit.shp and ' \
    'parcels_within_<walk_time>_minutes_walk_to_transit_by_jurisdiction.csv.')
    print('By default, this script does not require any command line arguments. However, you can specify a parcel polygon shapefile for spatial analysis using the -p option followed by the path to the shapefile.')
    
    print('Usage: python accessibility.py -p <parcel_polygon_path>')
    print('Options:')
    print('  -p <parcel_polygon_path> : Path to the parcel polygon shapefile for spatial analysis (optional).')
    print('Example:')
    print('  python accessibility.py -p "path/to/parcel_polygons.shp"')
 
def main():
    parcel_polygon_path = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:")
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-p':
            parcel_polygon_path = arg

    # read in data
    parcels = data_wrangling.load_parcel_data_without_JBLM_jobs(os.path.join(input_config.parcels_file_folder, access_config.parcels_file_name))
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

    net, links, nodes = data_wrangling.build_pandana_network(access_config.nodes_file_name, access_config.links_file_name)
    net_for_access, _, _ = data_wrangling.build_pandana_network(access_config.nodes_file_name, access_config.links_file_name)

    # export all street network to shape files for use in GIS. Save the shape files in ouputs/network/all_street_network folder
    import geopandas as gpd
    from shapely.geometry import LineString, Point
    valid_links = links.dropna(subset=['from_x', 'from_y', 'to_x', 'to_y']).copy()
    valid_links['geometry'] = [LineString([(row.from_x, row.from_y), (row.to_x, row.to_y)]) for row in valid_links.itertuples()]
    links_gdf = gpd.GeoDataFrame(valid_links, geometry='geometry', crs = input_config.gis_projection)
    links_gdf.rename(columns = {'from_node_id':'from_node', 'to_node_id':'to_node', 'Shape_Length': 'shp_length'}, inplace = True)
    from pathlib import Path
    output_path = Path(input_config.report_net_output_location) / Path('all_street_network') / (Path(access_config.links_file_name).stem + '.shp')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    links_gdf.to_file(output_path, index=False)
    nodes['geometry'] = [Point(row.x, row.y) for row in nodes.itertuples()]
    nodes_gdf = gpd.GeoDataFrame(nodes, geometry='geometry', crs = input_config.gis_projection)
    nodes_gdf.to_file(Path(input_config.report_net_output_location) / Path('all_street_network') / (Path(access_config.nodes_file_name).stem + '.shp'), index=True)


    # get transit stops
    transit_df = pd.read_csv(os.path.join(main_inputs_folder, 'networks', access_config.transit_stops_name),  index_col = None)
    transit_df['tstops'] = 1

    # intersections:
    # combine from and to columns
    all_nodes = pd.DataFrame(pd.concat([net.edges_df['from'], net.edges_df['to']], axis = 0), columns = ['node_ids'])
    # get the frequency of each node, which is the number of intersecting ways
    intersections_df = all_nodes['node_ids'].value_counts().reset_index()
    intersections_df = intersections_df.rename(columns = {'count' : 'edge_count'})

    # add a column for each way count
    intersections_df['nodes1'] = np.where(intersections_df['edge_count']==1, 1, 0)
    intersections_df['nodes3'] = np.where(intersections_df['edge_count']==3, 1, 0)
    intersections_df['nodes4'] = np.where(intersections_df['edge_count']>3, 1, 0)

    # assign network (pandana network) nodes to parcels, for buffer variables
    data_wrangling.assign_nodes_to_dataset(parcels, net, 'node_ids', 'XCOORD_P', 'YCOORD_P')

    # assign network (pandana network)nodes to transit stops, for buffer variable
    data_wrangling.assign_nodes_to_dataset(transit_df, net, 'node_ids', 'x', 'y')

    parcels_for_access = parcels[['PARCELID', 'node_ids', 'XCOORD_P', 'YCOORD_P', 'HH_P', 'EMPTOT_P']].copy()
    parcels[['PARCELID', 'node_ids', 'XCOORD_P', 'YCOORD_P']].to_csv(os.path.join(input_config.report_net_output_location, 'all_street_network', 'parcels_with_node_ids.csv'), index=False)
    transit_walk_access_to_jobs_hhs(parcels_for_access, transit_df, net_for_access, walk_time = access_config.transit_stop_walk_time, parcel_polygon_path = parcel_polygon_path)
    
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

    subarea_df = pd.read_csv(os.path.join(main_inputs_folder, 'subarea_definition', 'TAZ_subarea.csv'), low_memory=False)
    parcels = parcels.merge(subarea_df[['BKRCastTAZ', 'Subarea']], left_on='TAZ_P', right_on='BKRCastTAZ', how='left')

    # apply additional distance penalties for LRT stations for certain subareas to calibrate to boarding/transfer rates
    if not access_config.LRT_Station_Accessibility:
        for station, config in access_config.LRT_Station_Accessibility.items():
            if not config:
                parcels.loc[(parcels['dist_lrt'] <= 2) & (parcels['Subarea'].isin(config['impacted_subareas'])), 'dist_lrt'] = parcels['dist_lrt'] * config['multiplier']
    
    parcels.drop(columns=['BKRCastTAZ', 'Subarea'], inplace=True)
    parcels_done = clean_up(parcels)
    parcels_done.to_csv(access_config.output_parcels, index = False, sep = ' ')

if __name__ == '__main__':
    run_context = os.getenv('RUN_CONTEXT') # chained if this script is called from another script, otherwise it is standalone
    if run_context == 'chained':
        meta_data = False
    else:
        meta_data = True

    logger, start_time = data_wrangling.open_main_logger(meta_data, 'Accessibility')
    logger.info(f"Running script: {os.path.basename(__file__)} %s", " ".join(sys.argv[1:]))
    main()
    end_time = datetime.datetime.now()
    elapsed_total = end_time - start_time
    logger.info(f'Total run time: {elapsed_total}')