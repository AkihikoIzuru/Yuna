"""FastAPI + WebSocket Dashboard Server untuk Yuna."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        message_str = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


class StatusData(BaseModel):
    """Current status data."""
    status: str = "idle"  # idle, listening, thinking, speaking, error
    transcript: str = ""
    last_tool: Optional[str] = None
    last_tool_result: Optional[str] = None
    network_status: Dict[str, Any] = {}
    home_status: Dict[str, Any] = {}
    timestamp: str = ""


# Global instances
manager = ConnectionManager()
current_status = StatusData()
_event_queue: asyncio.Queue = asyncio.Queue()


def set_status(status: str, transcript: str = "", tool: str = None, tool_result: str = None):
    """Update current status and broadcast to clients."""
    global current_status
    current_status.status = status
    if transcript:
        current_status.transcript = transcript
    if tool:
        current_status.last_tool = tool
    if tool_result:
        current_status.last_tool_result = tool_result
    current_status.timestamp = datetime.now().isoformat()

    # Broadcast to all clients
    asyncio.create_task(broadcast_status())


async def broadcast_status():
    """Broadcast current status to all WebSocket clients."""
    await manager.broadcast({
        "type": "status",
        "data": current_status.model_dump(),
    })


async def broadcast_transcript(text: str, is_final: bool = True):
    """Broadcast transcript update."""
    await manager.broadcast({
        "type": "transcript",
        "data": {
            "text": text,
            "is_final": is_final,
            "timestamp": datetime.now().isoformat(),
        }
    })


async def broadcast_tool_call(tool_name: str, args: dict):
    """Broadcast tool call."""
    await manager.broadcast({
        "type": "tool_call",
        "data": {
            "tool": tool_name,
            "args": args,
            "timestamp": datetime.now().isoformat(),
        }
    })


async def broadcast_tool_result(tool_name: str, result: str):
    """Broadcast tool result."""
    await manager.broadcast({
        "type": "tool_result",
        "data": {
            "tool": tool_name,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    })


async def broadcast_network_status(status: dict):
    """Broadcast network status update."""
    global current_status
    current_status.network_status = status
    await manager.broadcast({
        "type": "network_status",
        "data": status,
    })


async def broadcast_home_status(status: dict):
    """Broadcast home automation status update."""
    global current_status
    current_status.home_status = status
    await manager.broadcast({
        "type": "home_status",
        "data": status,
    })


async def event_processor():
    """Background task to process events from queue and broadcast."""
    while True:
        try:
            event = await _event_queue.get()
            await manager.broadcast(event)
        except Exception as e:
            logger.error(f"Event processor error: {e}")
            await asyncio.sleep(1)


def emit_event(event_type: str, data: dict):
    """Emit event to queue for broadcasting."""
    event = {
        "type": event_type,
        "data": data,
    }
    try:
        _event_queue.put_nowait(event)
    except asyncio.QueueFull:
        logger.warning("Event queue full, dropping event")


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting dashboard server...")
    processor_task = asyncio.create_task(event_processor())
    yield
    # Shutdown
    processor_task.cancel()
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
    logger.info("Dashboard server stopped")


# FastAPI app
app = FastAPI(
    title="yuna Dashboard",
    description="Real-time dashboard untuk Yuna AI Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="yuna/ui/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve dashboard HTML."""
    html_path = "yuna/ui/static/index.html"
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dashboard not built yet</h1><p>Run build first.</p>")


@app.get("/api/status")
async def get_status():
    """Get current status."""
    return current_status.model_dump()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "init",
            "data": current_status.model_dump(),
        }))

        # Keep connection alive, handle incoming messages
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                await handle_ws_message(websocket, msg)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def handle_ws_message(websocket: WebSocket, msg: dict):
    """Handle incoming WebSocket message from client."""
    msg_type = msg.get("type")

    if msg_type == "ping":
        await websocket.send_text(json.dumps({"type": "pong"}))
    elif msg_type == "command":
        # Handle commands from UI (text input, PTT, etc.)
        command = msg.get("command")
        payload = msg.get("payload", {})
        # This would be handled by the main app
        logger.info(f"Received command: {command}, payload: {payload}")


# For external integration (called by voice loop, agent, etc.)
def notify_status_change(status: str, transcript: str = ""):
    """Notify status change (called from voice loop)."""
    set_status(status, transcript)


def notify_transcript(text: str, is_final: bool = True):
    """Notify transcript update."""
    asyncio.create_task(broadcast_transcript(text, is_final))


def notify_tool_call(tool_name: str, args: dict):
    """Notify tool call."""
    asyncio.create_task(broadcast_tool_call(tool_name, args))


def notify_tool_result(tool_name: str, result: str):
    """Notify tool result."""
    asyncio.create_task(broadcast_tool_result(tool_name, result))


def notify_network_status(status: dict):
    """Notify network status."""
    asyncio.create_task(broadcast_network_status(status))


def notify_home_status(status: dict):
    """Notify home status."""
    asyncio.create_task(broadcast_home_status(status))


# Helper to run server
def run_server(host: str = "127.0.0.1", port: int = 8080):
    """Run the dashboard server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
