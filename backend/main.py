"""
League of Legends AI Coaching Overlay - Backend Entry Point
FastAPI server with WebSocket support for real-time coaching commands
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.monitor import create_monitor, GameMonitor

# Configure logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")

# Global game monitor instance
game_monitor: GameMonitor = None
monitoring_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global game_monitor, monitoring_task

    logger.info("Starting LoL AI Coaching Backend...")

    # Initialize game monitor
    try:
        game_monitor = await create_monitor(capture_fps=1.0)
        logger.info("Game monitor created")
    except Exception as e:
        logger.error(f"Failed to create game monitor: {e}")

    yield

    logger.info("Shutting down LoL AI Coaching Backend...")
    if monitoring_task:
        monitoring_task.cancel()


app = FastAPI(
    title="LoL AI Coaching Backend",
    description="Real-time coaching overlay backend for League of Legends",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for Electron frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")


manager = ConnectionManager()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lol-ai-coaching-backend",
        "version": "0.1.0"
    }


async def monitor_and_send_commands(websocket: WebSocket):
    """
    Background task to monitor game and send coaching commands
    """
    global game_monitor

    if not game_monitor:
        logger.error("Game monitor not initialized")
        return

    # Try to find game window
    found_window = await game_monitor.find_game_window()
    if not found_window:
        await websocket.send_json({
            "type": "status",
            "message": "Waiting for League of Legends game window...",
            "timestamp": asyncio.get_event_loop().time()
        })
        logger.info("Game window not found, waiting...")

    last_command_time = 0
    retry_find_window = 0

    try:
        while True:
            # If no game window, try to find it periodically
            if not game_monitor.capture.target_window:
                retry_find_window += 1
                if retry_find_window % 10 == 0:  # Try every 10 seconds
                    found_window = await game_monitor.find_game_window()
                    if found_window:
                        await websocket.send_json({
                            "type": "status",
                            "message": "Game window found! Starting monitoring...",
                            "timestamp": asyncio.get_event_loop().time()
                        })
                await asyncio.sleep(1)
                continue

            # Capture and extract game data
            game_data = await game_monitor.capture_and_extract()

            if game_data:
                # Log extracted data at debug level only (not visible by default)
                logger.debug(f"Extracted data: gold={game_data.get('gold')}, cs={game_data.get('cs')}, "
                           f"time={game_data.get('game_time')}, hp={game_data.get('hp_percent'):.1f}%, "
                           f"mana={game_data.get('mana_percent'):.1f}%")

                # NOTE: Raw game_data is NOT sent to frontend - only coaching directives
                # The HUD should only display coaching commands, not raw stats

                # Build game state (try even without perfect OCR)
                game_state = game_monitor.build_game_state(game_data)

                if game_state:
                    # Generate coaching command (can be CoachingCommand or DirectiveV1)
                    command = await game_monitor.generate_coaching_command(game_state)

                    if command:
                        # Determine message type based on command format
                        command_dict = command.dict()

                        # Check if it's DirectiveV1 format (has 't' field)
                        if hasattr(command, 't') or 'primary' in command_dict:
                            # DirectiveV1 format
                            logger.info(f"Sending LLM directive: {command_dict.get('primary', {}).get('text', 'N/A')}")
                            await websocket.send_json({
                                "type": "directive",
                                "data": command_dict,
                                "timestamp": asyncio.get_event_loop().time()
                            })
                        else:
                            # CoachingCommand format (rule engine)
                            logger.info(f"Sending rule command: {command_dict.get('message', 'N/A')}")
                            await websocket.send_json({
                                "type": "command",
                                "data": command_dict,
                                "timestamp": asyncio.get_event_loop().time()
                            })
                        last_command_time = asyncio.get_event_loop().time()
                    else:
                        # No command generated - just log, don't send test data
                        logger.debug("No coaching command generated this cycle")
                else:
                    # Game state couldn't be built - just log
                    logger.debug("Game state not built, skipping this cycle")
            else:
                logger.debug("No game data extracted")

            # Wait based on capture FPS
            await asyncio.sleep(game_monitor.capture_interval)

    except asyncio.CancelledError:
        logger.info("Monitoring task cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in monitoring loop: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time coaching commands
    Client receives:
      - {"type": "status", "message": "...", "timestamp": ...}
      - {"type": "game_data", "data": {...}, "timestamp": ...}
      - {"type": "command", "data": {...}, "timestamp": ...}
    Client sends:
      - {"type": "config", "data": {...}}
      - {"type": "start_monitoring"}
      - {"type": "stop_monitoring"}
    """
    await manager.connect(websocket)

    monitoring_task = None

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            logger.info(f"Received from client: {data}")

            msg_type = data.get("type")

            if msg_type == "config":
                # Client configuration
                await websocket.send_json({
                    "type": "ack",
                    "message": "Configuration received",
                    "data": data
                })

            elif msg_type == "start_monitoring":
                # Start monitoring game state
                if monitoring_task is None or monitoring_task.done():
                    monitoring_task = asyncio.create_task(monitor_and_send_commands(websocket))
                    logger.info("Started monitoring task")
                    await websocket.send_json({
                        "type": "status",
                        "message": "Monitoring started",
                        "timestamp": asyncio.get_event_loop().time()
                    })

            elif msg_type == "stop_monitoring":
                # Stop monitoring
                if monitoring_task and not monitoring_task.done():
                    monitoring_task.cancel()
                    logger.info("Stopped monitoring task")
                    await websocket.send_json({
                        "type": "status",
                        "message": "Monitoring stopped",
                        "timestamp": asyncio.get_event_loop().time()
                    })

            elif msg_type == "debug":
                # Send debug info
                if game_monitor:
                    debug_info = await game_monitor.get_debug_info()
                    await websocket.send_json({
                        "type": "debug",
                        "data": debug_info,
                        "timestamp": asyncio.get_event_loop().time()
                    })

    except WebSocketDisconnect:
        if monitoring_task and not monitoring_task.done():
            monitoring_task.cancel()
        manager.disconnect(websocket)
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if monitoring_task and not monitoring_task.done():
            monitoring_task.cancel()
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
        log_level="info"
    )
