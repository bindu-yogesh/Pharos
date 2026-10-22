import requests


url = "https://api.open-meteo.com/v1/forecast"

params = {
    "latitude": 12.83,
    "longitude": 75.57,
    "hourly": "temperature_2m,precipitation,visibility,weather_code",
    "forecast_days": 1,
    "timezone": "Asia/Kolkata",
}

response = requests.get(url, params=params)

print("Status code:", response.status_code)

data = response.json()

print("Location:", data["latitude"], data["longitude"])
print("First 5 times:", data["hourly"]["time"][:5])
print("First 5 precipitation values:",
      data["hourly"]["precipitation"][:5])
print("First 5 visibility values:",
      data["hourly"]["visibility"][:5])