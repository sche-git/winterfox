"""
SQLite-backed knowledge graph storage with workspace isolation.

This module implements the KnowledgeGraph class which provides:
- Async SQLite operations for all graph CRUD
- Workspace isolation (multi-tenancy ready)
- Full-text search on claims
- Audit logging of all operations
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from .models import KnowledgeNode

logger = logging.getLogger(__name__)


# SQL schema for the database (as a list of statements)
SCHEMA_STATEMENTS = [
    # Workspaces table
    """
    CREATE TABLE IF NOT EXISTS workspaces (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        owner_id TEXT,
        tier TEXT DEFAULT 'free',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        settings JSON
    )
    """,

    # Default workspace
    """
    INSERT OR IGNORE INTO workspaces (id, name, tier)
    VALUES ('default', 'Default Workspace', 'free')
    """,

    # Nodes table
    """
    CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL DEFAULT 'default',
        parent_id TEXT,
        claim TEXT NOT NULL,
        confidence REAL NOT NULL DEFAULT 0.0,
        importance REAL NOT NULL DEFAULT 0.5,
        depth INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        data JSON NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_by_cycle INTEGER NOT NULL,
        updated_by_cycle INTEGER NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
        FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE CASCADE
    )
    """,

    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_workspace ON nodes(workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_parent ON nodes(parent_id)",
    "CREATE INDEX IF NOT EXISTS idx_workspace_parent ON nodes(workspace_id, parent_id)",
    "CREATE INDEX IF NOT EXISTS idx_confidence ON nodes(confidence)",
    "CREATE INDEX IF NOT EXISTS idx_importance ON nodes(importance)",
    "CREATE INDEX IF NOT EXISTS idx_updated ON nodes(updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_status ON nodes(status)",
    "CREATE INDEX IF NOT EXISTS idx_selection_score ON nodes(workspace_id, confidence, importance, updated_at)",

    # Full-text search
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
        id UNINDEXED,
        workspace_id UNINDEXED,
        claim,
        content=nodes,
        content_rowid=rowid
    )
    """,

    # FTS triggers
    """
    CREATE TRIGGER IF NOT EXISTS nodes_fts_insert AFTER INSERT ON nodes BEGIN
        INSERT INTO nodes_fts(rowid, id, workspace_id, claim)
        VALUES (new.rowid, new.id, new.workspace_id, new.claim);
    END
    """,

    """
    CREATE TRIGGER IF NOT EXISTS nodes_fts_update AFTER UPDATE ON nodes BEGIN
        UPDATE nodes_fts SET claim = new.claim WHERE rowid = new.rowid;
    END
    """,

    """
    CREATE TRIGGER IF NOT EXISTS nodes_fts_delete AFTER DELETE ON nodes BEGIN
        DELETE FROM nodes_fts WHERE rowid = old.rowid;
    END
    """,

    # Audit log
    """
    CREATE TABLE IF NOT EXISTS graph_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id TEXT NOT NULL DEFAULT 'default',
        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        cycle_id INTEGER NOT NULL,
        operation TEXT NOT NULL,
        node_id TEXT NOT NULL,
        details JSON,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_audit_workspace ON graph_operations(workspace_id, timestamp)",

    # Cycles table
    """
    CREATE TABLE IF NOT EXISTS cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id TEXT NOT NULL DEFAULT 'default',
        started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        focus_node_id TEXT,
        status TEXT NOT NULL DEFAULT 'running',
        agents_used JSON,
        total_cost_usd REAL DEFAULT 0.0,
        findings_count INTEGER DEFAULT 0,
        error_message TEXT,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_cycles_workspace ON cycles(workspace_id, started_at)",

    # Usage tracking
    """
    CREATE TABLE IF NOT EXISTS usage_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        cost_usd REAL DEFAULT 0.0,
        metadata JSON,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    )
    """,

    "CREATE INDEX IF NOT EXISTS idx_usage_workspace ON usage_events(workspace_id, timestamp)",
]


