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
  OverviewStats,
  TimelineResponse,
  Config,
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
    return response.data;
  }

  async getCycle(cycleId: number): Promise<CycleDetail> {
    const response = await this.client.get<CycleDetail>(`/api/cycles/${cycleId}`);
    return response.data;
  }

  async getActiveCycle(): Promise<ActiveCycle> {
    const response = await this.client.get<ActiveCycle>('/api/cycles/active');
    return response.data;
  }

  // Stats endpoints

  async getOverviewStats(): Promise<OverviewStats> {
    const response = await this.client.get<OverviewStats>('/api/stats/overview');
    return response.data;
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
    return response.data;
  }
}

// Export singleton instance
export const api = new WinterfoxAPI();
export default api;
