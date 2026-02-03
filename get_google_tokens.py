import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Scopes required for the agent
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'
]

def get_new_token():
    print("--- Google OAuth Token Generator ---")
    print("This script will help you generate a new Refresh Token.")
    print("You need your Client ID and Client Secret from Google Cloud Console.\n")

    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Client ID and Secret are required.")
        return

    # Create a client config dictionary
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    }

    try:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)
        
        print("\n✅ Authentication Successful!")
        print("-" * 50)
        print(f"GMAIL_CLIENT_ID={client_id}")
        print(f"GMAIL_CLIENT_SECRET={client_secret}")
        print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
        print("-" * 50)
        print("Copy these values into your .env file.")
        
        # Also print for Calendar for convenience (same values)
        print("\nFor Calendar (same credentials):")
        print(f"CALENDAR_CLIENT_ID={client_id}")
        print(f"CALENDAR_CLIENT_SECRET={client_secret}")
        print(f"CALENDAR_REFRESH_TOKEN={creds.refresh_token}")

    except Exception as e:
        print(f"\n❌ Error during authentication: {e}")

if __name__ == "__main__":
    get_new_token()
