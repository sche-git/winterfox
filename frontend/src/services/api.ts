/**
 * REST API client for winterfox backend.
 */

import axios, { AxiosInstance } from 'axios';
import type {
  GraphSummary,
  NodesListResponse,
  Node,
  GraphTree,
  SearchResponse,
  CyclesListResponse,
  CycleDetail,
  ActiveCycle,
  RunCycleRequest,
  RunCycleResponse,
  OverviewStats,
  TimelineResponse,
  Config,
  Report,
} from '../types/api';

class WinterfoxAPI {
  private client: AxiosInstance;

  constructor(baseURL: string = 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Graph endpoints

  async getGraphSummary(): Promise<GraphSummary> {
    const response = await this.client.get<GraphSummary>('/api/graph/summary');
    return response.data;
  }

  async getNodes(params?: {
    limit?: number;
    offset?: number;
    status?: string;
    min_confidence?: number;
    max_depth?: number;
    sort?: string;
  }): Promise<NodesListResponse> {
    const response = await this.client.get<NodesListResponse>('/api/graph/nodes', {
      params,
    });
    return response.data;
  }

  async getNode(nodeId: string): Promise<Node> {
    const response = await this.client.get<Node>(`/api/graph/nodes/${nodeId}`);
    return response.data;
  }

  async getTree(maxDepth: number = 3): Promise<GraphTree> {
    const response = await this.client.get<GraphTree>('/api/graph/tree', {
      params: { max_depth: maxDepth },
    });
    return response.data;
  }

  async searchNodes(query: string, limit: number = 10): Promise<SearchResponse> {
    const response = await this.client.get<SearchResponse>('/api/graph/search', {
      params: { q: query, limit },
    });
    return response.data;
  }

  // Cycle endpoints

  async getCycles(limit: number = 20, offset: number = 0): Promise<CyclesListResponse> {
    const response = await this.client.get<CyclesListResponse>('/api/cycles', {
      params: { limit, offset },
    });
    return {
      ...response.data,
      cycles: response.data.cycles.map((cycle) => ({
        ...cycle,
        lead_llm_cost_usd: cycle.lead_llm_cost_usd ?? 0,
        research_agents_cost_usd:
          (cycle.research_agents_cost_usd ?? 0) > 0
            ? (cycle.research_agents_cost_usd ?? 0)
            : Math.max(0, (cycle.total_cost_usd ?? 0) - (cycle.lead_llm_cost_usd ?? 0)),
        directions_count: cycle.directions_count ?? cycle.findings_count ?? 0,
      })),
    };
  }

  async getCycle(cycleId: number): Promise<CycleDetail> {
    const response = await this.client.get<CycleDetail>(`/api/cycles/${cycleId}`);
    const detail = response.data;
    const detailAny = detail as CycleDetail & {
      context_used?: unknown;
      context_snapshot?: unknown;
      researchContext?: unknown;
    };

    // Accept current and legacy context field shapes.
    const rawContext =
      detailAny.research_context ??
      detailAny.context_used ??
      detailAny.context_snapshot ??
      detailAny.researchContext ??
      null;

    const normalizedContext =
      typeof rawContext === 'string'
        ? (rawContext.trim() || null)
        : rawContext && typeof rawContext === 'object'
          ? ([
              (rawContext as Record<string, unknown>).focused_view,
              (rawContext as Record<string, unknown>).system_prompt,
              (rawContext as Record<string, unknown>).user_prompt,
            ]
              .filter((part): part is string => typeof part === 'string' && part.trim().length > 0)
              .join('\n\n') || null)
          : null;

    return {
      ...detail,
      research_context: normalizedContext,
      directions_created: detail.directions_created ?? detail.findings_created ?? 0,
      directions_updated: detail.directions_updated ?? detail.findings_updated ?? 0,
      directions_skipped: detail.directions_skipped ?? detail.findings_skipped ?? 0,
      consensus_directions: detail.consensus_directions ?? detail.consensus_findings ?? [],
      direction_node_refs: detail.direction_node_refs ?? [],
      lead_llm_cost_usd: detail.lead_llm_cost_usd ?? 0,
      research_agents_cost_usd:
        (detail.research_agents_cost_usd ?? 0) > 0
          ? (detail.research_agents_cost_usd ?? 0)
          : Math.max(0, (detail.total_cost_usd ?? 0) - (detail.lead_llm_cost_usd ?? 0)),
    };
  }

  async getActiveCycle(): Promise<ActiveCycle> {
    const response = await this.client.get<ActiveCycle>('/api/cycles/active');
    return response.data;
  }

  async runCycle(payload: RunCycleRequest = {}): Promise<RunCycleResponse> {
    const response = await this.client.post<RunCycleResponse>('/api/cycles', payload);
    return response.data;
  }

  // Stats endpoints

  async getOverviewStats(): Promise<OverviewStats> {
    const response = await this.client.get<OverviewStats>('/api/stats/overview');
    const stats = response.data;
    return {
      ...stats,
      graph: {
        ...stats.graph,
        direction_count: stats.graph.direction_count ?? stats.graph.total_nodes ?? 0,
      },
      cost: {
        ...stats.cost,
        lead_llm_usd: stats.cost.lead_llm_usd ?? 0,
        research_agents_usd: stats.cost.research_agents_usd ?? 0,
      },
    };
  }

  async getTimeline(period: string = 'day', limit: number = 30): Promise<TimelineResponse> {
    const response = await this.client.get<TimelineResponse>('/api/stats/timeline', {
      params: { period, limit },
    });
    return response.data;
  }

  // Config endpoint

  async getConfig(): Promise<Config> {
    const response = await this.client.get<Config>('/api/config');
    const cfg = response.data;
    return {
      ...cfg,
      lead_agent: cfg.lead_agent ?? (cfg.agents[0] ? {
        provider: cfg.agents[0].provider,
        model: cfg.agents[0].model,
        supports_native_search: cfg.agents[0].supports_native_search,
      } : {
        provider: '',
        model: '',
        supports_native_search: false,
      }),
      search_instructions: cfg.search_instructions ?? null,
      context_documents: cfg.context_documents ?? [],
    };
  }

  // Report endpoints

  async generateReport(): Promise<Report> {
    const response = await this.client.post<Report>('/api/report/generate', {}, {
      timeout: 120000,
    });
    return response.data;
  }

  async getLatestReport(): Promise<Report | null> {
    try {
      const response = await this.client.get<Report>('/api/report/latest');
      return response.data;
    } catch (err: any) {
      if (err.response?.status === 404) return null;
      throw err;
    }
  }
}

// Export singleton instance
export const api = new WinterfoxAPI();
export default api;
