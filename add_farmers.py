"""Script to add farmers to the database for daily weather broadcasts.

This script demonstrates how to pre-load farmer phone numbers and locations.
"""

import user_database as db


def add_farmers_from_list(farmers_list: list) -> dict:
	"""Add multiple farmers to the database.
	
	Args:
		farmers_list: List of dicts with keys: phone_number, location_name, latitude, longitude
		
	Returns:
		Summary of added farmers
	"""
	db.init_database()
	
	results = {
		"total": len(farmers_list),
		"added": 0,
		"updated": 0,
		"errors": []
	}
	
	print("\n" + "="*70)
	print("ADDING FARMERS TO DATABASE")
	print("="*70 + "\n")
	
	for farmer in farmers_list:
		try:
			phone = farmer.get("phone_number")
			location = farmer.get("location_name")
			lat = farmer.get("latitude")
			lon = farmer.get("longitude")
			
			# Validate all required fields
			if not all([phone, location, lat is not None, lon is not None]):
				error = f"Missing data for farmer: {farmer}"
				results["errors"].append(error)
				print(f"[ERROR] {error}")
				continue
			
			# Check if farmer already exists
			existing = db.get_user(phone)
			
			# Save farmer
			success = db.save_user(phone, location, lat, lon)
			
			if success:
				if existing:
					results["updated"] += 1
					print(f"[UPDATE] {phone} - {location}")
				else:
					results["added"] += 1
					print(f"[ADDED] {phone} - {location}")
			else:
				error = f"Failed to save {phone}"
				results["errors"].append(error)
				print(f"[ERROR] {error}")
		except Exception as e:
			error = f"Exception processing farmer: {str(e)}"
			results["errors"].append(error)
			print(f"[ERROR] {error}")
	
	print("\n" + "="*70)
	print("SUMMARY")
	print("="*70)
	print(f"[ADDED] {results['added']}")
	print(f"[UPDATED] {results['updated']}")
	print(f"[ERRORS] {len(results['errors'])}")
	print("="*70 + "\n")
	
	return results


def example_farmers():
	"""Example farmers to add to database. THESE ARE FAKE NUMBERS FOR TESTING ONLY."""
	return [
		{
			"phone_number": "+255799999001",
			"location_name": "Dar es Salaam",
			"latitude": -6.8161,
			"longitude": 39.2803
		},
		{
			"phone_number": "+255799999002",
			"location_name": "Morogoro",
			"latitude": -6.8163,
			"longitude": 37.6629
		},
		{
			"phone_number": "+255799999003",
			"location_name": "Arusha",
			"latitude": -3.3869,
			"longitude": 36.6830
		},
		{
			"phone_number": "+255799999004",
			"location_name": "Mbeya",
			"latitude": -8.7449,
			"longitude": 33.4833
		},
		{
			"phone_number": "+255799999005",
			"location_name": "Iringa",
			"latitude": -7.7667,
			"longitude": 35.6833
		},
	]


if __name__ == "__main__":
	import sys
	
	if len(sys.argv) > 1 and sys.argv[1] == "example":
		# Add example farmers
		farmers = example_farmers()
		results = add_farmers_from_list(farmers)
		
		print("\n[INFO] Example farmers added:")
		all_users = db.get_all_users()
		for user in all_users:
			print(f"   {user['phone_number']}: {user['location_name']} ({user['latitude']}, {user['longitude']})")
	
	elif len(sys.argv) > 1 and sys.argv[1] == "clear":
		# Clear all farmers from database
		db.init_database()
		all_users = db.get_all_users()
		count = 0
		for user in all_users:
			db.delete_user(user["phone_number"])
			count += 1
		print(f"\n🗑️  Deleted {count} farmers from database\n")
	
	elif len(sys.argv) > 1 and sys.argv[1] == "list":
		# List all farmers in database
		db.init_database()
		farmers = db.get_all_users()
		print(f"\n{'='*70}")
		print(f"FARMERS IN DATABASE ({len(farmers)} total)")
		print(f"{'='*70}\n")
		for farmer in farmers:
			print(f"📱 {farmer['phone_number']}")
			print(f"   📍 {farmer['location_name']}")
			print(f"   📡 {farmer['latitude']}, {farmer['longitude']}\n")
	
	else:
		print("""
Usage:
  python add_farmers.py example    - Add example farmers
  python add_farmers.py list       - List all farmers in database
  python add_farmers.py clear      - Remove all farmers (⚠️ be careful!)
  
To add custom farmers, edit this script or use user_database.save_user():
  
  import user_database as db
  db.init_database()
  db.save_user("+255700000001", "Dar es Salaam", -6.8161, 39.2803)
""")
