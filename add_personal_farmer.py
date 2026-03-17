"""Add a personal farmer/test user to the database.

This script lets you add your own phone number to test the SMS broadcasts.
"""

import user_database as db


def add_farmer(phone_number: str, location_name: str, latitude: float, longitude: float):
    """Add a single farmer to the database.
    
    Args:
        phone_number: Phone number (e.g., +32491234567 for Belgium, +255... for Tanzania)
        location_name: Location name (e.g., "Antwerp", "Dar es Salaam")
        latitude: Latitude coordinate
        longitude: Longitude coordinate
    """
    db.init_database()
    
    print(f"\n{'='*70}")
    print(f"ADDING FARMER TO DATABASE")
    print(f"{'='*70}\n")
    
    # Check if already exists
    existing = db.get_user(phone_number)
    if existing:
        print(f"[UPDATE] {phone_number} already exists, updating...")
    else:
        print(f"[NEW] Adding {phone_number}...")
    
    # Save farmer
    success = db.save_user(phone_number, location_name, latitude, longitude)
    
    if success:
        print(f"\n[OK] Farmer added successfully!")
        print(f"    Phone: {phone_number}")
        print(f"    Location: {location_name}")
        print(f"    Coordinates: {latitude}, {longitude}")
        print(f"\nReady to receive SMS broadcasts!\n")
    else:
        print(f"\n[ERROR] Failed to add farmer\n")
    
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 5:
        phone = sys.argv[1]
        location = sys.argv[2]
        lat = float(sys.argv[3])
        lon = float(sys.argv[4])
        add_farmer(phone, location, lat, lon)
    else:
        print("""
Usage:
  python add_personal_farmer.py <phone> <location> <latitude> <longitude>

Examples:
  python add_personal_farmer.py "+32491234567" "Antwerp" 51.2195 4.3954
  python add_personal_farmer.py "+255789123456" "Dar es Salaam" -6.8161 39.2803

For Belgium (Antwerp):
  python add_personal_farmer.py "+32491234567" "Antwerp" 51.2195 4.3954

For Tanzania (Dar es Salaam):
  python add_personal_farmer.py "+255789123456" "Dar es Salaam" -6.8161 39.2803
        """)
