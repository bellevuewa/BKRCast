import pandas as pd
import geopandas as gpd
import rasterio
import os, sys
import numpy as np
import getopt
from rasterstats import point_query
from multiprocessing import Pool, cpu_count
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import input_configuration as bkr_config
import emme_configuration as emme_config

from EmmeProject import *

# this script is to replace old cumulative slope calculation scripts bkr_slope.py and bkr_slope_step2.py.
# 3/18/2025

def split_line_to_points(row, spacing):
    line = row.geometry
    points = []

    split_count = max(1, int(line.length / spacing))
    distance = np.linspace(0, line.length, split_count + 1)
    points.extend([{'ID': row.ID, 'geometry': line.interpolate(d)} for d in distance])
    return points

# Group points by link ID and calculate elevation gains
def calculate_elevation_gains(group):
    elevations = group['elevation'].dropna().values
    if len(elevations) < 2:
        return pd.Series({'elev_gain_ij': 0})
    diff = np.diff(elevations)  # Calculate differences between consecutive points
    elev_gain_ij = np.sum(np.maximum(diff, 0)) 
    return pd.Series({'elev_gain_ij': elev_gain_ij})

def help():
    print('Usage: python calculate_cumulative_slopes_for_bike.py')
    print('This script calculates the cumulative slopes for each link.') 
    print('The output is saved in the report_bikes_output_location folder.')
    print('The output includes the following files:')
    print('  - emme_attr.in: Emme attribute file with the following columns: inode, jnode, @bkfac, @upslp. Saved in the inputs/bikes folder.')
    print('  - emme_attr.csv: CSV file with the following columns: inode, jnode, @bkfac, @upslp. Saved in the inputs/bikes folder.')
    print('  - link_components_elevation.geojson: GeoJSON file with the following columns: ID, geometry, elevation, if the -a option is used')
    print('  - link_elev_gains.csv: CSV file with the following columns: ID, elev_gain_ij, if the -a option is used')
    print('  - emme_link_with_elevation_gain.csv: CSV file with the following columns: ID, INODE, JNODE, F_biketype, LENGTH, elev_gain_ij, elev_gain, avg_upslope, if the -a option is used')
    print('  - shapefile folder: Shapefile folder with the following files: emme_links.shp, emme_links.shx, emme_links.dbf, emme_links.prj')
    print('Options:')
    print('  -a: Print all intermediate files. Files will be saved in the report_bikes_output_location folder.')
    print('  -h: Display help')


def main():
    print_all_files = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ha') 
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-a':
             print_all_files = True
        else:
            print('Invalid option: ' + opt)
            print('Use -h to display help.')
            exit(2)

    # use PM network to export shape file
    my_project = EmmeProject(emme_config.pm_project)
    my_project.set_primary_scenario('1002')
    export_shapefile_loc = os.path.join(bkr_config.report_bikes_output_location, 'shapefile')
    my_project.export_current_scenario_to_shapefile(export_shapefile_loc)

    # Load shapefile as GeoDataFrame, and convert to the correct projection
    emme_links = gpd.read_file(os.path.join(export_shapefile_loc, 'emme_links.shp'))
    if emme_links.crs == None:
        emme_links = emme_links.set_crs(bkr_config.gis_projection)
    elif emme_links.crs != bkr_config.gis_projection:
        emme_links = emme_links.to_crs(bkr_config.gis_projection)

    df = pd.DataFrame(emme_links)
    # Split network lines into points
    point_spacing = 30

    print('Line to points...')
    all_points = emme_links.apply(lambda row: split_line_to_points(row, point_spacing), axis = 1)
    points_list = [point for sublist in all_points for point in sublist]  # Flatten list of lists
    points_gdf = gpd.GeoDataFrame(points_list, crs=emme_links.crs)

    # Extract elevation values from raster
    print('Calculate elevations of each point in 30-ft apart...')

    # split points into chunks by numbver of cpus for multiprocessing
    geometry_with_index = list(zip(points_gdf.index, points_gdf.geometry))
    chunks = [geometry_with_index[i::cpu_count()] for i in range(cpu_count())]
    with Pool(cpu_count()) as pool:
        results = pool.map(query_chunk, chunks)
    # Combine results into a single GeoDataFrame
    flat_results_pair = [item for sublist in results for item in sublist]
    points_gdf['elevation'] = points_gdf.index.map(dict(flat_results_pair))

    # below is the old code to calculate elevation from raster, but it is too slow
    # with rasterio.open(bkr_config.elevation_raster_database) as src:
    #     points_gdf['elevation'] = point_query(points_gdf.geometry, src.read(1), affine = src.transform, nodata = src.nodata )

    # Calculate slopes
    print('Calculate cumulative slopes for each link...')
    # Apply the function to each group
    elev_gains = points_gdf.groupby('ID').apply(calculate_elevation_gains).reset_index()
    # Merge elevation gains with the original DataFrame
    df = pd.merge(df, elev_gains, on='ID', how='left')

    # Calculate elevation gain for both directions
    df['elev_gain'] = df['elev_gain_ij'].fillna(0)

    # Convert elevation gain to feet
    df['elev_gain'] *= 3.28084

    # Calculate average upslope
    df['avg_upslope'] = df['elev_gain'] / (df['LENGTH'] * 5280)

    if print_all_files:
        points_gdf.to_file(os.path.join(bkr_config.report_bikes_output_location, 'link_components_elevation.geojson'), driver='GeoJSON')
        elev_gains.to_csv(os.path.join(bkr_config.report_bikes_output_location, 'link_elev_gains.csv'))      
        df.to_csv(os.path.join(bkr_config.report_bikes_output_location, 'emme_link_with_elevation_gain.csv'))

    # Prepare final output
    to_export = df[['INODE', 'JNODE', '@biketype', 'elev_gain', 'avg_upslope']].copy()
    to_export.rename(columns={'INODE': 'inode', 'JNODE': 'jnode', '@biketype': '@bkfac', 'elev_gain': '@elegain', 'avg_upslope': '@upslp'}, inplace=True)
    to_export.fillna(0, inplace=True)

    to_export[['inode', 'jnode', '@upslp']].to_csv(os.path.join(os.path.join('inputs/bikes'), '@upslp.in'), sep=' ', index=False)
    to_export[['inode', 'jnode', '@elegain']].to_csv(os.path.join(os.path.join('inputs/bikes'), '@elegain.in'), sep=' ', index=False)
    # Export results
    to_export.to_csv(os.path.join(os.path.join('inputs/bikes'), 'emme_attr.in'), sep=' ', index=False)
    to_export['id'] = to_export['inode'].astype(str) + '-' + to_export['jnode'].astype(str)
    to_export.to_csv(os.path.join(os.path.join('inputs/bikes'), 'emme_attr.csv'), sep=' ', index=False)

    print('Processing complete.')


def query_chunk(indexed_geoms):
    idxs, geoms = zip(*indexed_geoms)
    with rasterio.open(bkr_config.elevation_raster_database) as src:
        elevations = point_query(geoms, src.read(1), affine=src.transform, nodata=src.nodata)
        return list(zip(idxs, elevations))

if __name__ == '__main__':
    main()
