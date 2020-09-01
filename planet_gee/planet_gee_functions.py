import os
import json
import requests
from requests.auth import HTTPBasicAuth


def get_image_ids(geometry, start_date, end_date, cloud_cover, api_key, image_type = 'PSScene4Band'):
    '''
    Get the Planet image ids within a geometry and time period.
    Code credit to: https://developers.planet.com/tutorials/index2.html
    
    Arguments:
    - geometry: geojson coordinates for a polygon
    - start_date/end_date: date in form '2020-01-01' etc.
    - cloud_cover: % cloud cover you are willing to accept in images
    - image_type: you could change this if you want a different kind of planet image
    
    Return: list of image IDs that meet specifications
    
    '''
    
    # get images that overlap with our AOI 
    geometry_filter = {
      "type": "GeometryFilter",
      "field_name": "geometry",
      "config": geometry
    }

    # get images acquired within a date range
    date_range_filter = {
      "type": "DateRangeFilter",
      "field_name": "acquired",
      "config": {
        "gte": str(start_date) + "T00:00:00.000Z",
        "lte": str(end_date) + "T00:00:00.000Z"
      }
    }

    cloud_cover_filter = {
      "type": "RangeFilter",
      "field_name": "cloud_cover",
      "config": {
        "lte": cloud_cover
      }
    }

    # combine our geo, date, cloud filters
    combined_filter = {
      "type": "AndFilter",
      "config": [geometry_filter, date_range_filter, cloud_cover_filter]
    }
    
    # API Key stored as an env variable
    PLANET_API_KEY = str(api_key)

    item_type = image_type

    # API request object
    search_request = {
      "item_types": [item_type], 
      "filter": combined_filter
    }

    # fire off the POST request
    search_result = \
      requests.post(
        'https://api.planet.com/data/v1/quick-search',
        auth=HTTPBasicAuth(PLANET_API_KEY, ''),
        json=search_request)

    # extract image IDs only
    image_ids = [feature['id'] for feature in search_result.json()['features']]
    
    return image_ids


def get_images_gee(image_ids, gee_project, gee_image_collection, email, password, image_type = 'analytic_sr'):
    
    '''
    Call POST request to Planet to send specified image ids to GEE account.
    
    Arguments:
    - image_ids: these are Planet image ids corresponding to images, can be gotten through get_image_ids
    - gee_project: this is the name of the GCP project that has earth engine writing permissions
    - gee_image_collection: this is the name of the image collection already created on the associated GEE account
    - email: your planet email
    - password: your planet password
    - image_type: defaults to 'analytic_sr', other choices can be found in planet documentation
    
    Return: the response from the POST request, should say "state":"queued" if all went well. May give
    401 error if the call was bad for some reason (bad image ids, incorrect email or password, etc.)
    
    '''
    
    url = "https://api.planet.com/compute/ops/orders/v2"
    
    json = {
    "name": "PS Shield Delivery to GEE",
    "products": [
            {
            "item_ids": image_ids,
            "item_type": "PSScene4Band",
            "product_bundle": str(image_type)
            }
        ],
    "delivery": {
        "google_earth_engine": {
            "project": str(gee_project),
            "collection": str(gee_image_collection)
            }
        }
    }

    response = requests.request("POST", url, auth=HTTPBasicAuth(str(email), str(password)), json = json)

    return response.text.encode('utf8')

