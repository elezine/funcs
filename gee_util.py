

def createMergedCollection(collection, windowSize, matchingProperty = 'system:time_start'):
    '''
    This function was originally written in javascript by Dr. Xiao Yang, UNC (https://github.com/seanyx)
    Creates an image collection with the images within windowSize of an image merged to that image.
    For example, giving a windowSize of 3 would merge the images 3 days before and 3 days after
    with an image under argument 'neighboringImages'.

    Arguments
    - collection: the image collection being used from gee
    - windowSize: the size of the merging window
    - matchingProperty: the property the images are being matched on, default is the timestamp property
    for MODIS

    Return: the merged collection
    '''

    join = ee.Join.saveAll(matchesKey = 'neighboringImages')
    diffFilter = ee.Filter.maxDifference(difference = 1000*60*60*24*windowSize, leftField = matchingProperty, rightField = matchingProperty)
    merged = join.apply(primary = collection, secondary = collection, condition = diffFilter)

    return merged


def averageMergedCollection(image):
    '''
    Inspired by by Dr. Xiao Yang, UNC (https://github.com/seanyx)
    Averages a merged collection of images from createMergedCollection

    Arguments
    - image: an image from createMergedCollection

    Return: averaged image (based on whatever windowSize specified in createMergedCollection)
    '''

    neighboringImagesCollection = ee.ImageCollection.fromImages(image.get('neighboringImages'))
    combinedReducer = ee.Reducer.mean()
    smoothedImage = neighboringImagesCollection.reduce(combinedReducer)

    return smoothedImage

def movingAverageCollection(collection, windowSize, matchingProperty = 'system:time_start'):
    '''
    Combines functions to create a moving average of the collection.
    '''
    mergedCollection = createMergedCollection(collection, windowSize, matchingProperty)
    smoothedCollection = mergedCollection.map(averageMergedCollection)

    return smoothedCollection


'''MODIS SPECIFIC FUNCTIONS:'''

def calculate_SCA_MODIS(image, area):
    '''
    Calculates SCA from MODIS data (assumed to be 500 m resolution) for one image.
    First converts NDSI to SCF using equation SCF = NDSI * 1.45 + -1.00.
    Then multiplies SCF by area of each pixel and adds total over specified area for SCA.

    Return: SCF and SCA for that image and region
    '''
    SCA = ee.Feature(None, ee.Image(image).multiply(1.45).add(-1.00).multiply(0.01).multiply(500*500).reduceRegion(ee.Reducer.sum(), area, 500))
    return SCA

def calculate_SCF_MODIS(image, area):
    '''
    Calculates SCF from MODIS data (assumed to be 500 m resolution) for one image.
    Converts NDSI to SCF using equation SCF = NDSI * 1.45 + -1.00.

    Return: SCF for that image and region
    '''
    SCF = ee.Feature(None, ee.Image(image).multiply(1.45).add(-1.00).multiply(0.01).reduceRegion(ee.Reducer.sum(), area, 500))
    return SCF

def moving_SCAF_Collection(collection, windowSize, region_shpfile, start_date, end_date, mask = False):
    '''
    Returns the SCF and SCA for a collection based on a moving averaged specified in windowSize.

    '''

    area = ee.FeatureCollection(region_shpfile)
    if mask:
        mask_area = ee.FeatureCollection(mask)
        area = area.geometry().difference(mask_area.geometry(), ee.ErrorMargin(1))

    collection = ee.ImageCollection(collection).filterDate(start_date, end_date)
    smoothedCollection = movingAverageCollection(collection, windowSize)

    calculate_SCF_area = calculate_SCF_MODIS.bind(None, area = area)
    SCF = ee.ImageCollection(smoothedCollection.map(calculate_SCF_area))

    calculate_SCA_area = calculate_SCA_MODIS.bind(None, area = area)
    SCA = ee.ImageCollection(smoothedCollection.map(calculate_SCA_area))

    SCF = SCF.aggregate_array('NDSI_Snow_Cover_mean').getInfo()
    SCA = SCA.aggregate_array('NDSI_Snow_Cover_mean').getInfo()

    return SCF, SCA
