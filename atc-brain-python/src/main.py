"""
FastAPI server for ATC Brain microservice
Handles HTTP endpoints and WebSocket connections for real-time updates
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

from config.settings import Settings
from database.connection import DatabaseManager
from services.event_publisher import EventPublisher
from atc_brain import ATCBrain

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
settings = Settings()
db_manager = DatabaseManager(settings)
event_publisher = EventPublisher(settings)
atc_brain = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting ATC Brain service...")
    
    # Initialize database connection
    await db_manager.connect()
    logger.info("Database connected")
    
    # Initialize event publisher
    await event_publisher.connect()
    logger.info("Redis connected")
    
    # Initialize ATC Brain
    global atc_brain
    atc_brain = ATCBrain(db_manager, event_publisher, settings)
    logger.info("ATC Brain initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ATC Brain service...")
    if atc_brain:
        await atc_brain.stop()
    await event_publisher.disconnect()
    await db_manager.disconnect()
    logger.info("Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="ATC Brain API",
    description="AI-powered Air Traffic Control Brain for automated aircraft management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "ATC Brain API is running", "status": "healthy"}

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check database connection
        db_status = await db_manager.health_check()
        
        # Check Redis connection
        redis_status = await event_publisher.health_check()
        
        # Check ATC Brain status
        brain_status = atc_brain.is_running if atc_brain else False
        
        return {
            "status": "healthy" if all([db_status, redis_status]) else "degraded",
            "database": "connected" if db_status else "disconnected",
            "redis": "connected" if redis_status else "disconnected",
            "atc_brain": "running" if brain_status else "stopped",
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start")
async def start_atc_brain():
    """Start the ATC Brain control loop"""
    try:
        if atc_brain and atc_brain.is_running:
            return {"message": "ATC Brain is already running", "status": "running"}
        
        await atc_brain.start()
        
        # Publish startup event
        await event_publisher.publish_event("atc_brain:started", {
            "message": "ATC Brain started successfully",
            "timestamp": asyncio.get_event_loop().time()
        })
        
        return {"message": "ATC Brain started successfully", "status": "started"}
    except Exception as e:
        logger.error(f"Failed to start ATC Brain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
async def stop_atc_brain():
    """Stop the ATC Brain control loop"""
    try:
        if not atc_brain or not atc_brain.is_running:
            return {"message": "ATC Brain is not running", "status": "stopped"}
        
        await atc_brain.stop()
        
        # Publish shutdown event
        await event_publisher.publish_event("atc_brain:stopped", {
            "message": "ATC Brain stopped",
            "timestamp": asyncio.get_event_loop().time()
        })
        
        return {"message": "ATC Brain stopped successfully", "status": "stopped"}
    except Exception as e:
        logger.error(f"Failed to stop ATC Brain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    """Get current ATC Brain status"""
    try:
        if not atc_brain:
            return {"status": "not_initialized", "message": "ATC Brain not initialized"}
        
        is_running = atc_brain.is_running
        active_aircraft = await atc_brain.get_active_aircraft_count()
        
        return {
            "status": "running" if is_running else "stopped",
            "active_aircraft": active_aircraft,
            "message": f"ATC Brain is {'running' if is_running else 'stopped'}"
        }
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.ATC_BRAIN_HOST,
        port=settings.ATC_BRAIN_PORT,
        reload=True,
        log_level="info"
    )
