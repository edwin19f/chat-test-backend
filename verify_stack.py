
import requests
import time
import sys

# Define URLs
FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://127.0.0.1:8000/api/chat"

def check_frontend():
    print(f"Checking Frontend at {FRONTEND_URL}...")
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is REACHABLE and responding with HTTP 200.")
            return True
        else:
            print(f"⚠️ Frontend reachable but returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend check FAILED: {e}")
        return False

def check_backend():
    print(f"Checking Backend at {BACKEND_URL}...")
    payload = {
        "messages": [],
        "new_message": "Hello from integration test",
        "conversation_id": "test-integration-123"
    }
    
    try:
        response = requests.post(BACKEND_URL, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is REACHABLE and responding with HTTP 200.")
            print(f"   Response from Agent: {data.get('text', 'No text in response')}")
            return True
        else:
            print(f"⚠️ Backend reachable but returned status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Backend check FAILED: {e}")
        return False

def main():
    print("--- Starting Integration Self-Check ---")
    time.sleep(2) # Give servers a moment to fully initialize if just started
    
    fe_ok = check_frontend()
    be_ok = check_backend()
    
    if fe_ok and be_ok:
        print("\n🎉 SUCCESS: Both Frontend and Backend are running and accessible!")
    else:
        print("\n❌ FAILURE: One or both services are not responding correctly.")

if __name__ == "__main__":
    main()
