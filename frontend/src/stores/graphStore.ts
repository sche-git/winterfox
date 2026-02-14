/**
 * Graph state store using Zustand.
 */

import { create } from 'zustand';
import type { Node, GraphSummary, NodeTreeItem } from '../types/api';
import { api } from '../services/api';

interface GraphState {
  // State
  summary: GraphSummary | null;
  nodes: Map<string, Node>;
  selectedNodeId: string | null;
  selectedNode: Node | null;
  tree: NodeTreeItem[];
  loading: boolean;
  treeLoading: boolean;
  nodeLoading: boolean;
  error: string | null;

  // Actions
  setSummary: (summary: GraphSummary) => void;
  setNodes: (nodes: Node[]) => void;
  addNode: (node: Node) => void;
  updateNode: (nodeId: string, updates: Partial<Node>) => void;
  selectNode: (nodeId: string | null) => void;
  setTree: (tree: NodeTreeItem[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clear: () => void;

  // Async actions
  loadTree: () => Promise<void>;
  loadNodeDetail: (nodeId: string) => Promise<void>;
}

export const useGraphStore = create<GraphState>((set, get) => ({
  // Initial state
  summary: null,
  nodes: new Map(),
  selectedNodeId: null,
  selectedNode: null,
  tree: [],
  loading: false,
  treeLoading: false,
  nodeLoading: false,
  error: null,

  // Actions
  setSummary: (summary) => set({ summary }),

  setNodes: (nodes) =>
    set((state) => {
      const newMap = new Map(state.nodes);
      nodes.forEach((node) => newMap.set(node.id, node));
      return { nodes: newMap };
    }),

  addNode: (node) =>
    set((state) => {
      const newMap = new Map(state.nodes);
      newMap.set(node.id, node);
      return { nodes: newMap };
    }),

  updateNode: (nodeId, updates) =>
    set((state) => {
      const existing = state.nodes.get(nodeId);
      if (!existing) return state;

      const updated = { ...existing, ...updates };
      const newMap = new Map(state.nodes);
      newMap.set(nodeId, updated);
      return { nodes: newMap };
    }),

  selectNode: (nodeId) => {
    set({ selectedNodeId: nodeId });
    if (nodeId) {
      get().loadNodeDetail(nodeId);
    } else {
      set({ selectedNode: null });
    }
  },

  setTree: (tree) => set({ tree }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  clear: () =>
    set({
      summary: null,
      nodes: new Map(),
      selectedNodeId: null,
      selectedNode: null,
      tree: [],
      loading: false,
      treeLoading: false,
      nodeLoading: false,
      error: null,
    }),

  // Async actions
  loadTree: async () => {
    set({ treeLoading: true });
    try {
      const response = await api.getTree(10);
      set({ tree: response.roots, treeLoading: false });
    } catch (error) {
      console.error('Failed to load tree:', error);
      set({ treeLoading: false });
    }
  },

  loadNodeDetail: async (nodeId: string) => {
    set({ nodeLoading: true });
    try {
      const node = await api.getNode(nodeId);
      set((state) => {
        const newMap = new Map(state.nodes);
        newMap.set(node.id, node);
        return { selectedNode: node, nodes: newMap, nodeLoading: false };
      });
    } catch (error) {
      console.error('Failed to load node:', error);
      set({ nodeLoading: false });
    }
  },
}));
