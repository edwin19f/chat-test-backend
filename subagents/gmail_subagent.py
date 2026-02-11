import os
import sys
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Path to the Gmail MCP Server script
# Assuming folder structure:
# Personal_Orchestrator/
#   subagents/
#     gmail_subagent.py
#   mcp_servers/
#     gmail_mcp.py
PATH_TO_GMAIL_MCP_SERVER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "gmail_mcp.py"))

if not os.path.exists(PATH_TO_GMAIL_MCP_SERVER):
    print(f"⚠️ ERROR: Gmail MCP Server not found at: {PATH_TO_GMAIL_MCP_SERVER}")

gmail_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='gmail_assistant',
    description="An agent that can read, draft, and send emails, and manage labels.",
    instruction=(
        "You are a smart email assistant. "
        "You can read emails, search specific threads, draft, and send, label, and unlabel, mark as read, and mark as unread, delete, and move emails for the user. "
        "Use the available tools on the Gmail_mcp_server to interact with Gmail and user needs. "
        "If the user or orchestrator asks to send an email (especially a meeting confirmation), DRAFT the email content first and show it to the user. "
        "Then ASK FOR CONFIRMATION ('Does this look good to send?') before calling the 'send_email' tool. "
        "For meeting confirmations, ensure the email is professional and includes the Zoom link and Time clearly. "
        "If the user asks to read/replay, ensure you are using their email."
    ),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='python',
                args=[PATH_TO_GMAIL_MCP_SERVER],
                env={
                    "PYTHONUNBUFFERED": "1",
                    "GMAIL_CLIENT_ID": os.getenv("GMAIL_CLIENT_ID", ""),
                    "GMAIL_CLIENT_SECRET": os.getenv("GMAIL_CLIENT_SECRET", ""),
                    "GMAIL_REFRESH_TOKEN": os.getenv("GMAIL_REFRESH_TOKEN", "")
                }
            )
        )
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1000
    )
)
