"""
Zenvuno Flask Backend
Provides API endpoints for NDVI calculation and map visualization
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import ee
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Initialize Earth Engine
try:
    ee.Initialize(project='zenvuno')
    print("Earth Engine initialized successfully")
except Exception as e:
    print(f"Error initializing Earth Engine: {e}")


def calculate_ndvi_for_polygon(geometry, start_date, end_date):
    """Calculate mean NDVI for a polygon over a time range"""
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(geometry) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    def add_ndvi(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)
    
    collection_ndvi = collection.map(add_ndvi)
    recent_image = collection_ndvi.sort('system:time_start', False).first()
    
    ndvi = recent_image.select('NDVI')
    mean_ndvi = ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=10,
        maxPixels=1e9
    )
    
    return mean_ndvi.getInfo()['NDVI']


def generate_ndvi_timeseries(geometry, start_date, end_date):
    """Generate monthly NDVI time series for a polygon"""
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(geometry) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    def add_ndvi(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)
    
    collection_ndvi = collection.map(add_ndvi)
    
    def get_monthly_mean(year, month):
        month_start = f'{year}-{month:02d}-01'
        if month == 12:
            month_end = f'{year+1}-01-01'
        else:
            month_end = f'{year}-{month+1:02d}-01'
        
        monthly_collection = collection_ndvi.filterDate(month_start, month_end)
        
        if monthly_collection.size().getInfo() == 0:
            return None
        
        monthly_composite = monthly_collection.median()
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
    """Interpret NDVI value into vegetation health category"""
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


def get_ndvi_color(ndvi_value):
    """Get color for NDVI value for map visualization"""
    if ndvi_value < 0.2:
        return '#8B4513'  # Brown - bare soil
    elif ndvi_value < 0.4:
        return '#FFFF00'  # Yellow - low vegetation
    elif ndvi_value < 0.6:
        return '#90EE90'  # Light green - moderate vegetation
    elif ndvi_value < 0.8:
        return '#228B22'  # Forest green - healthy vegetation
    else:
        return '#006400'  # Dark green - very dense vegetation


@app.route('/')
def index():
    """Render the main map interface"""
    return render_template('index.html')


@app.route('/api/calculate-ndvi', methods=['POST'])
def calculate_ndvi():
    """API endpoint to calculate NDVI for a polygon"""
    data = request.json
    coordinates = data.get('coordinates', [])
    start_date = data.get('start_date', '2024-01-01')
    end_date = data.get('end_date', '2025-01-01')
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    
    # Create polygon from coordinates
    geometry = ee.Geometry.Polygon([coordinates])
    
    try:
        # Calculate current NDVI
        current_ndvi = calculate_ndvi_for_polygon(geometry, start_date, end_date)
        
        # Generate time series
        timeseries = generate_ndvi_timeseries(geometry, start_date, end_date)
        
        # Interpret results
        status = interpret_ndvi(current_ndvi)
        color = get_ndvi_color(current_ndvi)
        
        return jsonify({
            'current_ndvi': round(current_ndvi, 3),
            'status': status,
            'color': color,
            'timeseries': timeseries.to_dict('records'),
            'polygon': coordinates
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
