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
from subagents.tester_subagent import create_tester_agent

# Create Agent Tools for the orchestrator to call
gmail_tool = AgentTool(gmail_agent)
calendar_tool = AgentTool(calendar_agent)
tester_agent = create_tester_agent([gmail_tool, calendar_tool])
tester_tool = AgentTool(tester_agent)


root_agent = Agent(
    name="Personal_Orchestrator",
    model="gemini-2.5-flash",
    description="The main orchestrator agent.",
    instruction=(
        "You are the Personal Orchestrator Agent. "
        "Your goal is to route user questions to the correct specialist sub-agent by DELEGATING execution to them."
        "1. For email operations (read, send, draft, label), delegate to 'gmail_assistant'. "
        "2. For calendar operations (list events, create, find nearest free slots, book appointments, schedule meetings), delegate to 'calendar_assistant'. "
        "3. If the user says 'test agent', 'test all', or wants to verify the system, delegate to 'qa_tester_agent'. "
        "Do not answer the question yourself directly if it requires these specialists. "
        "CRITICAL: To delegate, you must hand off control. Do not ask for confirmation or details yourself. Pass the user's full request to the sub-agent."
        "If the user asks a general question not related to email or calendar, you may answer it directly."
    ),
    sub_agents=[gmail_agent, calendar_agent, tester_agent]
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
