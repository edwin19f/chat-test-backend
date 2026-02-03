import os
import sys
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime, timezone
import time

load_dotenv()

# Path to the Calendar MCP Server script
# Assuming folder structure:
# Personal_Orchestrator/subagents/calendar_subagent.py/mcp_servers/calendar_mcp.py
PATH_TO_CALENDAR_MCP_SERVER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "calendar_mcp.py"))

if not os.path.exists(PATH_TO_CALENDAR_MCP_SERVER):
    print(f"⚠️ ERROR: Calendar MCP Server not found at: {PATH_TO_CALENDAR_MCP_SERVER}")

def get_current_time_str():
    """Returns current time string with timezone info."""
    # This is a simplistic way to get local time for the context
    # ideally we use a library like pytz or zoneinfo, but standard lib is safer for now
    now = datetime.now().astimezone()
    return now.strftime("%Y-%m-%d %H:%M:%S %Z%z")

current_time_str = get_current_time_str()

calendar_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='calendar_assistant',
    description="An agent that can list, create, and delete calendar events.",
    instruction=(
        f"You are a helpful calendar assistant. Current Date and Time: {current_time_str}. "
        "You can manage the user's Google Calendar events. "
        "Use the available tools on the Calendar_mcp_server to list upcoming events, create new ones, or delete them. "
        "if the user ask for booking appointment you will find the 3 nearest free slots and ask for confirmation to create the event."
        "You can use 'find_free_slots' to find available time for meetings (Mon-Fri, 8-5). "
        "IMPORTANT: If the user asks for a specific duration (e.g. '30 min slot', '1 hour', '45 mins'), you MUST pass this duration (in minutes) to the 'find_free_slots' tool. Default is 30 mins if not specified. "
        "The tool will return the top 3 nearest free slots. PRESENT these options to the user clearly so they can choose one. "
        "Always ask for confirmation before deleting an event. "
        "When creating an event, ensure you have the summary, start time, and end time. If the user provides relative times (e.g., 'tomorrow at 2pm'), calculate the ISO 8601 timestamp based on the Current Date and Time provided."
    ),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='python',
                args=[PATH_TO_CALENDAR_MCP_SERVER],
                env={
                    "PYTHONUNBUFFERED": "1",
                    "CALENDAR_CLIENT_ID": os.getenv("CALENDAR_CLIENT_ID", os.getenv("GMAIL_CLIENT_ID", "")),
                    "CALENDAR_CLIENT_SECRET": os.getenv("CALENDAR_CLIENT_SECRET", os.getenv("GMAIL_CLIENT_SECRET", "")),
                    "CALENDAR_REFRESH_TOKEN": os.getenv("CALENDAR_REFRESH_TOKEN", os.getenv("GMAIL_REFRESH_TOKEN", ""))
                }
            )
        )
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1000
    )
)
