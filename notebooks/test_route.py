import requests


# Temporary route points for testing OSRM.
# Final Shiradi Ghat coordinates will be verified before production use.
start = (75.71261, 12.87261)
end = (75.605, 12.806)


url = (
    f"https://router.project-osrm.org/route/v1/driving/"
    f"{start[0]},{start[1]};{end[0]},{end[1]}"
)

params = {
    "overview": "full",
    "geometries": "geojson",
}


response = requests.get(url, params=params)

print("Status code:", response.status_code)

data = response.json()

if data["code"] != "Ok":
    print("Routing failed:", data["code"])
    raise SystemExit(1)

route = data["routes"][0]

print("Route distance:", route["distance"], "meters")
print("Route duration:", route["duration"], "seconds")
print("Number of route points:", len(route["geometry"]["coordinates"]))