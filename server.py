import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sys

# Add the current directory to sys.path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

#rigins = ["*"] with this it can run on any origin local or cloud
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
origins = allowed_origins_str.split(",")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session service to store conversation history
session_service = InMemorySessionService()

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    new_message: str
    conversation_id: str = "default-session"

class ChatResponse(BaseModel):
    text: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        user_id = "user" # comprehensive-agent-user
        session_id = request.conversation_id

        # 1. Initialize Runner
        runner = Runner(agent=root_agent, app_name="personal_orchestrator", session_service=session_service)

        # 2. Ensure Session Exists
        # Check if session exists, if not create it
        # Note: InMemorySessionService doesn't have a simple 'exists' check exposed in all versions, 
        # but create_session usually handles idempotency or we can just try to create.
        # For simplicity in this demo, we'll just try to create and ignore if it already exists 
        # (or rely on the runner to handle session retrieval if the service supports it).
        # In a real app, you'd check or have a robust get_or_create method.
        # Here we'll just attempt to create a session if it's the first time for this ID.
        try:
             await session_service.create_session(app_name="personal_orchestrator", user_id=user_id, session_id=session_id)
        except Exception:
            # If session already exists or other error, we might logging it. 
            # For InMemorySessionService, create_session might overwrite or error depending on implementation.
            # Assuming standard ADK behavior, we might not strictly need to call create every time if it persists in memory.
            pass

        # 3. Prepare Input
        content = types.Content(role='user', parts=[types.Part(text=request.new_message)])

        # 4. Run Agent
        response_text = ""
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response_text = event.content.parts[0].text
                else:
                    response_text = "(No text response)"
            elif event.actions and event.actions.escalate:
                print(f"Error: {event.error_message}")
                raise HTTPException(status_code=500, detail=f"Agent Error: {event.error_message}")

        return ChatResponse(text=response_text)

    except Exception as e:
        print(f"Runtime Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- GOOGLE AUTHENTICATION FLOW ---

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

# Scopes needed
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'
]

# Redirect URI (Frontend URL where Google sends the user back)
REDIRECT_URI = "http://localhost:3000"

@app.get("/api/auth/google/url")
async def get_google_auth_url():
    """Generates the Google Login URL for the frontend button."""
    try:
        client_id = os.getenv("GMAIL_CLIENT_ID") or os.getenv("CALENDAR_CLIENT_ID")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET") or os.getenv("CALENDAR_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Missing Client ID/Secret in .env")

        # Create flow instance
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
             prompt='consent' # Force consent to ensure we get a refresh token
        )
        return {"url": auth_url}

    except Exception as e:
        print(f"Auth URL Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class AuthCodeRequest(BaseModel):
    code: str

@app.post("/api/auth/google/callback")
async def google_auth_callback(request: AuthCodeRequest):
    """Exchanges the code for tokens and saves them."""
    try:
        client_id = os.getenv("GMAIL_CLIENT_ID") or os.getenv("CALENDAR_CLIENT_ID")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET") or os.getenv("CALENDAR_CLIENT_SECRET")

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        # Exchange code for tokens
        flow.fetch_token(code=request.code)
        creds = flow.credentials

        # Save to .env (Simple persistence for single-user bot)
        # Note: In production, save to DB per user. Here we update the global env for the bot.
        update_env_file("GMAIL_REFRESH_TOKEN", creds.refresh_token)
        update_env_file("CALENDAR_REFRESH_TOKEN", creds.refresh_token)
        
        # Also update running process env
        os.environ["GMAIL_REFRESH_TOKEN"] = creds.refresh_token
        os.environ["CALENDAR_REFRESH_TOKEN"] = creds.refresh_token

        return {"status": "success", "message": "Tokens saved successfully!"}

    except Exception as e:
        print(f"Token Exchange Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


#call new refesh token and update the old one on .env
def update_env_file(key, value):
    """Helper to update .env file consistently."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    key_found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)
    
    if not key_found:
        new_lines.append(f"\n{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


if __name__ == "__main__":
   #uvicorn.run(app, host="0.0.0.0", port=8000)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
