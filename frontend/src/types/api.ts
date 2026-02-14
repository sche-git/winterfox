/**
 * TypeScript types matching backend Pydantic models.
 */

// Graph types

export interface Evidence {
  text: string;
  source: string;
  date: string | null;
  verified_by: string[];
}

export interface Node {
  id: string;
  claim: string;
  confidence: number;
  importance: number;
  depth: number;
  parent_id: string | null;
  children_ids: string[];
  evidence: Evidence[];
  status: 'active' | 'archived' | 'merged';
  node_type: 'direction' | 'question' | 'hypothesis' | 'supporting' | 'opposing' | null;
  created_by_cycle: number;
  updated_by_cycle: number;
  created_at: string;
  updated_at: string;
}

export interface GraphSummary {
  total_nodes: number;
  avg_confidence: number;
  avg_importance: number;
  root_nodes: number;
  low_confidence_count: number;
  last_cycle_at: string | null;
  workspace_id: string;
}

export interface NodesListResponse {
  nodes: Node[];
  total: number;
  limit: number;
  offset: number;
}

export interface NodeTreeItem {
  id: string;
  claim: string;
  confidence: number;
  importance: number;
  node_type: 'direction' | 'question' | 'hypothesis' | 'supporting' | 'opposing' | null;
  children: NodeTreeItem[];
}

export interface GraphTree {
  roots: NodeTreeItem[];
}

export interface SearchResult {
  node_id: string;
  claim: string;
  snippet: string;
  relevance_score: number;
}

export interface SearchResponse {
  results: SearchResult[];
}

// Cycle types

export interface Cycle {
  id: number;
  started_at: string;
  completed_at: string | null;
  status: 'running' | 'completed' | 'failed';
  focus_node_id: string | null;
  target_claim: string;
  total_cost_usd: number;
  lead_llm_cost_usd: number;
  research_agents_cost_usd: number;
  directions_count: number;
  findings_count: number;
  agents_used: string[];
  duration_seconds: number | null;
}

export interface CyclesListResponse {
  cycles: Cycle[];
  total: number;
}

export interface FindingEvidence {
  text: string;
  source: string;
  date: string | null;
}

export interface AgentFinding {
  claim: string;
  confidence: number;
  evidence: FindingEvidence[];
  tags: string[];
  finding_type: 'hypothesis' | 'supporting' | 'opposing' | null;
}

export interface AgentSearchRecord {
  query: string;
  engine: string;
  results_count: number;
}

export interface AgentOutputSummary {
  agent_name: string;
  model: string;
  role: string;
  cost_usd: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  duration_seconds: number;
  searches_performed: number;
  findings_count: number;
  self_critique: string;
  raw_text: string;
  findings: AgentFinding[];
  searches: AgentSearchRecord[];
}

export interface ContradictionItem {
  claim_a: string;
  claim_b: string;
  description: string;
}

export interface CycleDetail {
  id: number;
  target_node_id: string;
  target_claim: string;
  research_context: string | null;
  directions_created: number;
  directions_updated: number;
  directions_skipped: number;
  consensus_directions: string[];
  findings_created: number;
  findings_updated: number;
  findings_skipped: number;
  consensus_findings: string[];
  contradictions: ContradictionItem[];
  synthesis_reasoning: string;
  selection_strategy: 'EXPLORE' | 'DEEPEN' | 'CHALLENGE' | null;
  selection_reasoning: string | null;
  total_cost_usd: number;
  lead_llm_cost_usd: number;
  research_agents_cost_usd: number;
  total_tokens: number;
  duration_seconds: number;
  agent_count: number;
  success: boolean;
  error_message: string | null;
  created_at: string | null;
  agent_outputs: AgentOutputSummary[];
}

export interface ActiveCycle {
  cycle_id: number | null;
  status: 'running' | 'idle';
  focus_node_id: string | null;
  current_step: string | null;
  progress_percent: number;
}

// Stats types

export interface GraphStats {
  total_nodes: number;
  direction_count: number;
  avg_confidence: number;
  avg_importance: number;
  hypothesis_count: number;
  supporting_count: number;
  opposing_count: number;
}

