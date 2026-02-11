from google.adk.agents import Agent, SequentialAgent, ParallelAgent, LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.genai import types
from dotenv import load_dotenv
import os
import sys

# Ensure we can import from local subdirectories if running this script directly
sys.path.append(os.path.dirname(__file__))

load_dotenv()

# Define paths to MCP Servers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVERS_DIR = os.path.join(BASE_DIR, "mcp_servers")
CALENDAR_MCP = os.path.join(MCP_SERVERS_DIR, "calendar_mcp.py")
ZOOM_MCP = os.path.join(MCP_SERVERS_DIR, "zoom_mcp.py")
GMAIL_MCP = os.path.join(MCP_SERVERS_DIR, "gmail_mcp.py")

# --- Define Sub-Agents (Direct Tool Usage) ---

# 1. Booking Agent (Zoom)
Booking_Agent = LlmAgent(
    name="Booking_Agent",
    model="gemini-2.5-flash",
    description="Creates a Zoom meeting.",
    instruction=(
        "You create a Zoom meeting using the 'create_meeting' tool. "
        "Use the start time, duration, and user name provided in the context. "
        "Topic: 'Strategy Session with [User Name]'. Duration: 30 mins (unless specified otherwise). "
        "Output the Zoom Meeting ID, Join URL, and Time."
    ),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='python',
                args=[ZOOM_MCP],
                env={
                    "PYTHONUNBUFFERED": "1",
                    "ZOOM_ACCOUNT_ID": os.getenv("ZOOM_ACCOUNT_ID", ""),
                    "ZOOM_CLIENT_ID": os.getenv("ZOOM_CLIENT_ID", ""),
                    "ZOOM_CLIENT_SECRET": os.getenv("ZOOM_CLIENT_SECRET", "")
                }
            )
        )
    ],
    output_key="zoom_meeting_details"
)

# 2. Finalization Agents (Parallel: Email & Calendar)

# 2a. Email Confirmation (Gmail)
Email_Confirmation_Agent = LlmAgent(
    name="Email_Confirmation_Agent",
    model="gemini-2.5-flash",
    description="Sends a confirmation email.",
    instruction=(
        "Send a confirmation email using 'send_email' tool. "
        "To: [User Email]. Subject: 'Strategy Session with [User Name]'. "
        "Body: Include Zoom Meeting ID, Join URL, and Time from the previous steps."
    ),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='python',
                args=[GMAIL_MCP],
                env={
                    "PYTHONUNBUFFERED": "1",
                    "GMAIL_CLIENT_ID": os.getenv("GMAIL_CLIENT_ID", ""),
                    "GMAIL_CLIENT_SECRET": os.getenv("GMAIL_CLIENT_SECRET", ""),
                    "GMAIL_REFRESH_TOKEN": os.getenv("GMAIL_REFRESH_TOKEN", "")
                }
            )
        )
    ]
)

# 2b. Calendar Booking (Calendar)
Calendar_Booking_Agent = LlmAgent(
    name="Calendar_Booking_Agent",
    model="gemini-2.5-flash",
    description="Adds the meeting to the consultant's calendar.",
    instruction=(
        "Add the meeting to the calendar using 'create_event' tool. "
        "Summary: 'Strategy Session with [User Name]'. "
        "Start Time: Use the chosen start time. "
        "End Time: 30 mins after start time. "
        "Description: Youtube Zoom Link: [Zoom Join URL]. User Email: [User Email]"
    ),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='python',
                args=[CALENDAR_MCP],
                env={
                    "PYTHONUNBUFFERED": "1",
                    "CALENDAR_CLIENT_ID": os.getenv("CALENDAR_CLIENT_ID", ""),
                    "CALENDAR_CLIENT_SECRET": os.getenv("CALENDAR_CLIENT_SECRET", ""),
                    "CALENDAR_REFRESH_TOKEN": os.getenv("CALENDAR_REFRESH_TOKEN", "")
                }
            )
        )
    ]
)

# 2. Finalization (Parallel)
Finalization_Agent = ParallelAgent(
    name="Finalization_Agent",
    sub_agents=[Email_Confirmation_Agent, Calendar_Booking_Agent],
    description="Simultaneously sends confirmation email and adds event to calendar."
)

# --- Booking Execution Workflow (Sequential) ---
Booking_Execution_Workflow = SequentialAgent(
    name="Booking_Execution_Workflow",
    sub_agents=[Booking_Agent, Finalization_Agent],
    description="Executes the finalized booking: Books Zoom -> Confirm (Email & Calendar). REQUIRES: Name, Email, Start Time."
)

# Create Agent Tools for the orchestrator to call
execution_tool = AgentTool(Booking_Execution_Workflow)

# Create Calendar Tool for Negotiation (Check Availability)
calendar_negotiation_tool = MCPToolset(
    connection_params=StdioServerParameters(
        command='python',
        args=[CALENDAR_MCP],
        env={
            "PYTHONUNBUFFERED": "1",
            "CALENDAR_CLIENT_ID": os.getenv("CALENDAR_CLIENT_ID", ""),
            "CALENDAR_CLIENT_SECRET": os.getenv("CALENDAR_CLIENT_SECRET", ""),
            "CALENDAR_REFRESH_TOKEN": os.getenv("CALENDAR_REFRESH_TOKEN", "")
        }
    )
)

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
        "Your goal is to help the user schedule meetings efficiently. "
        "1. **General Questions**: Answer directly using the CANGRO CONTEXT below.\n"
        "2. **Booking Flow (Interactive)**:\n"
        "   a. **Negotiate Time**: If the user wants to book, use 'find_free_slots' (via calendar tool) to find availability. "
        "Discuss with the user until a specific time is AGREED upon. Do not guess.\n"
        "   b. **Collect Details**: Ensure you have the User's NAME and EMAIL.\n"
        "   c. **Execute Booking**: ONLY when Time, Name, and Email are confirmed, call the 'Booking_Execution_Workflow' tool. "
        "You MUST pass the 'start_time', 'user_name', and 'user_email' in the instructions/context to the tool.\n\n"
        "### CANGRO CONTEXT ###\n"
        f"{cangro_context}\n"
    ),  
    tools=[execution_tool, calendar_negotiation_tool]
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
