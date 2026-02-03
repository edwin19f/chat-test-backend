import sys
import os
import json
from datetime import datetime

# Add the directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from calendar_mcp import CalendarService

def test_final():
    print("--- Testing Final 'Top 5' `find_free_slots` Implementation ---")
    try:
        service = CalendarService()
    except Exception as e:
        print(f"Failed to init service: {e}")
        return

    # Test Case 1: 60 mins (Default max_slots=5)
    print("\nTest 1: 60 mins (Requesting 5 slots)")
    res1 = service.find_free_slots(duration_minutes=60, max_slots=5)
    print(f"-> Found {len(res1)} slots.")
    print(json.dumps(res1, indent=2))

    # Test Case 2: 120 mins (Default max_slots=5)
    print("\nTest 2: 120 mins (Requesting 5 slots)")
    res2 = service.find_free_slots(duration_minutes=120, max_slots=5)
    print(f"-> Found {len(res2)} slots.")
    print(json.dumps(res2, indent=2))

if __name__ == "__main__":
    test_final()
