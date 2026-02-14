"""
Tests for database migration 001_lead_llm_architecture.

These tests verify:
- Migration SQL file can be parsed and executed
- Node type conversion (question/hypothesis/supporting/opposing → direction)
- Cost column additions and backfilling
- Report metadata table creation
- Data integrity after migration
- Idempotency (migration can be run multiple times safely)
"""

import pytest
import json
from datetime import datetime
from pathlib import Path

from winterfox.graph.store import KnowledgeGraph


@pytest.mark.asyncio
async def test_migration_sql_syntax(tmp_path):
    """Test that migration SQL file has valid syntax and can be executed."""
    db_path = tmp_path / "test_sql_syntax.db"
    graph = KnowledgeGraph(str(db_path), workspace_id="test")

    # Initialize with base schema
    await graph.initialize()

    # Create test workspace
    async with graph._get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO workspaces (id, name, tier) VALUES (?, ?, ?)",
            ("test", "Test Workspace", "free"),
        )
        await db.commit()

    # Add a dummy node to test migration on
    async with graph._get_db() as db:
        await db.execute(
            """INSERT INTO nodes (id, workspace_id, claim, confidence, importance,
               depth, status, node_type, data, created_by_cycle, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "test_node", "test", "Test claim", 0.5, 0.8, 0, "active",
                "question", json.dumps({"id": "test_node", "node_type": "question"}),
                1, datetime.now().isoformat()
            )
        )
        await db.commit()

    # Read migration SQL file
    migration_file = Path(__file__).parent.parent.parent.parent / "src" / "winterfox" / "graph" / "migrations" / "001_lead_llm_architecture.sql"
    assert migration_file.exists(), f"Migration file not found: {migration_file}"

    sql = migration_file.read_text(encoding="utf-8")

    # Verify no transaction wrappers (aiosqlite doesn't support executescript)
    assert "BEGIN TRANSACTION" not in sql, "Migration SQL should not contain BEGIN TRANSACTION"
    assert sql.count("COMMIT") == 0, "Migration SQL should not contain COMMIT statements"

    # Try running the migration
    await graph.run_migrations()

    # Verify migration succeeded
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT name FROM migrations WHERE name = '001_lead_llm_architecture.sql'")
        result = await cursor.fetchone()
        assert result is not None, "Migration was not recorded in migrations table"


@pytest.fixture
async def pre_migration_graph(tmp_path):
    """
    Create a graph with old schema (pre-migration).

    This simulates a database before the Lead LLM architecture migration.
    """
    db_path = tmp_path / "test_migration.db"
    graph = KnowledgeGraph(str(db_path), workspace_id="test")

    # Initialize with base schema
    await graph.initialize()

    # Create test workspace
    async with graph._get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO workspaces (id, name, tier) VALUES (?, ?, ?)",
            ("test", "Test Workspace", "free"),
        )
        await db.commit()

    # Insert nodes with OLD node types (question, hypothesis, supporting, opposing)
    async with graph._get_db() as db:
        # Question node
        question_data = {
            "id": "q1",
            "workspace_id": "test",
            "parent_id": None,
            "claim": "What is AI?",
            "confidence": 0.5,
            "importance": 1.0,
            "depth": 0,
            "status": "active",
            "node_type": "question",  # OLD TYPE
            "children_ids": [],
            "tags": [],
            "evidence": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "created_by_cycle": 1,
            "updated_by_cycle": 1,
        }

        await db.execute(
            """INSERT INTO nodes (id, workspace_id, parent_id, claim, confidence,
               importance, depth, status, node_type, data, created_by_cycle, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "q1", "test", None, "What is AI?", 0.5, 1.0, 0, "active",
                "question", json.dumps(question_data), 1, datetime.now().isoformat()
            )
        )

        # Hypothesis node
        hypothesis_data = {
            "id": "h1",
            "workspace_id": "test",
            "parent_id": "q1",
            "claim": "AI is machine learning",
            "confidence": 0.7,
            "importance": 0.8,
            "depth": 1,
            "status": "active",
            "node_type": "hypothesis",  # OLD TYPE
            "children_ids": [],
            "tags": [],
            "evidence": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "created_by_cycle": 2,
            "updated_by_cycle": 2,
        }

        await db.execute(
            """INSERT INTO nodes (id, workspace_id, parent_id, claim, confidence,
               importance, depth, status, node_type, data, created_by_cycle, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "h1", "test", "q1", "AI is machine learning", 0.7, 0.8, 1, "active",
                "hypothesis", json.dumps(hypothesis_data), 2, datetime.now().isoformat()
            )
        )

        # Supporting node
        supporting_data = {
            "id": "s1",
            "workspace_id": "test",
            "parent_id": "h1",
            "claim": "Evidence supporting ML definition",
            "confidence": 0.8,
            "importance": 0.5,
            "depth": 2,
            "status": "active",
            "node_type": "supporting",  # OLD TYPE
            "children_ids": [],
            "tags": [],
            "evidence": [{"text": "Source A", "source": "http://example.com"}],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "created_by_cycle": 3,
            "updated_by_cycle": 3,
        }

        await db.execute(
            """INSERT INTO nodes (id, workspace_id, parent_id, claim, confidence,
               importance, depth, status, node_type, data, created_by_cycle, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "s1", "test", "h1", "Evidence supporting ML definition", 0.8, 0.5, 2, "active",
                "supporting", json.dumps(supporting_data), 3, datetime.now().isoformat()
            )
        )

        # Opposing node
        opposing_data = {
            "id": "o1",
            "workspace_id": "test",
            "parent_id": "h1",
            "claim": "Evidence opposing ML definition",
            "confidence": 0.6,
            "importance": 0.6,
            "depth": 2,
            "status": "active",
            "node_type": "opposing",  # OLD TYPE
            "children_ids": [],
            "tags": [],
            "evidence": [{"text": "Source B", "source": "http://example.org"}],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "created_by_cycle": 4,
            "updated_by_cycle": 4,
        }

        await db.execute(
            """INSERT INTO nodes (id, workspace_id, parent_id, claim, confidence,
               importance, depth, status, node_type, data, created_by_cycle, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "o1", "test", "h1", "Evidence opposing ML definition", 0.6, 0.6, 2, "active",
                "opposing", json.dumps(opposing_data), 4, datetime.now().isoformat()
            )
        )

        # Node with NULL node_type (edge case)
        null_data = {
            "id": "n1",
            "workspace_id": "test",
            "parent_id": None,
            "claim": "Node with null type",
            "confidence": 0.5,
            "importance": 0.5,
            "depth": 0,
            "status": "active",
            "node_type": None,  # NULL TYPE
            "children_ids": [],
            "tags": [],
            "evidence": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "created_by_cycle": 5,
            "updated_by_cycle": 5,
        }

        await db.execute(
            """INSERT INTO nodes (id, workspace_id, parent_id, claim, confidence,
               importance, depth, status, node_type, data, created_by_cycle, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "n1", "test", None, "Node with null type", 0.5, 0.5, 0, "active",
                None, json.dumps(null_data), 5, datetime.now().isoformat()
            )
        )

        # Add cycle outputs with old cost structure (no lead_llm_cost_usd column yet)
        await db.execute(
            """INSERT INTO cycle_outputs (
                cycle_id, workspace_id, target_node_id, synthesis_reasoning,
                total_cost_usd, duration_seconds, success, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                1, "test", "q1", "Cycle 1 synthesis",
                0.50, 30.0, 1, datetime.now().isoformat()
            )
        )

        await db.execute(
            """INSERT INTO cycle_outputs (
                cycle_id, workspace_id, target_node_id, synthesis_reasoning,
                total_cost_usd, duration_seconds, success, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                2, "test", "h1", "Cycle 2 synthesis",
                1.00, 45.0, 1, datetime.now().isoformat()
            )
        )

        await db.commit()

    yield graph

    await graph.close()


