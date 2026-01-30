# Nova Backend

Nova's API server that wraps the Klix backend for web access.

## Setup

```bash
cd Nova/backend
pip install -r requirements.txt
```

## Running

```bash
uvicorn server:app --reload --port 8000
```

## API Endpoints

- `POST /api/chat` - Send a message
- `GET /api/status` - System status
- `GET /api/threads` - List threads
- `POST /api/threads` - Create thread
- `GET /api/memories` - List memories
- `WS /ws` - WebSocket for streaming
