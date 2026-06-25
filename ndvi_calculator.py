"""
Zenvuno NDVI Calculator
Google Earth Engine script to calculate NDVI for a user-defined polygon
"""

import ee
import pandas as pd
from datetime import datetime

# Initialize Earth Engine
try:
    ee.Initialize(project='zenvuno')
    print("Earth Engine initialized successfully for project: zenvuno")
except Exception as e:
    print(f"Error initializing Earth Engine: {e}")
    print("Trying without project...")
    try:
        ee.Initialize()
        print("Earth Engine initialized successfully")
    except Exception as e2:
        print(f"Error initializing Earth Engine: {e2}")
        exit(1)


def calculate_ndvi_for_polygon(geometry, start_date, end_date):
    """
    Calculate mean NDVI for a polygon over a time range
    
    Args:
        geometry: ee.Geometry polygon
        start_date: str 'YYYY-MM-DD'
        end_date: str 'YYYY-MM-DD'
    
    Returns:
        float: mean NDVI value
    """
    # Get Sentinel-2 collection
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(geometry) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    # Calculate NDVI for each image
    def add_ndvi(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)
    
    collection_ndvi = collection.map(add_ndvi)
    
    # Get the most recent cloud-free image
    recent_image = collection_ndvi.sort('system:time_start', False).first()
    
    # Calculate mean NDVI over the polygon
    ndvi = recent_image.select('NDVI')
    mean_ndvi = ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=10,
        maxPixels=1e9
    )
    
    return mean_ndvi.getInfo()['NDVI']


def generate_ndvi_timeseries(geometry, start_date, end_date):
    """
    Generate monthly NDVI time series for a polygon
    
    Args:
        geometry: ee.Geometry polygon
        start_date: str 'YYYY-MM-DD'
        end_date: str 'YYYY-MM-DD'
    
    Returns:
        pd.DataFrame: DataFrame with date and NDVI columns
    """
    # Get Sentinel-2 collection
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(geometry) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    # Calculate NDVI for each image
    def add_ndvi(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)
    
    collection_ndvi = collection.map(add_ndvi)
    
    # Function to extract monthly mean NDVI
    def get_monthly_mean(year, month):
        month_start = f'{year}-{month:02d}-01'
        if month == 12:
            month_end = f'{year+1}-01-01'
        else:
            month_end = f'{year}-{month+1:02d}-01'
        
        monthly_collection = collection_ndvi.filterDate(month_start, month_end)
        
        if monthly_collection.size().getInfo() == 0:
            return None
        
        # Composite images for the month
        monthly_composite = monthly_collection.median()
        
        # Calculate mean NDVI over the polygon
        ndvi = monthly_composite.select('NDVI')
        mean_ndvi = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10,
            maxPixels=1e9
        )
        
        return {
            'date': f'{year}-{month:02d}-01',
            'NDVI': mean_ndvi.getInfo()['NDVI']
        }
    
    # Generate monthly data
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    results = []
    current_year = start.year
    current_month = start.month
    
    while current_year < end.year or (current_year == end.year and current_month <= end.month):
        monthly_data = get_monthly_mean(current_year, current_month)
        if monthly_data:
            results.append(monthly_data)
        
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    
    return pd.DataFrame(results)


def interpret_ndvi(ndvi_value):
    """
    Interpret NDVI value into vegetation health category
    
    Args:
        ndvi_value: float NDVI value
    
    Returns:
        str: Vegetation health category
    """
    if ndvi_value < 0.2:
        return "Bare soil / very sparse vegetation"
    elif ndvi_value < 0.4:
        return "Low vegetation"
    elif ndvi_value < 0.6:
        return "Moderate vegetation"
    elif ndvi_value < 0.8:
        return "Healthy vegetation"
    else:
        return "Very dense vegetation"


if __name__ == "__main__":
    # Test polygon (example: a farm in Kenya)
    # Coordinates for a test area near Nakuru, Kenya
    test_polygon = ee.Geometry.Polygon([
        [[36.06, -0.28], [36.07, -0.28], [36.07, -0.29], [36.06, -0.29], [36.06, -0.28]]
    ])
    
    # Date range for analysis
    start_date = '2024-01-01'
    end_date = '2025-01-01'
    
    print("Calculating current NDVI...")
    current_ndvi = calculate_ndvi_for_polygon(test_polygon, start_date, end_date)
    print(f"Current NDVI: {current_ndvi:.3f}")
    print(f"Status: {interpret_ndvi(current_ndvi)}")
    
    print("\nGenerating NDVI time series...")
    timeseries = generate_ndvi_timeseries(test_polygon, '2024-01-01', '2025-01-01')
    print(timeseries)
    
    # Export to CSV
    output_file = 'ndvi_timeseries.csv'
    timeseries.to_csv(output_file, index=False)
    print(f"\nTime series exported to {output_file}")
