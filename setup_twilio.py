"""Setup script to configure Twilio credentials.

Run this to set up your Twilio credentials for sending real SMS.
"""

import os
import sys
from pathlib import Path


def setup_twilio_credentials():
    """Interactively set up Twilio credentials."""
    
    print("\n" + "="*70)
    print("TWILIO SMS CONFIGURATION SETUP")
    print("="*70 + "\n")
    
    print("Get your Twilio credentials from: https://www.twilio.com/console\n")
    
    account_sid = input("Enter your TWILIO_ACCOUNT_SID: ").strip()
    auth_token = input("Enter your TWILIO_AUTH_TOKEN: ").strip()
    phone_number = input("Enter your TWILIO_PHONE_NUMBER (e.g., +1234567890): ").strip()
    
    if not all([account_sid, auth_token, phone_number]):
        print("\n[ERROR] All fields are required!\n")
        return False
    
    # Create .env file
    env_file = Path(".env")
    env_content = f"""# Twilio SMS Configuration
TWILIO_ACCOUNT_SID={account_sid}
TWILIO_AUTH_TOKEN={auth_token}
TWILIO_PHONE_NUMBER={phone_number}
"""
    
    try:
        env_file.write_text(env_content)
        print(f"\n[OK] Credentials saved to .env file")
        print(f"[INFO] The daily scheduler will now use these credentials to send real SMS\n")
        return True
    except Exception as e:
        print(f"\n[ERROR] Failed to save credentials: {e}\n")
        return False


def setup_via_manual():
    """Show how to set credentials manually."""
    print("\n" + "="*70)
    print("MANUAL SETUP (WINDOWS PowerShell)")
    print("="*70 + "\n")
    
    print("Run these commands in PowerShell to set environment variables:\n")
    print('$env:TWILIO_ACCOUNT_SID = "your_account_sid"')
    print('$env:TWILIO_AUTH_TOKEN = "your_auth_token"')
    print('$env:TWILIO_PHONE_NUMBER = "your_phone_number"')
    print("\nThen run: python daily_scheduler.py test\n")


if __name__ == "__main__":
    
    if len(sys.argv) > 1 and sys.argv[1] == "manual":
        setup_via_manual()
    else:
        success = setup_twilio_credentials()
        if success:
            print("[NEXT STEP] Run: python daily_scheduler.py test")
            print("          OR: python add_personal_farmer.py <phone> <location> <lat> <lon>")
            print("          Then run: python daily_scheduler.py test\n")
