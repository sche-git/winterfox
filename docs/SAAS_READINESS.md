# Winterfox SaaS Readiness Assessment

## Purpose

This document evaluates Winterfox's current state against a production SaaS target and outlines a practical, incremental path to get there.

## Executive Summary

Winterfox has strong foundations for SaaS evolution:

- API + web UI already exist (not CLI-only).
- Core domain model already includes `workspace_id` and workspace-scoped data.
- Cycle execution can now be triggered from the browser via API.
- Real-time event streaming exists through WebSocket.

Winterfox is **not yet production SaaS-ready** for multi-user internet exposure. The highest-risk gaps are auth/authorization, tenant isolation at request level, and durable background execution.

## Current Strengths

### Product/API Surface

- FastAPI backend with structured endpoints for graph/cycles/stats/config/report.
- Frontend consumes typed REST API and WebSocket events.
- Browser can initiate research cycles (`POST /api/cycles`), including:
  - Optional `target_node_id`
  - Optional one-off `cycle_instruction`

### Research Engine

- Orchestrator and cycle pipeline are modular and testable.
- Lead/research-agent architecture supports evolving prompts and toolchains.
- Real-time cycle step events are emitted and now bridged to WebSocket subscribers.

### Data Model

- Workspace-aware schema is already present in storage layer.
- Operational tables exist for cycles, outputs, agent outputs, and usage events.
- Context documents can be persisted and surfaced via API/UI.

## Critical Gaps for SaaS

### 1) Authentication and Authorization (Critical)

Current APIs and WebSocket channels do not enforce user identity or permission checks. This blocks safe multi-user SaaS operation.

Needs:

- User auth (session or JWT/OIDC).
- Workspace membership/role model (owner/admin/member/viewer).
- Endpoint-level authorization and resource ownership checks.

### 2) Tenant Isolation Model (Critical)

The running app binds to one workspace configuration at startup. For SaaS, workspace must be resolved per request from authenticated identity and enforced consistently.

Needs:

- Request-scoped workspace resolution.
- Strict data-access guardrails for every query.
- Removal of process-global workspace assumptions.

### 3) Background Job Durability and Scale (Critical)

Cycle execution currently runs in-process with an in-memory lock. This is okay for local/dev but not for horizontal scale or crash recovery.

Needs:

- Durable queue + worker model (e.g., Redis + worker framework).
- Persistent job states (`queued/running/succeeded/failed/cancelled`).
- Retry policy and idempotency keys.

### 4) Production Data Layer (High)

SQLite is a strong dev default but not ideal for high-concurrency multi-tenant SaaS.

Needs:

- Postgres migration path.
- Connection pooling and migration discipline.
- Tenant-aware indexing and performance baselines.

### 5) Operations and Compliance Baseline (High)

SaaS needs formalized operability and safety controls.

Needs:

- Structured logs + tracing + metrics (API latency, cycle duration, queue depth, error rates, cost).
- Rate limiting, quotas, abuse controls.
- Secret management and key rotation.
- Backups/restore drills and incident response playbook.

## Readiness Score (Current Snapshot)

- Product UX readiness: **6/10**
- API readiness: **6/10**
- Multi-user security readiness: **2/10**
- Multi-tenant runtime readiness: **3/10**
- Scalability readiness: **3/10**
- Operability readiness: **3/10**

Overall: **4/10 toward production SaaS**

## Recommended Incremental Roadmap

### Phase 1: Secure Multi-User Foundation

1. Add authentication (JWT/session).
2. Add workspace membership/roles.
3. Enforce authz across all REST and WebSocket routes.
4. Add request-scoped workspace context.

Exit criteria:

- Two users in two different workspaces cannot access each other’s data.

### Phase 2: Durable Execution Plane

1. Move cycle runs to queue + workers.
2. Add `jobs` API and persistent job lifecycle state.
3. Support cancel/retry semantics.
4. Keep WebSocket updates sourced from durable job events.

Exit criteria:

- Running cycles survive API process restart.

### Phase 3: Storage and Reliability

1. Introduce Postgres backend.
2. Add migration and rollback strategy.
3. Add observability dashboards + SLOs.
4. Add backup/recovery automation.

Exit criteria:

- Stable concurrent tenant traffic with predictable latency/error budget.

### Phase 4: Commercial SaaS Controls

1. Plan-based quotas and billing hooks.
2. Cost controls (per workspace budgets/alerts).
3. Admin tooling for workspace lifecycle and support operations.

Exit criteria:

- Workspace-level billing, usage enforcement, and support workflows are operational.

## Immediate Next Steps (1-2 sprints)

1. Implement auth + workspace membership schema and middleware.
2. Refactor global services to request-scoped tenant access.
3. Introduce a minimal job table and enqueue cycle API contract.
4. Keep current in-process runner as fallback until worker rollout is complete.

