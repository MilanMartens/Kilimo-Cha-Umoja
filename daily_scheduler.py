"""Daily weather broadcast scheduler for farmers in Tanzania.

Sends SMS to all registered farmers at 6:00 AM (Tanzania time) with next 7 days weather.
Also monitors for sudden weather changes and sends alerts when conditions change drastically.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import os

# Load environment variables from .env file if it exists
env_file = Path(".env")
if env_file.exists():
	with open(env_file) as f:
		for line in f:
			line = line.strip()
			if line and not line.startswith("#") and "=" in line:
				key, value = line.split("=", 1)
				os.environ[key.strip()] = value.strip()

import user_database as db
from WeatherAPI import prepare_sms_payload
from translator import translate_to_swahili


# Tanzania timezone
TZ_TANZANIA = pytz.timezone("Africa/Dar_es_Salaam")

# File to track previous weather for each farmer
WEATHER_CACHE_FILE = "weather_cache.json"

# Alert thresholds - what counts as "sudden change"
ALERT_THRESHOLDS = {
	"temperature_drop": 8,  # degrees C in 24h
	"temperature_spike": 8,  # degrees C in 24h
	"rain_probability_jump": 40,  # percentage point increase
	"wind_speed_increase": 15,  # km/h increase
	"weather_code_change": True,  # Any severe weather code change
}


class WeatherCache:
	"""Manage previous weather data to detect sudden changes."""
	
	def __init__(self, cache_file: str = WEATHER_CACHE_FILE):
		self.cache_file = Path(cache_file)
		self.data = self._load_cache()
	
	def _load_cache(self) -> Dict[str, Any]:
		"""Load cached weather from file."""
		if self.cache_file.exists():
			try:
				with open(self.cache_file, 'r') as f:
					return json.load(f)
			except Exception as e:
				print(f"Error loading cache: {e}")
		return {}
	
	def _save_cache(self):
		"""Save cache to file."""
		try:
			with open(self.cache_file, 'w') as f:
				json.dump(self.data, f, indent=2, default=str)
		except Exception as e:
			print(f"Error saving cache: {e}")
	
	def get_previous_weather(self, phone_number: str) -> Optional[Dict]:
		"""Get cached weather for a farmer."""
		return self.data.get(phone_number)
	
	def update_weather(self, phone_number: str, weather_data: Dict):
		"""Cache current weather for a farmer."""
		self.data[phone_number] = {
			"timestamp": datetime.now(TZ_TANZANIA).isoformat(),
			"weather": weather_data
		}
		self._save_cache()
	
	def clear_old_cache(self):
		"""Remove cached data older than 24 hours."""
		now = datetime.now(TZ_TANZANIA)
		expired = []
		
		for phone, data in self.data.items():
			try:
				cached_time = datetime.fromisoformat(data.get("timestamp", ""))
				if (now - cached_time).days >= 1:
					expired.append(phone)
			except:
				pass
		
		for phone in expired:
			del self.data[phone]
		
		if expired:
			self._save_cache()
			print(f"Cleared weather cache for {len(expired)} farmers")


def detect_sudden_changes(phone_number: str, current_weather: Dict, cache: WeatherCache) -> Optional[Dict]:
	"""Check if weather has changed significantly from previous day.
	
	Returns:
		Dict with alert info if significant change detected, None otherwise
	"""
	previous = cache.get_previous_weather(phone_number)
	if not previous:
		return None  # No previous data to compare
	
	prev_weather = previous.get("weather", {})
	
	# Compare today's stats
	today_current = current_weather.get("today", {})
	prev_today = prev_weather.get("today", {})
	
	alerts = []
	
	# Check temperature drop
	curr_temp_min = today_current.get("temperature_min", 0)
	prev_temp_min = prev_today.get("temperature_min", 0)
	if curr_temp_min and prev_temp_min:
		temp_drop = prev_temp_min - curr_temp_min
		if temp_drop >= ALERT_THRESHOLDS["temperature_drop"]:
			alerts.append(f"Halijoto imeshuka {temp_drop}°C (Temperature dropped {temp_drop}°C)")
	
	# Check temperature spike
	curr_temp_max = today_current.get("temperature_max", 0)
	prev_temp_max = prev_today.get("temperature_max", 0)
	if curr_temp_max and prev_temp_max:
		temp_spike = curr_temp_max - prev_temp_max
		if temp_spike >= ALERT_THRESHOLDS["temperature_spike"]:
			alerts.append(f"Halijoto imeinuka {temp_spike}°C (Temperature spiked {temp_spike}°C)")
	
	# Check rain probability jump
	curr_rain = today_current.get("rain_risk_next_12h") or 0
	prev_rain = prev_today.get("rain_risk_next_12h") or 0
	rain_jump = curr_rain - prev_rain
	if rain_jump >= ALERT_THRESHOLDS["rain_probability_jump"]:
		alerts.append(f"Mvua inatarajiwa kuongezeka ({rain_jump}% zaidi) - Rain expected to increase")
	
	# Check wind speed increase
	curr_wind = today_current.get("wind_peak_next_12h") or 0
	prev_wind = prev_today.get("wind_peak_next_12h") or 0
	wind_increase = curr_wind - prev_wind
	if wind_increase >= ALERT_THRESHOLDS["wind_speed_increase"]:
		alerts.append(f"Upepo utakuwa nguvu ({wind_increase} km/h zaidi) - Wind will be strong")
	
	if alerts:
		return {
			"type": "sudden_change",
			"changes": alerts
		}
	
	return None


class DailyWeatherBroadcaster:
	"""Send daily weather forecasts to all farmers at 6:00 AM Tanzania time."""
	
	def __init__(self, twilio_account_sid: str = None, twilio_auth_token: str = None, twilio_phone: str = None):
		"""Initialize broadcaster with Twilio credentials.
		
		Args:
			twilio_account_sid: Twilio Account SID (from environment if not provided)
			twilio_auth_token: Twilio Auth Token (from environment if not provided)
			twilio_phone: Twilio phone number sending SMS (from environment if not provided)
		"""
		import os
		
		self.account_sid = twilio_account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
		self.auth_token = twilio_auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
		self.twilio_phone = twilio_phone or os.environ.get("TWILIO_PHONE_NUMBER")
		
		if self.account_sid and self.auth_token:
			from twilio.rest import Client
			self.client = Client(self.account_sid, self.auth_token)
		else:
			self.client = None
			print("[WARNING] Twilio credentials not configured. Running in dry-run mode.")
		
		self.cache = WeatherCache()
	
	def send_sms(self, phone_number: str, message: str) -> bool:
		"""Send SMS via Twilio.
		
		Args:
			phone_number: Recipient phone number
			message: SMS message text
			
		Returns:
			True if sent successfully, False otherwise
		"""
		if not self.client or not self.twilio_phone:
			print(f"[DRY RUN] {phone_number}: {message[:100]}...")
			return False
		
		try:
			sms = self.client.messages.create(
				body=message,
				from_=self.twilio_phone,
				to=phone_number
			)
			print(f"[SMS SENT] SID: {sms.sid} | Status: {sms.status}")
			return True
		except Exception as e:
			print(f"[ERROR] SMS to {phone_number} failed: {e}")
			return False
	
	def broadcast_daily_weather(self, test_phone_number: str = None) -> Dict[str, Any]:
		"""Send daily weather to all registered farmers (or just test phone if specified).
		
		Args:
			test_phone_number: If provided, only send to this phone number (for testing)
		
		Returns:
			Summary of broadcast results
		"""
		# Ensure database is initialized
		db.init_database()
		
		farmers = db.get_all_users()
		
		# If test mode, only use the test phone number
		if test_phone_number:
			farmers = [f for f in farmers if f["phone_number"] == test_phone_number]
			if not farmers:
				print(f"[ERROR] Phone number {test_phone_number} not found in database")
				return {
					"status": "phone_not_found",
					"message": f"Phone number {test_phone_number} not found",
					"timestamp": datetime.now(TZ_TANZANIA).isoformat()
				}
		
		if not farmers:
			return {
				"status": "no_farmers",
				"message": "No farmers registered in database",
				"timestamp": datetime.now(TZ_TANZANIA).isoformat()
			}
		
		results = {
			"timestamp": datetime.now(TZ_TANZANIA).isoformat(),
			"total_farmers": len(farmers),
			"broadcast_sent": 0,
			"alerts_sent": 0,
			"errors": [],
			"details": []
		}
		
		print(f"\n{'='*70}")
		print(f"DAILY WEATHER BROADCAST - {results['timestamp']}")
		print(f"{'='*70}")
		print(f"[SENDING] Broadcasting to {len(farmers)} farmers...\n")
		
		for farmer in farmers:
			try:
				phone = farmer["phone_number"]
				location = farmer["location_name"]
				lat = farmer["latitude"]
				lon = farmer["longitude"]
				
				# Fetch 7-day weather for farmer
				payload = prepare_sms_payload(
					latitude=lat,
					longitude=lon,
					location_name=location,
					translate=True  # Translation happens here
				)
				
				# Get the translated weather message in Swahili
				weather_msg = payload["sms"]["next_7_days"]["message"]
				
				# For Trial accounts: send a longer but still single-segment message
				# Twilio Trial limit: ~160 characters for standard text, ~70 for Unicode
				# The message is already in Swahili, so use it as-is but truncate if needed
				
				broadcast_msg = weather_msg
				
				# If message is too long for Trial (>160 chars), trim it
				if len(broadcast_msg) > 160:
					# Take first complete sentence or first ~150 chars
					broadcast_msg = broadcast_msg[:150]
					# Try to find last space to avoid cutting mid-word
					last_space = broadcast_msg.rfind(' ')
					if last_space > 100:
						broadcast_msg = broadcast_msg[:last_space] + "..."
				
				# Send the broadcast SMS
				sent = self.send_sms(phone, broadcast_msg)
				if sent:
					results["broadcast_sent"] += 1
					print(f"[OK] {phone} ({location}) - Message: {len(broadcast_msg)} chars")
				else:
					print(f"[FAILED] {phone} ({location}) - SMS send failed")
				
				# Cache weather data for next comparison
				weather_data = {
					"today": {
						"temperature_min": payload.get("daily_summary_next_7d", {}).get("min_temp", 0),
						"temperature_max": payload.get("daily_summary_next_7d", {}).get("max_temp", 0),
						"rain_risk_next_12h": payload.get("daily_summary_next_7d", {}).get("rain_probability", 0),
						"wind_peak_next_12h": payload.get("daily_summary_next_7d", {}).get("wind_speed", 0)
					},
					"daily_summary_next_7d": payload.get("daily_summary_next_7d", {})
				}
				self.cache.update_weather(phone, weather_data)
				
				# Check for sudden weather changes and send alert if needed
				change_detected = detect_sudden_changes(phone, weather_data, self.cache)
				if change_detected:
					alert_msg = (
						f"ALERT - {location.upper()}\n"
						f"Weather alert!\n\n"
					)
					for change_item in change_detected.get("changes", []):
						alert_msg += f"- {change_item}\n"
					
					alert_sent = self.send_sms(phone, alert_msg)
					if alert_sent:
						results["alerts_sent"] += 1
						db.log_alert(phone, f"Sudden change alert: {', '.join(change_detected['changes'])}")
						print(f"   [ALERT] {change_detected['changes'][0]}")
			
			except Exception as e:
				error_msg = f"Error broadcasting to {farmer.get('phone_number', 'unknown')}: {str(e)}"
				results["errors"].append(error_msg)
				print(f"[ERROR] {error_msg}")
		
		print(f"\n{'='*70}")
		print(f"BROADCAST SUMMARY")
		print(f"{'='*70}")
		print(f"[OK] Weather sent: {results['broadcast_sent']}/{results['total_farmers']}")
		print(f"[ALERT] Alerts sent: {results['alerts_sent']}")
		print(f"[ERROR] Errors: {len(results['errors'])}")
		print(f"{'='*70}\n")
		
		return results


class SchedulerManager:
	"""Manage the APScheduler for daily broadcasts."""
	
	def __init__(self):
		self.scheduler = BackgroundScheduler()
		self.broadcaster = DailyWeatherBroadcaster()
	
	def start_daily_broadcast(self, hour: int = 6, minute: int = 0):
		"""Start scheduled daily weather broadcast at specified time (Tanzania time).
		
		Args:
			hour: Hour of day (0-23, Tanzania time)
			minute: Minute of hour (0-59)
		"""
		# APScheduler uses cron trigger with UTC times, but we specify timezone
		# Cron format: minute hour day month day_of_week
		
		job = self.scheduler.add_job(
			func=self.broadcaster.broadcast_daily_weather,
			trigger=CronTrigger(hour=hour, minute=minute, timezone=TZ_TANZANIA),
			id='daily_weather_broadcast',
			name='Daily weather broadcast at 6:00 AM Tanzania time',
			replace_existing=True
		)
		
		self.scheduler.start()
		
		print(f"[OK] Scheduler started")
		print(f"[SCHEDULE] Daily broadcast scheduled for {hour:02d}:{minute:02d} Tanzania time")
		print(f"[INFO] Press Ctrl+C to stop\n")
		
		try:
			# Keep scheduler running
			while True:
				import time
				time.sleep(1)
		except KeyboardInterrupt:
			print("\n\n[STOP] Scheduler stopped")
			self.scheduler.shutdown()
	
	def run_now(self, test_phone_number: str = None):
		"""Run broadcast immediately (for testing).
		
		Args:
			test_phone_number: If provided, only send to this phone number
		"""
		if test_phone_number:
			print(f"[TEST MODE] Broadcasting only to {test_phone_number}\n")
		else:
			print("[TEST] Running broadcast now (test mode)...\n")
		return self.broadcaster.broadcast_daily_weather(test_phone_number=test_phone_number)
	
	def stop(self):
		"""Stop the scheduler."""
		if self.scheduler.running:
			self.scheduler.shutdown()
			print("[STOP] Scheduler stopped")


def main():
	"""Run the daily scheduler."""
	import sys
	
	manager = SchedulerManager()
	
	if len(sys.argv) > 1 and sys.argv[1] == "test":
		# Test mode - optionally specify a phone number
		test_phone = sys.argv[2] if len(sys.argv) > 2 else None
		results = manager.run_now(test_phone_number=test_phone)
		print("[RESULTS] JSON output:")
		print(json.dumps(results, default=str, indent=2))
	else:
		# Start the scheduler to run at 6:00 AM Tanzania time
		manager.start_daily_broadcast(hour=6, minute=0)


if __name__ == "__main__":
	main()
