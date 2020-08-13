import glob as gl
import pandas as pd
import geopandas as gpd


def combine_shpfiles(folder_path, output_path):
    '''
    Combines all the shapefiles in a folder.
    '''
    shapes = gl.glob(folder_path + '*.shp')
    shapes_list = []
    for shape in shapes:
        shapes_list.append(gpd.read_file(shape))
    combined = gpd.GeoDataFrame(pd.concat(shapes_list))
    combined.to_file(output_path)
    return 'shapefiles have been combined'
