import requests
import sqlite3
import random
import string
import os
import time

# --- Configuration ---
API_URL = "http://localhost:8000/api/v1/auth/signup"
# Note: DB location resolution creates a double 'api' folder structure currently
DB_PATH = os.path.join("api", "api", "data", "vysalytica.db")

# --- Helpers ---
def generate_random_email():
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_str}@example.com"

def check_db_for_user(email):
    print(f"Checking database at {DB_PATH} for user {email}...")
    if not os.path.exists(DB_PATH):
        print("[FAILED] Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, created_at FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            print(f"[OK] User found in DB: {user}")
            return True
        else:
            print("[FAILED] User NOT found in DB.")
            return False
    except Exception as e:
        print(f"[FAILED] Database error: {e}")
        return False

# --- Main Test ---
def run_test():
    email = generate_random_email()
    payload = {
        "email": email,
        "password": "Password123!",
        "name": "Automated Test User"
    }
    
    print(f"Attempting signup for: {email}")
    
    try:
        # Wait a moment for server to ensure it's up if just started
        time.sleep(2) 
        
        response = requests.post(API_URL, json=payload)
        
        print(f"HTTP Status: {response.status_code}")
        try:
            data = response.json()
            print(f"Response Body: {data}")
        except:
            print(f"Raw Response: {response.text}")

        if response.status_code == 200 and data.get("success"):
            print("[OK] API Signup Successful")
            
            # Verify DB persistence
            if check_db_for_user(email):
                print("[OK] Data persistence verified.")
            else:
                print("[FAILED] Data persistence FAILED.")
        else:
            print("[FAILED] API Signup Failed")
            
    except requests.exceptions.ConnectionError:
        print("[FAILED] Could not connect to backend. Is the server running on port 8000?")
    except Exception as e:
        print(f"[FAILED] An error occurred: {e}")

if __name__ == "__main__":
    run_test()
