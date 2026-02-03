from datetime import datetime
import time

def check_time():
    now = datetime.now()
    now_aware = now.astimezone()
    
    print(f"System Local Time (according to Python): {now}")
    print(f"Timezone Aware String: {now_aware}")
    print(f"Formatted String (Agent sees this): {now_aware.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
    print(f"Timezone Name: {now_aware.tzname()}")
    
if __name__ == "__main__":
    check_time()
