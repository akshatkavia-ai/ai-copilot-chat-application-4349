# AI Copilot Backend (FastAPI)

## Overview

This FastAPI service powers the AI Copilot chat application. It exposes REST endpoints to:
- Manage chat sessions
- Store and retrieve message history (in memory, for development)
- Call the Gemini API to generate assistant replies

The service is designed for local development with CORS enabled for a React frontend on port 3000 and runs on port 3001 by default.

### Architecture

```mermaid
flowchart LR
  F["React Frontend (port 3000)"] -->|HTTP JSON| B["FastAPI Backend (port 3001)"]
  B -->|HTTPS JSON| G["Gemini API"]
```

## Environment variables

Place these in ai_copilot_backend/.env or export them before starting the app:

- GEMINI_API_KEY (required): API key for Google Gemini.
- GEMINI_MODEL (optional): Defaults to "gemini-1.5-flash".
- ALLOWED_ORIGINS (optional): Comma‑separated list of origins allowed by CORS. Defaults to "http://localhost:3000".
- PORT (optional): Intended server port (informational). Start uvicorn with the same port.

Example .env:
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
PORT=3001
```

## Setup and run (port 3001)

1) Install and configure
- cd ai-copilot-chat-application-4349/ai_copilot_backend
- (Optional) python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
- pip install -r requirements.txt
- Create .env as shown above

2) Start the server
- uvicorn src.api.main:app --reload --port 3001

3) Verify
- GET http://localhost:3001/ returns {"status":"ok"}
- Open http://localhost:3001/docs for interactive API docs
- Open http://localhost:3001/openapi.json for the schema

## API endpoints

- GET /: Health check
- GET /api/sessions: List sessions (SessionListResponse with "sessions": [SessionModel])
- POST /api/sessions: Create a new session (SessionCreateResponse with "session": SessionModel)
- GET /api/sessions/{session_id}/history: Return the message history (HistoryResponse with "session_id" and "history": [MessageModel])
- POST /api/chat: Send a message and receive an assistant reply (ChatResponse with "session_id", "reply", "message_id", "timestamp")

See interfaces/openapi.json or the /docs UI for field details.

## CORS configuration

CORS is configured via Starlette’s CORSMiddleware and reads ALLOWED_ORIGINS from the environment. Provide a comma‑separated list (e.g., http://localhost:3000,http://127.0.0.1:3000). The middleware is configured with:
- allow_credentials=True
- allow_methods=["*"]
- allow_headers=["*"]

If allow_credentials is true, do not use "*" for allow_origins. Always list exact origins.

## Troubleshooting

### CORS or “Network error” from the browser
- Ensure the frontend’s origin exactly matches an entry in ALLOWED_ORIGINS, including scheme and port.
- Restart the backend after changing ALLOWED_ORIGINS.
- Avoid https frontend + http backend; browsers block mixed content.

### Missing or invalid GEMINI_API_KEY
- Missing key: The /api/chat endpoint returns HTTP 500 with detail "GEMINI_API_KEY is not configured on the server."
- Invalid/unauthorized key or other upstream issues: The service returns HTTP 502 with detail "Gemini API error: …" propagated from the provider response.
- Confirm GEMINI_MODEL is valid for your key. Default is gemini-1.5-flash.

### Port or connectivity issues
- If port 3001 is taken, choose another (e.g., 3101) and start uvicorn with that port. Update the frontend’s REACT_APP_API_BASE_URL accordingly.
- Verify the health endpoint (/) and /docs are reachable from the frontend environment.

## Replacing the in‑memory store with a database

The app uses InMemorySessionStore in src/api/store.py. To persist data, implement a replacement with the same public interface:

- has_session(session_id: str) -> bool
- create_session(title: Optional[str]) -> Dict[str, Any] 
- list_sessions() -> List[Dict[str, Any]]
- append_message(session_id: str, role: str, content: str) -> Dict[str, Any]
- get_history(session_id: str) -> List[Dict[str, Any]]

Then in src/api/main.py, replace:
- store = InMemorySessionStore()
with your DB-backed store. Ensure you maintain API response shapes defined in src/api/models.py so the frontend remains compatible.

## OpenAPI generation

There are two recommended ways to refresh the API schema in interfaces/openapi.json:

1) From the running app:
- Start the backend and download http://localhost:3001/openapi.json to interfaces/openapi.json.

2) Using the built-in script:
- cd ai-copilot-chat-application-4349/ai_copilot_backend
- python -m src.api.generate_openapi
- The file is written to interfaces/openapi.json

This schema is used for documentation and can be the basis for future client generation.
