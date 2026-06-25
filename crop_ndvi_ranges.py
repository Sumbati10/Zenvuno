"""
Crop-specific NDVI ranges for different growth stages
Based on typical NDVI values for common agricultural crops
"""

CROP_NDVI_RANGES = {
    "corn": {
        "name": "Corn/Maize",
        "stages": {
            "emergence": {"min": 0.1, "max": 0.2, "description": "Early growth"},
            "vegetative": {"min": 0.3, "max": 0.5, "description": "Active growth"},
            "flowering": {"min": 0.6, "max": 0.8, "description": "Peak biomass"},
            "maturity": {"min": 0.5, "max": 0.7, "description": "Ripening"},
            "harvest": {"min": 0.2, "max": 0.4, "description": "Ready for harvest"}
        }
    },
    "wheat": {
        "name": "Wheat",
        "stages": {
            "emergence": {"min": 0.15, "max": 0.25, "description": "Early growth"},
            "tillering": {"min": 0.3, "max": 0.45, "description": "Tillering stage"},
            "heading": {"min": 0.5, "max": 0.7, "description": "Grain formation"},
            "flowering": {"min": 0.65, "max": 0.85, "description": "Peak biomass"},
            "maturity": {"min": 0.4, "max": 0.6, "description": "Ripening"},
            "harvest": {"min": 0.15, "max": 0.35, "description": "Ready for harvest"}
        }
    },
    "soybean": {
        "name": "Soybean",
        "stages": {
            "emergence": {"min": 0.1, "max": 0.2, "description": "Early growth"},
            "vegetative": {"min": 0.35, "max": 0.55, "description": "Active growth"},
            "flowering": {"min": 0.6, "max": 0.8, "description": "Peak biomass"},
            "pod_filling": {"min": 0.55, "max": 0.75, "description": "Pod development"},
            "maturity": {"min": 0.3, "max": 0.5, "description": "Ripening"},
            "harvest": {"min": 0.15, "max": 0.35, "description": "Ready for harvest"}
        }
    },
    "rice": {
        "name": "Rice",
        "stages": {
            "transplanting": {"min": 0.1, "max": 0.2, "description": "After planting"},
            "tillering": {"min": 0.35, "max": 0.55, "description": "Tillering stage"},
            "panicle_initiation": {"min": 0.5, "max": 0.7, "description": "Panicle formation"},
            "flowering": {"min": 0.65, "max": 0.85, "description": "Peak biomass"},
            "maturity": {"min": 0.4, "max": 0.6, "description": "Ripening"},
            "harvest": {"min": 0.2, "max": 0.4, "description": "Ready for harvest"}
        }
    },
    "cotton": {
        "name": "Cotton",
        "stages": {
            "emergence": {"min": 0.15, "max": 0.25, "description": "Early growth"},
            "vegetative": {"min": 0.3, "max": 0.5, "description": "Active growth"},
            "flowering": {"min": 0.55, "max": 0.75, "description": "Peak biomass"},
            "boll_development": {"min": 0.5, "max": 0.7, "description": "Boll formation"},
            "maturity": {"min": 0.3, "max": 0.5, "description": "Boll opening"},
            "harvest": {"min": 0.15, "max": 0.35, "description": "Ready for harvest"}
        }
    },
    "sugarcane": {
        "name": "Sugarcane",
        "stages": {
            "establishment": {"min": 0.2, "max": 0.35, "description": "Early growth"},
            "grand_growth": {"min": 0.6, "max": 0.85, "description": "Peak biomass"},
            "maturation": {"min": 0.5, "max": 0.75, "description": "Sugar accumulation"},
            "harvest": {"min": 0.3, "max": 0.5, "description": "Ready for harvest"}
        }
    },
    "potato": {
        "name": "Potato",
        "stages": {
            "emergence": {"min": 0.15, "max": 0.25, "description": "Early growth"},
            "vegetative": {"min": 0.4, "max": 0.6, "description": "Active growth"},
            "tuber_initiation": {"min": 0.5, "max": 0.7, "description": "Tuber formation"},
            "tuber_bulking": {"min": 0.55, "max": 0.75, "description": "Tuber growth"},
            "maturity": {"min": 0.35, "max": 0.55, "description": "Vine senescence"},
            "harvest": {"min": 0.2, "max": 0.4, "description": "Ready for harvest"}
        }
    },
    "alfalfa": {
        "name": "Alfalfa",
        "stages": {
            "establishment": {"min": 0.2, "max": 0.35, "description": "Early growth"},
            "vegetative": {"min": 0.5, "max": 0.75, "description": "Active growth"},
            "bud_stage": {"min": 0.6, "max": 0.8, "description": "Bud formation"},
            "flowering": {"min": 0.65, "max": 0.85, "description": "Peak biomass"},
            "harvest": {"min": 0.4, "max": 0.6, "description": "Ready for harvest"}
        }
    },
    "canola": {
        "name": "Canola/Rapeseed",
        "stages": {
            "emergence": {"min": 0.1, "max": 0.2, "description": "Early growth"},
            "vegetative": {"min": 0.3, "max": 0.5, "description": "Active growth"},
            "flowering": {"min": 0.6, "max": 0.8, "description": "Peak biomass"},
            "pod_filling": {"min": 0.5, "max": 0.7, "description": "Pod development"},
            "maturity": {"min": 0.3, "max": 0.5, "description": "Ripening"},
            "harvest": {"min": 0.15, "max": 0.35, "description": "Ready for harvest"}
        }
    },
    "sunflower": {
        "name": "Sunflower",
        "stages": {
            "emergence": {"min": 0.1, "max": 0.2, "description": "Early growth"},
            "vegetative": {"min": 0.3, "max": 0.5, "description": "Active growth"},
            "flowering": {"min": 0.6, "max": 0.8, "description": "Peak biomass"},
            "seed_filling": {"min": 0.5, "max": 0.7, "description": "Seed development"},
            "maturity": {"min": 0.3, "max": 0.5, "description": "Ripening"},
            "harvest": {"min": 0.15, "max": 0.35, "description": "Ready for harvest"}
        }
    }
}

