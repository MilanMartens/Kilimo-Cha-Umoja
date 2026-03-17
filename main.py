"""Collect weather data from Open-Meteo and prepare SMS-ready payloads."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


BASE_URL = "https://api.open-meteo.com/v1/forecast"

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

	today_max = (daily.get("temperature_2m_max") or [None])[0]
	today_min = (daily.get("temperature_2m_min") or [None])[0]

	condition = WEATHER_CODE_MAP.get(current.get("weather_code"), "Unknown")

	lines = [
		f"Weather update {datetime.now().strftime('%Y-%m-%d %H:%M')}",
		f"Now: {current.get('temperature_2m', '?')}C, {condition}, wind {current.get('wind_speed_10m', '?')} km/h",
		f"Today: {today_min}C to {today_max}C",
		f"Next {window.get('days_considered', 0)}d: {window.get('temp_min')}C to {window.get('temp_max')}C, {window.get('dominant_weather')}, rain {window.get('total_precipitation')} mm",
	]
	return " | ".join(lines)


def split_sms(text: str, segment_size: int = 160) -> list[str]:
	"""Split long content into SMS-sized segments."""
	return [text[i : i + segment_size] for i in range(0, len(text), segment_size)]


def prepare_sms_payload(latitude: float, longitude: float, timezone: str = "auto") -> dict[str, Any]:
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
			"generated_at": datetime.now().isoformat(timespec="seconds"),
			"latitude": latitude,
			"longitude": longitude,
			"timezone": weather_data.get("timezone"),
		},
		"current": weather_data.get("current", {}),
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


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Fetch Open-Meteo weather data and prepare SMS-ready payload"
	)
	parser.add_argument("--lat", type=float, default=51.2194, help="Latitude")
	parser.add_argument("--lon", type=float, default=4.4025, help="Longitude")
	parser.add_argument("--timezone", default="auto", help="Timezone value accepted by Open-Meteo")
	parser.add_argument(
		"--output",
		default="weather_sms_payload.json",
		help="Path to the JSON file that will store the generated payload",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	payload = prepare_sms_payload(latitude=args.lat, longitude=args.lon, timezone=args.timezone)
	output_path = Path(args.output)
	output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
	print(f"Saved weather payload to {output_path.resolve()}")


if __name__ == "__main__":
	main()
