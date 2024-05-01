import pandana as pdna
import os, sys
sys.path.append(os.getcwd())
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, Point
from scipy.spatial import KDTree

import accessibility_configuration as  access_config
import input_configuration as input_config
import emme_configuration as emme_config
from EmmeProject import *
import data_wrangling


def line_to_point(linestring, interval_distance, btype):
    # add start point to the list    
    points = [linestring.interpolate(0)]
    btypes = [btype]    
    distance = interval_distance    
    while distance <= linestring.length:
        pt = linestring.interpolate(distance) 
        points.append(pt)
        distance += interval_distance  
        btypes.append(btype)
    return points, btypes                                        

def count_objects_within_radius(node, objects, radius_feet=5280):  # 1 mile = 5280 feet
    # Calculate distance to each object
    distances = objects.geometry.distance(node.geometry)
    
    # Filter objects within radius
    within_radius = objects[distances <= radius_feet]
    
    return len(within_radius)
    
def count_and_sum_biketype(node, tree, radius, attributes_df):
    captured_pts = tree.query_ball_point((node.geometry.x, node.geometry.y), radius)
    captured_attributes = attributes_df.iloc[captured_pts]

    biketype_sizes = captured_attributes.groupby('biketype').size().to_dict()

    return len(captured_pts), biketype_sizes               

def calculate_bike_accessibility(parcels, disaggregated_bike_lanes_df):
    '''
       column length in ESRI shape file is 10 chars or less.       
    '''  
    print('Constructing geodataframe...')              
    parcels_node_df = pd.DataFrame(parcels[['node_id', 'x', 'y']])
    parcels_node_df = parcels_node_df.drop_duplicates()    
    parcels_node_df['geometry'] = parcels_node_df.apply(lambda row : Point(row['x'], row['y']), axis = 1)   
    parcels_node_gdf = gpd.GeoDataFrame(parcels_node_df, geometry = 'geometry')   

    print('Calculating bike accessibility for each parcel...')
    objects_coords = np.array([(geom.x, geom.y) for geom in disaggregated_bike_lanes_df.geometry])  
    tree = KDTree(objects_coords)   
    result = parcels_node_gdf.apply(lambda row: count_and_sum_biketype(row, tree, 5280, disaggregated_bike_lanes_df), axis = 1)

    parcels_node_gdf['counts'] = [res[0] for res in result]
    parcels_node_gdf['biketype_sums'] = [res[1] for res in result]
    
    biketype_available = disaggregated_bike_lanes_df['biketype'].unique().tolist()  
    #biketype_x_cnt    
    attr_list = [f'bt_{x}_cnt' for x in biketype_available]    

    for biketype in biketype_available:
        parcels_node_gdf[f'bt_{biketype}_cnt'] = parcels_node_gdf['biketype_sums'].apply(lambda x: x.get(biketype, 0)) 
    
    print('Exporting files...') 
    # be careful. ESRI shapefile only allows at most 10 chars in each column name
    parcels_node_gdf.drop(columns = ['biketype_sums']).to_file('outputs/bikes/nearest_node_to_parcel', driver = 'ESRI Shapefile')
    attr_list[0:0] = ['node_id', 'counts']
    parcels = parcels.merge(parcels_node_gdf[attr_list], on = 'node_id').reset_index() 
    attr_list.insert(0, 'PARCELID')
    attr_list[2:2] = ['x', 'y']    
    # export PARCELID, node_id, x, y, counts, bt_{biketype}_cnt
    parcels.loc[parcels['counts'] > 0, attr_list].to_csv('outputs/bikes/parcels_with_bike_access.csv', index = False)    
    return parcels, parcels_node_gdf       


