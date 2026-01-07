import pandana as pdna
import os, sys
import shutil
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
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

def create_bike_links_df(emme_proj_path, biketypes):
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
    bike_m_link_df = emme_link_df.loc[(emme_link_df['@biketype'].isin(biketypes)) & (emme_link_df['isConnector'] == False)].copy()
    bike_m_link_df['geometry'] = bike_m_link_df['shape'].apply(LineString)
    bike_m_link_gdf = gpd.GeoDataFrame(bike_m_link_df, geometry = 'geometry', crs = input_config.gis_projection)

    return bike_m_link_gdf

def calculate_park_accessibility_to_bike(parcels, emme_link_gdf, biketype = [10, 1, 2], buffer_dist = 5280):
    '''
        only bike lane (biketype=1, or 2) and bike trail (biketype=10) are considered.
        column length in ESRI shape file is 10 chars or less.       
    '''  
    print('Constructing geodataframe...')              
    parcels_node_df = pd.DataFrame(parcels)
    parcels_node_df = parcels_node_df.drop_duplicates()    
    parcels_node_df['geometry'] = parcels_node_df.apply(lambda row : Point(row['x'], row['y']), axis = 1)   
    parcels_node_gdf = gpd.GeoDataFrame(parcels_node_df, geometry = 'geometry', crs = input_config.gis_projection)   

    parcels_node_gdf['buffer'] = parcels_node_gdf.geometry.buffer(buffer_dist) # 1 mile = 5280 feet
    buffer = gpd.GeoDataFrame(parcels_node_gdf, geometry = parcels_node_gdf['buffer'], crs = input_config.gis_projection)

    print('Calculating bike accessibility for each parcel...')
    bike_links_gdf = emme_link_gdf[emme_link_gdf['@biketype'].isin(biketype) & (emme_link_gdf['isConnector'] == False)].copy()

    links_in_buffer = gpd.overlay(bike_links_gdf, buffer, how = 'intersection')
    links_in_buffer['length'] = links_in_buffer['geometry'].length
    links_in_buffer['area'] = links_in_buffer['length'] * links_in_buffer['@biketype'].map(access_config.bike_lane_weight) # sqft

    area_summary = links_in_buffer.groupby(['PSRC_ID', '@biketype'])[['area', 'length']].sum().reset_index()
    area_summary.to_csv('outputs/bikes/park_access_by_biketype.csv', index = False)
    area_summary_pivot = area_summary.pivot(index = 'PSRC_ID', columns = '@biketype', values = 'area').fillna(0)
    area_summary_pivot.columns = [f'bt_{int(b)}_sqft' for b in area_summary_pivot.columns] 

    parcels_node_gdf = parcels_node_gdf.merge(area_summary_pivot, left_on = 'PSRC_ID', right_index = True, how = 'left').fillna(0)
    parcels_node_gdf['accessibility'] = 0
    for type in biketype:
        parcels_node_gdf['accessibility'] += parcels_node_gdf[f'bt_{type}_sqft'] * access_config.bike_lane_weight[type] / 43560

    parcels_node_gdf['accessibility'] += access_config.park_size_weight * parcels_node_gdf['SHAPE_Area'] / 43560 # (park) parcel size in acre
    parcels_node_gdf['share'] = parcels_node_gdf['accessibility'] / parcels_node_gdf['accessibility'].sum() # share of accessibility for each park parcel

    print('Exporting files...') 

    pathfolder = 'outputs/bikes/nearest_node_to_parcel'
    os.makedirs(pathfolder, exist_ok = True)
    # be careful. ESRI shapefile only allows at most 10 chars in each column name
    parcels_node_gdf.drop(columns = ['buffer']).to_file(os.path.join(pathfolder, 'nearest_node_to_parcel.shp'), driver = 'ESRI Shapefile')
    links_in_buffer[['i_node', 'j_node', 'length', 'area', '@biketype', 'PSRC_ID', 'BKRCastTAZ', 'PARKNAME', 'geometry']].to_file(os.path.join(pathfolder, 'links_in_buffer.shp'), driver = 'ESRI Shapefile')
    buffer.drop(columns= ['geometry']).to_file(os.path.join(pathfolder, 'buffer.shp'), driver = 'ESRI Shapefile')

    parcel_acccessibility_df = parcels_node_gdf.drop(columns=['geometry'])
    parcel_acccessibility_df.to_csv('outputs/bikes/parcels_with_bike_access.csv', index = False)    
    return parcel_acccessibility_df, parcels_node_gdf       

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

    geolink_data = {'geometry': geolinks, 'biktype':btypes}
    geolink_gdf = gpd.GeoDataFrame(geolink_data, crs = input_config.gis_projection) 

    geonode_data = {'geometry': nodes_for_bike_links, 'biketype':nodes_btypes}  
    geonode_gdf = gpd.GeoDataFrame(geonode_data, crs = input_config.gis_projection)             
    geonode_gdf['biketype'] = geonode_gdf['biketype'].astype(int)

    folderpath = 'outputs/bikes/disaggregated_bike_links.shape'
    if os.path.exists(folderpath):
        shutil.rmtree(folderpath)
    geonode_gdf.to_file(folderpath, driver = 'ESRI Shapefile')

    return geolink_gdf, geonode_gdf    

