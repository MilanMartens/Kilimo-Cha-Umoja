# Two-Way SMS Weather System Setup Guide

## Overview
The Kilimo Cha Umoja system now includes a complete two-way SMS implementation that allows users to:
1. Register their location via SMS
2. Automatically receive weather alerts when conditions change
3. Request weather updates anytime
4. Update their location as needed

## System Architecture

```
User Phone (SMS)
    ↓
Twilio Webhook
    ↓
/sms_webhook endpoint (WeatherAPI.py)
    ↓
sms_handler.py (Process message)
    ↓
geopy (Geocode location)
    ↓
user_database.py (Store/retrieve user data)
    ↓
WeatherAPI.py (Fetch weather data)
    ↓
translator.py (Translate to Swahili)
    ↓
Response SMS back to user via Twilio
```

## Components

### 1. **sms_handler.py** - Core SMS Processing
- **Purpose**: Parse incoming SMS and generate responses based on user registration status
- **Key Functions**:
  - `send_intro_sms(phone_number)`: Send initial greeting asking for location (initiate contact)
  - `parse_location_from_message(message)`: Extract location name from user text
  - `geocode_location(location_name)`: Convert location name to coordinates using geopy
  - `register_user_location(phone, location)`: Save user + coordinates to database
  - `get_weather_for_user(phone)`: Fetch Swahili weather for registered user
  - `handle_incoming_sms(phone, message)`: Main handler with smart request routing

- **Smart Workflow**:
  1. Check if user is already registered
  2. If NOT registered and they didn't provide location → **Ask for location**
  3. If location provided → Register and send weather
  4. If registered → Handle their command (weather, help, update location, etc.)

- **Supported Message Formats**:
  ```
  "Dar es Salaam"          → Register location + get weather
  "Morogoro"               → Register location + get weather
  "badilisha Arusha"       → Update location and get weather
  "taarifa"                → Get weather (Swahili: "news/info")
  "weather"                → Get weather (English)
  "help" or "msaada"       → Show available commands
  "hello" or "habari"      → Greeting
  ```

### 2. **user_database.py** - Data Persistence
- **Purpose**: Store user information and alert audit trail
- **Database**: SQLite (users.db)
- **Tables**:
  - `users`: Stores phone_number, location_name, latitude, longitude, timestamps
  - `alert_log`: Audit trail of all alerts sent to users

- **Key Functions**:
  - `init_database()`: Create tables if they don't exist
  - `save_user(phone, location, lat, lon)`: Register or update user
  - `get_user(phone)`: Retrieve user by phone number
  - `get_all_users()`: Get all registered users
  - `log_alert(phone, message)`: Record alert sent
  - `delete_user(phone)`: Remove user from system

### 3. **alert_broadcaster.py** - Automatic Alerts
- **Purpose**: Monitor weather and send alerts to all users
- **Alert Triggers**:
  - Heavy rain (≥80% probability in next 12h)
  - High winds (≥40 km/h)
  - Extreme heat (≥35°C)
  - Extreme cold (≤5°C)
  - Severe weather (thunderstorms with hail)

- **Class**: `AlertBroadcaster`
  - `should_alert(weather_data)`: Evaluate if alert conditions met
  - `send_alert_sms(phone, message)`: Send SMS via Twilio
  - `broadcast_alerts()`: Check all users and send alerts

### 4. **WeatherAPI.py** - REST API with Webhook
- **New Endpoint**: `POST /sms_webhook`
  - Receives SMS from Twilio
  - Calls sms_handler to process message
  - Returns Twilio-compatible XML response

- **Integration Points**:
  - Fetches weather using existing `prepare_sms_payload()`
  - Uses `translate_to_swahili()` for responses
  - Receives `From` (phone) and `Body` (message) from Twilio

## Installation & Configuration

### Step 1: Install Dependencies
All required packages are in requirements.txt:
```bash
pip install -r requirements.txt
```

Packages needed:
- Flask >= 3.0
- deep-translator >= 1.11.0
- geopy >= 2.4
- twilio >= 8.0.0

### Step 2: Set Up Twilio Account
1. Sign up at https://www.twilio.com
2. Get your:
   - Account SID
   - Auth Token
   - Phone Number (SMS-enabled)

