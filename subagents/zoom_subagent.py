import os
import sys
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Path to the Zoom MCP Server script
PATH_TO_ZOOM_MCP_SERVER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "zoom_mcp.py"))

if not os.path.exists(PATH_TO_ZOOM_MCP_SERVER):
    print(f"⚠️ ERROR: Zoom MCP Server not found at: {PATH_TO_ZOOM_MCP_SERVER}")

def get_current_time_str():
    now = datetime.now().astimezone()
    return now.strftime("%Y-%m-%d %H:%M:%S %Z%z")

current_time_str = get_current_time_str()

zoom_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='zoom_assistant',
    description="An agent that can list and create Zoom meetings.",
    instruction=(
        f"You are a helpful Zoom assistant. Current Date and Time: {current_time_str}. "
        "You can manage user's Zoom meetings using the available tools on the zoom_mcp_server. "
        "You can 'list_meetings' to see upcoming scheduled meetings. "
        "You can 'create_meeting' to schedule a new meeting. "
        "When creating a meeting, you MUST ask for: "
        "1. Topic (what is the meeting about?) "
        "2. Start Time (when? I need a specific date and time) "
        "3. Duration (how long in minutes?) "
        "If the user provides relative times (e.g. 'tomorrow at 2pm'), calculate the ISO 8601 timestamp based on the Current Date and Time."
    ),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='python',
                args=[PATH_TO_ZOOM_MCP_SERVER],
                env={
                    "PYTHONUNBUFFERED": "1",
                    "ZOOM_ACCOUNT_ID": os.getenv("ZOOM_ACCOUNT_ID", ""),
                    "ZOOM_CLIENT_ID": os.getenv("ZOOM_CLIENT_ID", ""),
                    "ZOOM_CLIENT_SECRET": os.getenv("ZOOM_CLIENT_SECRET", "")
                }
            )
        )
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1000
    )
)
