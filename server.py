import os
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from dotenv import load_dotenv
import uvicorn

load_dotenv()

LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/getToken")
async def get_token():
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        return {"error": "API keys not found in .env file"}

    # --- DYNAMIC SESSION LOGIC ---
    # Generate a unique ID for this specific session
    unique_id = str(uuid.uuid4())[:8] 
    
    # 1. Unique Identity: Prevents "Identity already in use" errors
    user_identity = f"user_{unique_id}"
    
    # 2. Unique Room: Allows multiple independent sessions at once
    # We prefix it so the Agent still recognizes it's an Aria task
    room_name = f"aria-room-{unique_id}"

    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity(user_identity) \
        .with_name(f"Visitor {unique_id}") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name
        ))
    
    # We return the room_name so the frontend knows which room to join
    return {
        "token": token.to_jwt(),
        "roomName": room_name
    }

if __name__ == "__main__":
    print(f"Server starting... Keys loaded: {'Yes' if LIVEKIT_API_KEY else 'No'}")
    uvicorn.run(app, host="0.0.0.0", port=8000)