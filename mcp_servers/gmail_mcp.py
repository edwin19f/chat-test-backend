import asyncio
import os
import json
import base64
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from email.mime.text import MIMEText

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

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# --- Gmail Service ---
class GmailService:
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticates with Gmail API using credentials from env."""
        creds = None
        
        client_id = os.getenv('GMAIL_CLIENT_ID')
        client_secret = os.getenv('GMAIL_CLIENT_SECRET')
        refresh_token = os.getenv('GMAIL_REFRESH_TOKEN')

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
            logger.error("Missing GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, or GMAIL_REFRESH_TOKEN in .env")
            raise RuntimeError("Missing credentials in environment variables.")

        self.creds = creds
        self.service = build('gmail', 'v1', credentials=self.creds)
        logger.info("Gmail API Service initialized.")

    def list_threads(self, query: str = '', limit: int = 5) -> List[Dict]:
        """Lists threads matching the query."""
        try:
            results = self.service.users().threads().list(userId='me', q=query, maxResults=limit).execute()
            threads = results.get('threads', [])
            
            thread_details = []
            for thread in threads:
                t_data = self.service.users().threads().get(userId='me', id=thread['id']).execute()
                messages = t_data.get('messages', [])
                if not messages: continue
                
                last_msg = messages[-1]
                headers = last_msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                snippet = last_msg.get('snippet', '')
                
                thread_details.append({
                    'id': thread['id'],
                    'subject': subject,
                    'sender': sender,
                    'snippet': snippet,
                    'message_count': len(messages)
                })
            return thread_details
        except Exception as error:
            logger.error(f"An error occurred in list_threads: {error}")
            return []

    def read_thread(self, thread_id: str) -> Dict:
        """Reads a full thread."""
        try:
            thread = self.service.users().threads().get(userId='me', id=thread_id).execute()
            messages = []
            for msg in thread.get('messages', []):
                headers = msg['payload']['headers']
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                body = msg.get('snippet', '') # Simplified for this example
                messages.append(f"From: {sender}\nBody: {body}\n---")
            
            return {
                'id': thread['id'],
                'messages': messages
            }
        except Exception as error:
            logger.error(f"An error occurred in read_thread: {error}")
            return {'error': str(error)}

    def create_draft(self, to: str, subject: str, body: str) -> Dict:
        """Creates a draft email."""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            return {'id': draft['id'], 'status': 'Draft created'}
        except Exception as error:
             return {'error': str(error)}

    def send_email(self, to: str, subject: str, body: str) -> Dict:
        """Sends an email immediately."""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {'id': sent_message['id'], 'status': 'Email sent'}
        except Exception as error:
             return {'error': str(error)}

    def reply_to_thread(self, thread_id: str, body: str) -> Dict:
        """Replies to an email thread."""
        try:
            # Get last message to find headers
            thread = self.service.users().threads().get(userId='me', id=thread_id).execute()
            messages = thread['messages']
            last_msg = messages[-1]
            headers = last_msg['payload']['headers']
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            
            if not subject.lower().startswith('re:'):
                subject = f"Re: {subject}"

            message = MIMEText(body)
            message['to'] = sender
            message['subject'] = subject
            message['In-Reply-To'] = last_msg['id']
            message['References'] = last_msg.get('threadId')

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message, 'threadId': thread_id}
            ).execute()
            
            return {'id': sent_message['id'], 'threadId': sent_message['threadId'], 'status': 'Reply sent'}
        except Exception as e:
            return {'error': str(e)}

    def add_label(self, message_id: str, label_id: str) -> Dict:
        """Adds a label to a message."""
        try:
            body = {'addLabelIds': [label_id]}
            message = self.service.users().messages().modify(userId='me', id=message_id, body=body).execute()
            return {'id': message['id'], 'labels': message['labelIds'], 'status': 'Label added'}
        except Exception as e:
            return {'error': str(e)}

    def remove_label(self, message_id: str, label_id: str) -> Dict:
        """Removes a label from a message."""
        try:
            body = {'removeLabelIds': [label_id]}
            message = self.service.users().messages().modify(userId='me', id=message_id, body=body).execute()
            return {'id': message['id'], 'labels': message['labelIds'], 'status': 'Label removed'}
        except Exception as e:
            return {'error': str(e)}

    def mark_as_read(self, message_id: str) -> Dict:
        """Marks a message as read."""
        return self.remove_label(message_id, 'UNREAD')

    def mark_as_unread(self, message_id: str) -> Dict:
        """Marks a message as unread."""
        return self.add_label(message_id, 'UNREAD')

# --- MCP Server Setup ---
app = Server("gmail-mcp-server")
gmail_service = None # Initialize later

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="list_emails",
            description="List recent email threads from Gmail.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (e.g., 'from:boss', 'is:unread')."},
                    "limit": {"type": "integer", "description": "Max number of results (default 5)."}
                }
            }
        ),
        mcp_types.Tool(
            name="read_thread",
            description="Read the content of an email thread.",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "The ID of the thread to read."}
                },
                "required": ["thread_id"]
            }
        ),
        mcp_types.Tool(
            name="create_draft",
            description="Create a draft email.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address."},
                    "subject": {"type": "string", "description": "Email subject."},
                    "body": {"type": "string", "description": "Email body content."}
                },
                "required": ["to", "subject", "body"]
            }
        ),
        mcp_types.Tool(
            name="send_email",
            description="Send an email immediately.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address."},
                    "subject": {"type": "string", "description": "Email subject."},
                    "body": {"type": "string", "description": "Email body content."}
                },
                "required": ["to", "subject", "body"]
            }
        ),
        mcp_types.Tool(
            name="reply_to_thread",
            description="Reply to an existing email thread.",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "The ID of the thread to reply to."},
                    "body": {"type": "string", "description": "The content of the reply."}
                },
                "required": ["thread_id", "body"]
            }
        ),
        mcp_types.Tool(
            name="add_label",
            description="Add a label to a message (e.g., STARRED, TRASH, IMPORTANT). To Archive, remove INBOX label.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The ID of the message."},
                    "label_id": {"type": "string", "description": "The Label ID to add (e.g., STARRED)."}
                },
                "required": ["message_id", "label_id"]
            }
        ),
        mcp_types.Tool(
            name="remove_label",
            description="Remove a label from a message. To Archive, remove 'INBOX'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The ID of the message."},
                    "label_id": {"type": "string", "description": "The Label ID to remove."}
                },
                "required": ["message_id", "label_id"]
            }
        ),
        mcp_types.Tool(
            name="mark_as_read",
            description="Mark a message as read.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The ID of the message."}
                },
                "required": ["message_id"]
            }
        ),
        mcp_types.Tool(
            name="mark_as_unread",
            description="Mark a message as unread.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The ID of the message."}
                },
                "required": ["message_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    global gmail_service
    if not gmail_service:
        try:
            gmail_service = GmailService()
        except Exception as e:
             return [mcp_types.TextContent(type="text", text=f"Error initializing Gmail Service: {str(e)}")]

    if name == "list_emails":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        threads = gmail_service.list_threads(query, limit)
        return [mcp_types.TextContent(type="text", text=json.dumps(threads, indent=2))]

    elif name == "read_thread":
        thread_id = arguments["thread_id"]
        thread_data = gmail_service.read_thread(thread_id)
        return [mcp_types.TextContent(type="text", text=json.dumps(thread_data, indent=2))]

    elif name == "create_draft":
        result = gmail_service.create_draft(
            arguments["to"],
            arguments["subject"],
            arguments["body"]
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "send_email":
        result = gmail_service.send_email(
            arguments["to"],
            arguments["subject"],
            arguments["body"]
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "reply_to_thread":
        result = gmail_service.reply_to_thread(
            arguments["thread_id"],
            arguments["body"]
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "add_label":
        result = gmail_service.add_label(
            arguments["message_id"],
            arguments["label_id"]
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "remove_label":
        result = gmail_service.remove_label(
            arguments["message_id"],
            arguments["label_id"]
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "mark_as_read":
        result = gmail_service.mark_as_read(
            arguments["message_id"]
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "mark_as_unread":
        result = gmail_service.mark_as_unread(
            arguments["message_id"]
        )
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    return [mcp_types.TextContent(type="text", text="Tool not found")]

async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gmail-mcp-server",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run())