@pytest.mark.asyncio
async def test_node_type_conversion(pre_migration_graph):
    """Test that all old node types are converted to 'direction'."""
    graph = pre_migration_graph

    # Verify pre-migration state
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type")
        pre_types = dict(await cursor.fetchall())

    # Should have old types
    assert "question" in pre_types
    assert "hypothesis" in pre_types
    assert "supporting" in pre_types
    assert "opposing" in pre_types
    assert None in pre_types  # NULL type node

    # Run migration
    await graph.run_migrations()

    # Verify post-migration state
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT DISTINCT node_type FROM nodes")
        post_types = [row[0] for row in await cursor.fetchall()]

    # Should only have 'direction'
    assert len(post_types) == 1
    assert post_types[0] == "direction"

    # Verify data integrity - check specific nodes
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT id, data FROM nodes WHERE id IN ('q1', 'h1', 's1', 'o1', 'n1')")
        nodes = await cursor.fetchall()

    for node_id, data_json in nodes:
        data = json.loads(data_json)
        assert data["node_type"] == "direction", f"Node {node_id} not converted"

        # Verify other data preserved
        assert data["claim"] is not None
        assert data["confidence"] is not None
        assert data["importance"] is not None


@pytest.mark.asyncio
async def test_cost_column_additions(pre_migration_graph):
    """Test that cost tracking columns are added and backfilled."""
    graph = pre_migration_graph

    # Verify columns don't exist before migration
    async with graph._get_db() as db:
        cursor = await db.execute("PRAGMA table_info(cycle_outputs)")
        columns_before = {row[1] for row in await cursor.fetchall()}

    assert "lead_llm_cost_usd" not in columns_before
    assert "research_agents_cost_usd" not in columns_before

    # Run migration
    await graph.run_migrations()

    # Verify columns added
    async with graph._get_db() as db:
        cursor = await db.execute("PRAGMA table_info(cycle_outputs)")
        columns_after = {row[1] for row in await cursor.fetchall()}

    assert "lead_llm_cost_usd" in columns_after
    assert "research_agents_cost_usd" in columns_after

    # Verify backfilling (50/50 split)
    async with graph._get_db() as db:
        cursor = await db.execute(
            "SELECT cycle_id, total_cost_usd, lead_llm_cost_usd, research_agents_cost_usd FROM cycle_outputs"
        )
        cycles = await cursor.fetchall()

    for cycle_id, total, lead, research in cycles:
        # 50/50 split
        assert lead == pytest.approx(total * 0.5, rel=0.01)
        assert research == pytest.approx(total * 0.5, rel=0.01)
        assert lead + research == pytest.approx(total, rel=0.01)


