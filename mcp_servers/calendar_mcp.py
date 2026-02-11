import asyncio
import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone, time
import pytz # Ensure pytz is available or handle timezones carefully
from dotenv import load_dotenv

# Google API Imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# MCP Server Imports
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp import types as mcp_types

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
#https://developers.google.com/workspace/calendar/api/v3/reference
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- Calendar Service ---
class CalendarService:
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticates with Calendar API using credentials from env."""
        creds = None
        
        client_id = os.getenv('CALENDAR_CLIENT_ID')
        client_secret = os.getenv('CALENDAR_CLIENT_SECRET')
        refresh_token = os.getenv('CALENDAR_REFRESH_TOKEN')

        # Fallback to GMAIL credentials if CALENDAR ones are missing
        if not (client_id and client_secret and refresh_token):
            logger.info("CALENDAR credentials missing, trying GMAIL credentials fallback...")
            client_id = client_id or os.getenv('GMAIL_CLIENT_ID')
            client_secret = client_secret or os.getenv('GMAIL_CLIENT_SECRET')
            refresh_token = refresh_token or os.getenv('GMAIL_REFRESH_TOKEN')

        if client_id and client_secret and refresh_token:
            logger.info("Using credentials from environment variables.")
            creds = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES
            )
        else:
            logger.error("Missing credentials (CALENDAR_ or GMAIL_ prefixes) in .env")
            raise RuntimeError("Could not authenticate. Please provide credentials in .env.")

        self.creds = creds
        self.service = build('calendar', 'v3', credentials=self.creds)
        logger.info("Calendar API Service initialized.")

    def list_events(self, max_results: int = 10) -> List[Dict]:
        """Lists upcoming events."""
        try:
            now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            events_result = self.service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            event_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                event_list.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No Title'),
                    'start': start,
                    'status': event.get('status')
                })
            return event_list
        except Exception as error:
            logger.error(f"An error occurred in list_events: {error}")
            return []

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = "") -> Dict:
        """Creates a new event. Times must be in ISO format."""
        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time,
                },
                'end': {
                    'dateTime': end_time,
                },
            }

            event = self.service.events().insert(calendarId='primary', body=event).execute()
            return {'id': event['id'], 'status': 'Event created', 'link': event.get('htmlLink')}
        except Exception as error:
            return {'error': str(error)}
            
    def delete_event(self, event_id: str) -> Dict:
        """Deletes an event."""
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return {'status': 'Event deleted', 'id': event_id}
        except Exception as error:
             return {'error': str(error)}

    def find_free_slots(self, duration_minutes: int = 30, start_date: str = None, max_slots: int = 5) -> List[Dict]:
        """
        Finds the nearest free time slots (Mon-Fri, 8am-5pm) using Google Calendar FreeBusy API.
        
        Args:
            duration_minutes: Length of the desired slot in minutes.
            start_date: Optional ISO start time. Defaults to now.
            max_slots: Maximum number of slots to return (default 5).
        """
        try:
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            else:
                start_dt = datetime.now().astimezone()

            logger.info(f"Finding top {max_slots} free slots of {duration_minutes} mins via freebusy API.")
            
            # Look ahead 7 days
            end_dt = start_dt + timedelta(days=7)
            
            body = {
                "timeMin": start_dt.isoformat(),
                "timeMax": end_dt.isoformat(),
                "timeZone": str(start_dt.tzinfo) if start_dt.tzinfo else "UTC",
                "items": [{"id": "primary"}]
            }
            
            events_result = self.service.freebusy().query(body=body).execute()
            calendars = events_result.get('calendars', {})
            busy_list = calendars.get('primary', {}).get('busy', [])
            
            found_slots = []
            current_time = start_dt
            
            while current_time < end_dt and len(found_slots) < max_slots:
                 # Skip if weekend
                if current_time.weekday() >= 5: 
                    # Move to next Monday 8am
                    days_ahead = 7 - current_time.weekday()
                    current_time = current_time.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
                    continue

                work_start = current_time.replace(hour=8, minute=0, second=0, microsecond=0)
                work_end = current_time.replace(hour=17, minute=0, second=0, microsecond=0)

                if current_time < work_start:
                    current_time = work_start
                
                if current_time >= work_end:
                    current_time = (current_time + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
                    continue

                slot_end = current_time + timedelta(minutes=duration_minutes)
                
                conflict_found = False
                for busy in busy_list:
                    b_start = datetime.fromisoformat(busy['start'])
                    b_end = datetime.fromisoformat(busy['end'])
                    
                    # Check Overlap
                    if (current_time < b_end) and (slot_end > b_start):
                        # Jump to end of conflict
                        # MIGRATION: Ensure we stay in user's timezone!
                        current_time = b_end.astimezone(start_dt.tzinfo)
                        conflict_found = True
                        break
                
                if not conflict_found:
                    if slot_end <= work_end:
                        found_slots.append({
                            "start_time": current_time.isoformat(), 
                            "end_time": slot_end.isoformat(),
                        })
                        # Move past this slot to find the next one (e.g. 30 mins later)
                        # We jump by duration to avoid overlapping suggested slots? 
                        # Or should we jump by some small increment? default to jumping by duration.
                        current_time = slot_end
                    else:
                        # Slot fits in 'free' time but extends past work hours
                        current_time = (current_time + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
            
            return found_slots
        except Exception as e:
            logger.error(f"Error in find_free_slots: {e}")
            return [{"error": str(e)}]

# --- MCP Server Setup ---
app = Server("calendar-mcp-server")
calendar_service = None # Initialize later

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="list_events",
            description="List upcoming calendar events.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Max number of events to list (default 10)."}
                }
            }
        ),
        mcp_types.Tool(
            name="create_event",
            description="Create a new calendar event. Times must be in ISO format (e.g. '2023-10-27T10:00:00Z').",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title."},
                    "start_time": {"type": "string", "description": "Start time in ISO format (ISO 8601)."},
                    "end_time": {"type": "string", "description": "End time in ISO format (ISO 8601)."},
                    "description": {"type": "string", "description": "Optional description."}
                },
                "required": ["summary", "start_time", "end_time"]
            }
        ),
        mcp_types.Tool(
            name="delete_event",
            description="Delete a calendar event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "The ID of the event to delete."}
                },
                "required": ["event_id"]
            }
        ),
        mcp_types.Tool(
            name="find_free_slots",
            description="Find the nearest 5 free time slots during working hours (Mon-Fri, 8am-5pm).",
            inputSchema={
                "type": "object",
                "properties": {
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes (default 30)."},
                    "start_date": {"type": "string", "description": "Search start date (ISO format)."},
                    "max_slots": {"type": "integer", "description": "Max slots to return (default 5)."}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    global calendar_service
    if not calendar_service:
        try:
            calendar_service = CalendarService()
        except Exception as e:
             return [mcp_types.TextContent(type="text", text=f"Error initializing Calendar Service: {str(e)}")]

    if name == "list_events":
        max_results = arguments.get("max_results", 10)
        events = calendar_service.list_events(max_results)
        return [mcp_types.TextContent(type="text", text=json.dumps(events, indent=2))]

    elif name == "create_event":
        result = calendar_service.create_event(
            arguments["summary"],
            arguments["start_time"],
            arguments["end_time"],
            arguments.get("description", "")
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
    elif name == "delete_event":
        result = calendar_service.delete_event(arguments["event_id"])
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "find_free_slots":
        result = calendar_service.find_free_slots(
            arguments.get("duration_minutes", 30),
            arguments.get("start_date"),
            arguments.get("max_slots", 5)
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    return [mcp_types.TextContent(type="text", text="Tool not found")]

async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="calendar-mcp-server",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run())