def create_non_directional_bike_links_df(emme_proj_path, biketypes):
    '''
        emme_proj_path: .emp file 
        biketypes: list of values in @biketype which decides what bike links should be populated into the dataframe.  
        A dataframe with bike links, defined by biketypes without centroid connectors, is returned. Each link is non-directional.        
    '''

    # open PM databank
    print(emme_proj_path) #debug
    my_project = EmmeProject(emme_proj_path)

    # get emme_link and emme_node to df
    emme_link_df = my_project.emme_links_to_df()
    emme_node_df = my_project.emme_nodes_to_df()

    my_project.closeDesktop()    
    # get links with @biketype in biketypes, without censtroid connectors.
    bike_m_link_df = emme_link_df.loc[(emme_link_df['@biketype'].isin(biketypes)) & (emme_link_df['isConnector'] == False)]

    #add inodex, inodey, jnodex, jnodey to bike_m_link_df
    bike_m_link_df = bike_m_link_df.merge(emme_node_df[['id', 'x', 'y']], left_on = 'i_node', right_on = 'id', how = 'left')
    bike_m_link_df.drop(columns = ['id'], inplace = True)
    bike_m_link_df.rename(columns = {'x':'inodex', 'y':'inodey'}, inplace = True)
    bike_m_link_df = bike_m_link_df.merge(emme_node_df[['id', 'x', 'y']], left_on = 'j_node', right_on = 'id', how = 'left')
    bike_m_link_df.drop(columns = ['id'], inplace = True)
    bike_m_link_df.rename(columns = {'x':'jnodex', 'y':'jnodey'}, inplace = True)

    # remove reversed links. only keep one of them, not both direction
    bike_m_link_df[['i_node', 'j_node']] = pd.DataFrame(np.sort(bike_m_link_df[['i_node', 'j_node']], axis = 1), index = bike_m_link_df.index)
    reversed_link_df = bike_m_link_df[bike_m_link_df.duplicated(subset = ['i_node', 'j_node'], keep = 'first')]
    non_directional_bike_m_link_df = bike_m_link_df.drop(reversed_link_df.index)

    return non_directional_bike_m_link_df
 
def convert_bike_links_to_nodes(non_directional_bike_link_df, spacing = 20):
    # convert links to points with 20 feet apart, with @biketype,
    geolinks = []
    btypes = []
    nodes_for_bike_links = [] 
    nodes_btypes = []
    col_pos = non_directional_bike_link_df.columns.tolist().index('@biketype')
    for link in non_directional_bike_link_df.itertuples():
        line = LineString([(link.inodex, link.inodey), (link.jnodex, link.jnodey)])
        geolinks.append(line)
        bike_type =  getattr(link, f'_{col_pos + 1}')   
        btypes.append(bike_type)
        pts, bike_lane_type = line_to_point(line, spacing, bike_type)    
        nodes_for_bike_links.extend(pts)
        nodes_btypes.extend(bike_lane_type)

    # Assign NAD83(HARN) / Washington North (ftUS) CRS
    crs = 'EPSG:2926'

    geolink_data = {'geometry': geolinks, 'biktype':btypes}
    geolink_gdf = gpd.GeoDataFrame(geolink_data, crs = crs) 

    geonode_data = {'geometry': nodes_for_bike_links, 'biketype':nodes_btypes}  
    geonode_gdf = gpd.GeoDataFrame(geonode_data, crs = crs)             
    geonode_gdf['biketype'] = geonode_gdf['biketype'].astype(int)
    geonode_gdf.to_file('outputs/bikes/disaggregated_bike_links.shape', driver = 'ESRI Shapefile')

    return geolink_gdf, geonode_gdf    
        
parcel_path = os.path.join(input_config.parcels_file_folder, access_config.parcels_file_name)       
parcels = data_wrangling.load_parcel_data(parcel_path)
pm_model_path = f'projects/1530to1830/1530to1830.emp'
non_directional_bike_link_df = create_non_directional_bike_links_df(pm_model_path, [1, 2])
net, all_street_links, all_street_nodes = data_wrangling.build_pandana_network()
geolink_gdf, geonode_gdf = convert_bike_links_to_nodes(non_directional_bike_link_df, spacing = 20)   

# assign network nodes to parcels, for buffer variables
data_wrangling.assign_nodes_to_dataset(parcels, net, 'node_id', 'XCOORD_P', 'YCOORD_P')
parcels = parcels.merge(all_street_nodes.reset_index(), left_on = 'node_id', right_on = 'node_id')        
# calculate how many points within 1 mile radius of each parcel centroid. 
parcels, parcel_node_gdf = calculate_bike_accessibility(parcels, geonode_gdf)
print('Done')

    