export interface CycleStats {
  total: number;
  successful: number;
  failed: number;
  avg_duration_seconds: number;
}

export interface CostStats {
  total_usd: number;
  lead_llm_usd: number;
  research_agents_usd: number;
  by_agent: Record<string, number>;
}

export interface ActivityStats {
  last_cycle_at: string | null;
  nodes_created_today: number;
}

export interface OverviewStats {
  graph: GraphStats;
  cycles: CycleStats;
  cost: CostStats;
  activity: ActivityStats;
}

export interface TimelineEntry {
  timestamp: string;
  nodes_created: number;
  cycles_run: number;
  cost_usd: number;
}

export interface TimelineResponse {
  timeline: TimelineEntry[];
}

// Config types

export interface AgentConfig {
  provider: string;
  model: string;
  supports_native_search: boolean;
}

export interface LeadAgentConfig {
  provider: string;
  model: string;
  supports_native_search: boolean;
}

export interface SearchProvider {
  name: string;
  priority: number;
  enabled: boolean;
}

export interface Config {
  project_name: string;
  north_star: string;
  workspace_id: string;
  lead_agent: LeadAgentConfig;
  agents: AgentConfig[];
  search_providers: SearchProvider[];
}

// Report types

export interface Report {
  markdown: string;
  node_count: number;
  cycle_count: number;
  avg_confidence: number;
  cost_usd: number;
  duration_seconds: number;
  total_tokens: number;
  generated_at: string;
}

// WebSocket event types

export interface BaseEvent {
  type: string;
  timestamp: string;
  workspace_id: string;
  data: Record<string, any>;
}

export interface CycleStartedEvent extends BaseEvent {
  type: 'cycle.started';
  data: {
    cycle_id: number;
    focus_node_id: string;
    focus_claim: string;
  };
}

export interface CycleStepEvent extends BaseEvent {
  type: 'cycle.step';
  data: {
    cycle_id: number;
    step: string;
    progress_percent: number;
  };
}

export interface CycleCompletedEvent extends BaseEvent {
  type: 'cycle.completed';
  data: {
    cycle_id: number;
    directions_created?: number;
    directions_updated?: number;
    findings_created: number;
    findings_updated: number;
    total_cost_usd: number;
    duration_seconds: number;
  };
}

export interface CycleFailedEvent extends BaseEvent {
  type: 'cycle.failed';
  data: {
    cycle_id: number;
    error_message: string;
    step: string;
  };
}

export interface AgentStartedEvent extends BaseEvent {
  type: 'agent.started';
  data: {
    cycle_id: number;
    agent_name: string;
    prompt_preview: string;
  };
}

export interface AgentCompletedEvent extends BaseEvent {
  type: 'agent.completed';
  data: {
    cycle_id: number;
    agent_name: string;
    findings_count: number;
    cost_usd: number;
    duration_seconds: number;
  };
}

export interface NodeCreatedEvent extends BaseEvent {
  type: 'node.created';
  data: {
    cycle_id: number;
    node_id: string;
    parent_id: string | null;
    claim: string;
    confidence: number;
    node_type: string | null;
  };
}

export interface NodeUpdatedEvent extends BaseEvent {
  type: 'node.updated';
  data: {
    cycle_id: number;
    node_id: string;
    old_confidence: number;
    new_confidence: number;
    evidence_added: number;
  };
}

export interface SynthesisStartedEvent extends BaseEvent {
  type: 'synthesis.started';
  data: {
    cycle_id: number;
    agent_count: number;
  };
}

export interface SynthesisCompletedEvent extends BaseEvent {
  type: 'synthesis.completed';
  data: {
    cycle_id: number;
    consensus_count: number;
    divergent_count: number;
  };
}

export type WinterFoxEvent =
  | CycleStartedEvent
  | CycleStepEvent
  | CycleCompletedEvent
  | CycleFailedEvent
  | AgentStartedEvent
  | AgentCompletedEvent
  | NodeCreatedEvent
  | NodeUpdatedEvent
  | SynthesisStartedEvent
  | SynthesisCompletedEvent;
