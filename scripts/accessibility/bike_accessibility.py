import pandana as pdna
import os, sys
sys.path.append(os.getcwd())
import pandas as pd
import numpy as np
import re
import geopandas as gpd
from shapely.geometry import LineString, Point
from scipy.spatial import cKDTree

from accessibility_configuration import *
import input_configuration as input_config
import emme_configuration as emme_config
from EmmeProject import *



def line_to_point(linstring, interval_distance, btype):
    # add start point to the list    
    points = [linstring.interpolate(0)]
    btypes = [btype]    
    distance = interval_distance    
    while distance <= linstring.length:
        pt = line.interpolate(distance) 
        points.append(pt)
        distance += interval_distance  
        btypes.append(btype)
    return points, btypes                                        

def assign_nodes_to_dataset(dataset, network, column_name, x_name, y_name):
    """Adds an attribute node_ids to the given dataset."""
    dataset[column_name] = network.get_node_ids(dataset[x_name].values, dataset[y_name].values)

def process_net_attribute(network, attr, fun):
    print("Processing %s" % attr)
    newdf = None
    for dist_index, dist in distances.items():        
        res_name = "%s_%s" % (re.sub("_?p$", "", attr), dist_index) # remove '_p' if present
        aggr = network.aggregate(dist, type=fun, decay="exp", name=attr)
        if newdf is None:
            newdf = pd.DataFrame({res_name: aggr, "node_ids": aggr.index.values})
        else:
            newdf[res_name] = aggr
    return newdf

def count_objects_within_radius(node, objects, radius_feet=5280):  # 1 mile = 5280 feet
    # Calculate distance to each object
    distances = objects.geometry.distance(node.geometry)
    
    # Filter objects within radius
    within_radius = objects[distances <= radius_feet]
    
    return len(within_radius)
    

def calculate_bike_accessibility(parcels, network, disaggregated_bike_lanes_df):
    parcels_node_df = pd.DataFrame(parcels[['node_id', 'x', 'y']])
    parcels_node_df = parcels_node_df.drop_duplicates()    
    parcels_node_df['geometry'] = parcels_node_df.apply(lambda row : Point(row['x'], row['y']), axis = 1)   
    parcels_node_gdf = gpd.GeoDataFrame(parcels_node_df, geometry = 'geometry')   
    parcels_node_df['counts'] = 0          

    objects_coords = np.array([(geom.x, geom.y) for geom in disaggregated_bike_lanes_df.geometry])  
    tree = cKDTree(objects_coords)    
    for node in parcels_node_gdf.itertuples():
        geom = node.geometry        
        captured_pts = tree.query_ball_point((geom.x, geom.y), 5280)
        parcels_node_df.loc[parcels_node_df['node_id'] == node.node_id, 'counts'] = len(captured_pts)  

    parcels = parcels.merge(parcels_node_df[['node_id', 'counts']], on = 'node_id').reset_index() 
    parcels_node_gdf.to_file('outputs/bikes/nearest_node_to_parcel', driver = 'ESRI Shapefile')
    return parcels, parcels_node_df       

# def calculate_bike_accessibility(parcels, network, disaggregated_bike_lanes_df):
#     parcels_node_df = pd.DataFrame(parcels[['PARCELID', 'node_id', 'x', 'y']])
#     parcels_node_df['geometry'] = parcels_node_df.apply(lambda row : Point(row['x'], row['y']), axis = 1)   
#     parcels_node_gdf = gpd.GeoDataFrame(parcels_node_df, geometry = 'geometry')   
#     parcels_node_df['counts'] = 0          
#     for node in parcels_node_gdf.itertuples():
#         count = count_objects_within_radius(node, disaggregated_bike_lanes_df)
#         parcels_node_df.loc[parcels_node_df['node_id'] == node.node_id, 'counts'] = count  
#         print(f'{node.node_id}, {count}')        
                
parcels = pd.read_csv(os.path.join(parcels_file_folder, parcels_file_name), sep = " ", index_col = None )
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

# nodes must be indexed by node_id column, which is the first column
all_street_nodes = pd.read_csv(nodes_file_name, index_col = 'node_id')
all_street_links = pd.read_csv(links_file_name, index_col = None )
# get rid of circular links
all_street_links = all_street_links.loc[(all_street_links.from_node_id != all_street_links.to_node_id)]
# assign impedance
imp = pd.DataFrame(all_street_links.Shape_Length)
imp = imp.rename(columns = {'Shape_Length':'distance'})

all_street_links['from_node_id'] = all_street_links['from_node_id'].astype('int')
all_street_links['to_node_id'] = all_street_links['to_node_id'].astype('int')

# create pandana network
net = pdna.network.Network(all_street_nodes.x, all_street_nodes.y, all_street_links.from_node_id, all_street_links.to_node_id, imp)
for dist in distances:
    net.precompute(dist)

# open PM databank
pm_model_path = f'projects/1530to1830/1530to1830.emp'
print(pm_model_path) #debug
my_project = EmmeProject(pm_model_path)

# get emme_link and emme_node to df
emme_link_df = my_project.emme_links_to_df()
emme_node_df = my_project.emme_nodes_to_df()

my_project.closeDesktop()    
# get links with @biketype == 1, without censtroid connectors.
bike_m_link_df = emme_link_df.loc[(emme_link_df['@biketype'] == 1) & (emme_link_df['isConnector'] == False)]

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
cleaned_bike_m_link_df = bike_m_link_df.drop(reversed_link_df.index)

# convert links to points with 20 feet apart, with @biketype,
geolinks = []
btypes = []
nodes_for_bike_links = [] 
nodes_btypes = []
col_pos = cleaned_bike_m_link_df.columns.tolist().index('@biketype')
counter = 0
for link in cleaned_bike_m_link_df.itertuples():
    line = LineString([(link.inodex, link.inodey), (link.jnodex, link.jnodey)])
    geolinks.append(line)
    bike_type =  getattr(link, f'_{col_pos + 1}')   
    btypes.append(bike_type)
    pts, bike_lane_type = line_to_point(line, 20, bike_type)    
    nodes_for_bike_links.extend(pts)
    nodes_btypes.extend(bike_lane_type)
    

# Assign NAD83(HARN) / Washington North (ftUS) CRS
crs = 'EPSG:2926'

geolink_data = {'geometry': geolinks, 'biktype':btypes}
geolink_df = gpd.GeoDataFrame(geolink_data, crs = crs) 

geonode_data = {'geometry': nodes_for_bike_links, 'biketype':nodes_btypes}  
geonode_df = gpd.GeoDataFrame(geonode_data, crs = crs)             

geonode_df.to_file('outputs/bikes/disaggregated_bike_links.shape', driver = 'ESRI Shapefile')

# assign network nodes to parcels, for buffer variables
assign_nodes_to_dataset(parcels, net, 'node_id', 'XCOORD_P', 'YCOORD_P')
parcels = parcels.merge(all_street_nodes.reset_index(), left_on = 'node_id', right_on = 'node_id')        
# calculate how many points within 1 mile radius of each parcel centroid. 
print("Calculating 1-mile buffer")    
parcels, parcel_node_df = calculate_bike_accessibility(parcels, net, geonode_df)
bike_access = parcels.loc[parcels['counts'] > 0]
bike_access[['PARCELID', 'node_id', 'counts']].to_csv('outputs/bikes/bike_access.csv')
print('Done')

    