# original method to calculate bike accessibility
# use weighted bike surface area and elevation gain within buffer as bike accessibility
def calculate_TAZ_accessibility_to_bike2 (taz_gdf, emme_link_gdf, biketype = [10, 1, 2], buffer_dist = 5280):
    '''
        taz_gdf: geodataframe with TAZs
        emme_link_gdf: geodataframe with bike links
    '''
    # create buffer for each TAZ
    taz_gdf.rename(columns = {'TAZNUM':'BKRCastTAZ'}, inplace = True)
    taz_gdf['buffer'] = taz_gdf.geometry.buffer(buffer_dist)
    buffer = gpd.GeoDataFrame(taz_gdf, geometry = taz_gdf['buffer'], crs = input_config.gis_projection)

    # gis calculation to find out the bike links within buffer, and calculate the surface area of bike links within buffer
    bike_links_gdf = emme_link_gdf[emme_link_gdf['@biketype'].isin(biketype)].copy()
    links_in_buffer = gpd.overlay(bike_links_gdf, buffer, how = 'intersection')
    links_in_buffer['length'] = links_in_buffer.geometry.length
    links_in_buffer['area'] = links_in_buffer['length'] * links_in_buffer['@biketype'].map(access_config.bike_lane_width) 
    links_in_buffer['elegain_area'] = links_in_buffer['@elegain'] * links_in_buffer['@biketype'].map(access_config.bike_lane_width)     
    links_in_buffer[['BKRCastTAZ', 'i_node', 'j_node', '@biketype', 'length', 'area', '@elegain', 'elegain_area', '@upslp']].to_csv('outputs/bikes/bike_links_in_buffer.csv', index = False)

    # summarize the area of bike links within buffer for each TAZ, by @biketype
    area_summary = links_in_buffer.groupby(['BKRCastTAZ', '@biketype'])[['area', 'length', '@elegain', 'elegain_area']].sum().reset_index()
    area_summary.to_csv('outputs/bikes/TAZ_bike_access_by_biketype.csv', index = False)
    area_summary_pivot = area_summary.pivot(index = 'BKRCastTAZ', columns = '@biketype', values = 'area').fillna(0)
    area_summary_pivot.columns = [f'bt_{int(b)}_sqft' for b in area_summary_pivot.columns]  

    slope_summary_pivot = area_summary.pivot(index = 'BKRCastTAZ', columns = '@biketype', values = 'elegain_area').fillna(0)
    slope_summary_pivot.columns = [f'bt_{int(b)}_elegainsqft' for b in slope_summary_pivot.columns] 
    
    taz_gdf = taz_gdf[['BKRCastTAZ', 'Shape_Area', 'geometry']].merge(area_summary_pivot, left_on = 'BKRCastTAZ', right_index = True, how = 'left').fillna(0)
    taz_gdf = taz_gdf.merge(slope_summary_pivot, left_on = 'BKRCastTAZ', right_on = 'BKRCastTAZ', how = 'left').fillna(0)
    taz_gdf['Shape_Area'] = taz_gdf['Shape_Area'].round(0).astype(int)

    # calculate the accessibility for each TAZ
    taz_gdf['wsa'] = 0 # wighted surface area
    taz_gdf['slope_accessibility'] = 0 # slope accessibility
    for type in biketype:
        taz_gdf['wsa'] += taz_gdf[f'bt_{type}_sqft'] * access_config.bike_lane_weight.get(type, 0) / 43560 # convert sqft to acre 
        taz_gdf['slope_accessibility'] += 10* taz_gdf[f'bt_{type}_elegainsqft'] * access_config.bike_lane_weight.get(type, 0) / 43560 # convert sqft to acre  
    
    taz_gdf['facility_accessibility'] = taz_gdf['wsa'] 
    taz_gdf['accessibility'] = (taz_gdf['facility_accessibility'] - taz_gdf['slope_accessibility']).clip(lower = 0)

    # calculate share of accessibility for each TAZ
    taz_gdf['share'] = taz_gdf['accessibility'] / taz_gdf['accessibility'].sum()
    
    path_folder = 'outputs/bikes/TAZ_bike_access'
    if os.path.exists(path_folder):
        shutil.rmtree(path_folder) 
    taz_gdf.to_file(path_folder, driver = 'ESRI Shapefile')
    taz_df = taz_gdf.drop(columns = ['geometry'])      
    taz_df.to_csv('outputs/bikes/TAZ_bike_accessibility.csv', index = False)   

    return taz_df

def main():  
    print('Start recreational bike accessibility...')

    project_dir = os.path.dirname(emme_config.pm_project)  
    taz_gdf = gpd.read_file(os.path.join(project_dir, 'Media', 'BKRCast_TAZ.shp'))
    taz_gdf = taz_gdf.to_crs(input_config.gis_projection)
    taz_gdf['Shape_Area'] = taz_gdf['Shape_Area'] / 43560.0 # convert sqft to acre

    my_project = EmmeProject(emme_config.pm_project)
    # import @upslp and @elegain from input_config.project_folder
    my_project.create_extra_attribute('LINK', '@upslp', 'cumulative slope for uphill only', True)
    my_project.import_attribute_values(os.path.join(input_config.project_folder, 'outputs/bikes/@upslp.in'), False)
    my_project.create_extra_attribute('LINK', '@elegain', 'cumulative elevation gain uphill only', True)
    my_project.import_attribute_values(os.path.join(input_config.project_folder, 'outputs/bikes/@elegain.in'), False)

    # get emme_link and emme_node to df
    emme_link_df = my_project.emme_links_to_df()
    emme_link_df = emme_link_df.loc[(emme_link_df['isConnector'] == False) & (emme_link_df['@biketype'].isin([10, 1, 2, 9, 5]))]
    emme_link_df['geometry'] = emme_link_df['shape'].apply(LineString)
    emme_link_gdf = gpd.GeoDataFrame(emme_link_df, geometry = 'geometry', crs = input_config.gis_projection)
    my_project.closeDesktop()

    accessibility_df = calculate_TAZ_accessibility_to_bike2(taz_gdf, emme_link_gdf, biketype = [10, 1, 2, 9, 5], buffer_dist = 2640)    
           
    print('Recreational bike accessibility is finished')

if __name__ == '__main__':
    main()    