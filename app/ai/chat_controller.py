from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_database
from app.ai.chat_service import ChatService
from app.schemas.chat_ai import ChatRequest, ChatResponse, ChatHistory
import json
import time
import asyncio
from typing import Dict, List

router = APIRouter(prefix="/chat", tags=["chat"])

# Conversation context storage (in production, use Redis or database)
conversation_context: Dict[str, List[Dict]] = {}


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_database)):
    """Non-streaming chat endpoint"""
    try:
        # Get or create conversation context
        if request.session_id not in conversation_context:
            conversation_context[request.session_id] = []

        # Add user message to context
        user_message = {
            "role": "user",
            "message": request.message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        conversation_context[request.session_id].append(user_message)

        # Initialize chat service
        chat_service = ChatService(db)

        # Generate response
        response = chat_service.process_chat_message(request.message)

        # Add AI response to context
        ai_message = {
            "role": "assistant",
            "message": response,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        conversation_context[request.session_id].append(ai_message)

        # Keep only last 10 messages for context
        if len(conversation_context[request.session_id]) > 10:
            conversation_context[request.session_id] = conversation_context[
                request.session_id
            ][-10:]

        return ChatResponse(
            response=response,
            session_id=request.session_id,
            timestamp=ai_message["timestamp"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream_endpoint(
    request: ChatRequest, db: Session = Depends(get_database)
):
    """Streaming chat endpoint"""
    try:

        async def generate_stream():
            # Get or create conversation context
            if request.session_id not in conversation_context:
                conversation_context[request.session_id] = []

            # Add user message to context
            user_message = {
                "role": "user",
                "message": request.message,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            conversation_context[request.session_id].append(user_message)

            # Initialize chat service
            chat_service = ChatService(db)

            # Generate response
            response = chat_service.process_chat_message(request.message)

            # Stream the response word by word
            words = response.split()
            streamed_response = ""

            for i, word in enumerate(words):
                streamed_response += word + " "

                chunk = {
                    "content": word + " ",
                    "full_response": streamed_response.strip(),
                    "is_complete": i == len(words) - 1,
                    "session_id": request.session_id,
                }

                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.1)  # Simulate streaming delay

            # Add AI response to context
            ai_message = {
                "role": "assistant",
                "message": response,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            conversation_context[request.session_id].append(ai_message)

            # Keep only last 10 messages for context
            if len(conversation_context[request.session_id]) > 10:
                conversation_context[request.session_id] = conversation_context[
                    request.session_id
                ][-10:]

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get conversation history for a session"""
    if session_id not in conversation_context:
        return {"history": [], "session_id": session_id}

    return {"history": conversation_context[session_id], "session_id": session_id}


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear conversation history for a session"""
    if session_id in conversation_context:
        del conversation_context[session_id]

    return {"message": f"Chat history cleared for session {session_id}"}


@router.get("/test")
async def test_chat(db: Session = Depends(get_database)):
    """Test endpoint with sample queries"""
    test_queries = [
        "How many books are overdue?",
        "Which department borrowed the most books?",
        "How many new books were added this week?",
        "How many unread notifications are there?",
    ]

    results = []
    chat_service = ChatService(db)

    for query in test_queries:
        try:
            response = chat_service.process_chat_message(query)
            results.append({"query": query, "response": response, "status": "success"})
        except Exception as e:
            results.append({"query": query, "error": str(e), "status": "error"})

    return {"test_results": results}
