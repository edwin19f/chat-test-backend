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
        "If you need to send an email, first ask for confirmation, do not send automatically, a create an structured direct email."
        "to send email, move email or delete email, you need a confirmation from the user with yes or no. so always ask for confirmation and wait for the user confirmation before sending the email."
        "if the user ask for the last or latest or any related with the unread or read emails, you need to show the unread emails from the primary box, do not read promotions, social, and updates, unless the user ask for it."
        "if the user ask for replay the email make sure the replay is from the user email and not from the assistant email or any other email., unless the user ask for it."     
    ),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command=sys.executable,
                args=[PATH_TO_GMAIL_MCP_SERVER],
                env=os.environ.copy() | {
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