### Step 3: Configure Environment Variables
Create a `.env` file in the project directory:
```bash
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

Or set in your environment before running:
```bash
export TWILIO_ACCOUNT_SID=your_account_sid
export TWILIO_AUTH_TOKEN=your_auth_token
export TWILIO_PHONE_NUMBER=+1234567890
```

### Step 4: Start the Flask Server
```bash
python WeatherAPI.py --serve --host 0.0.0.0 --port 5001
```

The server will start at `http://localhost:5001`

### Step 5: Configure Twilio Webhook
1. Log in to Twilio Console
2. Go to Phone Numbers → Manage Numbers
3. Select your SMS phone number
4. In "Messaging" section:
   - **Webhook URL**: `https://YOUR_DOMAIN:5001/sms_webhook`
   - **HTTP Method**: POST
5. Save

**Note**: Your server must be publicly accessible. Use ngrok for local testing:
```bash
ngrok http 5001
# Get public URL and use it in Twilio webhook
```

## Usage Examples

### Guided Registration Flow (Recommended)

The system now uses a **guided conversation flow** where it asks users for their location first:

```
System sends SMS: "Habari! Karibu kwenye Kilimo Cha Umoja.
                   Tafadhali tuma eneo lako ili upokee taarifa za hali ya hewa.
                   Mfano: Dar es Salaam"

User replies with: "Dar es Salaam"
                    ↓
System geocodes: (-6.8160837, 39.2803583)
                    ↓
System saves to database
                    ↓
Response: "Karibu! Umesajiliwa eneo lako: Dar es Salaam. 
          Utapokea taarifa ya takakataka.
          
          [Automatic weather for Dar es Salaam]"
```

### Command Reference

After registering, users can send these commands:

| Message | Response |
|---------|----------|
| Location name (e.g., "Morogoro") | Register/update location + get weather |
| `taarifa` or `weather` | Get weather for registered location |
| `badilisha X` (e.g., "badilisha Arusha") | Update location to X |
| `help` or `msaada` | Show available commands |
| `hello` or `habari` | Greeting |

### Conversation Example

```
System → User: "Habari! Karibu kwenye Kilimo Cha Umoja.
               Tafadhali tuma eneo lako..."

User → System: "Dar es Salaam"

System → User: "Karibu! Umesajiliwa eneo lako: Dar es Salaam...
               [Full weather report in Swahili]"

User → System: "taarifa" (one day later)

System → User: "[Updated weather report]"

User → System: "badilisha Morogoro"

System → User: "Karibu! Umesajiliwa eneo lako: Morogoro...
               [Weather for Morogoro]"
```

## Running Automatic Alerts

### Initiating Contact with New Users

To start the process, send the initial greeting SMS to users:

```python
from sms_handler import send_intro_sms

# Send intro SMS to a single user
send_intro_sms(phone_number="+255700000001")

# Or with Twilio client for actual sending
from twilio.rest import Client
import os

client = Client(
    os.environ.get("TWILIO_ACCOUNT_SID"),
    os.environ.get("TWILIO_AUTH_TOKEN")
)

send_intro_sms(twilio_client=client, phone_number="+255700000001")
```

From a notebook or script:

```python
from sms_handler import send_intro_sms

# List of farmer phone numbers to contact
farmers = [
    "+255700000001",
    "+255700000002",
    "+255700000003",
]

for phone in farmers:
    send_intro_sms(phone_number=phone)
    print(f"Intro sent to {phone}")
```

This will send:
```
Habari! Karibu kwenye Kilimo Cha Umoja.
Tafadhali tuma eneo lako ili upokee taarifa za hali ya hewa.
Mfano: Dar es Salaam

(Hello! Welcome to Kilimo Cha Umoja.
Please send your location to receive weather updates.
Example: Dar es Salaam)
```

Users then reply with their location, and they're automatically registered.

### Manual Broadcast (Testing)
```bash
python alert_broadcaster.py
```

### Scheduled Broadcasting (Production)
Use cron (Linux/Mac):
```bash
# Every hour
0 * * * * cd /path/to/project && python alert_broadcaster.py
```

