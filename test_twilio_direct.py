"""Direct test of Twilio SMS sending.

This script tests if Twilio credentials are working and if SMS can be sent.
"""

import os
from pathlib import Path

# Load .env file
env_file = Path(".env")
if env_file.exists():
	print("[INFO] Loading .env file...")
	with open(env_file) as f:
		for line in f:
			line = line.strip()
			if line and not line.startswith("#") and "=" in line:
				key, value = line.split("=", 1)
				os.environ[key.strip()] = value.strip()
				if key.startswith("TWILIO"):
					print(f"[LOADED] {key.strip()}")
else:
	print("[ERROR] .env file not found!")

print("\n" + "="*70)
print("TWILIO CREDENTIALS TEST")
print("="*70 + "\n")

# Check credentials
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")

print(f"[CHECK] TWILIO_ACCOUNT_SID: {'SET' if account_sid else 'NOT SET'}")
print(f"[CHECK] TWILIO_AUTH_TOKEN: {'SET' if auth_token else 'NOT SET'}")
print(f"[CHECK] TWILIO_PHONE_NUMBER: {twilio_phone if twilio_phone else 'NOT SET'}")

if not all([account_sid, auth_token, twilio_phone]):
	print("\n[ERROR] Missing credentials!\n")
	exit(1)

# Try to create Twilio client
print("\n[ATTEMPTING] Connecting to Twilio API...")
try:
	from twilio.rest import Client
	client = Client(account_sid, auth_token)
	print("[SUCCESS] Twilio client created successfully!\n")
except Exception as e:
	print(f"[FAILED] Could not create Twilio client: {e}\n")
	exit(1)

# Try to send SMS
print("="*70)
print("SENDING TEST SMS")
print("="*70 + "\n")

recipient = "+32474060826"
message = "Test SMS from Kilimo Cha Umoja - Weather System\n\nThis is a test message to verify Twilio is working correctly."

print(f"[FROM] {twilio_phone}")
print(f"[TO] {recipient}")
print(f"[MESSAGE] {message}\n")

try:
	print("[SENDING] Please wait...")
	sms = client.messages.create(
		body=message,
		from_=twilio_phone,
		to=recipient
	)
	print(f"[SUCCESS] SMS sent!")
	print(f"[SID] {sms.sid}")
	print(f"[STATUS] {sms.status}")
	print(f"\nCheck your phone for the message. It may take 1-2 minutes to arrive.\n")
except Exception as e:
	print(f"[ERROR] Failed to send SMS: {e}\n")
	import traceback
	traceback.print_exc()
