from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from dotenv import load_dotenv
import os
import sys

# Ensure we can import from local subdirectories if running this script directly
sys.path.append(os.path.dirname(__file__))

load_dotenv()

# Import sub-agents
from subagents.gmail_subagent import gmail_agent
from subagents.calendar_subagent import calendar_agent
from subagents.zoom_subagent import zoom_agent

# Create Agent Tools for the orchestrator to call

def load_cangro_context():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'cangro.md'), 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return "Cangro documentation not found."

cangro_context = load_cangro_context()

root_agent = Agent(
    name="Personal_Orchestrator",
    model="gemini-2.5-flash",
    description="The main orchestrator agent.",
    instruction=(
        "You are the Personal Orchestrator Agent and the main assistant for CANGRO. "
        "Your goal is to route user questions to the correct specialist sub-agent by DELEGATING execution to them, but do not mention that you are delegating to the user "
        "your task is get the user name and email before delegate to the sub-agent, if the user does not provide the name and email, ask for it"
        "OR answer questions directly about CANGRO using the provided documentation.\n\n"
        "### CANGRO CONTEXT ###\n"
        f"{cangro_context}\n\n"
        "### INSTRUCTIONS ###\n"
        "1. For CANGRO User Questions: Use the context above to answer questions about CANGRO, acting as its main assistant. "
        "Follow the RESPONSE STYLE & PERSONA RULES and HARD RULES defined in the context.\n"
        "2. For  email operations (read, send, draft, label), delegate to 'gmail_assistant'. "
        "3. For  calendar operations (list events, create, find nearest free slots, book appointments, schedule meetings), delegate to 'calendar_assistant'. "
        "4. For Zoom operations (list meetings, create meeting, schedule Zoom), delegate to 'zoom_assistant'. "
        "Do not answer the question yourself directly if it requires these specialists (email, calendar, zoom). "
        "CRITICAL: To delegate, you must hand off control. Do not ask for confirmation or details yourself. Pass the user's full request to the sub-agent.\n"
        "### CANGRO MEETING, BOOKING, SCHEDULE WORKFLOW ###\n"
        "If the user wants to book a strategy session, or meeting or schedule an appointment, or meeting to discuss ask for name and email  CANGRO:\n"
        "1. **Check Availability**: Delegate to 'calendar_agent' to find free slots (default 30 mins).\n"
        "2. **Get Details**: Once a slot is chosen, if no email or name is provided, ask for it.\n"
        "3. **Book Meeting**: Delegate to 'zoom_agent' to create a meeting on the chosen slot. Topic: 'Strategy Session with [Name]'. Duration: 30 mins. then show the user the zoom meeting id, zoom url and time.\n"
        "4. **Send Confirmation**: Delegate to 'gmail_agent' to send an email to the user ([EMAIL_ADDRESS]) with the Subject (create a subject base on the conversation) and Body (create an email with the full zoom details, date, time, zoom url and zoom meeting id)."
    ),  
    sub_agents=[gmail_agent, calendar_agent, zoom_agent]
)



if __name__ == "__main__":
    import asyncio
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    
    async def run_interactive_loop():
        print("--- Personal Orchestrator Agent (ADK) ---")
        session_service = InMemorySessionService()
        runner = Runner(agent=root_agent, app_name="personal_orchestrator", session_service=session_service)
        session_id = "interactive_session"
        user_id = "user"
        
        await session_service.create_session(app_name="personal_orchestrator", user_id=user_id, session_id=session_id)
        
        print("Type 'quit' to exit.")
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ["quit", "exit"]:
                break
                
            content = types.Content(role='user', parts=[types.Part(text=user_input)])
            
            try:
                async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                    if event.is_final_response():
                        if event.content and event.content.parts:
                            print(f"Agent: {event.content.parts[0].text}")
                        else:
                            print("Agent: (No text response)")
                    elif event.actions and event.actions.escalate:
                        print(f"Error: {event.error_message}")
            except Exception as e:
                print(f"Runtime Error: {e}")

    asyncio.run(run_interactive_loop())
