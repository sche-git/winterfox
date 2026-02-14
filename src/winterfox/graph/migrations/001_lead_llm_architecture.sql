-- Migration: Lead LLM Architecture
-- Purpose: Convert to direction-only model and add Lead LLM cost tracking
-- Date: 2025-02-14

-- ═══════════════════════════════════════════════════════════════════════
-- PART 1: Convert all existing nodes to direction type
-- ═══════════════════════════════════════════════════════════════════════

-- Update nodes table: convert all node_type values to 'direction'
UPDATE nodes
SET data = json_set(data, '$.node_type', 'direction')
WHERE json_extract(data, '$.node_type') IN ('question', 'hypothesis', 'supporting', 'opposing')
   OR json_extract(data, '$.node_type') IS NULL;

-- Log migration statistics
-- (This is informational - SQLite doesn't have SELECT INTO, so we just comment)
-- Expected: All nodes should now have node_type='direction'

-- ═══════════════════════════════════════════════════════════════════════
-- PART 2: Add Lead LLM cost tracking to cycle_outputs table
-- ═══════════════════════════════════════════════════════════════════════

-- Add new columns for separate cost tracking
ALTER TABLE cycle_outputs ADD COLUMN lead_llm_cost_usd REAL DEFAULT 0.0;
ALTER TABLE cycle_outputs ADD COLUMN research_agents_cost_usd REAL DEFAULT 0.0;

-- Backfill: Split existing total_cost_usd 50/50 between Lead and Research
-- This is a conservative estimate for existing cycles
UPDATE cycle_outputs
SET lead_llm_cost_usd = total_cost_usd * 0.5,
    research_agents_cost_usd = total_cost_usd * 0.5
WHERE lead_llm_cost_usd IS NULL OR lead_llm_cost_usd = 0.0;

-- ═══════════════════════════════════════════════════════════════════════
-- PART 3: Add report regeneration tracking
-- ═══════════════════════════════════════════════════════════════════════

-- Create table to track report generation metadata
CREATE TABLE IF NOT EXISTS report_metadata (
    workspace_id TEXT PRIMARY KEY,
    last_generated_cycle INTEGER NOT NULL,
    last_generated_at TIMESTAMP NOT NULL,
    regeneration_interval INTEGER DEFAULT 10,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

-- Initialize report metadata for existing workspaces
INSERT OR IGNORE INTO report_metadata (workspace_id, last_generated_cycle, last_generated_at, regeneration_interval)
SELECT DISTINCT workspace_id, 0, CURRENT_TIMESTAMP, 10
FROM nodes
WHERE workspace_id IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- PART 4: Update indexes for direction-only model
-- ═══════════════════════════════════════════════════════════════════════

-- The existing indexes should still work, but we can optimize queries
-- by dropping any node_type-specific indexes if they exist
-- (None exist in current schema, so this is a no-op - keeping for documentation)

-- ═══════════════════════════════════════════════════════════════════════
-- PART 5: Validation and integrity checks
-- ═══════════════════════════════════════════════════════════════════════

-- Ensure all nodes have valid direction node_type
-- This is a safety check - UPDATE above should have handled this
UPDATE nodes
SET data = json_set(data, '$.node_type', 'direction')
WHERE json_extract(data, '$.node_type') != 'direction';

-- Verify no NULL node_types remain
UPDATE nodes
SET data = json_set(data, '$.node_type', 'direction')
WHERE json_extract(data, '$.node_type') IS NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- Migration Complete
-- ═══════════════════════════════════════════════════════════════════════
-- All nodes are now direction-only
-- Cost tracking separated for Lead LLM vs Research agents
-- Report regeneration metadata initialized
