import glob as gl
from osgeo import gdal,ogr,osr,gdalconst
from osgeo.gdalconst import GA_Update
import geopandas as gpd
import rasterio as rio
import earthpy.spatial as es
import numpy as np
from shapely import geometry
from rasterio.mask import mask

def merge_rasters(folder_path, output_path, srs = 'EPSG:4326'):
    files = gl.glob(folder_path + '*.tif')
    gdals = []
    for i in range(0, len(files)):
        gdals.append(gdal.Open(files[i]))
    gdal.Warp(output_path, gdals, dstSRS = srs)
    print('done merging rasters')

def reproject_raster(raster_path, output_path, srs = 'EPSG:4326'):
    input = gdal.Open(raster_path)
    gdal.Warp(output_path, input, dstSRS = srs)
    print('done reprojecting raster')

def add_no_data_val(raster_path, val):
    ras = gdal.Open(raster_path, GA_Update)
    for i in range(1, ras.RasterCount + 1):
        ras.GetRasterBand(i).SetNoDataValue(val)
    ras = None
    print('done setting no data value')

def reproj_ras_to_ref(raster_path, reference_path, output_path):

    input = gdal.Open(raster_path, gdalconst.GA_ReadOnly)
    inputProj = input.GetProjection()
    inputTrans = input.GetGeoTransform()
    bandreference_0 = input.GetRasterBand(1)

    reference = gdal.Open(reference_path, gdalconst.GA_ReadOnly)
    referenceProj = reference.GetProjection()
    referenceTrans = reference.GetGeoTransform()
    bandreference_1 = reference.GetRasterBand(1)
    x = reference.RasterXSize
    y = reference.RasterYSize

    driver = gdal.GetDriverByName('GTiff')
    output = driver.Create(output_path, x, y, 1, bandreference_0.DataType)
    output.SetGeoTransform(referenceTrans)
    output.SetProjection(referenceProj)

    gdal.ReprojectImage(input, output, inputProj, referenceProj, gdalconst.GDT_Float32)
    del output

    print('done reprojecting raster')

def crop_ras_to_shpfile(raster_path, shpfile_path, output_path, no_data_val):
    shpfile = gpd.read_file(shpfile_path)
    with rio.open(raster_path) as ras:
        ras_crop, ras_crop_meta = es.crop_image(ras, shpfile)
    ras_crop_aff = ras_crop_meta["transform"]

    ras_crop_meta.update({'transform': ras_crop_aff,
                       'height': ras_crop.shape[1],
                       'width': ras_crop.shape[2],
                       'nodata': no_data_val})

    with rio.open(output_path, 'w', **ras_crop_meta) as ff:
        ff.write(ras_crop[0], 1)

    print('done cropping raster to shapefile')

def get_lat_lon_ras(raster_path, lat_output_path, lon_output_path):
    ras = rio.open(raster_path)
    #ras = ras.read(1)
    ras_coord_lon = np.zeros(ras.shape)
    ras_coord_lat = np.zeros(ras.shape)
    for i in range(0, ras.shape[0]):
        for j in range(0, ras.shape[1]):
            coord = rio.transform.xy(ras.transform, i, j, offset='center')
            ras_coord_lon[i,j] = coord[0]
            ras_coord_lat[i,j] = coord[1]

    np.save(lat_output_path, ras_coord_lat)
    np.save(lon_output_path, ras_coord_lon)
    print('done saving lat and lon arrays')

def check_no_data_val(raster_path):
    ras = rio.open(raster_path)
    return ras.nodatavals

#PEKEL SPECIFIC FUNCTIONS

def threshold_pekel_dem(pekel_path, dem_path, output_path, threshold, remove_water_size = 20000):
    pekel = rio.open(pekel_path)
    dem = rio.open(dem_path)

    pekel = pekel.read(1)
    pekel = pekel.astype(np.float32)
    pekel[pekel < threshold] = np.nan
    pekel[pekel > 100] = np.nan
    pekel[~np.isnan(pekel)] = 1

    pekel = pekel*dem.read(1)
    pekel[~np.isnan(pekel)] = 1
    pekel[np.isnan(pekel)] = 0

    labeled_minima = measure.label(pekel, connectivity = 2)

    if remove_water_size:
        regs = measure.regionprops(labeled_minima)

        for i in range(0, len(regs)):
            if regs[i].area > remove_water_size:
                k = regs[i].coords[:,0] #the i coords
                j = regs[i].coords[:,1] #the j coords
                labeled_minima[k,j] = 0

    np.save(output_path, labeled_minima)
    print('saved thresholded and labeled pekel regions')


#### THESE FUNCTIONS CAME FROM STACK EXCHANGE AND ARE REALLY USEFUL TO SPLITTING A RASTER INTO SMALLER FILES:
#### FOR THAT, JUST USE THE FIRST FUNCTION:
#### OG SOURCE: Ciaran Evans, https://gis.stackexchange.com/questions/306861/split-geotiff-into-multiple-cells-with-rasterio

def splitImageIntoCells(img, filename, squareDim):
    numberOfCellsWide = img.shape[1] // squareDim
    numberOfCellsHigh = img.shape[0] // squareDim
    x, y = 0, 0
    count = 0
    for hc in range(numberOfCellsHigh):
        y = hc * squareDim
        for wc in range(numberOfCellsWide):
            x = wc * squareDim
            geom = getTileGeom(img.transform, x, y, squareDim)
            getCellFromGeom(img, geom, filename, count)
            count = count + 1

# Generate a bounding box from the pixel-wise coordinates using the original datasets transform property
def getTileGeom(transform, x, y, squareDim):
    corner1 = (x, y) * transform
    corner2 = (x + squareDim, y + squareDim) * transform
    return geometry.box(corner1[0], corner1[1],
                        corner2[0], corner2[1])

# Crop the dataset using the generated box and write it out as a GeoTIFF
def getCellFromGeom(img, geom, filename, count):
    crop, cropTransform = mask(img, [geom], crop=True)
    writeImageAsGeoTIFF(crop,
                        cropTransform,
                        img.meta,
                        img.crs,
                        filename+"_"+str(count))

# Write the passed in dataset as a GeoTIFF
def writeImageAsGeoTIFF(img, transform, metadata, crs, filename):
    metadata.update({"driver":"GTiff",
                     "height":img.shape[1],
                     "width":img.shape[2],
                     "transform": transform,
                     "crs": crs})
    with rio.open(filename+".tif", "w", **metadata) as dest:
        dest.write(img)
