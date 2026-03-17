# First, install geopy if you haven't already
from flask import Flask, jsonify, request
from geopy.geocoders import Nominatim

app = Flask(__name__)
geolocator = Nominatim(user_agent="my_geocoder_app")


@app.route("/", methods=["GET"])
def index() -> tuple:
    return (
        jsonify(
            {
                "service": "Location Geocoding API",
                "endpoint": "/geocode",
                "usage": {
                    "forward": "/geocode?location=Antwerp,Belgium",
                    "reverse": "/geocode?lat=51.2194&lon=4.4025",
                },
            }
        ),
        200,
    )


@app.route("/geocode", methods=["GET"])
def geocode_endpoint() -> tuple:
    location_query = request.args.get("location", type=str)
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    if location_query:
        result = geolocator.geocode(location_query)
        if not result:
            return jsonify({"error": f"No result found for '{location_query}'"}), 404
        return (
            jsonify(
                {
                    "type": "forward",
                    "query": location_query,
                    "address": result.address,
                    "latitude": result.latitude,
                    "longitude": result.longitude,
                }
            ),
            200,
        )

    if lat is not None and lon is not None:
        result = geolocator.reverse((lat, lon))
        if not result:
            return jsonify({"error": f"No result found for coordinates ({lat}, {lon})"}), 404
        return (
            jsonify(
                {
                    "type": "reverse",
                    "query": {"lat": lat, "lon": lon},
                    "address": result.address,
                    "latitude": result.latitude,
                    "longitude": result.longitude,
                }
            ),
            200,
        )

    return (
        jsonify(
            {
                "error": "Provide either 'location' or both 'lat' and 'lon' query parameters."
            }
        ),
        400,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)