Or use Windows Task Scheduler:
- Create new task
- Action: `python alert_broadcaster.py`
- Trigger: Every hour

## Testing Without Twilio (Dry Run)

The system can run without Twilio credentials (dry run mode):

```python
from alert_broadcaster import AlertBroadcaster

broadcaster = AlertBroadcaster()
# Without credentials, it prints alerts instead of sending
results = broadcaster.broadcast_alerts()
print(results)
```

Output example:
```
[DRY RUN] Would send to +255700000001: ⚠️ ONYO LA TAKAKATAKA: ...
```

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | API documentation |
| `/weather?lat=X&lon=Y&translate=true` | GET | Point weather (Swahili) |
| `/weather/tanzania?translate=true` | GET | Tanzania-wide weather (Swahili) |
| `/weather/bounding-box?lat1=X...` | GET | Area weather (Swahili) |
| `/sms_webhook` | POST | Receive SMS from Twilio |

## Database Schema

### users table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL UNIQUE,
    location_name TEXT,
    latitude REAL,
    longitude REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### alert_log table
```sql
CREATE TABLE alert_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Querying the Database

```python
import user_database as db

# Initialize
db.init_database()

# Get all users
all_users = db.get_all_users()
for user in all_users:
    print(f"{user['phone_number']}: {user['location_name']}")

# Get specific user
user = db.get_user("+255700000001")
print(f"Weather for: {user['location_name']}")

# Get alert history
from sqlite3 import connect
conn = connect("users.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM alert_log WHERE phone_number = ?", ("+255700000001",))
alerts = cursor.fetchall()
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'geopy'"
**Solution**: Install packages: `pip install -r requirements.txt`

### Issue: SMS not being received
**Check**:
1. Twilio webhook URL is correct and public
2. Server is running: `python WeatherAPI.py --serve`
3. Webhook method is POST
4. Phone number is registered in Twilio

### Issue: Slow geocoding
- geopy uses OpenStreetMap (Nominatim), which has rate limits
- Add location to database once, then weather is fast
- Consider adding caching for frequently-requested locations

### Issue: Alerts not being sent
**Check**:
1. Twilio credentials in environment variables
2. Twilio phone number is valid
3. Users are registered in database
4. Weather conditions meet alert thresholds

## Performance Tips

1. **Cache weather data**: Store results for 30 minutes to avoid API spam
2. **Batch alerts**: Send alerts every hour instead of on every change
3. **Limit geocoding**: Cache location → coordinates mappings
4. **Database indexing**: Add index on phone_number for faster lookups

## Sample Conversation Flow

```
User:     "Dar es Salaam"
System:   "Karibu! Umesajiliwa eneo lako: Dar es Salaam. 
           Utapokea taarifa ya takakataka."
User:     "taarifa" (1 hour later)
System:   "Weather update 2024-01-15 14:30
           Now: 28C, Partly cloudy, wind 15 km/h
           Today: 24C to 31C, humidity 65%, rain 2mm
           Next 12h: rain risk 20%, wind up to 20 km/h, Partly cloudy
           Next 3d: 23C to 32C, Partly cloudy, rain 5mm"
           
[Later, automatic alert triggered]
System:   "⚠️ ONYO LA TAKAKATAKA: High rainfall expected (85% chance)
           Eneo: Dar es Salaam
           ..."
```

## Deployment Checklist

- [ ] Install all dependencies: `pip install -r requirements.txt`
- [ ] Set Twilio environment variables
- [ ] Create Twilio webhook pointing to `/sms_webhook`
- [ ] Start Flask server on port 5001
- [ ] Test with `python sms_handler.py` (manual test)
- [ ] Register test user via SMS
- [ ] Verify weather retrieval
- [ ] Set up alert scheduler (cron/Task Scheduler)
- [ ] Deploy to production server (ngrok for dev, real server for prod)

## Success Indicators

✅ System is working if:
1. Users can register location via SMS
2. Their phone + coordinates save to users.db
3. They receive weather in Swahili on request
4. Alerts are sent when weather conditions warrant
5. Alert logs show all alerts sent

---

**Last Updated**: 2024
**Version**: 2.0 (Two-way SMS system)
