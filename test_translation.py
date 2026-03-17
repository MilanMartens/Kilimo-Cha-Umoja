"""Check what the weather API is returning with translation."""

import json
from WeatherAPI import prepare_sms_payload

print("Testing translation in prepare_sms_payload...\n")

# Get weather for Belgium coordinates
payload = prepare_sms_payload(
    latitude=50.8503,
    longitude=4.3517,
    location_name="Belgium",
    translate=True
)

print("="*70)
print("TESTING SWAHILI TRANSLATION")
print("="*70 + "\n")

# Check next_7_days message
weather_msg = payload["sms"]["next_7_days"]["message"]
print("[WEATHER MESSAGE - Next 7 Days]")
print(f"Length: {len(weather_msg)} chars")
print(f"First 200 chars:\n{weather_msg[:200]}\n")

print("="*70)
print("Checking if it's translated (looking for Swahili keywords)")
print("="*70 + "\n")

# Check for Swahili indicators
swahili_keywords = ["Joto", "Mvua", "Upepo", "Habari", "Sasa", "Kesho", "Leo", "Tarehe"]
found_swahili = False

for keyword in swahili_keywords:
    if keyword in weather_msg:
        print(f"[SWAHILI] Found '{keyword}' - Translation IS working!")
        found_swahili = True
        break

if not found_swahili:
    print("[ENGLISH] No Swahili keywords found - Translation may NOT be working")
    print("\nFirst few lines:")
    for i, line in enumerate(weather_msg.split('\n')[:5]):
        print(f"  {i+1}. {line}")
