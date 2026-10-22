import requests


url = "https://api.open-meteo.com/v1/elevation"

params = {
    "latitude": "12.83,12.84,12.85",
    "longitude": "75.57,75.58,75.59",
}

response = requests.get(url, params=params)

print("Status code:", response.status_code)

data = response.json()

print("Elevations:", data["elevation"])