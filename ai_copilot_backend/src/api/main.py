from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.gemini_client import GeminiAPIError, generate_reply
from src.api.models import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HistoryResponse,
    MessageModel,
    SessionCreateResponse,
    SessionListResponse,
    SessionModel,
)
from src.api.store import InMemorySessionStore, SessionNotFoundError

# Load environment variables from .env if present
load_dotenv()

# Environment configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
PORT = os.getenv("PORT", "3001")  # Informational, server runner config uses this externally

# FastAPI application metadata and tags for OpenAPI
openapi_tags = [
    {"name": "Health", "description": "Service health and diagnostics."},
    {"name": "Sessions", "description": "Create and list chat sessions, and view their histories."},
    {"name": "Chat", "description": "Send messages to the AI via Gemini and receive responses."},
]

app = FastAPI(
    title="AI Copilot Backend API",
    description="Backend service for AI Copilot chat using Gemini API. Provides session management and chat endpoints.",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# Configure CORS from environment
allowed_origins: List[str] = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store instance
store = InMemorySessionStore()


@app.get(
    "/",
    tags=["Health"],
    summary="Health Check",
    description="Simple service health check endpoint.",
    responses={
        200: {"description": "Service is healthy."},
    },
)
# PUBLIC_INTERFACE
def health_check():
    """Return a simple health status for the service.

    Returns:
        dict: A health status payload with a single `status` field of 'ok'.
    """
    return {"status": "ok"}


@app.post(
    "/api/sessions",
    tags=["Sessions"],
    summary="Create chat session",
    description="Create a new in-memory chat session and return it.",
    response_model=SessionCreateResponse,
    responses={
        200: {"description": "Session created successfully."},
        500: {"model": ErrorResponse, "description": "Server error."},
    },
)
# PUBLIC_INTERFACE
def create_session():
    """Create a new chat session.

    Returns:
        SessionCreateResponse: The newly created session resource.
    """
    session_dict = store.create_session()
    return SessionCreateResponse(session=SessionModel(**session_dict))


@app.get(
    "/api/sessions",
    tags=["Sessions"],
    summary="List chat sessions",
    description="Retrieve a list of all in-memory chat sessions.",
    response_model=SessionListResponse,
    responses={
        200: {"description": "List of sessions returned."},
        500: {"model": ErrorResponse, "description": "Server error."},
    },
)
# PUBLIC_INTERFACE
def list_sessions():
    """List all existing chat sessions.

    Returns:
        SessionListResponse: A list of available sessions.
    """
    sessions = [SessionModel(**s) for s in store.list_sessions()]
    return SessionListResponse(sessions=sessions)


@app.get(
    "/api/sessions/{session_id}/history",
    tags=["Sessions"],
    summary="Get session history",
    description="Retrieve the message history for the specified session.",
    response_model=HistoryResponse,
    responses={
        200: {"description": "History returned successfully."},
        404: {"model": ErrorResponse, "description": "Session not found."},
        500: {"model": ErrorResponse, "description": "Server error."},
    },
)
# PUBLIC_INTERFACE
def get_session_history(
    session_id: str = Path(..., description="The session ID for which to fetch history."),
):
    """Get the message history for a given session.

    Parameters:
        session_id: The identifier of the session whose history is requested.

    Returns:
        HistoryResponse: The session's message history.

    Raises:
        HTTPException: 404 if the session does not exist.
    """
    try:
        history = [MessageModel(**m) for m in store.get_history(session_id)]
        return HistoryResponse(session_id=session_id, history=history)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


@app.post(
    "/api/chat",
    tags=["Chat"],
    summary="Send chat message",
    description=(
        "Send a message to the AI model and receive a reply. "
        "The request must include an existing session_id."
    ),
    response_model=ChatResponse,
    responses={
        200: {"description": "Reply returned successfully."},
        400: {"model": ErrorResponse, "description": "Invalid request."},
        404: {"model": ErrorResponse, "description": "Session not found."},
        500: {"model": ErrorResponse, "description": "Server error."},
    },
)
# PUBLIC_INTERFACE
async def chat(req: ChatRequest):
    """Send a message to Gemini and receive the assistant's reply.

    Parameters:
        req: ChatRequest containing session_id, message, and optional stream flag.

    Returns:
        ChatResponse: Includes the assistant's reply and metadata.

    Raises:
        HTTPException: If the session is missing, invalid input, or Gemini errors occur.
    """
    if not req.session_id or not req.message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id and message are required.")

    if not store.has_session(req.session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Store the user message first
    try:
        store.append_message(req.session_id, role="user", content=req.message)
    except SessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Ensure API key is configured
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is not configured on the server.",
        )

    # Generate reply via Gemini
    try:
        reply_text = await generate_reply(req.message, model=GEMINI_MODEL, api_key=GEMINI_API_KEY)
    except GeminiAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API error: {str(e)}",
        )

    # Store the assistant message
    assistant_msg = store.append_message(req.session_id, role="assistant", content=reply_text)

    return ChatResponse(
        session_id=req.session_id,
        reply=reply_text,
        message_id=assistant_msg["id"],
        timestamp=assistant_msg["timestamp"],
    )
