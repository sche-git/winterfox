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

    # Cycle outputs table (for storing raw agent outputs and synthesis)
    """
    CREATE TABLE IF NOT EXISTS cycle_outputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cycle_id INTEGER NOT NULL,
        workspace_id TEXT NOT NULL DEFAULT 'default',
        target_node_id TEXT NOT NULL,
        target_claim TEXT NOT NULL,
        synthesis_reasoning TEXT,
        consensus_findings TEXT,
        contradictions TEXT,
        findings_created INTEGER DEFAULT 0,
        findings_updated INTEGER DEFAULT 0,
        findings_skipped INTEGER DEFAULT 0,
        agent_count INTEGER NOT NULL,
        total_tokens INTEGER NOT NULL,
        total_cost_usd REAL NOT NULL,
        duration_seconds REAL NOT NULL,
        success INTEGER NOT NULL DEFAULT 1,
        error_message TEXT,
        selection_strategy TEXT,
        selection_reasoning TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
        FOREIGN KEY (target_node_id) REFERENCES nodes(id) ON DELETE SET NULL
    )
    """,

    # Agent outputs table (normalized agent data)
    """
    CREATE TABLE IF NOT EXISTS agent_outputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cycle_output_id INTEGER NOT NULL,
        agent_name TEXT NOT NULL,
        agent_model TEXT NOT NULL,
        role TEXT NOT NULL,
        findings TEXT NOT NULL,
        self_critique TEXT NOT NULL,
        searches_performed TEXT NOT NULL,
        cost_usd REAL NOT NULL,
        total_tokens INTEGER NOT NULL,
        input_tokens INTEGER NOT NULL,
        output_tokens INTEGER NOT NULL,
        duration_seconds REAL NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cycle_output_id) REFERENCES cycle_outputs(id) ON DELETE CASCADE
    )
    """,

    # Cycle outputs indexes
    "CREATE INDEX IF NOT EXISTS idx_cycle_outputs_workspace_time ON cycle_outputs(workspace_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_cycle_outputs_cycle ON cycle_outputs(cycle_id)",
    "CREATE INDEX IF NOT EXISTS idx_cycle_outputs_node ON cycle_outputs(target_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_cycle_outputs_cost ON cycle_outputs(total_cost_usd)",
    "CREATE INDEX IF NOT EXISTS idx_agent_outputs_cycle ON agent_outputs(cycle_output_id)",

    # Full-text search for cycle outputs
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS cycle_outputs_fts USING fts5(
        id UNINDEXED,
        workspace_id UNINDEXED,
        synthesis_reasoning,
        target_claim,
        content=cycle_outputs
    )
    """,

    # FTS triggers for cycle outputs
    """
    CREATE TRIGGER IF NOT EXISTS cycle_outputs_fts_insert AFTER INSERT ON cycle_outputs BEGIN
        INSERT INTO cycle_outputs_fts(rowid, id, workspace_id, synthesis_reasoning, target_claim)
        VALUES (new.rowid, new.id, new.workspace_id, new.synthesis_reasoning, new.target_claim);
    END
    """,

    """
    CREATE TRIGGER IF NOT EXISTS cycle_outputs_fts_delete AFTER DELETE ON cycle_outputs BEGIN
        DELETE FROM cycle_outputs_fts WHERE rowid = old.rowid;
    END
    """,
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

            # Enable WAL mode for better read concurrency
            # (allows simultaneous reads while writes are in progress)
            if not self._is_memory:
                await db.execute("PRAGMA journal_mode = WAL")
                await db.execute("PRAGMA synchronous = NORMAL")

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

    # --- Cycle Output Operations ---

    async def save_cycle_output(
        self,
        cycle_id: int,
        target_node: KnowledgeNode,
        agent_outputs: list[Any],
        synthesis_result: Any | None,
        merge_stats: dict[str, int],
        duration_seconds: float,
        total_cost_usd: float,
        success: bool = True,
        error_message: str | None = None,
        selection_strategy: str | None = None,
        selection_reasoning: str | None = None,
    ) -> int:
        """
        Save complete cycle output to database.

        Args:
            cycle_id: Cycle ID
            target_node: Target node that was researched
            agent_outputs: List of AgentOutput objects
            synthesis_result: SynthesisResult if multi-agent mode
            merge_stats: Merge statistics (created, updated, skipped)
            duration_seconds: Cycle duration
            total_cost_usd: Total cost across all agents
            success: Whether cycle succeeded
            error_message: Optional error message
            selection_strategy: LLM selection strategy (EXPLORE/DEEPEN/CHALLENGE)
            selection_reasoning: LLM selection reasoning

        Returns:
            cycle_output_id (int)
        """
        if not self._initialized:
            await self.initialize()

        # Extract synthesis data
        synthesis_reasoning = None
        consensus_findings = []
        contradictions = []

        if synthesis_result:
            synthesis_reasoning = synthesis_result.synthesis_reasoning
            consensus_findings = synthesis_result.consensus_findings
            contradictions = synthesis_result.contradictions

        # Serialize data for storage
        consensus_findings_json = json.dumps(consensus_findings) if consensus_findings else None
        contradictions_json = json.dumps(contradictions) if contradictions else None

        # Calculate total tokens
        total_tokens = sum(output.total_tokens for output in agent_outputs)

        async with self._get_db() as db:
            # Insert cycle output
            cursor = await db.execute(
                """
                INSERT INTO cycle_outputs (
                    cycle_id, workspace_id, target_node_id, target_claim,
                    synthesis_reasoning, consensus_findings, contradictions,
                    findings_created, findings_updated, findings_skipped,
                    agent_count, total_tokens, total_cost_usd, duration_seconds,
                    success, error_message, selection_strategy, selection_reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cycle_id,
                    self.workspace_id,
                    target_node.id,
                    target_node.claim,
                    synthesis_reasoning,
                    consensus_findings_json,
                    contradictions_json,
                    merge_stats.get("created", 0),
                    merge_stats.get("updated", 0),
                    merge_stats.get("skipped", 0),
                    len(agent_outputs),
                    total_tokens,
                    total_cost_usd,
                    duration_seconds,
                    1 if success else 0,
                    error_message,
                    selection_strategy,
                    selection_reasoning,
                ),
            )

            cycle_output_id = cursor.lastrowid

            # Insert agent outputs
            for i, output in enumerate(agent_outputs):
                # Determine role (first is primary if multi-agent)
                role = "primary" if i == 0 and len(agent_outputs) > 1 else "secondary"

                # Serialize findings and searches
                findings_json = self._serialize_agent_findings(output.findings)
                searches_json = self._serialize_agent_searches(output.searches_performed)

                await db.execute(
                    """
                    INSERT INTO agent_outputs (
                        cycle_output_id, agent_name, agent_model, role,
                        findings, self_critique, searches_performed,
                        cost_usd, total_tokens, input_tokens, output_tokens,
                        duration_seconds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cycle_output_id,
                        output.agent_name,
                        output.model,
                        role,
                        findings_json,
                        output.self_critique,
                        searches_json,
                        output.cost_usd,
                        output.total_tokens,
                        output.input_tokens,
                        output.output_tokens,
                        output.duration_seconds,
                    ),
                )

            await db.commit()

        logger.debug(f"Saved cycle output {cycle_output_id} for cycle {cycle_id}")
        return cycle_output_id

    def _serialize_agent_findings(self, findings: list[Any]) -> str:
        """Serialize agent findings to JSON."""
        findings_data = []
        for finding in findings:
            finding_dict = {
                "claim": finding.claim,
                "confidence": finding.confidence,
                "evidence": [
                    {
                        "text": e.text,
                        "source": e.source,
                        "date": e.date.isoformat() if hasattr(e.date, "isoformat") else str(e.date),
                        "verified_by": e.verified_by,
                    }
                    for e in finding.evidence
                ],
                "tags": finding.tags,
                "finding_type": getattr(finding, "finding_type", None),
            }
            findings_data.append(finding_dict)
        return json.dumps(findings_data)

    def _serialize_agent_searches(self, searches: list[Any]) -> str:
        """Serialize agent searches to JSON."""
        searches_data = []
        for search in searches:
            search_dict = {
                "query": search.query,
                "engine": search.engine,
                "timestamp": search.timestamp.isoformat() if hasattr(search.timestamp, "isoformat") else str(search.timestamp),
                "results_summary": getattr(search, "results_summary", ""),
                "urls_visited": getattr(search, "urls_visited", []),
            }
            searches_data.append(search_dict)
        return json.dumps(searches_data)

    async def get_cycle_output(self, cycle_id: int) -> dict[str, Any] | None:
        """
        Get cycle output with all agent outputs.

        Args:
            cycle_id: Cycle ID to retrieve

        Returns:
            Dict with cycle data and agent outputs, or None if not found
        """
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            # Get cycle output
            cursor = await db.execute(
                """
                SELECT
                    id, cycle_id, workspace_id, target_node_id, target_claim,
                    synthesis_reasoning, consensus_findings, contradictions,
                    findings_created, findings_updated, findings_skipped,
                    agent_count, total_tokens, total_cost_usd, duration_seconds,
                    success, error_message, created_at,
                    selection_strategy, selection_reasoning
                FROM cycle_outputs
                WHERE cycle_id = ? AND workspace_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (cycle_id, self.workspace_id),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            # Parse cycle data
            cycle_data = {
                "id": row[0],
                "cycle_id": row[1],
                "workspace_id": row[2],
                "target_node_id": row[3],
                "target_claim": row[4],
                "synthesis_reasoning": row[5],
                "consensus_findings": json.loads(row[6]) if row[6] else [],
                "contradictions": json.loads(row[7]) if row[7] else [],
                "findings_created": row[8],
                "findings_updated": row[9],
                "findings_skipped": row[10],
                "agent_count": row[11],
                "total_tokens": row[12],
                "total_cost_usd": row[13],
                "duration_seconds": row[14],
                "success": bool(row[15]),
                "error_message": row[16],
                "created_at": row[17],
                "selection_strategy": row[18],
                "selection_reasoning": row[19],
            }

            # Get agent outputs
            cursor = await db.execute(
                """
                SELECT
                    agent_name, agent_model, role, findings, self_critique,
                    searches_performed, cost_usd, total_tokens, input_tokens,
                    output_tokens, duration_seconds
                FROM agent_outputs
                WHERE cycle_output_id = ?
                ORDER BY id
                """,
                (cycle_data["id"],),
            )
            agent_rows = await cursor.fetchall()

            agent_outputs = []
            for agent_row in agent_rows:
                agent_data = {
                    "agent_name": agent_row[0],
                    "agent_model": agent_row[1],
                    "role": agent_row[2],
                    "findings": json.loads(agent_row[3]),
                    "self_critique": agent_row[4],
                    "searches_performed": json.loads(agent_row[5]),
                    "cost_usd": agent_row[6],
                    "total_tokens": agent_row[7],
                    "input_tokens": agent_row[8],
                    "output_tokens": agent_row[9],
                    "duration_seconds": agent_row[10],
                }
                agent_outputs.append(agent_data)

            cycle_data["agent_outputs"] = agent_outputs
            return cycle_data

    async def get_max_cycle_id(self) -> int:
        """
        Get the maximum cycle_id stored for this workspace.

        Returns:
            Maximum cycle_id, or 0 if no cycles exist
        """
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            cursor = await db.execute(
                "SELECT MAX(cycle_id) FROM cycle_outputs WHERE workspace_id = ?",
                (self.workspace_id,),
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] is not None else 0

    async def list_cycle_outputs(
        self,
        workspace_id: str,
        limit: int = 20,
        offset: int = 0,
        min_cost: float | None = None,
        max_cost: float | None = None,
        target_node_id: str | None = None,
        success_only: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List cycle outputs with filtering.

        Args:
            workspace_id: Workspace ID
            limit: Maximum results
            offset: Offset for pagination
            min_cost: Minimum cost filter
            max_cost: Maximum cost filter
            target_node_id: Filter by target node
            success_only: Only show successful cycles

        Returns:
            List of cycle output dicts
        """
        if not self._initialized:
            await self.initialize()

        # Build query with filters
        filters = ["workspace_id = ?"]
        params: list[Any] = [workspace_id]

        if min_cost is not None:
            filters.append("total_cost_usd >= ?")
            params.append(min_cost)

        if max_cost is not None:
            filters.append("total_cost_usd <= ?")
            params.append(max_cost)

        if target_node_id:
            filters.append("target_node_id = ?")
            params.append(target_node_id)

        if success_only:
            filters.append("success = 1")

        where_clause = " AND ".join(filters)
        params.extend([limit, offset])

        async with self._get_db() as db:
            cursor = await db.execute(
                f"""
                SELECT
                    cycle_id, workspace_id, target_node_id, target_claim,
                    findings_created, findings_updated, findings_skipped,
                    agent_count, total_tokens, total_cost_usd, duration_seconds,
                    success, error_message, created_at
                FROM cycle_outputs
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                tuple(params),
            )
            rows = await cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                "cycle_id": row[0],
                "workspace_id": row[1],
                "target_node_id": row[2],
                "target_claim": row[3],
                "findings_created": row[4],
                "findings_updated": row[5],
                "findings_skipped": row[6],
                "agent_count": row[7],
                "total_tokens": row[8],
                "total_cost_usd": row[9],
                "duration_seconds": row[10],
                "success": bool(row[11]),
                "error_message": row[12],
                "created_at": row[13],
            })

        return results

    async def search_cycle_outputs(
        self,
        query: str,
        workspace_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Full-text search on synthesis reasoning and claims.

        Args:
            query: Search query
            workspace_id: Workspace ID
            limit: Maximum results

        Returns:
            List of matching cycle outputs
        """
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT
                    co.cycle_id, co.workspace_id, co.target_node_id, co.target_claim,
                    co.findings_created, co.findings_updated, co.findings_skipped,
                    co.agent_count, co.total_tokens, co.total_cost_usd, co.duration_seconds,
                    co.success, co.error_message, co.created_at
                FROM cycle_outputs co
                JOIN cycle_outputs_fts fts ON co.rowid = fts.rowid
                WHERE fts MATCH ? AND co.workspace_id = ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, workspace_id, limit),
            )
            rows = await cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                "cycle_id": row[0],
                "workspace_id": row[1],
                "target_node_id": row[2],
                "target_claim": row[3],
                "findings_created": row[4],
                "findings_updated": row[5],
                "findings_skipped": row[6],
                "agent_count": row[7],
                "total_tokens": row[8],
                "total_cost_usd": row[9],
                "duration_seconds": row[10],
                "success": bool(row[11]),
                "error_message": row[12],
                "created_at": row[13],
            })

        return results

    async def get_all_search_queries(self, limit: int = 200) -> list[dict[str, str]]:
        """
        Get all search queries from recent agent outputs (batch query, no N+1).

        Args:
            limit: Maximum number of agent_output rows to scan

        Returns:
            List of dicts with 'query' and 'engine' keys
        """
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT ao.searches_performed
                FROM agent_outputs ao
                JOIN cycle_outputs co ON ao.cycle_output_id = co.id
                WHERE co.workspace_id = ? AND co.success = 1
                ORDER BY co.created_at DESC
                LIMIT ?
                """,
                (self.workspace_id, limit),
            )
            rows = await cursor.fetchall()

        results: list[dict[str, str]] = []
        for row in rows:
            try:
                searches = json.loads(row[0]) if row[0] else []
                for search in searches:
                    if isinstance(search, dict) and "query" in search:
                        results.append({
                            "query": search["query"],
                            "engine": search.get("engine", "unknown"),
                        })
            except (json.JSONDecodeError, TypeError):
                continue

        return results

    async def get_recent_critiques(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent agent self-critiques (batch query, no N+1).

        Args:
            limit: Maximum number of critiques to return

        Returns:
            List of dicts with 'agent_name', 'cycle_id', 'self_critique'
        """
        if not self._initialized:
            await self.initialize()

        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT ao.agent_name, co.cycle_id, ao.self_critique
                FROM agent_outputs ao
                JOIN cycle_outputs co ON ao.cycle_output_id = co.id
                WHERE co.workspace_id = ? AND co.success = 1
                    AND ao.self_critique != ''
                ORDER BY co.created_at DESC
                LIMIT ?
                """,
                (self.workspace_id, limit),
            )
            rows = await cursor.fetchall()

        return [
            {
                "agent_name": row[0],
                "cycle_id": row[1],
                "self_critique": row[2],
            }
            for row in rows
        ]

    async def delete_old_cycle_outputs(
        self,
        workspace_id: str,
        retention_days: int = 90,
    ) -> int:
        """
        Delete cycle outputs older than retention period.

        Args:
            workspace_id: Workspace ID
            retention_days: Days to keep (0 = keep forever)

        Returns:
            Number of deleted cycles
        """
        if not self._initialized:
            await self.initialize()

        if retention_days == 0:
            return 0  # Keep forever

        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cutoff_str = cutoff_date.isoformat()

        async with self._get_db() as db:
            # Count how many will be deleted
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM cycle_outputs
                WHERE workspace_id = ? AND created_at < ?
                """,
                (workspace_id, cutoff_str),
            )
            count_row = await cursor.fetchone()
            delete_count = count_row[0] if count_row else 0

            if delete_count > 0:
                # Delete old cycle outputs (CASCADE will delete agent_outputs)
                await db.execute(
                    """
                    DELETE FROM cycle_outputs
                    WHERE workspace_id = ? AND created_at < ?
                    """,
                    (workspace_id, cutoff_str),
                )
                await db.commit()

                logger.info(f"Deleted {delete_count} old cycle outputs from workspace {workspace_id}")

        return delete_count

    async def close(self) -> None:
        """Close database connection (important for in-memory databases)."""
        if self._conn:
            await self._conn.close()
            self._conn = None
        self._initialized = False