def get_crop_list():
    """Get list of available crops"""
    return list(CROP_NDVI_RANGES.keys())

def get_crop_stages(crop_type):
    """Get growth stages for a specific crop"""
    if crop_type in CROP_NDVI_RANGES:
        return CROP_NDVI_RANGES[crop_type]["stages"]
    return None

def compare_ndvi_to_range(ndvi_value, crop_type, growth_stage):
    """Compare NDVI value to expected range for crop and stage"""
    if crop_type not in CROP_NDVI_RANGES:
        return {"status": "unknown", "message": "Crop not found in database"}
    
    if growth_stage not in CROP_NDVI_RANGES[crop_type]["stages"]:
        return {"status": "unknown", "message": "Growth stage not found for this crop"}
    
    stage_info = CROP_NDVI_RANGES[crop_type]["stages"][growth_stage]
    min_ndvi = stage_info["min"]
    max_ndvi = stage_info["max"]
    
    if ndvi_value < min_ndvi:
        return {
            "status": "below_expected",
            "message": f"NDVI is below expected range for {growth_stage} stage",
            "expected_min": min_ndvi,
            "expected_max": max_ndvi,
            "actual": ndvi_value,
            "deviation": min_ndvi - ndvi_value
        }
    elif ndvi_value > max_ndvi:
        return {
            "status": "above_expected",
            "message": f"NDVI is above expected range for {growth_stage} stage",
            "expected_min": min_ndvi,
            "expected_max": max_ndvi,
            "actual": ndvi_value,
            "deviation": ndvi_value - max_ndvi
        }
    else:
        return {
            "status": "within_range",
            "message": f"NDVI is within expected range for {growth_stage} stage",
            "expected_min": min_ndvi,
            "expected_max": max_ndvi,
            "actual": ndvi_value,
            "deviation": 0
        }
