"""Automatic weather alert broadcaster for registered users."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from twilio.rest import Client
import user_database as db
from WeatherAPI import prepare_sms_payload


# Alert thresholds - customize as needed
ALERT_THRESHOLDS = {
	"heavy_rain_probability": 80,  # % chance of rain in next 12h
	"high_wind": 40,  # km/h
	"temperature_extremes": {
		"too_hot": 35,  # Celsius
		"too_cold": 5,  # Celsius
	},
	"severe_weather_codes": [95, 96, 99],  # Thunderstorms with hail
}


class AlertBroadcaster:
	"""Send weather alerts to registered users based on conditions."""
	
	def __init__(self, twilio_account_sid: str = None, twilio_auth_token: str = None, twilio_phone: str = None):
		"""Initialize with Twilio credentials.
		
		Args:
			twilio_account_sid: Twilio Account SID (from environment if not provided)
			twilio_auth_token: Twilio Auth Token (from environment if not provided)
			twilio_phone: Twilio phone number (from environment if not provided)
		"""
		import os
		
		self.account_sid = twilio_account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
		self.auth_token = twilio_auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
		self.twilio_phone = twilio_phone or os.environ.get("TWILIO_PHONE_NUMBER")
		
		if self.account_sid and self.auth_token:
			self.client = Client(self.account_sid, self.auth_token)
		else:
			self.client = None
			print("WARNING: Twilio credentials not configured. Alerts will not be sent via SMS.")
	
	
	def should_alert(self, weather_data: Dict[str, Any]) -> Dict[str, str]:
		"""Evaluate if weather conditions warrant an alert.
		
		Returns:
			Dict with alert type and reason, or empty dict if no alert
		"""
		current = weather_data.get("current", {})
		today = weather_data.get("today", {})
		
		# Check for severe weather
		if current.get("weather_code") in ALERT_THRESHOLDS["severe_weather_codes"]:
			return {
				"type": "severe_weather",
				"reason": f"Severe weather detected: {current.get('weather_code')}"
			}
		
		# Check for rain probability
		rain_risk = today.get("rain_risk_next_12h")
		if rain_risk and rain_risk >= ALERT_THRESHOLDS["heavy_rain_probability"]:
			return {
				"type": "heavy_rain",
				"reason": f"High rainfall expected ({rain_risk}% chance)"
			}
		
		# Check for high wind
		max_wind = today.get("wind_peak_next_12h")
		if max_wind and max_wind >= ALERT_THRESHOLDS["high_wind"]:
			return {
				"type": "high_wind",
				"reason": f"Strong winds expected ({max_wind} km/h)"
			}
		
		# Check temperature extremes
		today_max = today.get("temperature_max")
		today_min = today.get("temperature_min")
		
		if today_max and today_max >= ALERT_THRESHOLDS["temperature_extremes"]["too_hot"]:
			return {
				"type": "extreme_heat",
				"reason": f"Very hot weather expected ({today_max}°C)"
			}
		
		if today_min and today_min <= ALERT_THRESHOLDS["temperature_extremes"]["too_cold"]:
			return {
				"type": "extreme_cold",
				"reason": f"Very cold weather expected ({today_min}°C)"
			}
		
		return {}
	
	
	def send_alert_sms(self, phone_number: str, alert_message: str) -> bool:
		"""Send an alert message via SMS.
		
		Args:
			phone_number: Recipient phone number
			alert_message: Alert message text
			
		Returns:
			True if sent successfully, False otherwise
		"""
		if not self.client or not self.twilio_phone:
			print(f"[DRY RUN] Would send to {phone_number}: {alert_message}")
			return False
		
		try:
			message = self.client.messages.create(
				body=alert_message,
				from_=self.twilio_phone,
				to=phone_number
			)
			print(f"Alert sent to {phone_number}: {message.sid}")
			return True
		except Exception as e:
			print(f"Error sending SMS to {phone_number}: {e}")
			return False
	
	
	def broadcast_alerts(self, check_all_users: bool = False) -> Dict[str, Any]:
		"""Check weather for all users and send alerts if needed.
		
		Args:
			check_all_users: If True, check all users even if recently alerted
			
		Returns:
			Summary of alerts sent and any errors
		"""
		# Ensure database is initialized
		db.init_database()
		
		users = db.get_all_users()
		if not users:
			return {
				"status": "no_users",
				"message": "No users registered in database",
				"alerts_sent": 0,
				"timestamp": datetime.now().isoformat()
			}
		
		results = {
			"total_users": len(users),
			"alerts_sent": 0,
			"alerts_skipped": 0,
			"errors": [],
			"timestamp": datetime.now().isoformat(),
			"details": []
		}
		
		for user in users:
			try:
				phone = user["phone_number"]
				location = user["location_name"]
				lat = user["latitude"]
				lon = user["longitude"]
				
				# Get weather for this user's location
				payload = prepare_sms_payload(
					latitude=lat,
					longitude=lon,
					location_name=location,
					translate=True  # Send in Swahili
				)
				
				weather_data = {
					"current": payload.get("current", {}),
					"today": payload.get("today", {}),
				}
				
				# Check if alert needed
				alert_info = self.should_alert(weather_data)
				
				if alert_info:
					# Build alert message
					alert_msg = (
						f"⚠️ ONYO LA TAKAKATAKA: {alert_info['reason']}\n"
						f"Eneo: {location}\n"
						f"Sehemu ya kumtegemeea: {payload['sms']['next_3_days']['message']}"
					)
					
					sent = self.send_alert_sms(phone, alert_msg)
					
					if sent:
						# Log the alert
						db.log_alert(phone, alert_msg)
						results["alerts_sent"] += 1
						results["details"].append({
							"phone": phone,
							"location": location,
							"alert_type": alert_info["type"],
							"sent": True
						})
					else:
						results["alerts_skipped"] += 1
						results["details"].append({
							"phone": phone,
							"location": location,
							"alert_type": alert_info["type"],
							"sent": False,
							"reason": "SMS send failed"
						})
				else:
					results["details"].append({
						"phone": phone,
						"location": location,
						"alert_type": "none",
						"reason": "No alert conditions met"
					})
			
			except Exception as e:
				results["errors"].append({
					"phone": phone if 'phone' in locals() else "unknown",
					"error": str(e)
				})
		
		return results


def main():
	"""Run alert broadcast when executed directly."""
	broadcaster = AlertBroadcaster()
	results = broadcaster.broadcast_alerts()
	
	print("\n" + "="*60)
	print("WEATHER ALERT BROADCAST REPORT")
	print("="*60)
	print(json.dumps(results, indent=2, default=str))
	print("="*60)


if __name__ == "__main__":
	main()
