// Zenvuno NDVI Calculator - Google Earth Engine JavaScript
// Run this in the Earth Engine Code Editor: https://code.earthengine.google.com/

// Test polygon (example: a farm in Kenya)
var testPolygon = ee.Geometry.Polygon([
  [[36.06, -0.28], [36.07, -0.28], [36.07, -0.29], [36.06, -0.29], [36.06, -0.28]]
]);

// Date range for analysis
var startDate = '2024-01-01';
var endDate = '2025-01-01';

print('=== Zenvuno NDVI Calculator ===');
print('Calculating NDVI for test area in Kenya...');

// Get Sentinel-2 collection
var collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(testPolygon)
  .filterDate(startDate, endDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20));

// Calculate NDVI for each image
var addNDVI = function(image) {
  var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
  return image.addBands(ndvi);
};

var collectionNDVI = collection.map(addNDVI);

// Get the most recent cloud-free image
var recentImage = collectionNDVI.sort('system:time_start', false).first();

// Calculate mean NDVI over the polygon
var ndvi = recentImage.select('NDVI');
var meanNDVI = ndvi.reduceRegion({
  reducer: ee.Reducer.mean(),
  geometry: testPolygon,
  scale: 10,
  maxPixels: 1e9
});

print('Current NDVI:', meanNDVI.get('NDVI'));

// Interpret NDVI value
var ndviValue = meanNDVI.get('NDVI').getInfo();
var status = '';
if (ndviValue < 0.2) {
  status = 'Bare soil / very sparse vegetation';
} else if (ndviValue < 0.4) {
  status = 'Low vegetation';
} else if (ndviValue < 0.6) {
  status = 'Moderate vegetation';
} else if (ndviValue < 0.8) {
  status = 'Healthy vegetation';
} else {
  status = 'Very dense vegetation';
}

print('Status:', status);

// Generate monthly NDVI time series
print('\n=== Monthly NDVI Time Series ===');

var getMonthlyMean = function(year, month) {
  var monthStart = ee.Date.fromYMD(year, month, 1);
  var monthEnd = monthStart.advance(1, 'month');
  
  var monthlyCollection = collectionNDVI.filterDate(monthStart, monthEnd);
  
  var count = monthlyCollection.size();
  
  // Return null if no images for this month
  var monthlyNDVI = ee.Algorithms.If(
    count.gt(0),
    monthlyCollection.median().select('NDVI').reduceRegion({
      reducer: ee.Reducer.mean(),
      geometry: testPolygon,
      scale: 10,
      maxPixels: 1e9
    }).get('NDVI'),
    null
  );
  
  return {
    'date': monthStart.format('YYYY-MM-dd'),
    'NDVI': monthlyNDVI
  };
};

// Generate monthly data for 2024
var months = [];
for (var m = 1; m <= 12; m++) {
  var data = getMonthlyMean(2024, m);
  months.push(data);
}

print('Monthly NDVI values:', months);

// Create a chart
var chart = ui.Chart.array.values({
  array: ee.Array(months.map(function(m) {return m.NDVI})),
  axis: 0,
  xLabels: months.map(function(m) {return m.date})
}).setOptions({
  title: 'Monthly NDVI Time Series - 2024',
  hAxis: {title: 'Date'},
  vAxis: {title: 'NDVI'},
  lineWidth: 2,
  pointSize: 4
});

print(chart);

// Display the NDVI map on the map
Map.centerObject(testPolygon, 13);
Map.addLayer(recentImage.select('NDVI'), {
  min: 0,
  max: 1,
  palette: ['red', 'yellow', 'green']
}, 'NDVI');
Map.addLayer(testPolygon, {color: 'red'}, 'Farm Boundary');

print('\n=== Complete ===');
print('Check the "Layers" panel to see the NDVI map');
print('Check the "Console" panel for numerical results');
