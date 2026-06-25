"""
Zenvuno Flask Backend
Provides API endpoints for NDVI calculation and map visualization
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import ee
import pandas as pd
from datetime import datetime
from database import Database
import numpy as np
from PIL import Image
import io
from crop_ndvi_ranges import compare_ndvi_to_range, get_crop_list, get_crop_stages
from vegetation_indexes import (
    calculate_all_indexes, get_index_description, 
    get_available_indexes, get_recommended_index,
    calculate_ndvi, calculate_ndre, calculate_msavi, calculate_reci,
    calculate_pri, calculate_mcari, calculate_ndmi, calculate_smi, calculate_ndwi
)

app = Flask(__name__)
CORS(app)

# Initialize database
db = Database()

# Initialize Earth Engine
try:
    ee.Initialize(project='zenvuno')
    print("Earth Engine initialized successfully")
except Exception as e:
    print(f"Error initializing Earth Engine: {e}")


@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """Render the new dashboard page"""
    return render_template('dashboard.html')


@app.route('/ndvi-viewer')
def ndvi_viewer():
    """Render the NDVI viewer page"""
    return render_template('ndvi_viewer.html')


@app.route('/ndvi_analysis')
def ndvi_analysis():
    """Render the NDVI Analysis page"""
    return render_template('ndvi_analysis.html')


@app.route('/api/vegetation-indexes', methods=['GET'])
def get_vegetation_indexes():
    """Get list of all available vegetation indexes with descriptions"""
    indexes = get_available_indexes()
    descriptions = {}
    for index in indexes:
        descriptions[index] = get_index_description(index)
    
    return jsonify({
        'indexes': indexes,
        'descriptions': descriptions
    })


@app.route('/api/vegetation-index/<index_name>/description', methods=['GET'])
def get_index_info(index_name):
    """Get description and best use case for a specific index"""
    description = get_index_description(index_name)
    return jsonify(description)


@app.route('/api/vegetation-index/recommend', methods=['POST'])
def recommend_index():
    """Get recommended index based on growth stage and crop type"""
    data = request.json
    growth_stage = data.get('growth_stage', 'mid')
    crop_type = data.get('crop_type')
    
    recommendation = get_recommended_index(growth_stage, crop_type)
    return jsonify(recommendation)


@app.route('/api/calculate-vegetation-index', methods=['POST'])
def calculate_vegetation_index():
    """Calculate a specific vegetation index for a polygon"""
    data = request.json
    coordinates = data.get('coordinates', [])
    start_date = data.get('start_date', '2024-01-01')
    end_date = data.get('end_date', '2025-01-01')
    index_name = data.get('index', 'NDVI')  # Default to NDVI
    viz_params = data.get('viz_params', {})
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    
    geometry = ee.Geometry.Polygon([coordinates])
    
    # Map index names to calculation functions
    index_functions = {
        'NDVI': calculate_ndvi,
        'NDRE': calculate_ndre,
        'MSAVI': calculate_msavi,
        'RECI': calculate_reci,
        'PRI': calculate_pri,
        'MCARI': calculate_mcari,
        'NDMI': calculate_ndmi,
        'SMI': calculate_smi,
        'NDWI': calculate_ndwi
    }
    
    if index_name not in index_functions:
        return jsonify({'error': f'Index {index_name} not supported'}), 400
    
    try:
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(geometry) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        # Calculate the specified index
        index_function = index_functions[index_name]
        collection_with_index = collection.map(lambda img: img.addBands(index_function(img)))
        
        # Get the most recent image
        recent_image = collection_with_index.sort('system:time_start', False).first()
        
        if recent_image.getInfo() is None:
            return jsonify({'error': 'No satellite data available for the selected date range'}), 400
        
        # Get the index band
        index_band = recent_image.select(index_name)
        
        # Calculate statistics
        stats = index_band.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.min(),
                sharedInputs=True
            ).combine(
                ee.Reducer.max(),
                sharedInputs=True
            ),
            geometry=geometry,
            scale=10,
            maxPixels=1e10
        )
        
        index_stats = stats.getInfo()
        current_value = index_stats.get(f'{index_name}_mean', 0)
        min_value = index_stats.get(f'{index_name}_min', 0)
        max_value = index_stats.get(f'{index_name}_max', 0)
        
        # Get index description
        index_info = get_index_description(index_name)
        
        # Determine status based on index value
        status, color = get_index_status(index_name, current_value)
        
        # Generate visualization parameters with clean NDVI color palette
        min_val = viz_params.get('min', 0.0)
        max_val = viz_params.get('max', 1.0)
        # Clean NDVI color palette: red (low) -> yellow (medium) -> green (high)
        palette = viz_params.get('palette', 'd73027,f46d43,fdae61,fee08b,d9ef8b,a6d96a,66bd63,1a9850,006837')
        
        # Generate map ID for visualization
        vis_params = {
            'min': float(min_val),
            'max': float(max_val),
            'palette': palette.split(','),
            'opacity': 0.6
        }
        
        map_id = index_band.getMapId(vis_params)
        
        return jsonify({
            'current_value': current_value,
            'min_value': min_value,
            'max_value': max_value,
            'index_name': index_name,
            'status': status,
            'color': color,
            'description': index_info['description'],
            'best_use': index_info['best_use'],
            'range': index_info['range'],
            'tile_url': map_id['tile_fetcher'].url_format,
            'polygon': coordinates
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ndvi-at-point', methods=['POST'])
def get_ndvi_at_point():
    """Get NDVI value at a specific point"""
    try:
        data = request.get_json()
        lat = data.get('lat')
        lng = data.get('lng')
        start_date = data.get('start_date', '2024-01-01')
        end_date = data.get('end_date', '2024-12-31')
        
        if not lat or not lng:
            return jsonify({'error': 'Latitude and longitude required'}), 400
        
        # Create point geometry
        point = ee.Geometry.Point([lng, lat])
        
        # Get Sentinel-2 imagery
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(point) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        if collection.size().getInfo() == 0:
            return jsonify({'error': 'No satellite data available for this location'}), 404
        
        # Calculate NDVI
        def calculate_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)
        
        collection = collection.map(calculate_ndvi)
        
        # Get median NDVI
        ndvi_median = collection.select('NDVI').median()
        
        # Get NDVI value at point
        ndvi_value = ndvi_median.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=10,
            maxPixels=1e9
        ).get('NDVI').getInfo()
        
        if ndvi_value is None:
            return jsonify({'error': 'Could not retrieve NDVI value'}), 500
        
        # Determine vegetation status based on NDVI scale
        if ndvi_value < 0.1:
            status = 'Non-vegetated (water, clouds, snow, bare rock, urban)'
            color = '#8B4513'
        elif ndvi_value < 0.2:
            status = 'Bare soil or sparse, dry earth'
            color = '#D2691E'
        elif ndvi_value < 0.5:
            status = 'Sparse vegetation, grasslands, moisture-stressed crops'
            color = '#FFD700'
        elif ndvi_value <= 0.9:
            status = 'Dense, healthy vegetation (forests, robust crops, tropical jungles)'
            color = '#228B22'
        else:
            status = 'Very dense vegetation'
            color = '#006400'
        
        return jsonify({
            'ndvi_value': ndvi_value,
            'status': status,
            'color': color
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_index_status(index_name, value):
    """Determine status and color based on index value"""
    # Different indexes have different optimal ranges
    if index_name in ['NDVI', 'NDRE', 'MSAVI']:
        if value < 0.2:
            return 'Low Vegetation', '#e74c3c'
        elif value < 0.4:
            return 'Moderate Vegetation', '#f39c12'
        elif value < 0.6:
            return 'Good Vegetation', '#27ae60'
        else:
            return 'Excellent Vegetation', '#006400'
    elif index_name in ['NDMI', 'NDWI', 'SMI']:
        if value < -0.2:
            return 'Water Stress', '#e74c3c'
        elif value < 0.2:
            return 'Moderate Moisture', '#f39c12'
        else:
            return 'Good Moisture', '#27ae60'
    elif index_name in ['RECI', 'MCARI']:
        if value < 1:
            return 'Low Chlorophyll', '#e74c3c'
        elif value < 2:
            return 'Moderate Chlorophyll', '#f39c12'
        else:
            return 'High Chlorophyll', '#27ae60'
    else:  # PRI
        if value < -0.05:
            return 'High Stress', '#e74c3c'
        elif value < 0:
            return 'Moderate Stress', '#f39c12'
        else:
            return 'Healthy', '#27ae60'


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
        maxPixels=1e10
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
            maxPixels=1e10
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


def generate_multi_year_comparison(geometry, years):
    """Generate NDVI comparison across multiple years"""
    yearly_data = []
    
    for year in years:
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'
        
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(geometry) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        def add_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)
        
        collection_ndvi = collection.map(add_ndvi)
        
        if collection_ndvi.size().getInfo() == 0:
            continue
        
        # Calculate annual mean NDVI
        annual_composite = collection_ndvi.median()
        ndvi = annual_composite.select('NDVI')
        mean_ndvi = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10,
            maxPixels=1e10
        )
        
        yearly_data.append({
            'year': year,
            'ndvi': mean_ndvi.getInfo()['NDVI']
        })
    
    return pd.DataFrame(yearly_data)


def detect_seasonal_anomalies(geometry, start_date, end_date):
    """Detect seasonal anomalies in NDVI data"""
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(geometry) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    def add_ndvi(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)
    
    collection_ndvi = collection.map(add_ndvi)
    
    # Generate monthly time series
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    monthly_data = []
    current_year = start.year
    current_month = start.month
    
    while current_year < end.year or (current_year == end.year and current_month <= end.month):
        month_start = f'{current_year}-{current_month:02d}-01'
        if current_month == 12:
            month_end = f'{current_year+1}-01-01'
        else:
            month_end = f'{current_year}-{current_month+1:02d}-01'
        
        monthly_collection = collection_ndvi.filterDate(month_start, month_end)
        
        if monthly_collection.size().getInfo() > 0:
            monthly_composite = monthly_collection.median()
            ndvi = monthly_composite.select('NDVI')
            mean_ndvi = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=10,
                maxPixels=1e10
            )
            
            monthly_data.append({
                'date': f'{current_year}-{current_month:02d}-01',
                'month': current_month,
                'year': current_year,
                'ndvi': mean_ndvi.getInfo()['NDVI']
            })
        
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    
    df = pd.DataFrame(monthly_data)
    
    if len(df) == 0:
        return []
    
    # Calculate anomalies using z-score
    mean_ndvi = df['ndvi'].mean()
    std_ndvi = df['ndvi'].std()
    
    anomalies = []
    for _, row in df.iterrows():
        if std_ndvi > 0:
            z_score = (row['ndvi'] - mean_ndvi) / std_ndvi
            if abs(z_score) > 2:  # More than 2 standard deviations
                anomaly_type = 'high' if z_score > 0 else 'low'
                anomalies.append({
                    'date': row['date'],
                    'ndvi': row['ndvi'],
                    'z_score': z_score,
                    'type': anomaly_type,
                    'severity': abs(z_score)
                })
    
    return anomalies


@app.route('/api/fields', methods=['GET'])
def get_fields():
    """Get all saved fields"""
    try:
        fields = db.get_fields()
        return jsonify({'fields': fields})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fields', methods=['POST'])
def save_field():
    """Save a new field"""
    try:
        data = request.json
        name = data.get('name', 'Unnamed Field')
        coordinates = data.get('coordinates', [])
        
        if not coordinates:
            return jsonify({'error': 'No coordinates provided'}), 400
        
        field_id = db.save_field(name, coordinates)
        return jsonify({'id': field_id, 'message': 'Field saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fields/<int:field_id>', methods=['GET'])
def get_field(field_id):
    """Get a specific field"""
    try:
        field = db.get_field(field_id)
        if field:
            return jsonify(field)
        else:
            return jsonify({'error': 'Field not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fields/<int:field_id>', methods=['DELETE'])
def delete_field(field_id):
    """Delete a field"""
    try:
        if db.delete_field(field_id):
            return jsonify({'message': 'Field deleted successfully'})
        else:
            return jsonify({'error': 'Field not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/historical-analysis', methods=['POST'])
def historical_analysis():
    """API endpoint for multi-year historical trend analysis"""
    data = request.json
    coordinates = data.get('coordinates', [])
    years = data.get('years', [2022, 2023, 2024])
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    
    geometry = ee.Geometry.Polygon([coordinates])
    
    try:
        # Generate multi-year comparison
        yearly_comparison = generate_multi_year_comparison(geometry, years)
        
        # Calculate trend
        if len(yearly_comparison) > 1:
            yearly_comparison_sorted = yearly_comparison.sort_values('year')
            ndvi_values = yearly_comparison_sorted['ndvi'].values
            years_sorted = yearly_comparison_sorted['year'].values
            
            # Simple trend calculation
            if len(ndvi_values) >= 2:
                trend = (ndvi_values[-1] - ndvi_values[0]) / (years_sorted[-1] - years_sorted[0])
                trend_direction = 'increasing' if trend > 0 else 'decreasing' if trend < 0 else 'stable'
            else:
                trend = 0
                trend_direction = 'insufficient data'
        else:
            trend = 0
            trend_direction = 'insufficient data'
        
        return jsonify({
            'yearly_data': yearly_comparison.to_dict('records'),
            'trend': trend,
            'trend_direction': trend_direction
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomaly-detection', methods=['POST'])
def anomaly_detection():
    """API endpoint for seasonal anomaly detection"""
    data = request.json
    coordinates = data.get('coordinates', [])
    start_date = data.get('start_date', '2023-01-01')
    end_date = data.get('end_date', '2024-12-31')
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    
    geometry = ee.Geometry.Polygon([coordinates])
    
    try:
        anomalies = detect_seasonal_anomalies(geometry, start_date, end_date)
        
        return jsonify({
            'anomalies': anomalies,
            'count': len(anomalies)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/geojson', methods=['POST'])
def export_geojson():
    """API endpoint to export polygon as GeoJSON"""
    data = request.json
    coordinates = data.get('coordinates', [])
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    
    try:
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coordinates]
            },
            "properties": {
                "name": "Zenvuno Field",
                "export_date": datetime.now().isoformat()
            }
        }
        
        return jsonify(geojson)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/crops', methods=['GET'])
def get_available_crops():
    """Get list of available crops for NDVI comparison"""
    try:
        from crop_ndvi_ranges import CROP_NDVI_RANGES
        crops = []
        for crop_key, crop_info in CROP_NDVI_RANGES.items():
            crops.append({
                'key': crop_key,
                'name': crop_info['name'],
                'stages': list(crop_info['stages'].keys())
            })
        return jsonify({'crops': crops})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/crop-compare', methods=['POST'])
def compare_crop_ndvi():
    """Compare NDVI value to crop-specific expected ranges"""
    data = request.json
    ndvi_value = data.get('ndvi_value')
    crop_type = data.get('crop_type')
    growth_stage = data.get('growth_stage')
    
    if ndvi_value is None:
        return jsonify({'error': 'NDVI value required'}), 400
    if not crop_type:
        return jsonify({'error': 'Crop type required'}), 400
    if not growth_stage:
        return jsonify({'error': 'Growth stage required'}), 400
    
    try:
        comparison = compare_ndvi_to_range(ndvi_value, crop_type, growth_stage)
        return jsonify(comparison)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ndvi-change-alerts', methods=['POST'])
def ndvi_change_alerts():
    """Detect significant NDVI changes between two time periods"""
    data = request.json
    coordinates = data.get('coordinates', [])
    start_date1 = data.get('start_date1')
    end_date1 = data.get('end_date1')
    start_date2 = data.get('start_date2')
    end_date2 = data.get('end_date2')
    threshold = data.get('threshold', 0.15)  # 15% change threshold
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    if not all([start_date1, end_date1, start_date2, end_date2]):
        return jsonify({'error': 'All date parameters required'}), 400
    
    geometry = ee.Geometry.Polygon([coordinates])
    
    try:
        def calculate_mean_ndvi_for_period(geometry, start_date, end_date):
            collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterBounds(geometry) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            collection_ndvi = collection.map(add_ndvi)
            
            if collection_ndvi.size().getInfo() == 0:
                return None
            
            composite = collection_ndvi.median()
            ndvi = composite.select('NDVI')
            mean_ndvi = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=10,
                maxPixels=1e10
            )
            
            return mean_ndvi.getInfo()['NDVI']
        
        ndvi1 = calculate_mean_ndvi_for_period(geometry, start_date1, end_date1)
        ndvi2 = calculate_mean_ndvi_for_period(geometry, start_date2, end_date2)
        
        if ndvi1 is None or ndvi2 is None:
            return jsonify({'error': 'No satellite data available for one or both time periods'}), 400
        
        change = ndvi2 - ndvi1
        percent_change = (change / ndvi1) * 100 if ndvi1 != 0 else 0
        
        alerts = []
        if abs(percent_change) > threshold * 100:
            if change < 0:
                severity = 'critical' if abs(percent_change) > threshold * 200 else 'high'
                alerts.append({
                    'type': 'decrease',
                    'severity': severity,
                    'message': f'NDVI dropped by {abs(percent_change):.1f}% (from {ndvi1:.3f} to {ndvi2:.3f})',
                    'period1_start': start_date1,
                    'period1_end': end_date1,
                    'period2_start': start_date2,
                    'period2_end': end_date2,
                    'ndvi1': ndvi1,
                    'ndvi2': ndvi2,
                    'change': change,
                    'percent_change': percent_change
                })
            else:
                severity = 'moderate' if abs(percent_change) > threshold * 200 else 'low'
                alerts.append({
                    'type': 'increase',
                    'severity': severity,
                    'message': f'NDVI increased by {percent_change:.1f}% (from {ndvi1:.3f} to {ndvi2:.3f})',
                    'period1_start': start_date1,
                    'period1_end': end_date1,
                    'period2_start': start_date2,
                    'period2_end': end_date2,
                    'ndvi1': ndvi1,
                    'ndvi2': ndvi2,
                    'change': change,
                    'percent_change': percent_change
                })
        
        return jsonify({
            'alerts': alerts,
            'ndvi1': ndvi1,
            'ndvi2': ndvi2,
            'change': change,
            'percent_change': percent_change,
            'has_alerts': len(alerts) > 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/vra-zones', methods=['POST'])
def generate_vra_zones():
    """Generate variable rate application zones based on NDVI"""
    data = request.json
    coordinates = data.get('coordinates', [])
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    if not start_date or not end_date:
        return jsonify({'error': 'Start and end dates required'}), 400
    
    geometry = ee.Geometry.Polygon([coordinates])
    
    try:
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(geometry) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        def add_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)
        
        collection_ndvi = collection.map(add_ndvi)
        
        if collection_ndvi.size().getInfo() == 0:
            return jsonify({'error': 'No satellite data available for the selected date range'}), 400
        
        composite = collection_ndvi.median()
        ndvi = composite.select('NDVI')
        
        # Get NDVI statistics for zoning
        stats = ndvi.reduceRegion(
            reducer=ee.Reducer.percentiles([25, 50, 75]),
            geometry=geometry,
            scale=10,
            maxPixels=1e10
        )
        
        ndvi_stats = stats.getInfo()
        p25 = ndvi_stats.get('NDVI_p25', 0.3)
        p50 = ndvi_stats.get('NDVI_p50', 0.5)
        p75 = ndvi_stats.get('NDVI_p75', 0.7)
        
        # Define zones based on NDVI percentiles
        zones = [
            {
                'zone': 'low',
                'name': 'Low Productivity Zone',
                'ndvi_range': [0, p25],
                'description': 'Low vigor - minimal input recommended',
                'application_rate': 0.5,
                'color': '#e74c3c'
            },
            {
                'zone': 'medium',
                'name': 'Medium Productivity Zone',
                'ndvi_range': [p25, p75],
                'description': 'Moderate vigor - standard application rate',
                'application_rate': 1.0,
                'color': '#f39c12'
            },
            {
                'zone': 'high',
                'name': 'High Productivity Zone',
                'ndvi_range': [p75, 1.0],
                'description': 'High vigor - maximum input for yield potential',
                'application_rate': 1.5,
                'color': '#27ae60'
            }
        ]
        
        # Generate map ID for visualization
        zone_vis = {
            'min': 0,
            'max': 1,
            'palette': ['red', 'yellow', 'green'],
            'opacity': 0.7
        }
        
        zone_map_id = ndvi.getMapId(zone_vis)
        
        return jsonify({
            'zones': zones,
            'statistics': ndvi_stats,
            'zone_tile_url': zone_map_id['tile_fetcher'].url_format,
            'recommendations': {
                'low_zone': 'Apply minimal inputs - focus on soil improvement',
                'medium_zone': 'Apply standard rates - monitor response',
                'high_zone': 'Apply maximum rates for optimal yield'
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/desiccation-planning', methods=['POST'])
def desiccation_planning():
    """Analyze NDVI patterns for desiccation planning and harvest optimization"""
    data = request.json
    coordinates = data.get('coordinates', [])
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    if not start_date or not end_date:
        return jsonify({'error': 'Start and end dates required'}), 400
    
    geometry = ee.Geometry.Polygon([coordinates])
    
    try:
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(geometry) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        def add_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)
        
        collection_ndvi = collection.map(add_ndvi)
        
        if collection_ndvi.size().getInfo() == 0:
            return jsonify({'error': 'No satellite data available for the selected date range'}), 400
        
        composite = collection_ndvi.median()
        ndvi = composite.select('NDVI')
        
        # Get NDVI statistics for maturity analysis
        stats = ndvi.reduceRegion(
            reducer=ee.Reducer.percentiles([20, 40, 60, 80]),
            geometry=geometry,
            scale=10,
            maxPixels=1e10
        )
        
        ndvi_stats = stats.getInfo()
        p20 = ndvi_stats.get('NDVI_p20', 0.2)
        p40 = ndvi_stats.get('NDVI_p40', 0.4)
        p60 = ndvi_stats.get('NDVI_p60', 0.6)
        p80 = ndvi_stats.get('NDVI_p80', 0.8)
        
        # Categorize maturity zones based on NDVI
        maturity_zones = [
            {
                'zone': 'early_maturity',
                'name': 'Early Maturity Zone',
                'ndvi_range': [p20, p40],
                'description': 'Behind schedule - needs desiccant application',
                'action': 'Apply desiccant to accelerate drying',
                'priority': 'high',
                'color': '#e74c3c'
            },
            {
                'zone': 'on_schedule',
                'name': 'On Schedule Zone',
                'ndvi_range': [p40, p60],
                'description': 'Optimal maturity - monitor for timing',
                'action': 'Monitor closely, apply desiccant if needed',
                'priority': 'medium',
                'color': '#f39c12'
            },
            {
                'zone': 'advanced_maturity',
                'name': 'Advanced Maturity Zone',
                'ndvi_range': [p60, p80],
                'description': 'Ahead of schedule - may not need desiccant',
                'action': 'Consider no treatment or reduced rate',
                'priority': 'low',
                'color': '#27ae60'
            },
            {
                'zone': 'over_mature',
                'name': 'Over-Mature Zone',
                'ndvi_range': [p80, 1.0],
                'description': 'Very advanced - harvest immediately',
                'action': 'Harvest as soon as possible',
                'priority': 'critical',
                'color': '#8B4513'
            }
        ]
        
        # Generate map ID for visualization
        maturity_vis = {
            'min': 0,
            'max': 1,
            'palette': ['red', 'orange', 'yellow', 'green'],
            'opacity': 0.7
        }
        
        maturity_map_id = ndvi.getMapId(maturity_vis)
        
        return jsonify({
            'maturity_zones': maturity_zones,
            'statistics': ndvi_stats,
            'maturity_tile_url': maturity_map_id['tile_fetcher'].url_format,
            'harvest_recommendations': {
                'total_area_coverage': '100% of field analyzed',
                'uniformity_score': 'Based on NDVI variance',
                'optimal_harvest_window': 'Target when 70-80% of field is in optimal maturity zone',
                'desiccant_strategy': 'Focus on early maturity zones first, then reassess'
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pgr-zones', methods=['POST'])
def pgr_zones():
    """Generate plant growth regulator application zones based on growth vigor"""
    data = request.json
    coordinates = data.get('coordinates', [])
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    if not start_date or not end_date:
        return jsonify({'error': 'Start and end dates required'}), 400
    
    geometry = ee.Geometry.Polygon([coordinates])
    
    try:
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(geometry) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        def add_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)
        
        collection_ndvi = collection.map(add_ndvi)
        
        if collection_ndvi.size().getInfo() == 0:
            return jsonify({'error': 'No satellite data available for the selected date range'}), 400
        
        composite = collection_ndvi.median()
        ndvi = composite.select('NDVI')
        
        # Get NDVI statistics for growth vigor analysis
        stats = ndvi.reduceRegion(
            reducer=ee.Reducer.percentiles([33, 66]),
            geometry=geometry,
            scale=10,
            maxPixels=1e10
        )
        
        ndvi_stats = stats.getInfo()
        p33 = ndvi_stats.get('NDVI_p33', 0.33)
        p66 = ndvi_stats.get('NDVI_p66', 0.66)
        
        # Categorize growth vigor zones for PGR application
        pgr_zones = [
            {
                'zone': 'low_vigor',
                'name': 'Low Vigor Zone',
                'ndvi_range': [0, p33],
                'description': 'Weak growth - no PGR needed',
                'pgr_rate': 0,
                'action': 'No PGR application - focus on nutrition',
                'color': '#3498db'
            },
            {
                'zone': 'moderate_vigor',
                'name': 'Moderate Vigor Zone',
                'ndvi_range': [p33, p66],
                'description': 'Normal growth - standard PGR rate',
                'pgr_rate': 1.0,
                'action': 'Apply standard PGR rate for uniformity',
                'color': '#f39c12'
            },
            {
                'zone': 'high_vigor',
                'name': 'High Vigor Zone',
                'ndvi_range': [p66, 1.0],
                'description': 'Excessive growth - high PGR rate needed',
                'pgr_rate': 1.5,
                'action': 'Apply higher PGR rate to control lodging',
                'color': '#e74c3c'
            }
        ]
        
        # Generate map ID for visualization
        pgr_vis = {
            'min': 0,
            'max': 1,
            'palette': ['blue', 'yellow', 'red'],
            'opacity': 0.7
        }
        
        pgr_map_id = ndvi.getMapId(pgr_vis)
        
        return jsonify({
            'pgr_zones': pgr_zones,
            'statistics': ndvi_stats,
            'pgr_tile_url': pgr_map_id['tile_fetcher'].url_format,
            'pgr_recommendations': {
                'lodging_risk': 'High vigor zones have increased lodging risk',
                'uniformity_goal': 'Target uniform maturity across field',
                'application_strategy': 'Zone-specific rates for optimal growth regulation',
                'timing': 'Apply during active vegetative growth stage'
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calculate-ndvi', methods=['POST'])
def calculate_ndvi_old():
    """API endpoint to calculate NDVI for a polygon and generate satellite imagery"""
    data = request.json
    coordinates = data.get('coordinates', [])
    start_date = data.get('start_date', '2024-01-01')
    end_date = data.get('end_date', '2025-01-01')
    viz_params = data.get('viz_params', {})
    satellite_source = data.get('satellite_source', 'sentinel2')  # sentinel2, landsat
    
    if not coordinates:
        return jsonify({'error': 'No coordinates provided'}), 400
    
    # Create polygon from coordinates
    geometry = ee.Geometry.Polygon([coordinates])
    
    try:
        # Select satellite data source
        if satellite_source == 'landsat':
            collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2') \
                .filterBounds(geometry) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUD_COVER', 20))
            
            # Landsat NDVI calculation (NIR = Band 5, Red = Band 4)
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            # Landsat RGB bands (Band 4, 3, 2)
            satellite_bands = ['SR_B4', 'SR_B3', 'SR_B2']
            satellite_vis = {'min': 0, 'max': 30000, 'bands': satellite_bands}
        else:
            # Default to Sentinel-2
            collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterBounds(geometry) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            satellite_bands = ['B4', 'B3', 'B2']
            satellite_vis = {'min': 0, 'max': 3000, 'bands': satellite_bands}
        
        collection_ndvi = collection.map(add_ndvi)
        
        # Check if collection has any images
        if collection_ndvi.size().getInfo() == 0:
            return jsonify({'error': 'No satellite images found for the selected date range. Try expanding the date range or switching to Sentinel-2.'}), 400
        
        # Get the most recent cloud-free image
        recent_image = collection_ndvi.sort('system:time_start', False).first()
        
        if recent_image is None:
            return jsonify({'error': 'No valid images found after filtering. Try expanding the date range.'}), 400
        
        # Calculate mean NDVI over the polygon
        ndvi = recent_image.select('NDVI')
        mean_ndvi = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10,
            maxPixels=1e10
        )
        
        current_ndvi = mean_ndvi.getInfo()['NDVI']
        
        # Generate time series
        timeseries = generate_ndvi_timeseries(geometry, start_date, end_date)
        
        # Interpret results
        status = interpret_ndvi(current_ndvi)
        color = get_ndvi_color(current_ndvi)
        
        # Generate map ID for satellite imagery
        satellite_vis = {
            'min': 0,
            'max': 3000,
            'bands': ['B4', 'B3', 'B2']  # RGB
        }
        
        satellite_map_id = recent_image.getMapId(satellite_vis)
        
        # Generate map ID for NDVI imagery with custom parameters
        ndvi_min = viz_params.get('min', 0)
        ndvi_max = viz_params.get('max', 1)
        ndvi_palette = viz_params.get('palette', 'red,yellow,green').split(',')
        
        ndvi_vis = {
            'min': ndvi_min,
            'max': ndvi_max,
            'palette': ndvi_palette
        }
        
        ndvi_map_id = recent_image.select('NDVI').getMapId(ndvi_vis)
        
        return jsonify({
            'current_ndvi': round(current_ndvi, 3),
            'status': status,
            'color': color,
            'timeseries': timeseries.to_dict('records'),
            'polygon': coordinates,
            'satellite_tile_url': satellite_map_id['tile_fetcher'].url_format,
            'ndvi_tile_url': ndvi_map_id['tile_fetcher'].url_format
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
