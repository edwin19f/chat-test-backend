import asyncio
import os
import json
import logging
import base64
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# MCP Server Imports
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp import types as mcp_types

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


#https://developers.zoom.us/docs/api/meetings/#tag/meetings/post/users/{userId}/meetings

load_dotenv()

class ZoomService:
    BASE_URL = "https://api.zoom.us/v2"
    OAUTH_URL = "https://zoom.us/oauth/token"

    def __init__(self):
        self.account_id = os.getenv("ZOOM_ACCOUNT_ID")
        self.client_id = os.getenv("ZOOM_CLIENT_ID")
        self.client_secret = os.getenv("ZOOM_CLIENT_SECRET")
        self.access_token = None
        self.token_expires_at = 0

    def _get_access_token(self):
        """Retrieves an access token using Server-to-Server OAuth."""
        if self.access_token and datetime.now().timestamp() < self.token_expires_at:
            return self.access_token

        if not (self.account_id and self.client_id and self.client_secret):
            raise ValueError("Missing Zoom credentials (ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET)")

        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "account_credentials",
            "account_id": self.account_id
        }

        response = requests.post(self.OAUTH_URL, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        # Set expiry slightly before actual expiry to be safe
        self.token_expires_at = datetime.now().timestamp() + token_data["expires_in"] - 60
        
        return self.access_token

    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Helper to make authenticated requests to Zoom API."""
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        url = f"{self.BASE_URL}{endpoint}"
        
        response = requests.request(method, url, headers=headers, json=data, params=params)
        response.raise_for_status()
        return response.json()

    def list_meetings(self, user_id: str = "me", page_size: int = 10) -> List[Dict]:
        """Lists scheduled meetings for a user."""
        try:
            params = {"page_size": page_size, "type": "scheduled"}
            result = self._make_request("GET", f"/users/{user_id}/meetings", params=params)
            meetings = result.get("meetings", [])
            
            meeting_list = []
            for m in meetings:
                meeting_list.append({
                    "id": m.get("id"),
                    "topic": m.get("topic"),
                    "start_time": m.get("start_time"),
                    "duration": m.get("duration"),
                    "join_url": m.get("join_url")
                })
            return meeting_list
        except Exception as e:
            logger.error(f"Error listing meetings: {e}")
            return [{"error": str(e)}]

    def create_meeting(self, topic: str, start_time: str, duration: int, user_id: str = "me") -> Dict:
        """Creates a meeting."""
        try:
            payload = {
                "topic": topic,
                "type": 2, # Scheduled meeting
                "start_time": start_time,
                "duration": duration,
                "settings": {
                    "host_video": True,
                    "participant_video": True,
                    "join_before_host": False,
                    "mute_upon_entry": False,
                    "waiting_room": True
                }
            }
            result = self._make_request("POST", f"/users/{user_id}/meetings", data=payload)
            return {
                "id": result.get("id"),
                "topic": result.get("topic"),
                "start_time": result.get("start_time"),
                "join_url": result.get("join_url"),
                "password": result.get("password")
            }
        except Exception as e:
            logger.error(f"Error creating meeting: {e}")
            return {"error": str(e)}

# --- MCP Server Setup ---
app = Server("zoom-mcp-server")
zoom_service = None

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="list_meetings",
            description="List upcoming Zoom meetings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_size": {"type": "integer", "description": "Max number of meetings to list (default 10)."}
                }
            }
        ),
        mcp_types.Tool(
            name="create_meeting",
            description="Create a new Zoom meeting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Meeting topic."},
                    "start_time": {"type": "string", "description": "Start time in ISO format (e.g. '2023-10-27T10:00:00Z')."},
                    "duration": {"type": "integer", "description": "Duration in minutes."},
                },
                "required": ["topic", "start_time", "duration"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    global zoom_service
    if not zoom_service:
        try:
            zoom_service = ZoomService()
        except Exception as e:
            return [mcp_types.TextContent(type="text", text=f"Error initializing Zoom Service: {str(e)}")]

    if name == "list_meetings":
        result = zoom_service.list_meetings(page_size=arguments.get("page_size", 10))
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "create_meeting":
        result = zoom_service.create_meeting(
            arguments["topic"],
            arguments["start_time"],
            arguments["duration"]
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    return [mcp_types.TextContent(type="text", text="Tool not found")]

async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="zoom-mcp-server",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run())
