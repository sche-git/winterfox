"""
JSON export for knowledge graphs.

Produces machine-readable JSON with complete graph structure:
- Full node details
- Parent-child relationships
- Evidence with sources
- Metadata and timestamps
"""

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..graph.models import Evidence, KnowledgeNode
    from ..graph.store import KnowledgeGraph


def _serialize_evidence(evidence: "Evidence") -> dict[str, Any]:
    """Serialize evidence to JSON-compatible dict."""
    return {
        "text": evidence.text,
        "source": evidence.source,
        "date": evidence.date.isoformat() if evidence.date else None,
        "verified_by": evidence.verified_by,
    }


def _serialize_node(node: "KnowledgeNode") -> dict[str, Any]:
    """Serialize node to JSON-compatible dict."""
    return {
        "id": node.id,
        "workspace_id": node.workspace_id,
        "parent_id": node.parent_id,
        "claim": node.claim,
        "confidence": node.confidence,
        "importance": node.importance,
        "depth": node.depth,
        "staleness_hours": node.staleness_hours,
        "status": node.status,
        "tags": node.tags,
        "evidence": [_serialize_evidence(e) for e in node.evidence],
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
        "created_by_cycle": node.created_by_cycle,
        "updated_by_cycle": node.updated_by_cycle,
    }


async def export_to_json(
    graph: "KnowledgeGraph",
    output_path: str,
    pretty: bool = True,
    include_metadata: bool = True,
) -> None:
    """
    Export knowledge graph to JSON file.

    Args:
        graph: Knowledge graph to export
        output_path: Output file path
        pretty: Pretty-print JSON with indentation
        include_metadata: Include export metadata

    Example output:
        {
            "metadata": {
                "workspace_id": "default",
                "exported_at": "2024-01-15T10:30:00",
                "total_nodes": 47,
                "average_confidence": 0.72,
                "version": "0.1.0"
            },
            "nodes": [
                {
                    "id": "abc123",
                    "parent_id": null,
                    "claim": "Market opportunity exists",
                    "confidence": 0.82,
                    "evidence": [...]
                },
                ...
            ],
            "edges": [
                {"parent": "abc123", "child": "def456"},
                ...
            ]
        }
    """
    output_file = Path(output_path)

    # Get all nodes
    nodes = await graph.get_all_active_nodes()

    # Build export structure
    export_data: dict[str, Any] = {}

    # Metadata
    if include_metadata:
        total_nodes = len(nodes)
        avg_confidence = sum(n.confidence for n in nodes) / total_nodes if total_nodes else 0

        export_data["metadata"] = {
            "workspace_id": graph.workspace_id,
            "exported_at": datetime.now().isoformat(),
            "total_nodes": total_nodes,
            "average_confidence": avg_confidence,
            "version": "0.1.0",  # TODO: Get from package metadata
        }

    # Nodes
    export_data["nodes"] = [_serialize_node(node) for node in nodes]

    # Edges (parent-child relationships)
    edges = []
    for node in nodes:
        if node.parent_id:
            edges.append({"parent": node.parent_id, "child": node.id})
    export_data["edges"] = edges

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(export_data, f, ensure_ascii=False)


async def export_node_to_json(
    graph: "KnowledgeGraph",
    node_id: str,
    output_path: str,
    include_children: bool = True,
    pretty: bool = True,
) -> None:
    """
    Export a specific node (and optionally its subtree) to JSON.

    Args:
        graph: Knowledge graph
        node_id: Root node ID to export
        output_path: Output file path
        include_children: Include all descendants
        pretty: Pretty-print JSON
    """
    output_file = Path(output_path)

    # Get root node
    node = await graph.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")

    # Collect nodes
    nodes = [node]
    edges = []

    if include_children:
        # BFS to collect all descendants
        queue = [node_id]
        visited = {node_id}

        while queue:
            current_id = queue.pop(0)
            children = await graph.get_children(current_id)

            for child in children:
                if child.id not in visited:
                    nodes.append(child)
                    edges.append({"parent": current_id, "child": child.id})
                    queue.append(child.id)
                    visited.add(child.id)

    # Build export structure
    export_data = {
        "root_node_id": node_id,
        "nodes": [_serialize_node(n) for n in nodes],
        "edges": edges,
        "exported_at": datetime.now().isoformat(),
    }

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(export_data, f, ensure_ascii=False)


async def import_from_json(
    graph: "KnowledgeGraph",
    input_path: str,
    merge_strategy: str = "skip",  # "skip" | "update" | "replace"
) -> dict[str, int]:
    """
    Import knowledge graph from JSON file.

    Args:
        graph: Target knowledge graph
        input_path: Input JSON file path
        merge_strategy: How to handle existing nodes
            - "skip": Skip nodes that already exist
            - "update": Update existing nodes with new data
            - "replace": Delete and recreate existing nodes

    Returns:
        Stats dict with imported/updated/skipped counts
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Load JSON
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = {"imported": 0, "updated": 0, "skipped": 0, "errors": 0}

    # Import nodes
    for node_data in data.get("nodes", []):
        try:
            node_id = node_data["id"]

            # Check if node exists
            existing = await graph.get_node(node_id)

            if existing:
                if merge_strategy == "skip":
                    stats["skipped"] += 1
                    continue
                elif merge_strategy == "update":
                    # Update existing node
                    # TODO: Implement update logic
                    stats["updated"] += 1
                elif merge_strategy == "replace":
                    # Delete and recreate
                    await graph.kill_node(node_id)
                    # Fall through to create new

            # Create node from imported data
            from ..graph.models import Evidence, KnowledgeNode

            evidence = [
                Evidence(
                    text=e["text"],
                    source=e["source"],
                    date=datetime.fromisoformat(e["date"]) if e["date"] else None,
                    verified_by=e.get("verified_by", []),
                )
                for e in node_data.get("evidence", [])
            ]

            await graph.add_node(
                claim=node_data["claim"],
                parent_id=node_data.get("parent_id"),
                confidence=node_data.get("confidence", 0.0),
                importance=node_data.get("importance", 0.5),
                depth=node_data.get("depth", 0),
                created_by_cycle=node_data.get("created_by_cycle", 0),
                evidence=evidence,
                tags=node_data.get("tags", []),
            )

            stats["imported"] += 1

        except Exception as e:
            print(f"Error importing node {node_data.get('id', 'unknown')}: {e}")
            stats["errors"] += 1

    return stats
