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

if __name__ == "__main__":
   #uvicorn.run(app, host="0.0.0.0", port=8000)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
