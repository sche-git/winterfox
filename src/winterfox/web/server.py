"""
FastAPI app factory for winterfox dashboard.

Creates and configures the FastAPI application with:
- REST API routers
- CORS middleware
- Service initialization
- Static file serving (for React frontend)
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import api
from .api import config as config_api
from .api import cycles, graph, stats
from .websocket import get_connection_manager

logger = logging.getLogger(__name__)


def create_app(
    config_path: Path,
    db_path: str,
    workspace_id: str = "default",
) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        config_path: Path to winterfox.toml
        db_path: Path to SQLite database
        workspace_id: Workspace identifier for multi-tenancy

    Returns:
        Configured FastAPI application
    """

    # Lifecycle manager for startup/shutdown
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle."""
        # Startup
        logger.info("Starting winterfox dashboard...")

        # Initialize services
        graph.init_graph_service(db_path, workspace_id)
        config_api.init_config(config_path)

        logger.info("Dashboard ready")

        yield

        # Shutdown
        logger.info("Shutting down dashboard...")
        await graph.shutdown_graph_service()
        logger.info("Dashboard stopped")

    # Create app
    app = FastAPI(
        title="Winterfox Dashboard",
        description="Web dashboard for winterfox autonomous research system",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # CORS middleware (for development with separate frontend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:3000",  # Alternative dev port
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
    app.include_router(cycles.router, prefix="/api/cycles", tags=["cycles"])
    app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
    app.include_router(config_api.router, prefix="/api/config", tags=["config"])

    # WebSocket endpoint for real-time events
    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket, workspace_id: str = "default"):
        """
        WebSocket endpoint for real-time cycle events.

        Query Parameters:
            workspace_id: Workspace to subscribe to (default: "default")

        Events:
            - cycle.started, cycle.step, cycle.completed, cycle.failed
            - agent.started, agent.search, agent.completed
            - node.created, node.updated
            - synthesis.started, synthesis.completed

        Example:
            ws://localhost:8000/ws/events?workspace_id=default
        """
        manager = get_connection_manager()

        await manager.connect(websocket, workspace_id)

        try:
            # Keep connection alive and listen for messages
            while True:
                # Wait for messages from client (optional ping/pong)
                try:
                    data = await websocket.receive_text()
                    logger.debug(f"Received WebSocket message: {data}")

                    # Could handle client commands here if needed
                    # For now, just acknowledge
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})

                except WebSocketDisconnect:
                    break

        except Exception as e:
            logger.error(f"WebSocket error: {e}")

        finally:
            await manager.disconnect(websocket, workspace_id)

    # Mount static files (if frontend is built)
    static_path = Path(__file__).parent / "static"
    if static_path.exists() and static_path.is_dir():
        logger.info(f"Mounting static files: {static_path}")
        app.mount(
            "/",
            StaticFiles(directory=str(static_path), html=True),
            name="static",
        )
    else:
        logger.info("Static files not found (frontend not built yet)")

        # Add simple root endpoint for testing
        @app.get("/")
        async def root():
            return {
                "message": "Winterfox Dashboard API",
                "version": "0.1.0",
                "docs": "/api/docs",
                "redoc": "/api/redoc",
            }

    return app
