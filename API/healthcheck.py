import os
import time
from sqlalchemy import create_engine, text

def check_env_variables():
    print("\n--- Checking Environment Variables ---")
    required_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_API_KEY",
        "TWILIO_API_SECRET",
        "TWILIO_PHONE_NUMBER",
        "DATABASE_URL",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD"
    ]
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✔ {var} is set")
        else:
            print(f"  ✘ {var} is MISSING")
            all_set = False
    return all_set

def check_twilio():
    print("\n--- Checking Twilio Package ---")
    try:
        from twilio.rest import Client
        print("  ✔ Twilio package is installed")

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        client = Client(account_sid, auth_token)
        account = client.api.accounts(account_sid).fetch()
        print(f"  ✔ Twilio connection successful — Account: {account.friendly_name}")
        return True
    except ImportError:
        print("  ✘ Twilio package is NOT installed")
        return False
    except Exception as e:
        print(f"  ✘ Twilio connection failed: {e}")
        return False

def check_database(retries=5, delay=3):
    print("\n--- Checking Database Connection ---")
    try:
        import pymysql
        print("  ✔ pymysql package is installed")
    except ImportError:
        print("  ✘ pymysql is NOT installed")
        return False

    try:
        import sqlalchemy
        print("  ✔ SQLAlchemy package is installed")
    except ImportError:
        print("  ✘ SQLAlchemy is NOT installed")
        return False

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("  ✘ DATABASE_URL is not set")
        return False

    for attempt in range(1, retries + 1):
        try:
            print(f"  Attempting database connection ({attempt}/{retries})...")
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("  ✔ Database connection successful")
            return True
        except Exception as e:
            print(f"  ✘ Attempt {attempt} failed: {e}")
            if attempt < retries:
                print(f"  Retrying in {delay} seconds...")
                time.sleep(delay)

    print("  ✘ Could not connect to the database after all attempts")
    return False

def main():
    print("========================================")
    print("        HEALTHCHECK STARTING            ")
    print("========================================")

    env_ok = check_env_variables()
    twilio_ok = check_twilio()
    db_ok = check_database()

    print("\n========================================")
    print("            HEALTHCHECK SUMMARY         ")
    print("========================================")
    print(f"  Environment Variables : {'✔ OK' if env_ok else '✘ FAILED'}")
    print(f"  Twilio Connection     : {'✔ OK' if twilio_ok else '✘ FAILED'}")
    print(f"  Database Connection   : {'✔ OK' if db_ok else '✘ FAILED'}")
    print("========================================")

    if env_ok and twilio_ok and db_ok:
        print("\n  All checks passed! 🎉")
    else:
        print("\n  Some checks failed. Please review the output above.")

if __name__ == "__main__":
    main()