@pytest.mark.asyncio
async def test_report_metadata_table(pre_migration_graph):
    """Test that report_metadata table is created and initialized."""
    graph = pre_migration_graph

    # Run migration
    await graph.run_migrations()

    # Verify table exists
    async with graph._get_db() as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='report_metadata'"
        )
        result = await cursor.fetchone()

    assert result is not None, "report_metadata table not created"

    # Verify workspace initialized
    async with graph._get_db() as db:
        cursor = await db.execute(
            "SELECT workspace_id, regeneration_interval FROM report_metadata WHERE workspace_id='test'"
        )
        row = await cursor.fetchone()

    assert row is not None, "Workspace not initialized in report_metadata"
    assert row[1] == 10, "Default regeneration_interval not set to 10"


@pytest.mark.asyncio
async def test_migration_idempotency(pre_migration_graph):
    """Test that migration can be run multiple times safely."""
    graph = pre_migration_graph

    # Run migration first time
    await graph.run_migrations()

    # Get state after first migration
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM nodes WHERE json_extract(data, '$.node_type') = 'direction'")
        count_after_first = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM cycle_outputs WHERE lead_llm_cost_usd IS NOT NULL")
        cycles_after_first = (await cursor.fetchone())[0]

    # Run migration again (should be safe)
    await graph.run_migrations()

    # Get state after second migration
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM nodes WHERE json_extract(data, '$.node_type') = 'direction'")
        count_after_second = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM cycle_outputs WHERE lead_llm_cost_usd IS NOT NULL")
        cycles_after_second = (await cursor.fetchone())[0]

    # Counts should be identical
    assert count_after_first == count_after_second
    assert cycles_after_first == cycles_after_second

    # No duplicate rows or data corruption
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM nodes")
        total_nodes = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(DISTINCT id) FROM nodes")
        unique_nodes = (await cursor.fetchone())[0]

    assert total_nodes == unique_nodes, "Duplicate nodes created by repeated migration"


@pytest.mark.asyncio
async def test_data_integrity_after_migration(pre_migration_graph):
    """Test that all data is preserved after migration."""
    graph = pre_migration_graph

    # Capture pre-migration data
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT id, claim, confidence, importance FROM nodes ORDER BY id")
        pre_data = await cursor.fetchall()

    # Run migration
    await graph.run_migrations()

    # Capture post-migration data
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT id, claim, confidence, importance FROM nodes ORDER BY id")
        post_data = await cursor.fetchall()

    # Data should be identical (except node_type which we tested separately)
    assert len(pre_data) == len(post_data)

    for pre, post in zip(pre_data, post_data):
        assert pre[0] == post[0], "Node ID changed"
        assert pre[1] == post[1], "Claim changed"
        assert pre[2] == post[2], "Confidence changed"
        assert pre[3] == post[3], "Importance changed"


@pytest.mark.asyncio
async def test_migration_tracking(pre_migration_graph):
    """Test that migration is tracked in migrations table."""
    graph = pre_migration_graph

    # Run migration
    await graph.run_migrations()

    # Verify migration tracked
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT name, applied_at FROM migrations ORDER BY id")
        migrations = await cursor.fetchall()

    assert len(migrations) > 0, "No migrations tracked"

    # Should have our migration
    migration_names = [m[0] for m in migrations]
    assert "001_lead_llm_architecture.sql" in migration_names


