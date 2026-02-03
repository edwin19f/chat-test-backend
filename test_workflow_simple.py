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

async def run_single_turn():
    print("--- Single Turn Workflow Test ---")
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="test_runner", session_service=session_service)
    session_id = "test_session_002"
    user_id = "tester"
    
    await session_service.create_session(app_name="test_runner", user_id=user_id, session_id=session_id)
    
    query = "Find the next available 60 minute slot and book a meeting called 'Test Meeting' there."
    
    print(f"\nUser Query: {query}\n")
    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    try:
        # Run until the first turn completes (which might involve tool calls)
        # We manually iterate to see what happens
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            if event.error_message:
                print(f"XXX Error: {event.error_message}")
            if event.content:
                 print(f"Event Content: {event.content}")
            if event.actions:
                 print(f"Event Actions: {event.actions}")
                 
    except Exception as e:
        print(f"Runtime Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_single_turn())
    except KeyboardInterrupt:
        pass
