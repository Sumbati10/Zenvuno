"""
Vegetation Index Calculations for Zenvuno
Supports multiple satellite-derived vegetation indexes for comprehensive crop monitoring
"""

import ee

def calculate_ndvi(image):
    """Calculate NDVI (Normalized Difference Vegetation Index)"""
    return image.normalizedDifference(['B8', 'B4']).rename('NDVI')


def calculate_ndre(image):
    """Calculate NDRE (Normalized Difference Red Edge Index)
    Sensitive to chlorophyll in later stages of plant growth.
    Best for dense crops at mid-to-late stages.
    """
    # For Sentinel-2: B5 = Red Edge (704 nm), B8 = NIR (842 nm)
    return image.normalizedDifference(['B8', 'B5']).rename('NDRE')


def calculate_msavi(image):
    """Calculate MSAVI (Modified Soil Adjusted Vegetation Index)
    Minimizes the influence of bare soil on early growth readings.
    Best for early crop development, sparse vegetation.
    """
    # MSAVI = (2 * NIR + 1 - sqrt((2 * NIR + 1)^2 - 8 * (NIR - Red))) / 2
    nir = image.select('B8')
    red = image.select('B4')
    
    msavi = nir.multiply(2).add(1).subtract(
        nir.multiply(2).add(1).pow(2).subtract(
            nir.subtract(red).multiply(8)
        ).sqrt()
    ).divide(2).rename('MSAVI')
    
    return msavi


def calculate_reci(image):
    """Calculate RECI (Red Edge Chlorophyll Index)
    Highlights chlorophyll content.
    Best for nutrient monitoring and chlorophyll mapping.
    """
    # RECI = (NIR / Red Edge) - 1
    nir = image.select('B8')
    red_edge = image.select('B5')
    
    reci = nir.divide(red_edge).subtract(1).rename('RECI')
    return reci


def calculate_pri(image):
    """Calculate PRI (Photochemical Reflectance Index)
    Detects stress and changes in photosynthesis.
    Best for early signs of crop stress.
    """
    # PRI = (531 nm - 570 nm) / (531 nm + 570 nm)
    # Sentinel-2 doesn't have exact bands, we'll use B2 (Blue) and B3 (Green) as approximation
    # For better accuracy, Landsat 8 would be preferred
    blue = image.select('B2')
    green = image.select('B3')
    
    pri = blue.subtract(green).divide(blue.add(green)).rename('PRI')
    return pri


def calculate_mcari(image):
    """Calculate MCARI (Modified Chlorophyll Absorption Ratio Index)
    Focuses on chlorophyll absorption.
    Best for assessing plant health and pigment activity.
    """
    # MCARI = ((Red Edge - Red) - 0.2 * (Red Edge - Green)) * (Red Edge / Red)
    red_edge = image.select('B5')
    red = image.select('B4')
    green = image.select('B3')
    
    mcari = red_edge.subtract(red).subtract(
        red_edge.subtract(green).multiply(0.2)
    ).multiply(red_edge.divide(red)).rename('MCARI')
    
    return mcari


def calculate_ndmi(image):
    """Calculate NDMI (Normalized Difference Moisture Index)
    Estimates plant moisture content.
    Best for detecting drought or irrigation needs.
    """
    # NDMI = (NIR - SWIR) / (NIR + SWIR)
    # Sentinel-2: B8 = NIR, B11 = SWIR (1610 nm)
    nir = image.select('B8')
    swir = image.select('B11')
    
    ndmi = nir.subtract(swir).divide(nir.add(swir)).rename('NDMI')
    return ndmi


def calculate_smi(image):
    """Calculate SMI (Soil Moisture Index)
    Measures moisture directly in the soil.
    Best for early-stage water availability.
    """
    # SMI uses thermal and SWIR bands for soil moisture estimation
    # Using simplified version with available Sentinel-2 bands
    swir1 = image.select('B11')
    swir2 = image.select('B12')
    
    smi = swir1.subtract(swir2).divide(swir1.add(swir2)).rename('SMI')
    return smi


def calculate_ndwi(image):
    """Calculate NDWI (Normalized Difference Water Index)
    Highlights surface water and high moisture zones.
    Best for flooding or waterlogging analysis.
    """
    # NDWI = (Green - NIR) / (Green + NIR)
    green = image.select('B3')
    nir = image.select('B8')
    
    ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI')
    return ndwi


