# Zenvuno - Vegetation Health Monitoring

MVP focused on NDVI (Normalized Difference Vegetation Index) analysis for agricultural areas.

## Project Goal

Prove the concept: "Given a farm boundary, Zenvuno can calculate NDVI and show vegetation health."

## Setup Instructions

### Quick Start (Recommended - No Python Setup)

The fastest way to test the concept is using the Google Earth Engine Code Editor:

1. Go to [Earth Engine Code Editor](https://code.earthengine.google.com/)
2. Copy the contents of `ndvi_calculator_js.js`
3. Paste it into the Code Editor
4. Click "Run" button
5. View results in the Console panel and map in the Layers panel

This approach requires no Python setup or authentication.

### Python Setup (Advanced)

If you prefer to use Python:

#### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing one)
3. Enable the Earth Engine API:
   - Search for "Earth Engine API" in the API Library
   - Click "Enable"

#### 2. Set Up Virtual Environment and Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. Authenticate with Google Earth Engine

```bash
python -c "import ee; ee.Authenticate()"
```

This will open a browser window where you'll authenticate with your Google account.

#### 4. Run the NDVI Calculator

```bash
python ndvi_calculator.py
```

**Note:** Python setup may require additional IAM permissions. The JavaScript approach in the Code Editor is recommended for initial testing.

This will:
- Calculate current NDVI for a test polygon
- Generate a monthly NDVI time series
- Export results to `ndvi_timeseries.csv`
- Display vegetation health interpretation

## NDVI Categories

| NDVI Range | Interpretation |
|------------|----------------|
| < 0.2 | Bare soil / very sparse vegetation |
| 0.2–0.4 | Low vegetation |
| 0.4–0.6 | Moderate vegetation |
| 0.6–0.8 | Healthy vegetation |
| > 0.8 | Very dense vegetation |

## Current Features

- ✅ NDVI calculation for user-defined polygons
- ✅ Monthly NDVI time series generation
- ✅ CSV export functionality
- ✅ Vegetation health interpretation

## Next Steps

1. Test with different farm boundaries
2. Integrate with a frontend map interface
3. Add data persistence (PostgreSQL)
4. Build user authentication
5. Scale to cover more regions

## Technical Stack

- **Backend**: Python
- **Earth Engine**: Google Earth Engine API
- **Data**: Sentinel-2 satellite imagery (10m resolution)
- **Output**: CSV, JSON (future)

## Data Source

Uses Sentinel-2 SR (Surface Reflectance) data from Google Earth Engine:
- Collection: `COPERNICUS/S2_SR_HARMONIZED`
- Bands: B8 (NIR), B4 (Red)
- Cloud filtering: < 20% cloud cover