class KnowledgeGraph:
    """SQLite-backed knowledge graph with workspace isolation."""

    def __init__(self, db_path: str | Path, workspace_id: str = "default"):
        """
        Initialize knowledge graph.

        Args:
            db_path: Path to SQLite database (use ':memory:' for in-memory)
            workspace_id: Workspace ID for multi-tenancy (default: 'default' for CLI)
        """
        self.db_path = str(db_path)
        self.workspace_id = workspace_id
        self._initialized = False
        self._conn: aiosqlite.Connection | None = None  # Persistent connection for :memory:
        self._is_memory = self.db_path == ":memory:"

    async def initialize(self) -> None:
        """Initialize database schema. Call this before any operations."""
        if self._initialized:
            return

        # For in-memory databases, keep a persistent connection
        if self._is_memory:
            self._conn = await aiosqlite.connect(self.db_path)
            db = self._conn
        else:
            db = await aiosqlite.connect(self.db_path)

        try:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")

            # Execute each schema statement
            for statement in SCHEMA_STATEMENTS:
                await db.execute(statement.strip())

            await db.commit()

            self._initialized = True
            logger.info(f"Initialized knowledge graph at {self.db_path} for workspace {self.workspace_id}")
        finally:
            # Only close if not keeping persistent connection
            if not self._is_memory:
                await db.close()

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a database connection (persistent for :memory:, new for file)."""
        if self._is_memory:
            if self._conn is None:
                raise RuntimeError("Database not initialized. Call initialize() first.")
            return self._conn
        else:
            return await aiosqlite.connect(self.db_path)

    @asynccontextmanager
    async def _get_db(self):
        """Context manager for database connections."""
        if self._is_memory:
            # Use persistent connection (don't close)
            yield self._conn
        else:
            # Open and close connection per operation
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA foreign_keys = ON")
                yield db

    # --- Write Operations ---

    async def add_node(
        self,
        claim: str,
        parent_id: str | None = None,
        confidence: float = 0.0,
        importance: float = 0.5,
        depth: int = 0,
        created_by_cycle: int = 0,
        **kwargs: Any,
    ) -> KnowledgeNode:
        """
        Add a new node to the graph.

        Args:
            claim: The claim text
            parent_id: Optional parent node ID
            confidence: Initial confidence score
            importance: Strategic importance score
            depth: Depth of research
            created_by_cycle: Cycle ID that created this
            **kwargs: Additional node attributes

        Returns:
            The created KnowledgeNode
        """
        if not self._initialized:
            await self.initialize()

        # Create node
        node = KnowledgeNode(
            workspace_id=self.workspace_id,
            parent_id=parent_id,
            claim=claim,
            confidence=confidence,
            importance=importance,
            depth=depth,
            created_by_cycle=created_by_cycle,
            updated_by_cycle=created_by_cycle,
            **kwargs,
        )

        # Serialize to JSON
        node_data = node.model_dump(mode="json")

        async with self._get_db() as db:
            # Insert node
            await db.execute(
                """
                INSERT INTO nodes (
                    id, workspace_id, parent_id, claim, confidence, importance,
                    depth, status, data, created_at, updated_at,
                    created_by_cycle, updated_by_cycle
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.workspace_id,
                    node.parent_id,
                    node.claim,
                    node.confidence,
                    node.importance,
                    node.depth,
                    node.status,
                    json.dumps(node_data),
                    node.created_at.isoformat(),
                    node.updated_at.isoformat(),
                    node.created_by_cycle,
                    node.updated_by_cycle,
                ),
            )

            # Update parent's children list if parent exists
            if parent_id:
                parent = await self._get_node_internal(db, parent_id)
                if parent:
                    parent.add_child(node.id)
                    await self._update_node_internal(db, parent)

            # Audit log
            await db.execute(
                """
                INSERT INTO graph_operations (workspace_id, cycle_id, operation, node_id, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self.workspace_id,
                    created_by_cycle,
                    "create",
                    node.id,
                    json.dumps({"parent_id": parent_id, "claim": claim[:100]}),
                ),
            )

            await db.commit()

        logger.debug(f"Added node {node.id}: {claim[:50]}...")
        return node

    async def update_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """
        Update an existing node.

        Args:
            node: The node to update

        Returns:
            The updated node
        """
        if not self._initialized:
            await self.initialize()

        node.updated_at = datetime.now()

        async with self._get_db() as db:
            await self._update_node_internal(db, node)
            await db.commit()

        logger.debug(f"Updated node {node.id}")
        return node

    async def _update_node_internal(
        self, db: aiosqlite.Connection, node: KnowledgeNode
    ) -> None:
        """Internal method to update node within a transaction."""
        node_data = node.model_dump(mode="json")

        await db.execute(
            """
            UPDATE nodes
            SET claim = ?, confidence = ?, importance = ?, depth = ?,
                status = ?, data = ?, updated_at = ?, updated_by_cycle = ?
            WHERE id = ? AND workspace_id = ?
            """,
            (
                node.claim,
                node.confidence,
                node.importance,
                node.depth,
                node.status,
                json.dumps(node_data),
                node.updated_at.isoformat(),
                node.updated_by_cycle,
                node.id,
                self.workspace_id,
            ),
        )

    async def kill_node(self, node_id: str, reason: str, cycle_id: int) -> None:
        """Mark a node as killed (never delete, audit trail matters)."""
        if not self._initialized:
            await self.initialize()

        node = await self.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        node.kill(reason)
        node.updated_by_cycle = cycle_id

        async with self._get_db() as db:
            await self._update_node_internal(db, node)

            # Audit log
            await db.execute(
                """
                INSERT INTO graph_operations (workspace_id, cycle_id, operation, node_id, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self.workspace_id,
                    cycle_id,
                    "kill",
                    node_id,
                    json.dumps({"reason": reason}),
                ),
            )

            await db.commit()

        logger.info(f"Killed node {node_id}: {reason}")

    # --- Read Operations ---

    async def get_node(self, node_id: str) -> KnowledgeNode | None:
        """
        Get a node by ID.

        Args:
            node_id: Node ID to retrieve

        Returns:
            KnowledgeNode if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            return await self._get_node_internal(db, node_id)

    async def _get_node_internal(
        self, db: aiosqlite.Connection, node_id: str
    ) -> KnowledgeNode | None:
        """Internal method to get node within a transaction."""
        cursor = await db.execute(
            """
            SELECT data FROM nodes
            WHERE id = ? AND workspace_id = ?
            """,
            (node_id, self.workspace_id),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        node_data = json.loads(row[0])
        return KnowledgeNode(**node_data)

    async def get_all_active_nodes(self) -> list[KnowledgeNode]:
        """Get all active nodes in the workspace."""
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT data FROM nodes
                WHERE workspace_id = ? AND status = 'active'
                ORDER BY updated_at DESC
                """,
                (self.workspace_id,),
            )
            rows = await cursor.fetchall()

        nodes = [KnowledgeNode(**json.loads(row[0])) for row in rows]
        logger.debug(f"Retrieved {len(nodes)} active nodes")
        return nodes

    async def get_root_nodes(self) -> list[KnowledgeNode]:
        """Get all root nodes (nodes with no parent) in the workspace."""
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT data FROM nodes
                WHERE workspace_id = ? AND parent_id IS NULL AND status = 'active'
                ORDER BY importance DESC, updated_at DESC
                """,
                (self.workspace_id,),
            )
            rows = await cursor.fetchall()

        nodes = [KnowledgeNode(**json.loads(row[0])) for row in rows]
        return nodes

    async def get_children(self, node_id: str) -> list[KnowledgeNode]:
        """Get all child nodes of a given node."""
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT data FROM nodes
                WHERE workspace_id = ? AND parent_id = ? AND status = 'active'
                ORDER BY confidence DESC, updated_at DESC
                """,
                (self.workspace_id, node_id),
            )
            rows = await cursor.fetchall()

        return [KnowledgeNode(**json.loads(row[0])) for row in rows]

    async def search(self, query: str, limit: int = 10) -> list[KnowledgeNode]:
        """
        Full-text search on node claims.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching nodes
        """
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT n.data
                FROM nodes n
                JOIN nodes_fts fts ON n.rowid = fts.rowid
                WHERE fts.claim MATCH ? AND n.workspace_id = ? AND n.status = 'active'
                ORDER BY rank
                LIMIT ?
                """,
                (query, self.workspace_id, limit),
            )
            rows = await cursor.fetchall()

        return [KnowledgeNode(**json.loads(row[0])) for row in rows]

    async def count_nodes(self) -> int:
        """Count total active nodes in workspace."""
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM nodes
                WHERE workspace_id = ? AND status = 'active'
                """,
                (self.workspace_id,),
            )
            row = await cursor.fetchone()

        return row[0] if row else 0

    async def close(self) -> None:
        """Close database connection (important for in-memory databases)."""
        if self._conn:
            await self._conn.close()
            self._conn = None
        self._initialized = False