def calculate_all_indexes(image):
    """Calculate all supported vegetation indexes for an image"""
    indexes = ee.ImageCollection([
        calculate_ndvi(image),
        calculate_ndre(image),
        calculate_msavi(image),
        calculate_reci(image),
        calculate_pri(image),
        calculate_mcari(image),
        calculate_ndmi(image),
        calculate_smi(image),
        calculate_ndwi(image)
    ])
    
    return indexes.toBands()


def get_index_description(index_name):
    """Get description and best use case for each index"""
    descriptions = {
        'NDVI': {
            'description': 'Normalized Difference Vegetation Index - indicator of plant health',
            'best_use': 'General vegetation monitoring throughout the season',
            'range': '0 to 1 (plants), -1 to 0 (non-vegetation)',
            'color_scale': 'red-yellow-green'
        },
        'NDRE': {
            'description': 'Normalized Difference Red Edge Index - sensitive to chlorophyll in later growth stages',
            'best_use': 'Dense crops at mid-to-late stages',
            'range': '0 to 1',
            'color_scale': 'red-yellow-green'
        },
        'MSAVI': {
            'description': 'Modified Soil Adjusted Vegetation Index - minimizes bare soil influence',
            'best_use': 'Early crop development, sparse vegetation',
            'range': '-0.5 to 1',
            'color_scale': 'red-yellow-green'
        },
        'RECI': {
            'description': 'Red Edge Chlorophyll Index - highlights chlorophyll content',
            'best_use': 'Nutrient monitoring and chlorophyll mapping',
            'range': '0 to 5',
            'color_scale': 'blue-green-yellow-red'
        },
        'PRI': {
            'description': 'Photochemical Reflectance Index - detects stress and photosynthesis changes',
            'best_use': 'Early signs of crop stress',
            'range': '-0.1 to 0.1',
            'color_scale': 'red-yellow-green'
        },
        'MCARI': {
            'description': 'Modified Chlorophyll Absorption Ratio Index - focuses on chlorophyll absorption',
            'best_use': 'Assessing plant health and pigment activity',
            'range': '-0.5 to 2',
            'color_scale': 'blue-green-yellow-red'
        },
        'NDMI': {
            'description': 'Normalized Difference Moisture Index - estimates plant moisture content',
            'best_use': 'Detecting drought or irrigation needs',
            'range': '-1 to 1',
            'color_scale': 'white-blue-green'
        },
        'SMI': {
            'description': 'Soil Moisture Index - measures moisture directly in soil',
            'best_use': 'Early-stage water availability',
            'range': '-1 to 1',
            'color_scale': 'white-blue-green'
        },
        'NDWI': {
            'description': 'Normalized Difference Water Index - highlights surface water and high moisture zones',
            'best_use': 'Flooding or waterlogging analysis',
            'range': '-1 to 1',
            'color_scale': 'white-blue'
        }
    }
    
    return descriptions.get(index_name, {
        'description': 'Vegetation index',
        'best_use': 'General monitoring',
        'range': 'Variable',
        'color_scale': 'red-yellow-green'
    })


def get_available_indexes():
    """Return list of all available vegetation indexes"""
    return ['NDVI', 'NDRE', 'MSAVI', 'RECI', 'PRI', 'MCARI', 'NDMI', 'SMI', 'NDWI']


def get_recommended_index(growth_stage, crop_type=None):
    """Recommend the best vegetation index based on growth stage and crop type"""
    recommendations = {
        'early': {
            'primary': 'MSAVI',
            'secondary': 'SMI',
            'reason': 'Minimizes bare soil influence during sparse vegetation'
        },
        'mid': {
            'primary': 'NDVI',
            'secondary': 'NDRE',
            'reason': 'Standard vegetation monitoring with enhanced chlorophyll sensitivity'
        },
        'late': {
            'primary': 'NDRE',
            'secondary': 'RECI',
            'reason': 'Better penetration in dense canopies for chlorophyll assessment'
        },
        'stress_detection': {
            'primary': 'PRI',
            'secondary': 'NDVI',
            'reason': 'Early stress detection before visible symptoms'
        },
        'moisture': {
            'primary': 'NDMI',
            'secondary': 'SMI',
            'reason': 'Plant and soil moisture assessment'
        }
    }
    
    return recommendations.get(growth_stage, {
        'primary': 'NDVI',
        'secondary': 'NDRE',
        'reason': 'Standard vegetation monitoring'
    })
