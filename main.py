"""Collect weather data from Open-Meteo and prepare SMS-ready payloads."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen
from flask import Flask, jsonify, request


BASE_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_LOCATION_NAME = "Dodoma, Tanzania"
DEFAULT_LATITUDE = -6.1630
DEFAULT_LONGITUDE = 35.7516
DEFAULT_TIMEZONE = "Africa/Dar_es_Salaam"
DEFAULT_OUTPUT_FILE = "weather_sms_payload.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5001

TANZANIA_BBOX = {
	"min_lat": -11.7613,
	"max_lat": -0.9853,
	"min_lon": 29.3272,
	"max_lon": 40.4432,
}

WEATHER_CODE_MAP = {
	0: "Clear sky",
	1: "Mainly clear",
	2: "Partly cloudy",
	3: "Overcast",
	45: "Fog",
	48: "Rime fog",
	51: "Light drizzle",
	53: "Moderate drizzle",
	55: "Dense drizzle",
	56: "Freezing drizzle",
	57: "Heavy freezing drizzle",
	61: "Slight rain",
	63: "Moderate rain",
	65: "Heavy rain",
	66: "Freezing rain",
	67: "Heavy freezing rain",
	71: "Slight snow",
	73: "Moderate snow",
	75: "Heavy snow",
	77: "Snow grains",
	80: "Slight showers",
	81: "Moderate showers",
	82: "Violent showers",
	85: "Slight snow showers",
	86: "Heavy snow showers",
	95: "Thunderstorm",
	96: "Thunderstorm + hail",
	99: "Heavy thunderstorm + hail",
}

app = Flask(__name__)


def fetch_weather(
	latitude: float, longitude: float, timezone: str = "auto", forecast_days: int = 7
) -> dict[str, Any]:
	"""Fetch current, hourly, and daily forecast data from Open-Meteo."""
	params = {
		"latitude": latitude,
		"longitude": longitude,
		"timezone": timezone,
		"current": ",".join(
			[
				"temperature_2m",
				"relative_humidity_2m",
				"apparent_temperature",
				"is_day",
				"precipitation",
				"weather_code",
				"wind_speed_10m",
			]
		),
		"hourly": ",".join(
			[
				"temperature_2m",
				"relative_humidity_2m",
				"precipitation_probability",
				"weather_code",
				"wind_speed_10m",
			]
		),
		"daily": ",".join(
			[
				"weather_code",
				"temperature_2m_max",
				"temperature_2m_min",
				"sunrise",
				"sunset",
				"precipitation_sum",
			]
		),
		"forecast_days": forecast_days,
	}
	url = f"{BASE_URL}?{urlencode(params)}"
	with urlopen(url, timeout=20) as response:
		return json.loads(response.read().decode("utf-8"))


def dominant_condition(conditions: list[str]) -> str:
	"""Return the most common condition string in a list."""
	clean_conditions = [condition for condition in conditions if condition]
	if not clean_conditions:
		return "Unknown"
	return max(set(clean_conditions), key=clean_conditions.count)


def sample_bbox_points(bbox: dict[str, float]) -> list[dict[str, float | str]]:
	"""Create representative sample points from a bounding box."""
	center_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2
	center_lon = (bbox["min_lon"] + bbox["max_lon"]) / 2
	points = [
		{"name": "north_west", "lat": bbox["max_lat"], "lon": bbox["min_lon"]},
		{"name": "north_east", "lat": bbox["max_lat"], "lon": bbox["max_lon"]},
		{"name": "south_west", "lat": bbox["min_lat"], "lon": bbox["min_lon"]},
		{"name": "south_east", "lat": bbox["min_lat"], "lon": bbox["max_lon"]},
		{"name": "center", "lat": center_lat, "lon": center_lon},
	]

	unique_points: list[dict[str, float | str]] = []
	seen: set[tuple[float, float]] = set()
	for point in points:
		key = (round(float(point["lat"]), 4), round(float(point["lon"]), 4))
		if key in seen:
			continue
		seen.add(key)
		unique_points.append(point)
	return unique_points


def calculate_bounding_box(points: list[dict[str, float]]) -> dict[str, float]:
	"""Calculate a bounding box from a list of latitude/longitude pairs."""
	lats = [point["lat"] for point in points]
	lons = [point["lon"] for point in points]
	return {
		"min_lat": min(lats),
		"max_lat": max(lats),
		"min_lon": min(lons),
		"max_lon": max(lons),
	}


def normalize_points(raw_points: Any, expected_count: int = 3) -> list[dict[str, float]]:
	"""Validate and normalize a fixed number of input coordinates."""
	if not isinstance(raw_points, list) or len(raw_points) != expected_count:
		raise ValueError(f"Provide exactly {expected_count} coordinate points.")

	normalized_points: list[dict[str, float]] = []
	for raw_point in raw_points:
		if isinstance(raw_point, dict):
			lat = raw_point.get("lat", raw_point.get("latitude"))
			lon = raw_point.get("lon", raw_point.get("longitude"))
		elif isinstance(raw_point, (list, tuple)) and len(raw_point) == 2:
			lat, lon = raw_point
		else:
			raise ValueError(
				"Each point must be an object with lat/lon or a two-item list [lat, lon]."
			)

		if lat is None or lon is None:
			raise ValueError("Each point must include both latitude and longitude.")

		normalized_points.append({"lat": float(lat), "lon": float(lon)})

	return normalized_points


def parse_query_points(expected_count: int = 3) -> list[dict[str, float]]:
	"""Read coordinate pairs from query parameters like lat1/lon1 ... latN/lonN."""
	points: list[dict[str, float]] = []
	for index in range(1, expected_count + 1):
		lat = request.args.get(f"lat{index}", type=float)
		lon = request.args.get(f"lon{index}", type=float)
		if lat is None or lon is None:
			raise ValueError(
				f"Provide query parameters lat{index} and lon{index} for all {expected_count} points."
			)
		points.append({"lat": lat, "lon": lon})
	return points


def summarize_hourly(hourly: dict[str, list[Any]], hours: int = 12) -> dict[str, Any]:
	"""Build compact hourly stats for the next N hours."""
	temperatures = hourly.get("temperature_2m", [])[:hours]
	rain_prob = hourly.get("precipitation_probability", [])[:hours]
	wind_speed = hourly.get("wind_speed_10m", [])[:hours]
	weather_codes = hourly.get("weather_code", [])[:hours]

	if not temperatures:
		return {
			"hours_considered": 0,
			"temp_min": None,
			"temp_max": None,
			"max_rain_probability": None,
			"max_wind_speed": None,
			"dominant_weather": "Unknown",
		}

	dominant_code = max(set(weather_codes), key=weather_codes.count) if weather_codes else None
	return {
		"hours_considered": len(temperatures),
		"temp_min": min(temperatures),
		"temp_max": max(temperatures),
		"max_rain_probability": max(rain_prob) if rain_prob else None,
		"max_wind_speed": max(wind_speed) if wind_speed else None,
		"dominant_weather": WEATHER_CODE_MAP.get(dominant_code, "Unknown"),
	}


def summarize_today(weather_data: dict[str, Any]) -> dict[str, Any]:
	"""Build a detailed summary for today that is useful in an SMS context."""
	current = weather_data.get("current", {})
	daily = weather_data.get("daily", {})
	hourly_summary = summarize_hourly(weather_data.get("hourly", {}), hours=12)

	weather_code = (daily.get("weather_code") or [None])[0]
	today_precipitation = (daily.get("precipitation_sum") or [None])[0]
	sunrise = (daily.get("sunrise") or [None])[0]
	sunset = (daily.get("sunset") or [None])[0]
	today_max = (daily.get("temperature_2m_max") or [None])[0]
	today_min = (daily.get("temperature_2m_min") or [None])[0]

	return {
		"date": (daily.get("time") or [None])[0],
		"current_temperature": current.get("temperature_2m"),
		"apparent_temperature": current.get("apparent_temperature"),
		"humidity": current.get("relative_humidity_2m"),
		"current_condition": WEATHER_CODE_MAP.get(current.get("weather_code"), "Unknown"),
		"today_condition": WEATHER_CODE_MAP.get(weather_code, "Unknown"),
		"temperature_min": today_min,
		"temperature_max": today_max,
		"wind_speed": current.get("wind_speed_10m"),
		"precipitation_today": today_precipitation,
		"rain_risk_next_12h": hourly_summary.get("max_rain_probability"),
		"wind_peak_next_12h": hourly_summary.get("max_wind_speed"),
		"likely_weather_next_12h": hourly_summary.get("dominant_weather"),
		"sunrise": sunrise,
		"sunset": sunset,
	}


def summarize_daily_window(daily: dict[str, list[Any]], days: int) -> dict[str, Any]:
	"""Summarize the next N days from the daily forecast block."""
	times = daily.get("time", [])[:days]
	tmax = daily.get("temperature_2m_max", [])[:days]
	tmin = daily.get("temperature_2m_min", [])[:days]
	rain = daily.get("precipitation_sum", [])[:days]
	weather_codes = daily.get("weather_code", [])[:days]

	if not times:
		return {
			"days_considered": 0,
			"period_start": None,
			"period_end": None,
			"temp_min": None,
			"temp_max": None,
			"total_precipitation": None,
			"dominant_weather": "Unknown",
		}

	dominant_code = max(set(weather_codes), key=weather_codes.count) if weather_codes else None
	return {
		"days_considered": len(times),
		"period_start": times[0],
		"period_end": times[-1],
		"temp_min": min(tmin) if tmin else None,
		"temp_max": max(tmax) if tmax else None,
		"total_precipitation": round(sum(rain), 2) if rain else None,
		"dominant_weather": WEATHER_CODE_MAP.get(dominant_code, "Unknown"),
	}


def build_sms_message(weather_data: dict[str, Any], days: int) -> str:
	"""Create a concise text message for an N-day forecast window."""
	current = weather_data.get("current", {})
	daily = weather_data.get("daily", {})
	window = summarize_daily_window(daily, days)
	today = summarize_today(weather_data)

	condition = WEATHER_CODE_MAP.get(current.get("weather_code"), "Unknown")

	lines = [
		f"Weather update {datetime.now().strftime('%Y-%m-%d %H:%M')}",
		f"Now: {current.get('temperature_2m', '?')}C, {condition}, wind {current.get('wind_speed_10m', '?')} km/h",
		f"Today: {today.get('temperature_min')}C to {today.get('temperature_max')}C, humidity {today.get('humidity')}%, rain {today.get('precipitation_today')} mm",
		f"Next 12h: rain risk {today.get('rain_risk_next_12h')}%, wind up to {today.get('wind_peak_next_12h')} km/h, {today.get('likely_weather_next_12h')}",
		f"Next {window.get('days_considered', 0)}d: {window.get('temp_min')}C to {window.get('temp_max')}C, {window.get('dominant_weather')}, rain {window.get('total_precipitation')} mm",
	]
	return " | ".join(lines)


def build_area_sms_message(summary: dict[str, Any]) -> str:
	"""Create a concise area-based SMS message from aggregated weather summaries."""
	today = summary.get("today", {})
	next_3_days = summary.get("next_3_days", {})
	next_7_days = summary.get("next_7_days", {})
	lines = [
		f"Weather area update {datetime.now().strftime('%Y-%m-%d %H:%M')}",
		f"Today: {today.get('temp_min')}C to {today.get('temp_max')}C, {today.get('dominant_weather')}, rain risk up to {today.get('max_rain_risk_next_12h')}%",
		f"Next 3d: {next_3_days.get('temp_min')}C to {next_3_days.get('temp_max')}C, {next_3_days.get('dominant_weather')}, rain up to {next_3_days.get('max_total_precipitation')} mm",
		f"Next 7d: {next_7_days.get('temp_min')}C to {next_7_days.get('temp_max')}C, {next_7_days.get('dominant_weather')}, rain up to {next_7_days.get('max_total_precipitation')} mm",
	]
	return " | ".join(lines)


def split_sms(text: str, segment_size: int = 160) -> list[str]:
	"""Split long content into SMS-sized segments."""
	return [text[i : i + segment_size] for i in range(0, len(text), segment_size)]


def prepare_sms_payload(
	latitude: float,
	longitude: float,
	timezone: str = "auto",
	location_name: str | None = None,
) -> dict[str, Any]:
	"""Collect weather information and package it for downstream SMS sending."""
	weather_data = fetch_weather(
		latitude=latitude,
		longitude=longitude,
		timezone=timezone,
		forecast_days=7,
	)

	payload = {
		"meta": {
			"source": "open-meteo",
			"scope": "point",
			"generated_at": datetime.now().isoformat(timespec="seconds"),
			"latitude": latitude,
			"longitude": longitude,
			"timezone": weather_data.get("timezone"),
			"location_name": location_name or f"{latitude:.4f},{longitude:.4f}",
		},
		"current": weather_data.get("current", {}),
		"today": summarize_today(weather_data),
		"hourly_summary_next_12h": summarize_hourly(weather_data.get("hourly", {}), hours=12),
		"daily_summary_next_3d": summarize_daily_window(weather_data.get("daily", {}), days=3),
		"daily_summary_next_7d": summarize_daily_window(weather_data.get("daily", {}), days=7),
		"daily": {
			"time": weather_data.get("daily", {}).get("time", []),
			"weather_code": weather_data.get("daily", {}).get("weather_code", []),
			"temperature_2m_max": weather_data.get("daily", {}).get("temperature_2m_max", []),
			"temperature_2m_min": weather_data.get("daily", {}).get("temperature_2m_min", []),
			"sunrise": weather_data.get("daily", {}).get("sunrise", []),
			"sunset": weather_data.get("daily", {}).get("sunset", []),
			"precipitation_sum": weather_data.get("daily", {}).get("precipitation_sum", []),
		},
	}

	sms_text_3d = build_sms_message(weather_data, days=3)
	sms_text_7d = build_sms_message(weather_data, days=7)
	payload["sms"] = {
		"next_3_days": {
			"message": sms_text_3d,
			"segments": split_sms(sms_text_3d),
			"segment_count": len(split_sms(sms_text_3d)),
		},
		"next_7_days": {
			"message": sms_text_7d,
			"segments": split_sms(sms_text_7d),
			"segment_count": len(split_sms(sms_text_7d)),
		},
	}
	return payload


def aggregate_area_payload(
	bbox: dict[str, float],
	timezone: str = DEFAULT_TIMEZONE,
	input_points: list[dict[str, float]] | None = None,
) -> dict[str, Any]:
	"""Build an aggregated weather payload for a bounding box area."""
	sample_points = sample_bbox_points(bbox)
	sample_payloads = [
		prepare_sms_payload(
			latitude=float(point["lat"]),
			longitude=float(point["lon"]),
			timezone=timezone,
			location_name=f"sample_{point['name']}",
		)
		for point in sample_points
	]

	today_entries = [payload["today"] for payload in sample_payloads]
	three_day_entries = [payload["daily_summary_next_3d"] for payload in sample_payloads]
	seven_day_entries = [payload["daily_summary_next_7d"] for payload in sample_payloads]

	area_summary = {
		"today": {
			"temp_min": min(entry["temperature_min"] for entry in today_entries),
			"temp_max": max(entry["temperature_max"] for entry in today_entries),
			"max_rain_risk_next_12h": max(entry["rain_risk_next_12h"] for entry in today_entries),
			"max_wind_peak_next_12h": max(entry["wind_peak_next_12h"] for entry in today_entries),
			"dominant_weather": dominant_condition(
				[entry["today_condition"] for entry in today_entries]
			),
		},
		"next_3_days": {
			"temp_min": min(entry["temp_min"] for entry in three_day_entries),
			"temp_max": max(entry["temp_max"] for entry in three_day_entries),
			"max_total_precipitation": max(
				entry["total_precipitation"] for entry in three_day_entries
			),
			"dominant_weather": dominant_condition(
				[entry["dominant_weather"] for entry in three_day_entries]
			),
		},
		"next_7_days": {
			"temp_min": min(entry["temp_min"] for entry in seven_day_entries),
			"temp_max": max(entry["temp_max"] for entry in seven_day_entries),
			"max_total_precipitation": max(
				entry["total_precipitation"] for entry in seven_day_entries
			),
			"dominant_weather": dominant_condition(
				[entry["dominant_weather"] for entry in seven_day_entries]
			),
		},
	}

	sms_text = build_area_sms_message(area_summary)
	return {
		"meta": {
			"source": "open-meteo",
			"scope": "area",
			"generated_at": datetime.now().isoformat(timespec="seconds"),
			"timezone": timezone,
			"sample_count": len(sample_payloads),
		},
		"bounding_box": bbox,
		"input_points": input_points or [],
		"area_summary": area_summary,
		"sample_points": [
			{
				"name": point["name"],
				"latitude": point["lat"],
				"longitude": point["lon"],
				"today": payload["today"],
				"daily_summary_next_3d": payload["daily_summary_next_3d"],
				"daily_summary_next_7d": payload["daily_summary_next_7d"],
			}
			for point, payload in zip(sample_points, sample_payloads)
		],
		"sms": {
			"message": sms_text,
			"segments": split_sms(sms_text),
			"segment_count": len(split_sms(sms_text)),
		},
	}


def prepare_tanzania_payload(timezone: str = DEFAULT_TIMEZONE) -> dict[str, Any]:
	"""Build an aggregated payload for the whole of Tanzania."""
	return aggregate_area_payload(
		bbox=TANZANIA_BBOX,
		timezone=timezone,
	)


@app.get("/")
def home() -> Any:
	"""Return a small API description."""
	return jsonify(
		{
			"service": "Open-Meteo SMS Weather API",
			"endpoints": {
				"GET /weather?lat=<lat>&lon=<lon>": "Get weather payload for one point.",
				"GET /weather": "Get Tanzania-wide area payload when no coordinates are provided.",
				"GET /weather/tanzania": "Get Tanzania-wide area payload.",
				"GET /weather/bounding-box?lat1=<>&lon1=<>&lat2=<>&lon2=<>&lat3=<>&lon3=<>": "Send 3 coordinate pairs and receive an aggregated area payload.",
			},
		}
	)


@app.get("/weather")
def get_weather() -> Any:
	"""Return a point payload or the Tanzania-wide payload when coordinates are omitted."""
	lat = request.args.get("lat", type=float)
	lon = request.args.get("lon", type=float)
	timezone = request.args.get("timezone", default=DEFAULT_TIMEZONE, type=str)
	location_name = request.args.get("location_name", type=str)

	if lat is None and lon is None:
		return jsonify(prepare_tanzania_payload(timezone=timezone))

	if lat is None or lon is None:
		return jsonify({"error": "Provide both lat and lon, or neither."}), 400

	payload = prepare_sms_payload(
		latitude=lat,
		longitude=lon,
		timezone=timezone,
		location_name=location_name,
	)
	return jsonify(payload)


@app.get("/weather/tanzania")
def get_tanzania_weather() -> Any:
	"""Return the aggregated Tanzania-wide payload."""
	timezone = request.args.get("timezone", default=DEFAULT_TIMEZONE, type=str)
	return jsonify(prepare_tanzania_payload(timezone=timezone))


@app.get("/weather/bounding-box")
def get_bounding_box_weather() -> Any:
	"""Return an aggregated payload for a custom bounding box built from 3 coordinates."""
	timezone = request.args.get("timezone", default=DEFAULT_TIMEZONE, type=str)

	try:
		points = parse_query_points(expected_count=3)
	except ValueError as error:
		return jsonify({"error": str(error)}), 400

	bbox = calculate_bounding_box(points)
	payload = aggregate_area_payload(
		bbox=bbox,
		timezone=timezone,
		input_points=points,
	)
	return jsonify(payload)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Fetch Open-Meteo weather data and prepare SMS-ready payload"
	)
	parser.add_argument("--lat", type=float, default=DEFAULT_LATITUDE, help="Latitude")
	parser.add_argument("--lon", type=float, default=DEFAULT_LONGITUDE, help="Longitude")
	parser.add_argument(
		"--timezone",
		default=DEFAULT_TIMEZONE,
		help="Timezone value accepted by Open-Meteo",
	)
	parser.add_argument(
		"--output",
		default=DEFAULT_OUTPUT_FILE,
		help="Path to the JSON file that will store the generated payload",
	)
	parser.add_argument(
		"--serve",
		action="store_true",
		help="Start the Flask API instead of writing a local JSON file",
	)
	parser.add_argument("--host", default=DEFAULT_HOST, help="Host for the Flask API")
	parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port for the Flask API")
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	if args.serve:
		app.run(host=args.host, port=args.port)
		return

	payload = prepare_sms_payload(
		latitude=args.lat,
		longitude=args.lon,
		timezone=args.timezone,
		location_name=DEFAULT_LOCATION_NAME,
	)
	output_path = Path(args.output)
	output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
	print(f"Saved weather payload to {output_path.resolve()}")


if __name__ == "__main__":
	main()
