import asyncio
import sys
import os
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Ensure we can import from local subdirectories
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from agent import root_agent

async def run_workflow():
    print("--- Running Complex Verification Workflow ---")
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="personal_orchestrator", session_service=session_service)
    session_id = "workflow_session"
    user_id = "user"
    
    await session_service.create_session(app_name="personal_orchestrator", user_id=user_id, session_id=session_id)

    # The user's complex request
    user_prompt = (
        "List my upcoming calendar events to see what I have. "
        "2. Find a free time slot after the last event and create a new event called 'Deep Work Session' there. "
        "3. Send an email to edwin19flp@gmail.com with subject 'Agent Test Run' and body 'This is a test of the fully integrated Gmail and Calendar agents.'. "
        "4. Finally, list my unread emails from the primary inbox."
    )
    
    print(f"\nUser: {user_prompt}\n")
    
    content = types.Content(role='user', parts=[types.Part(text=user_prompt)])
    
    # We increase the max turns because this might involve multiple back-and-forths between orchestrator and sub-agents
    # although standard LlmAgent might try to do it all in one context if it's smart enough, 
    # OR it will do one thing and return. 
    # Since we are using a standard Runner logic in a loop, we simulate one turn.
    # But wait, a single runner.run_async call processes ONE user message until the agent returns a final response.
    # If the Orchestrator delegates, it gets the result back, and might continue.
    
    try:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            if event.is_final_response():
                if event.content and event.content.parts:
                    print(f"Agent: {event.content.parts[0].text}")
                else:
                    print("Agent: (No text response)")
            
            # Print intermediate steps for visibility (optional, but good for debugging)
            elif event.actions:
                 # Check if it called a tool
                 pass
            
            elif event.actions and event.actions.escalate:
                print(f"Error: {event.error_message}")
                
    except Exception as e:
        print(f"Runtime Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_workflow())
