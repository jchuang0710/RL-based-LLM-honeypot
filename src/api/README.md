# RL-based LLM Honeypot API

FastAPI application for honeypot and attacker services.

## Installation

```bash
pip install -r requirements.txt
```

## Running the API

```bash
python -m src.api.main
```

Or using uvicorn directly:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Session Management
- `POST /api/session/create` - Create a new session
- `DELETE /api/session/{session_id}` - Delete a session

### Honeypot Endpoints
- `POST /api/honeypot/command` - Execute a command on the honeypot
- `WebSocket /api/honeypot/ws` - Real-time WebSocket connection for SSH-like interaction

### Attacker Endpoints
- `POST /api/attacker/detect-honeypot` - Detect if system is honeypot
- `POST /api/attacker/detect-state` - Detect MITRE tactic/technique
- `POST /api/attacker/get-technique` - Get next attack technique

## Example Usage

### Execute Command on Honeypot

```python
import requests

response = requests.post("http://localhost:8000/api/honeypot/command", json={
    "command": "whoami"
})
print(response.json())
```

### Detect Honeypot

```python
response = requests.post("http://localhost:8000/api/attacker/detect-honeypot", json={
    "history": ["whoami", "root"]
})
print(response.json())
```

### WebSocket Example

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/api/honeypot/ws"
    async with websockets.connect(uri) as websocket:
        # Send command
        await websocket.send(json.dumps({
            "type": "command",
            "command": "whoami"
        }))
        
        # Receive response
        response = await websocket.recv()
        print(json.loads(response))

asyncio.run(test_websocket())
```
