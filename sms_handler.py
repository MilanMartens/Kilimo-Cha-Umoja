"""SMS handler to process incoming messages and send weather responses."""

import os
from typing import Optional, Tuple, Dict
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import user_database as db
from WeatherAPI import prepare_sms_payload
from translator import translate_to_swahili


# Initialize geocoder
geocoder = Nominatim(user_agent="kilimo_cha_umoja")

# Ensure database is initialized
db.init_database()


def parse_location_from_message(message: str) -> Optional[str]:
	"""Extract location name from incoming SMS message.
	
	Expected formats:
	- "My location is Dar es Salaam"
	- "Location: Dar es Salaam"
	- "Dar es Salaam"
	- "I am in Morogoro"
	
	Args:
		message: Raw SMS message from user
		
	Returns:
		Location name or None if not found
	"""
	message = message.lower().strip()
	
	# Remove common prefixes
	for prefix in ["my location is ", "location: ", "i am in ", "location ", "where is ", "send weather for "]:
		if message.startswith(prefix):
			return message[len(prefix):].strip()
	
	# If no prefix, treat entire message as location (unless it's a command)
	if message not in ["hello", "hi", "help", "status", "weather"]:
		return message
	
	return None


def geocode_location(location_name: str) -> Optional[Tuple[float, float, str]]:
	"""Convert location name to coordinates using geopy.
	
	Args:
		location_name: Name of the location
		
	Returns:
		Tuple of (latitude, longitude, full_location_name) or None if not found
	"""
	try:
		# Add "Tanzania" to improve accuracy
		search_query = f"{location_name}, Tanzania"
		location = geocoder.geocode(search_query, timeout=10)
		
		if location:
			return (location.latitude, location.longitude, location.address)
		
		# Try without Tanzania
		location = geocoder.geocode(location_name, timeout=10)
		if location:
			return (location.latitude, location.longitude, location.address)
		
		return None
	except (GeocoderTimedOut, GeocoderUnavailable) as e:
		print(f"Geocoding error: {e}")
		return None


def register_user_location(phone_number: str, location_name: str) -> Tuple[bool, str]:
	"""Register or update a user's location.
	
	Args:
		phone_number: User's phone number from Twilio
		location_name: Location name provided by user
		
	Returns:
		Tuple of (success: bool, response_message: str)
	"""
	# Geocode the location
	geocoded = geocode_location(location_name)
	
	if not geocoded:
		return False, f"Sijaweza kupata eneo '{location_name}'. Jaribu kwa jina jingine au takwimu. (Could not find location '{location_name}'. Try another name.)"
	
	latitude, longitude, full_address = geocoded
	
	# Save to database
	success = db.save_user(phone_number, location_name, latitude, longitude)
	
	if success:
		message = f"Karibu! Umesajiliwa eneo lako: {location_name}. Utapokea taarifa ya takakataka. (Welcome! Registered location: {location_name}. You will receive weather updates.)"
		return True, message
	else:
		return False, "Kuna hitilafu wakati wa kusajili. Jaribu tena. (Error during registration. Try again.)"


def get_weather_for_user(phone_number: str) -> Tuple[bool, str]:
	"""Get weather for a registered user's location.
	
	Args:
		phone_number: User's phone number
		
	Returns:
		Tuple of (success: bool, weather_message: str)
	"""
	user = db.get_user(phone_number)
	
	if not user:
		return False, "Samahani, hujasajili eneo lako. Tafadhali tuma eneo lako. (Sorry, location not registered. Please send your location.)"
	
	try:
		# Fetch weather for user's coordinates
		payload = prepare_sms_payload(
			latitude=user["latitude"],
			longitude=user["longitude"],
			translate=True  # Always translate to Swahili
		)
		
		# Get the SMS message
		weather_msg = payload["sms"]["next_3_days"]["message"]
		
		# Log the alert
		db.log_alert(phone_number, weather_msg)
		
		return True, weather_msg
	except Exception as e:
		print(f"Error fetching weather: {e}")
		return False, "Hitilafu wakati wa kupakua taarifa ya hali ya hewa. (Error fetching weather.)"


