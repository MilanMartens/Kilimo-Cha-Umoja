import requests
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
from dotenv import load_dotenv

# --- Load .env file ---
load_dotenv()


def clean_env(name):
    value = os.getenv(name)
    if value is None:
        return None
    # Remove common copy/paste artifacts from .env values.
    return value.strip().strip('"').strip("'")

# --- Twilio setup variables ---
ACCOUNT_SID = clean_env("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = clean_env("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = clean_env("TWILIO_PHONE_NUMBER")
TO_NUMBER = clean_env("TO_NUMBER")

missing = [
    name
    for name, value in {
        "TWILIO_ACCOUNT_SID": ACCOUNT_SID,
        "TWILIO_AUTH_TOKEN": AUTH_TOKEN,
        "TWILIO_NUMBER": TWILIO_NUMBER,
        "TO_NUMBER": TO_NUMBER,
    }.items()
    if not value
]
if missing:
    raise RuntimeError(f"Missing required .env value(s): {', '.join(missing)}")

print("Twilio number:", TWILIO_NUMBER)
print("To number:", TO_NUMBER)
print("Account SID loaded:", ACCOUNT_SID is not None)
# make client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

def get_weather():
    url = "http://127.0.0.1:5001/weather/tanzania"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()

def format_message(data):
    parts = data["sms"]["message"].split(" | ")

    # --- Header ---
    header = parts[0].replace("Weather area update", "Weather")

    # --- Today ---
    today = parts[1]
    today = today.replace("Today:", "")
    today = today.replace("rain risk up to", "rain")
    today = today.strip()

    # --- Next 3 days ---
    next3 = parts[2]
    next3 = next3.replace("Next 3d:", "")
    next3 = next3.replace("Slight showers", "showers")
    next3 = next3.replace("rain up to", "")
    next3 = next3.strip()

    # --- Next 7 days ---
    next7 = parts[3]
    next7 = next7.replace("Next 7d:", "")
    next7 = next7.replace("Thunderstorm", "storm")
    next7 = next7.replace("rain up to", "")
    next7 = next7.strip()

    # --- Final compact SMS ---
    sms = f"{header} | Today: {today} | 3d: {next3} | 7d: {next7}"

    return sms


# --- 3. Send SMS ---
def send_sms(message):
    try:
        result = client.messages.create(
            body=message,
            from_=TWILIO_NUMBER,
            to=TO_NUMBER,
        )
        print("Twilio message SID:", result.sid)
    except TwilioRestException as exc:
        print(f"Twilio error {exc.code}: {exc.msg}")
        if exc.code == 20003:
            print(
                "Auth failed: use ACCOUNT SID + AUTH TOKEN from the same Twilio project/account."
            )
            print(
                "If you rotated your token, update TWILIO_AUTH_TOKEN in .env and retry."
            )
        raise


weather = get_weather()
sms_text = format_message(weather)
print("Sending:", sms_text)
send_sms(sms_text)