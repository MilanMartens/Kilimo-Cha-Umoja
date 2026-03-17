"""User database to store phone numbers and coordinates."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple

DATABASE_FILE = Path(__file__).parent / "users.db"


def init_database() -> None:
	"""Initialize the users database with required tables."""
	conn = sqlite3.connect(DATABASE_FILE)
	cursor = conn.cursor()
	
	# Create users table
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS users (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			phone_number TEXT UNIQUE NOT NULL,
			location_name TEXT NOT NULL,
			latitude REAL NOT NULL,
			longitude REAL NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	""")
	
	# Create alerts log table (for tracking sent alerts)
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS alert_log (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			user_id INTEGER NOT NULL,
			alert_message TEXT NOT NULL,
			sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (user_id) REFERENCES users(id)
		)
	""")
	
	conn.commit()
	conn.close()
	print(f"Database initialized at {DATABASE_FILE}")


def save_user(phone_number: str, location_name: str, latitude: float, longitude: float) -> bool:
	"""Save or update user location.
	
	Args:
		phone_number: User's phone number (from Twilio)
		location_name: User's location name
		latitude: Location latitude
		longitude: Location longitude
		
	Returns:
		True if successful, False otherwise
	"""
	try:
		conn = sqlite3.connect(DATABASE_FILE)
		cursor = conn.cursor()
		
		# Use INSERT OR REPLACE to update if exists
		cursor.execute("""
			INSERT OR REPLACE INTO users (phone_number, location_name, latitude, longitude, updated_at)
			VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
		""", (phone_number, location_name, latitude, longitude))
		
		conn.commit()
		conn.close()
		print(f"Saved user {phone_number} at {location_name} ({latitude}, {longitude})")
		return True
	except Exception as e:
		print(f"Error saving user: {e}")
		return False


def get_user(phone_number: str) -> Optional[Dict]:
	"""Get user information by phone number.
	
	Args:
		phone_number: User's phone number
		
	Returns:
		Dictionary with user info or None if not found
	"""
	try:
		conn = sqlite3.connect(DATABASE_FILE)
		cursor = conn.cursor()
		
		cursor.execute("""
			SELECT id, phone_number, location_name, latitude, longitude, created_at, updated_at
			FROM users WHERE phone_number = ?
		""", (phone_number,))
		
		row = cursor.fetchone()
		conn.close()
		
		if row:
			return {
				"id": row[0],
				"phone_number": row[1],
				"location_name": row[2],
				"latitude": row[3],
				"longitude": row[4],
				"created_at": row[5],
				"updated_at": row[6]
			}
		return None
	except Exception as e:
		print(f"Error fetching user: {e}")
		return None


def get_all_users() -> List[Dict]:
	"""Get all registered users.
	
	Returns:
		List of dictionaries with user info
	"""
	try:
		conn = sqlite3.connect(DATABASE_FILE)
		cursor = conn.cursor()
		
		cursor.execute("""
			SELECT id, phone_number, location_name, latitude, longitude, created_at, updated_at
			FROM users
		""")
		
		rows = cursor.fetchall()
		conn.close()
		
		users = []
		for row in rows:
			users.append({
				"id": row[0],
				"phone_number": row[1],
				"location_name": row[2],
				"latitude": row[3],
				"longitude": row[4],
				"created_at": row[5],
				"updated_at": row[6]
			})
		return users
	except Exception as e:
		print(f"Error fetching users: {e}")
		return []


def delete_user(phone_number: str) -> bool:
	"""Delete a user from the database.
	
	Args:
		phone_number: User's phone number
		
	Returns:
		True if successful, False otherwise
	"""
	try:
		conn = sqlite3.connect(DATABASE_FILE)
		cursor = conn.cursor()
		
		cursor.execute("DELETE FROM users WHERE phone_number = ?", (phone_number,))
		
		conn.commit()
		conn.close()
		print(f"Deleted user {phone_number}")
		return True
	except Exception as e:
		print(f"Error deleting user: {e}")
		return False


def log_alert(phone_number: str, alert_message: str) -> bool:
	"""Log an alert sent to a user.
	
	Args:
		phone_number: User's phone number
		alert_message: The alert message sent
		
	Returns:
		True if successful, False otherwise
	"""
	try:
		user = get_user(phone_number)
		if not user:
			return False
		
		conn = sqlite3.connect(DATABASE_FILE)
		cursor = conn.cursor()
		
		cursor.execute("""
			INSERT INTO alert_log (user_id, alert_message)
			VALUES (?, ?)
		""", (user["id"], alert_message))
		
		conn.commit()
		conn.close()
		return True
	except Exception as e:
		print(f"Error logging alert: {e}")
		return False


def get_user_count() -> int:
	"""Get total number of registered users."""
	try:
		conn = sqlite3.connect(DATABASE_FILE)
		cursor = conn.cursor()
		
		cursor.execute("SELECT COUNT(*) FROM users")
		count = cursor.fetchone()[0]
		conn.close()
		
		return count
	except Exception as e:
		print(f"Error counting users: {e}")
		return 0


if __name__ == "__main__":
	# Initialize database when run directly
	init_database()