def handle_incoming_sms(phone_number: str, message_body: str) -> str:
	"""Main handler for incoming SMS messages.
	
	Workflow:
	1. If user is not registered: ask for location
	2. If location provided: register and send weather
	3. If user is registered: respond to their request
	
	Args:
		phone_number: Incoming phone number (from Twilio)
		message_body: Content of SMS
		
	Returns:
		Response message to send back to user
	"""
	message_body = message_body.strip()
	user = db.get_user(phone_number)
	
	# Check if user is providing a location (could be new user or updating location)
	location_name = parse_location_from_message(message_body)
	
	if location_name and message_body.lower() not in ["help", "msaada", "?", "nini", "taarifa", "weather", "status"]:
		# User is registering/updating their location
		success, response = register_user_location(phone_number, location_name)
		if success:
			# Also send weather for their new location
			weather_success, weather_msg = get_weather_for_user(phone_number)
			if weather_success:
				return f"{response}\n\n{weather_msg}"
			else:
				return response
		else:
			return response
	
	# If user not registered and didn't provide location, ask for it
	if not user:
		# New user - ask for location
		return (
			"Habari! Karibu kwenye Kilimo Cha Umoja.\n"
			"Tafadhali tuma eneo lako ili upokee taarifa za hali ya hewa.\n"
			"Mfano: Dar es Salaam, Morogoro, Arusha, Mbeya\n\n"
			"(Hello! Welcome to Kilimo Cha Umoja.\n"
			"Please send your location to receive weather updates.\n"
			"Example: Dar es Salaam, Morogoro, Arusha, Mbeya)"
		)
	
	# User is registered - handle their request
	lower_msg = message_body.lower()
	
	if lower_msg in ["hi", "hello", "habari", "jambo"]:
		return f"Habari! Umesajiliwa eneo: {user['location_name']}. Jibu na 'taarifa' kuomba taarifa ya hali ya hewa. (Registered location: {user['location_name']}. Send 'taarifa' for weather.)"
	
	if lower_msg in ["help", "msaada", "?", "nini"]:
		return (
			f"Eneo lako: {user['location_name']}\n"
			"Jina amri: 'taarifa' (get weather), 'badilisha X' (update location), 'saidiya' (help)\n\n"
			f"(Your location: {user['location_name']}\n"
			"Commands: 'taarifa' (weather), 'badilisha X' (update), 'saidiya' (help))"
		)
	
	if lower_msg in ["weather", "taarifa", "status", "state"]:
		success, response = get_weather_for_user(phone_number)
		return response
	
	# Check if they're trying to change location
	if lower_msg.startswith("badilisha ") or lower_msg.startswith("change "):
		new_location = message_body.split(" ", 1)[1] if " " in message_body else None
		if new_location:
			success, response = register_user_location(phone_number, new_location)
			if success:
				weather_success, weather_msg = get_weather_for_user(phone_number)
				if weather_success:
					return f"{response}\n\n{weather_msg}"
				else:
					return response
			else:
				return response
	
	# If message doesn't match commands, treat as possible location update
	success, response = register_user_location(phone_number, message_body)
	if success:
		weather_success, weather_msg = get_weather_for_user(phone_number)
		if weather_success:
			return f"{response}\n\n{weather_msg}"
		else:
			return response
	else:
		# Location not found - suggest valid location
		return (
			f"Sijaweza kupata eneo '{message_body}'.\n"
			"Jaribu: Dar es Salaam, Morogoro, Arusha, Mbeya, Iringa, Moshi\n"
			"Au andika 'taarifa' kuomba hali ya hewa.\n\n"
			f"(Could not find location '{message_body}'.\n"
			"Try: Dar es Salaam, Morogoro, Arusha, Mbeya, Iringa, Moshi\n"
			"Or send 'taarifa' for weather.)"
		)


def send_intro_sms(twilio_client=None, phone_number: str = None) -> bool:
	"""Send initial greeting SMS asking for location.
	
	Used to initiate contact with a user and ask them to provide their location.
	
	Args:
		twilio_client: Twilio client instance (optional, for dry-run without client)
		phone_number: Phone number to send to
		
	Returns:
		True if sent successfully, False otherwise
	"""
	if not phone_number:
		print("Error: phone_number required")
		return False
	
	message = (
		"Habari! Karibu kwenye Kilimo Cha Umoja.\n"
		"Tafadhali tuma eneo lako ili upokee taarifa za hali ya hewa.\n"
		"Mfano: Dar es Salaam\n\n"
		"(Hello! Welcome to Kilimo Cha Umoja.\n"
		"Please send your location to receive weather updates.\n"
		"Example: Dar es Salaam)"
	)
	
	if twilio_client:
		try:
			from twilio.rest import Client
			import os
			
			account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
			auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
			twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
			
			if account_sid and auth_token and twilio_phone:
				client = Client(account_sid, auth_token)
				sms = client.messages.create(
					body=message,
					from_=twilio_phone,
					to=phone_number
				)
				print(f"Intro SMS sent to {phone_number}: {sms.sid}")
				return True
		except Exception as e:
			print(f"Error sending intro SMS to {phone_number}: {e}")
			return False
	else:
		# Dry run - just print
		print(f"[DRY RUN] Would send to {phone_number}:")
		print(message)
		return True


if __name__ == "__main__":
	# Test the SMS handler
	print("Testing SMS handler...")
	
	# Test 1: New user (not registered) - should ask for location
	print("\n" + "="*60)
	print("Test 1: New user requesting weather before registering")
	print("="*60)
	response = handle_incoming_sms("+255700001111", "taarifa")
	print(response)
	
	# Test 2: Register location
	print("\n" + "="*60)
	print("Test 2: User provides location")
	print("="*60)
	response = handle_incoming_sms("+255700001111", "Dar es Salaam")
	print(response)
	
	# Test 3: Request weather (now registered)
	print("\n" + "="*60)
	print("Test 3: Registered user requests weather")
	print("="*60)
	response = handle_incoming_sms("+255700001111", "taarifa")
	print(response)
	
	# Test 4: Help
	print("\n" + "="*60)
	print("Test 4: Help command")
	print("="*60)
	response = handle_incoming_sms("+255700001111", "help")
	print(response)
