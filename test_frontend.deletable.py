import os
import logging
from aiohttp import web
from livekit.api import AccessToken
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("frontend")

async def get_token(request):
    room_name = request.query.get('room', 'test-room')
    participant_name = request.query.get('participant', 'web-user')
    
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    url = os.getenv("LIVEKIT_URL")
    
    if not all([api_key, api_secret, url]):
        return web.json_response({"error": "Missing LiveKit credentials in .env"}, status=500)

    token = AccessToken(api_key, api_secret) \
        .with_identity(participant_name) \
        .with_name(participant_name) \
        .with_grants({
            "roomJoin": True, 
            "room": room_name,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True
        })
    
    logger.info(f"Generated token for participant {participant_name} in room {room_name}")
    return web.json_response({
        "token": token.to_jwt(), 
        "url": url
    })

async def handle_index(request):
    return web.FileResponse('./index.html')

def main():
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index),
        web.get('/token', get_token)
    ])
    
    port = 8080
    logger.info(f"Frontend server starting at http://localhost:{port}")
    web.run_app(app, port=port)

if __name__ == '__main__':
    main()
