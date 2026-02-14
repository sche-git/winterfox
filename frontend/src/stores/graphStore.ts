/**
 * Graph state store using Zustand.
 */

import { create } from 'zustand';
import type { Node, GraphSummary, NodeTreeItem } from '../types/api';

interface GraphState {
  // State
  summary: GraphSummary | null;
  nodes: Map<string, Node>;
  selectedNodeId: string | null;
  tree: NodeTreeItem[];
  loading: boolean;
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
}

export const useGraphStore = create<GraphState>((set) => ({
  // Initial state
  summary: null,
  nodes: new Map(),
  selectedNodeId: null,
  tree: [],
  loading: false,
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

  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

  setTree: (tree) => set({ tree }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  clear: () =>
    set({
      summary: null,
      nodes: new Map(),
      selectedNodeId: null,
      tree: [],
      loading: false,
      error: null,
    }),
}));
