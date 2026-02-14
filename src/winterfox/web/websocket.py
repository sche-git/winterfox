"""
WebSocket connection manager for real-time event streaming.

Manages WebSocket connections and broadcasts events to subscribed clients.
Supports workspace-based isolation for multi-tenancy.
"""

import logging
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time event streaming.

    Features:
    - Workspace-based connection grouping
    - Automatic disconnection handling
    - Broadcast to all connections in a workspace
    - Connection lifecycle logging
    """

    def __init__(self):
        """Initialize connection manager."""
        # Map workspace_id -> set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._connection_count = 0

    async def connect(self, websocket: WebSocket, workspace_id: str) -> None:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection to register
            workspace_id: Workspace identifier for this connection
        """
        await websocket.accept()

        # Add to workspace's connection set
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = set()

        self.active_connections[workspace_id].add(websocket)
        self._connection_count += 1

        logger.info(
            f"WebSocket connected: workspace={workspace_id}, "
            f"total_connections={self._connection_count}"
        )

    async def disconnect(self, websocket: WebSocket, workspace_id: str) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection to unregister
            workspace_id: Workspace identifier
        """
        if workspace_id in self.active_connections:
            self.active_connections[workspace_id].discard(websocket)
            self._connection_count -= 1

            # Clean up empty workspace sets
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]

        logger.info(
            f"WebSocket disconnected: workspace={workspace_id}, "
            f"total_connections={self._connection_count}"
        )

    async def broadcast(self, event: dict, workspace_id: str) -> None:
        """
        Broadcast event to all connections in a workspace.

        Args:
            event: Event data to broadcast (must be JSON-serializable)
            workspace_id: Workspace to broadcast to

        Note:
            Automatically handles disconnected clients by removing them.
        """
        if workspace_id not in self.active_connections:
            logger.debug(f"No connections for workspace {workspace_id}, skipping broadcast")
            return

        # Get copy of connections to avoid mutation during iteration
        connections = list(self.active_connections[workspace_id])

        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(event)
            except WebSocketDisconnect:
                # Client disconnected, mark for removal
                disconnected.append(connection)
                logger.debug(f"Client disconnected during broadcast: {workspace_id}")
            except Exception as e:
                # Other errors (e.g., connection closed)
                logger.warning(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection, workspace_id)

    async def send_to_connection(self, event: dict, websocket: WebSocket) -> bool:
        """
        Send event to a specific connection.

        Args:
            event: Event data to send
            websocket: Target WebSocket connection

        Returns:
            True if sent successfully, False if connection is broken
        """
        try:
            await websocket.send_json(event)
            return True
        except (WebSocketDisconnect, Exception) as e:
            logger.warning(f"Failed to send to specific connection: {e}")
            return False

    def get_connection_count(self, workspace_id: str | None = None) -> int:
        """
        Get number of active connections.

        Args:
            workspace_id: If provided, count for specific workspace.
                         If None, return total count.

        Returns:
            Number of active connections
        """
        if workspace_id is None:
            return self._connection_count

        if workspace_id in self.active_connections:
            return len(self.active_connections[workspace_id])

        return 0

    def get_workspace_ids(self) -> list[str]:
        """
        Get list of workspaces with active connections.

        Returns:
            List of workspace IDs
        """
        return list(self.active_connections.keys())


# Global connection manager instance
_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """
    Get or create global ConnectionManager instance.

    Returns:
        ConnectionManager singleton
    """
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
        logger.info("ConnectionManager initialized")
    return _manager
