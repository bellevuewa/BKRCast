import pandas as pd
import geopandas as gpd
import rasterio
import os
import numpy as np
from shapely.geometry import Point
from rasterstats import point_query

# this script is to replace old cumulative slope calculation scripts bkr_slope.py and bkr_slope_step2.py.
# 3/18/2025

def split_line_to_points(row, spacing):
    line = row.geometry
    points = []

    split_count = max(1, int(line.length / spacing))
    distance = np.linspace(0, line.length, split_count + 1)
    points.extend([{'ID': row.ID, 'geometry': line.interpolate(d)} for d in distance])
    return points


# Define input locations
geodb = r'V:\TransDeptGIS\GeoDB\Planning\Modeling\BKRCast_Bikenetwork_Slopes.gdb'
in_raster = r'V:\ExternalData\UWGeology\xDelete\GeoMapNWFeb2010\usgs_dem_30ft'
output_dir = r'D:\bike_cumulative_slopes'

# Load shapefile as GeoDataFrame
emme_links = gpd.read_file(geodb, layer = 'base_year_2023_emmelinks_from_S8056')

# Convert to pandas DataFrame
df = pd.DataFrame(emme_links)
df.to_csv(os.path.join(output_dir, 'emme_link_outputs.csv'))

# Split network lines into points
segment_len = 30
points = []

print('Line to points...')
all_points = emme_links.apply(lambda row: split_line_to_points(row, segment_len), axis = 1)
points_list = [point for sublist in all_points for point in sublist]  # Flatten list of lists
points_gdf = gpd.GeoDataFrame(points_list, crs=emme_links.crs)
points_gdf.to_file(os.path.join(output_dir, 'link_components.geojson'), driver='GeoJSON')

# Extract elevation values from raster
print('Calculate elevations of each point in 30-ft apart...')
with rasterio.open(in_raster) as src:
    points_gdf['elevation'] = point_query(points_gdf.geometry, src.read(1), affine = src.transform, nodata = src.nodata )

points_gdf.to_file(os.path.join(output_dir, 'link_components_elevation.geojson'), driver='GeoJSON')

# Calculate slopes
upslope_ij = {}
upslope_ji = {}

# Group points by link ID and calculate elevation gains
def calculate_elevation_gains(group):
    elevations = group['elevation'].dropna().values
    if len(elevations) < 2:
        return pd.Series({'elev_gain_ij': 0})
    diff = np.diff(elevations)  # Calculate differences between consecutive points
    elev_gain_ij = np.sum(np.maximum(diff, 0))  # Sum positive differences (upslope_ij)
    return pd.Series({'elev_gain_ij': elev_gain_ij})

print('Calculate cumulative slopes for each link...')
# Apply the function to each group
elev_gains = points_gdf.groupby('ID').apply(calculate_elevation_gains, include_groups = False).reset_index()
elev_gains.to_csv(os.path.join(output_dir, 'link_elev_gains.csv'))
# Merge elevation gains with the original DataFrame
df = pd.merge(df, elev_gains, on='ID', how='left')

# Calculate elevation gain for both directions
df['elev_gain'] = df['elev_gain_ij'].fillna(0)

# Convert elevation gain to feet
df['elev_gain'] *= 3.28084

# Calculate average upslope
df['avg_upslope'] = df['elev_gain'] / (df['LENGTH'] * 5280)

df.to_csv(os.path.join(output_dir, 'emme_link_with_elevation_gain.csv'))
# Prepare final output
to_export = df[['INODE', 'JNODE', 'F_biketype', 'avg_upslope']].copy()
to_export.rename(columns={'INODE': 'inode', 'JNODE': 'jnode', 'F_biketype': '@bkfac', 'avg_upslope': '@upslp'}, inplace=True)
to_export.fillna(0, inplace=True)

# Export results
to_export.to_csv(os.path.join(output_dir, 'emme_attr.in'), sep=' ', index=False)
to_export['id'] = to_export['inode'].astype(str) + '-' + to_export['jnode'].astype(str)
to_export.to_csv(os.path.join(output_dir, 'emme_attr.csv'), sep=' ', index=False)

print('Processing complete.')
