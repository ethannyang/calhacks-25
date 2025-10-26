"""
League of Legends AI Coaching Overlay - Backend Entry Point
FastAPI server with WebSocket support for real-time coaching commands
"""

import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from game_loop import GameLoop
from src.models.game_state import CoachingCommand

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")

# Global game loop instance
game_loop: GameLoop = None
game_loop_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global game_loop, game_loop_task

    logger.info("Starting LoL AI Coaching Backend...")

    # Start game loop in background
    game_loop = GameLoop()
    game_loop_task = asyncio.create_task(game_loop.run())
    logger.info("Game loop started in background")

    yield

    # Stop game loop
    logger.info("Shutting down LoL AI Coaching Backend...")
    if game_loop:
        game_loop.stop()
    if game_loop_task:
        await game_loop_task


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


@app.get("/test-command")
async def test_command():
    """Send a test coaching command to verify overlay is working"""
    import time
    test_cmd = CoachingCommand(
        priority="high",
        category="safety",
        icon="⚠️",
        message="TEST: Overlay is working! You should see this message.",
        duration=10,
        timestamp=time.time()
    )
    await manager.broadcast({
        "type": "command",
        "data": {
            "priority": test_cmd.priority,
            "category": test_cmd.category,
            "icon": test_cmd.icon,
            "message": test_cmd.message,
            "duration": test_cmd.duration,
            "timestamp": test_cmd.timestamp
        }
    })
    return {"status": "test command sent"}


async def broadcast_command(command: CoachingCommand):
    """Callback for game loop to broadcast commands to all connected clients"""
    message = {
        "type": "command",
        "data": {
            "priority": command.priority,
            "category": command.category,
            "icon": command.icon,
            "message": command.message,
            "duration": command.duration,
            "timestamp": command.timestamp
        }
    }
    await manager.broadcast(message)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time coaching commands
    Client receives: {"type": "command", "data": {...}}
    Client sends: {"type": "config", "data": {...}}
    """
    global game_loop

    await manager.connect(websocket)

    # Connect game loop to broadcast commands
    if game_loop and not game_loop.on_command:
        game_loop.set_command_callback(broadcast_command)
        logger.info("Game loop connected to WebSocket broadcast")

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            logger.info(f"Received from client: {data}")

            # Handle different message types
            msg_type = data.get("type")

            if msg_type == "ability_used":
                # Manual ability reporting from voice input
                ability_data = data.get("data", {})
                ability = ability_data.get("ability")
                target = ability_data.get("target", "enemy")

                logger.info(f"Voice input: {target} used {ability}")

                # Forward to combat coach module
                if game_loop and game_loop.combat_coach:
                    game_loop.combat_coach.manual_report_ability(ability, target)
                    logger.info(f"Reported {ability} to combat coach")

                    # Get updated cooldowns
                    cooldowns = game_loop.combat_coach.audio_detector.get_ability_cooldowns()

                    # Broadcast cooldowns to all clients
                    await manager.broadcast({
                        "type": "cooldowns",
                        "data": cooldowns
                    })

                    # Send acknowledgment
                    await websocket.send_json({
                        "type": "ack",
                        "message": f"Tracked {target} {ability}",
                        "data": ability_data
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Combat coach not available"
                    })

            elif msg_type == "voice_question":
                # Handle voice questions from user
                question_data = data.get("data", {})
                question_text = question_data.get("text", "")

                logger.info(f"Voice question received: {question_text}")

                # Use LLM engine to answer the question
                if game_loop and game_loop.llm_engine:
                    try:
                        # Generate coaching response (game state context not available yet)
                        coaching_response = await game_loop.llm_engine.answer_coaching_question(
                            question_text,
                            None  # TODO: Pass game state when available
                        )

                        if coaching_response:
                            # Broadcast the coaching command to all clients
                            await manager.broadcast({
                                "type": "command",
                                "data": {
                                    "priority": coaching_response.priority,
                                    "category": coaching_response.category,
                                    "icon": coaching_response.icon,
                                    "message": coaching_response.message,
                                    "duration": coaching_response.duration,
                                    "timestamp": coaching_response.timestamp
                                }
                            })
                            logger.info(f"Sent coaching response: {coaching_response.message}")
                        else:
                            # Fallback if no response generated
                            fallback_cmd = CoachingCommand(
                                priority="medium",
                                category="advice",
                                icon="💭",
                                message="I couldn't understand that. Try asking about laning, farming, or objectives.",
                                duration=5,
                                timestamp=time.time()
                            )
                            await manager.broadcast({
                                "type": "command",
                                "data": {
                                    "priority": fallback_cmd.priority,
                                    "category": fallback_cmd.category,
                                    "icon": fallback_cmd.icon,
                                    "message": fallback_cmd.message,
                                    "duration": fallback_cmd.duration,
                                    "timestamp": fallback_cmd.timestamp
                                }
                            })
                    except Exception as e:
                        logger.error(f"Error processing voice question: {e}")
                        # Send error message to user
                        error_cmd = CoachingCommand(
                            priority="low",
                            category="error",
                            icon="❌",
                            message="Failed to process question. Please try again.",
                            duration=3,
                            timestamp=time.time()
                        )
                        await manager.broadcast({
                            "type": "command",
                            "data": {
                                "priority": error_cmd.priority,
                                "category": error_cmd.category,
                                "icon": error_cmd.icon,
                                "message": error_cmd.message,
                                "duration": error_cmd.duration,
                                "timestamp": error_cmd.timestamp
                            }
                        })
                else:
                    logger.warning("LLM engine not available for voice questions")
                    await websocket.send_json({
                        "type": "error",
                        "message": "AI coach not available"
                    })

            else:
                # Default acknowledgment for other message types
                await websocket.send_json({
                    "type": "ack",
                    "message": "Message received",
                    "data": data
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
