# Open-Meteo Elevation API Test

## Purpose

Test whether elevation data can be retrieved for route points for the RoadSafe risk engine.

## API Endpoint

https://api.open-meteo.com/v1/elevation

## Test

Three coordinate points were requested.

## Result

Status code: 200

Elevations returned:

- Point 1: 207 m
- Point 2: 500 m
- Point 3: 791 m

## Conclusion

The elevation API successfully returns elevation values for multiple coordinates.

This data can be used to calculate the slope of RoadSafe route segments.