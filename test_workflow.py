import sys
import os
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv

# Add the directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent import root_agent

load_dotenv()

async def run_test():
    print("--- Starting End-to-End Workflow Test ---")
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="test_runner", session_service=session_service)
    session_id = "test_session_001"
    user_id = "tester"
    
    await session_service.create_session(app_name="test_runner", user_id=user_id, session_id=session_id)
    
    # prompting "next spot available" implies we trust the agent to pick one.
    query = "Create a meeting on the next available spot for 30 min (just pick the first one you find) and then send the details of the meeting to edwin19flp@gmail.com with subject 'test' and body 'meeting details'."
    
    print(f"\nUser Query: {query}\n")
    
    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    try:
        # We run the loop. The agent might return multiple intermediate steps/events.
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            if event.is_final_response():
                if event.content and event.content.parts:
                    print(f"\n[Final Response]: {event.content.parts[0].text}")
                else:
                    print("\n[Final Response]: (No text)")
            elif event.actions:
                # print(f"Action: {event.actions}")
                pass
            
            if event.error_message:
                 print(f"Error: {event.error_message}")
            
            # Additional debug
            if event.content:
                 print(f"DEBUG Event Content: {event.content}")

    except Exception as e:
        print(f"Runtime Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
