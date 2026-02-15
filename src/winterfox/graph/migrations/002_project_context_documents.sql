-- Migration: Persist project context documents
-- Purpose: Add table for storing context files in DB for API/UI access
-- Date: 2026-02-14

CREATE TABLE IF NOT EXISTS project_context_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL DEFAULT 'default',
    filename TEXT NOT NULL,
    content TEXT NOT NULL,
    source_path TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    UNIQUE(workspace_id, filename)
);

CREATE INDEX IF NOT EXISTS idx_project_context_workspace
ON project_context_documents(workspace_id, filename);
