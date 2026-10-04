# Open-Meteo Weather API Test

## Purpose

Test whether Open-Meteo can provide weather data required by the RoadSafe risk engine.

## API Endpoint

https://api.open-meteo.com/v1/forecast

## Parameters Tested

- Temperature
- Precipitation
- Visibility
- Weather code
- Hourly forecast
- Asia/Kolkata timezone

## Test Result

Status code: 200

The API successfully returned:

- Hourly timestamps
- Precipitation values
- Visibility values
- Location coordinates

## Sample Result

Precipitation:
0.0, 0.0, 0.0, 0.1, 0.1

Visibility:
12900 m, 11040 m, 9480 m, 6180 m, 9920 m

## Conclusion

Open-Meteo can be used as the weather data source for the RoadSafe risk engine.