import sys
import os
import logging
from datetime import datetime, timedelta

# Ensure we can import from local subdirectories
current_dir = os.path.dirname(os.path.abspath(__file__))
# Add mcp_servers to path to import CalendarService
mcp_servers_dir = os.path.join(current_dir, "mcp_servers")
sys.path.append(mcp_servers_dir)

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from calendar_mcp import CalendarService
    print("✅ Successfully imported CalendarService")
except ImportError as e:
    print(f"❌ Failed to import CalendarService: {e}")
    sys.exit(1)

def test_create_event():
    print("\n--- Testing Calendar Event Creation ---")
    
    try:
        service = CalendarService()
        print("✅ CalendarService initialized")
    except Exception as e:
        print(f"❌ Failed to initialize CalendarService: {e}")
        return

    # Define test event data
    # "Feb 3, 2026, from 1pm to 2pm"
    # ISO Format: 2026-02-03T13:00:00Z
    
    start_time = "2026-02-03T13:00:00Z"
    end_time = "2026-02-03T14:00:00Z"
    summary = "Debug Test - Deep Work Session"
    description = "This is a test event from the debug script."

    print(f"Attempting to create event: {summary}")
    print(f"Start: {start_time}")
    print(f"End: {end_time}")

    result = service.create_event(summary, start_time, end_time, description)
    
    print("\n--- Result ---")
    print(result)

    if 'error' in result:
        print("❌ Event creation failed!")
    elif 'id' in result:
        print("✅ Event created successfully!")
        print(f"Link: {result.get('link')}")
        
        # Cleanup (Optional: Comment out to keep the event)
        # print("Cleaning up (deleting test event)...")
        # del_result = service.delete_event(result['id'])
        # print(f"Delete result: {del_result}")
    else:
        print("⚠️ Unexpected result format.")

if __name__ == "__main__":
    test_create_event()