@pytest.mark.asyncio
async def test_complex_node_preserved(pre_migration_graph):
    """Test that complex nodes with evidence are preserved correctly."""
    graph = pre_migration_graph

    # Get complex nodes before migration
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT data FROM nodes WHERE id IN ('s1', 'o1')")
        pre_nodes = {json.loads(row[0])["id"]: json.loads(row[0]) for row in await cursor.fetchall()}

    # Run migration
    await graph.run_migrations()

    # Get complex nodes after migration
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT data FROM nodes WHERE id IN ('s1', 'o1')")
        post_nodes = {json.loads(row[0])["id"]: json.loads(row[0]) for row in await cursor.fetchall()}

    # Verify evidence preserved
    for node_id in ["s1", "o1"]:
        pre = pre_nodes[node_id]
        post = post_nodes[node_id]

        assert len(post["evidence"]) == len(pre["evidence"]), f"Evidence count changed for {node_id}"
        assert post["claim"] == pre["claim"], f"Claim changed for {node_id}"
        assert post["confidence"] == pre["confidence"], f"Confidence changed for {node_id}"

        # Only node_type should change
        assert post["node_type"] == "direction"


@pytest.mark.asyncio
async def test_null_cost_backfill(pre_migration_graph):
    """Test that NULL or 0 costs are backfilled correctly."""
    graph = pre_migration_graph

    # Add a cycle with zero cost before migration
    async with graph._get_db() as db:
        await db.execute(
            """INSERT INTO cycle_outputs (
                cycle_id, workspace_id, target_node_id, synthesis_reasoning,
                total_cost_usd, duration_seconds, success, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                99, "test", "q1", "Zero cost cycle",
                0.0, 10.0, 1, datetime.now().isoformat()
            )
        )
        await db.commit()

    # Run migration
    await graph.run_migrations()

    # Verify zero cost is handled (should be 0/0 split)
    async with graph._get_db() as db:
        cursor = await db.execute(
            "SELECT lead_llm_cost_usd, research_agents_cost_usd FROM cycle_outputs WHERE cycle_id=99"
        )
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == 0.0
    assert row[1] == 0.0


@pytest.mark.asyncio
async def test_all_node_types_converted(pre_migration_graph):
    """Test comprehensive conversion of all 4 old node types plus NULL."""
    graph = pre_migration_graph

    # Verify we have all types before migration
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT id, node_type FROM nodes ORDER BY id")
        pre_nodes = await cursor.fetchall()

    pre_types = {node_id: node_type for node_id, node_type in pre_nodes}

    # Verify pre-state
    assert pre_types["q1"] == "question"
    assert pre_types["h1"] == "hypothesis"
    assert pre_types["s1"] == "supporting"
    assert pre_types["o1"] == "opposing"
    assert pre_types["n1"] is None

    # Run migration
    await graph.run_migrations()

    # Verify all converted
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT id, node_type FROM nodes ORDER BY id")
        post_nodes = await cursor.fetchall()

    post_types = {node_id: node_type for node_id, node_type in post_nodes}

    # All should be 'direction'
    for node_id in ["q1", "h1", "s1", "o1", "n1"]:
        assert post_types[node_id] == "direction", f"Node {node_id} not converted to direction"


@pytest.mark.asyncio
async def test_json_data_field_updated(pre_migration_graph):
    """Test that the JSON data field is updated, not just the node_type column."""
    graph = pre_migration_graph

    # Run migration
    await graph.run_migrations()

    # Check that JSON data field has updated node_type
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT id, data FROM nodes")
        nodes = await cursor.fetchall()

    for node_id, data_json in nodes:
        data = json.loads(data_json)
        json_node_type = data.get("node_type")

        # JSON field should also be updated to 'direction'
        assert json_node_type == "direction", f"Node {node_id} JSON data not updated (got {json_node_type})"


@pytest.mark.asyncio
async def test_parent_child_relationships_preserved(pre_migration_graph):
    """Test that parent-child relationships are preserved after migration."""
    graph = pre_migration_graph

    # Capture relationships before migration
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT id, parent_id FROM nodes WHERE parent_id IS NOT NULL ORDER BY id")
        pre_relationships = await cursor.fetchall()

    # Run migration
    await graph.run_migrations()

    # Capture relationships after migration
    async with graph._get_db() as db:
        cursor = await db.execute("SELECT id, parent_id FROM nodes WHERE parent_id IS NOT NULL ORDER BY id")
        post_relationships = await cursor.fetchall()

    # Should be identical
    assert len(pre_relationships) == len(post_relationships)

    for pre, post in zip(pre_relationships, post_relationships):
        assert pre[0] == post[0], "Child ID changed"
        assert pre[1] == post[1], "Parent ID changed"
