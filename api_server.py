"""
FastAPI Backend for Mutual Funds Agent Frontend
===============================================

This FastAPI server exposes the existing mutual funds agent functionality
through HTTP endpoints for the React frontend.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import json
import uuid
import logging
from datetime import datetime

# Import existing agent components
from agent.core import MutualFundsAgent
from agent.config import AgentConfig
from main import MutualFundsInterface, UserSession, InteractionMode
from utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

# FastAPI app
app = FastAPI(
    title="Mutual Funds Agent API",
    description="AI-powered mutual funds agent with comprehensive fund data and analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
config = AgentConfig.from_env()
interface = MutualFundsInterface(config)

# Active sessions storage
active_sessions: Dict[str, UserSession] = {}

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_name: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    confidence: Optional[float] = None

class SessionRequest(BaseModel):
    user_name: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    user_name: Optional[str]
    timestamp: str

class FundSearchRequest(BaseModel):
    fund_name: str
    search_type: Optional[str] = "general"  # general, nav, performance, etc.

class FundSearchResponse(BaseModel):
    found: bool
    results: List[Dict[str, Any]]
    confidence: float
    source: str
    error: Optional[str] = None

# Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session: {session_id}")

    async def send_personal_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)

manager = ConnectionManager()

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Mutual Funds Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "chat": "/api/chat",
            "session": "/api/session",
            "fund_search": "/api/funds/search",
            "websocket": "/ws/{session_id}"
        }
    }

@app.post("/api/session", response_model=SessionResponse)
async def create_session(request: SessionRequest):
    """Create a new chat session"""
    try:
        session = await interface.start_session(
            user_name=request.user_name,
            mode=InteractionMode.API
        )
        
        # Store session
        active_sessions[session.session_id] = session
        
        return SessionResponse(
            session_id=session.session_id,
            user_name=session.user_name,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Process chat message and return AI response"""
    try:
        session_id = message.session_id
        
        # Create session if not provided
        if not session_id or session_id not in active_sessions:
            session = await interface.start_session(
                user_name=message.user_name,
                mode=InteractionMode.API
            )
            session_id = session.session_id
            active_sessions[session_id] = session
        
        # Set current session
        interface.current_session = active_sessions[session_id]
        
        # Process message with full agentic processing (no timeout)
        try:
            # Pure agentic approach - no templates, no hardcoded responses
            # The agent autonomously decides tool usage and synthesizes responses
            response = await interface.process_user_input(message.message)
        except Exception as e:
            # Show exact error details to frontend
            logger.error(f"Agent processing error: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": "Agent Processing Error",
                    "message": str(e),
                    "type": type(e).__name__,
                    "suggestion": "The agent encountered an issue while processing your request. Please try rephrasing your question."
                }
            )

        return ChatResponse(
            response=response,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            confidence=0.85  # Default confidence
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        # Return exact error details to frontend
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Chat Processing Error", 
                "message": str(e),
                "type": type(e).__name__,
                "session_id": session_id or "unknown"
            }
        )

@app.post("/api/funds/search", response_model=FundSearchResponse)
async def search_funds(request: FundSearchRequest):
    """Search for mutual funds directly"""
    try:
        # Use the tool orchestrator directly for fund search
        tool_orchestrator = interface.agent.tool_orchestrator
        
        # Call DB API first
        result = await tool_orchestrator.call_db_api(
            fund_name=request.fund_name,
            metric=request.search_type if request.search_type != "general" else None
        )
        
        if result.get("found"):
            return FundSearchResponse(
                found=True,
                results=result.get("results", []),
                confidence=result.get("confidence", 0.0),
                source=result.get("source", "DATABASE")
            )
        
        # Fallback to Tavily search
        tavily_result = await tool_orchestrator.call_tavily_search(request.fund_name)
        
        if tavily_result.get("found"):
            return FundSearchResponse(
                found=True,
                results=tavily_result.get("results", []),
                confidence=tavily_result.get("confidence", 0.0),
                source=tavily_result.get("source", "TAVILY_API")
            )
        
        return FundSearchResponse(
            found=False,
            results=[],
            confidence=0.0,
            source="NONE",
            error="No funds found matching your search"
        )
        
    except Exception as e:
        logger.error(f"Error searching funds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search funds: {str(e)}")

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session information and conversation history"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    return {
        "session_id": session.session_id,
        "user_name": session.user_name,
        "conversation_history": session.conversation_history,
        "created_at": session.conversation_history[0]["timestamp"] if session.conversation_history else None
    }

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": "Session deleted successfully"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Create or get session
            if session_id not in active_sessions:
                session = await interface.start_session(
                    user_name=message_data.get("user_name"),
                    mode=InteractionMode.API
                )
                active_sessions[session_id] = session
            
            interface.current_session = active_sessions[session_id]
            
            # Process message
            response = await interface.process_user_input(message_data["message"])
            
            # Send response
            await manager.send_personal_message(
                json.dumps({
                    "type": "response",
                    "message": response,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                }),
                session_id
            )
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await manager.send_personal_message(
            json.dumps({
                "type": "error",
                "message": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }),
            session_id
        )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(active_sessions),
        "config": {
            "api_base": config.PRODUCTION_API_BASE,
            "tavily_configured": bool(config.TAVILY_API_KEY),
            "moonshot_configured": bool(config.MOONSHOT_API_KEY)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
