import sys
import os
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv

# Add the directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the subagent directly
try:
    from subagents.calendar_subagent import calendar_agent
except ImportError:
    # If running from root, this might fail if __init__.py missing? 
    # Try adding subagents to path? No, assuming root is Personal_Orchestrator
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'subagents'))
    from calendar_subagent import calendar_agent

load_dotenv()

async def run_calendar_test():
    print("--- Testing Calendar Agent Direct ---\n")
    session_service = InMemorySessionService()
    
    # We use the calendar_agent directly in the runner
    runner = Runner(agent=calendar_agent, app_name="calendar_tester", session_service=session_service)
    session_id = "cal_test_001"
    user_id = "tester"
    
    await session_service.create_session(app_name="calendar_tester", user_id=user_id, session_id=session_id)
    
    # Specific prompt to trigger find and book
    query = "Find a free 30 min slot tomorrow morning and book a meeting called 'Direct Agent Test'."
    
    print(f"User Query: {query}\n")
    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    try:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            if event.error_message:
                print(f"ERROR: {event.error_message}")
            
            if event.content and event.content.parts:
                print(f"Agent: {event.content.parts[0].text}")
                
            if event.actions:
                 # Debugging tool calls
                 print(f"Action: {event.actions}")

    except Exception as e:
        print(f"\nRuntime Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_calendar_test())
