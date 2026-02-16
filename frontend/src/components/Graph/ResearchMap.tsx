import React, { useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  Position,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node,
  type NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useGraphStore } from '../../stores/graphStore';
import type { NodeTreeItem } from '../../types/api';
import BubbleMapNode from './BubbleMapNode';

type BubbleNodeData = {
  id: string;
  claim: string;
  description: string | null;
  confidence: number;
  importance: number;
  nodeType: string | null;
  status: 'active' | 'archived' | 'merged' | null;
  matched: boolean;
  selected: boolean;
  focused: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
};

type FlattenedItem = {
  node: NodeTreeItem;
  depth: number;
  y: number;
  parentId: string | null;
};

type LeafPath = NodeTreeItem[];
type ViewMode = 'graph' | 'paths';

const nodeTypes: NodeTypes = {
  bubble: BubbleMapNode,
};

const DEPTH_GAP = 340;
const INTRA_CLUSTER_GAP = 124;
const INTER_CLUSTER_GAP = 142;
const INTER_ROOT_CLUSTER_GAP = 220;

function flattenTree(roots: NodeTreeItem[]): FlattenedItem[] {
  const out: FlattenedItem[] = [];
  let cursorY = 0;

  const walk = (node: NodeTreeItem, depth: number, parentId: string | null): number => {
    const entry: FlattenedItem = { node, depth, y: 0, parentId };
    out.push(entry);

    if (node.children.length === 0) {
      entry.y = cursorY;
      cursorY += INTRA_CLUSTER_GAP;
      return entry.y;
    }

    const childYs: number[] = [];
    node.children.forEach((child, index) => {
      childYs.push(walk(child, depth + 1, node.id));
      if (index < node.children.length - 1) {
        cursorY += INTER_CLUSTER_GAP;
      }
    });

    entry.y = (childYs[0] + childYs[childYs.length - 1]) / 2;
    return entry.y;
  };

  roots.forEach((root, index) => {
    walk(root, 0, null);
    if (index < roots.length - 1) {
      cursorY += INTER_ROOT_CLUSTER_GAP;
    }
  });

  if (out.length === 0) return out;
  const minY = Math.min(...out.map((item) => item.y));
  const maxY = Math.max(...out.map((item) => item.y));
  const centerY = (minY + maxY) / 2;
  return out.map((item) => ({ ...item, y: item.y - centerY }));
}

function buildParentMap(flat: FlattenedItem[]): Record<string, string | null> {
  const parents: Record<string, string | null> = {};
  for (const item of flat) {
    parents[item.node.id] = item.parentId;
  }
  return parents;
}

function buildUpstreamSet(
  selectedNodeId: string | null,
  parentMap: Record<string, string | null>
): Set<string> {
  const upstream = new Set<string>();
  if (!selectedNodeId) return upstream;

  let current: string | null = selectedNodeId;
  while (current) {
    upstream.add(current);
    current = parentMap[current] ?? null;
  }
  return upstream;
}

function buildLeafPaths(roots: NodeTreeItem[]): LeafPath[] {
  const rows: LeafPath[] = [];

  const walk = (node: NodeTreeItem, path: NodeTreeItem[]) => {
    const next = [...path, node];
    if (node.children.length === 0) {
      rows.push(next);
      return;
    }

    node.children.forEach((child) => walk(child, next));
  };

  roots.forEach((root) => walk(root, []));
  return rows;
}

function getConfidenceColor(confidence: number): string {
  if (confidence < 0.35) return 'text-red-600';
  if (confidence < 0.55) return 'text-orange-600';
  if (confidence < 0.75) return 'text-amber-600';
  if (confidence < 0.9) return 'text-lime-600';
  return 'text-green-600';
}

const ResearchMapCanvas: React.FC = () => {
  const tree = useGraphStore((s) => s.tree);
  const treeLoading = useGraphStore((s) => s.treeLoading);
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const selectNode = useGraphStore((s) => s.selectNode);
  const [query, setQuery] = useState('');
  const [minConfidence, setMinConfidence] = useState(0);
  const [focusMode, setFocusMode] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('paths');
  const { fitView, setCenter, getZoom } = useReactFlow();

  const queryLower = query.trim().toLowerCase();

  const computed = useMemo(() => {
    const flat = flattenTree(tree);
    const parentMap = buildParentMap(flat);
    const upstreamSet = buildUpstreamSet(selectedNodeId, parentMap);

    const nodes: Node<BubbleNodeData>[] = flat
      .filter(({ node }) => node.confidence >= minConfidence / 100)
      .map(({ node, depth, y }) => {
        const haystack = `${node.claim} ${node.description ?? ''}`.toLowerCase();
        const matchesSearch = queryLower.length === 0 || haystack.includes(queryLower);
        const focused = selectedNodeId ? upstreamSet.has(node.id) : true;
        const dimmed = !matchesSearch || (focusMode && selectedNodeId ? !focused : false);

        return {
          id: node.id,
          type: 'bubble',
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          data: {
            id: node.id,
            claim: node.claim,
            description: node.description,
            confidence: node.confidence,
            importance: node.importance,
            nodeType: node.node_type,
            status: node.status ?? 'active',
            matched: queryLower.length > 0 && matchesSearch,
            selected: selectedNodeId === node.id,
            focused,
            dimmed,
            onSelect: selectNode,
          },
          position: { x: depth * DEPTH_GAP, y },
        };
      });

    const visibleNodeIds = new Set(nodes.map((n) => n.id));

    const edges: Edge[] = flat
      .filter((item) => item.parentId && visibleNodeIds.has(item.node.id) && visibleNodeIds.has(item.parentId))
      .map((item) => {
        const isFocusedEdge =
          !!selectedNodeId &&
          upstreamSet.has(item.node.id) &&
          upstreamSet.has(item.parentId as string) &&
          parentMap[item.node.id] === item.parentId;
        return {
          id: `${item.parentId}-${item.node.id}`,
          source: item.parentId as string,
          target: item.node.id,
          type: 'smoothstep',
          animated: false,
          style: {
            stroke: isFocusedEdge ? '#334155' : '#94a3b8',
            strokeWidth: isFocusedEdge ? 2.2 : 1.4,
            opacity: isFocusedEdge ? 0.95 : 0.45,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isFocusedEdge ? '#334155' : '#94a3b8',
            width: 12,
            height: 12,
          },
        };
      });

    return { nodes, edges };
  }, [tree, selectedNodeId, selectNode, queryLower, minConfidence, focusMode]);

  const leafPathRows = useMemo(() => {
    const rows = buildLeafPaths(tree).filter((path) => {
      if (path.length === 0) return false;

      const leaf = path[path.length - 1];
      if (leaf.confidence < minConfidence / 100) return false;

      if (queryLower.length === 0) return true;
      return path.some((node) => `${node.claim} ${node.description ?? ''}`.toLowerCase().includes(queryLower));
    });

    const maxDepth = rows.reduce((max, path) => Math.max(max, path.length), 0);
    return { rows, maxDepth };
  }, [tree, minConfidence, queryLower]);

  const [nodes, setNodes, onNodesChange] = useNodesState<BubbleNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    setNodes(computed.nodes);
    setEdges(computed.edges);
  }, [computed.nodes, computed.edges, setNodes, setEdges]);

  useEffect(() => {
    if (viewMode !== 'graph' || !selectedNodeId || computed.nodes.length === 0) return;
    const target = computed.nodes.find((n) => n.id === selectedNodeId);
    if (!target) return;
    const zoom = Math.max(getZoom(), 0.72);
    setCenter(target.position.x + 150, target.position.y + 30, { duration: 220, zoom });
  }, [selectedNodeId, computed.nodes, setCenter, getZoom, viewMode]);

  if (treeLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading research map...</p>
      </div>
    );
  }

  return (
    <div className="h-full w-full overflow-hidden rounded-xl border bg-background">
      <div className="flex items-center justify-between border-b bg-card px-3 py-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Research Map</p>
          <p className="text-[11px] text-muted-foreground">
            {viewMode === 'graph' ? `${nodes.length} nodes` : `${leafPathRows.rows.length} root→leaf paths`}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-md border p-0.5">
            <Button
              size="sm"
              variant={viewMode === 'graph' ? 'default' : 'ghost'}
              onClick={() => setViewMode('graph')}
              className="h-7 px-2 text-xs"
            >
              Map
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'paths' ? 'default' : 'ghost'}
              onClick={() => setViewMode('paths')}
              className="h-7 px-2 text-xs"
            >
              Leaf Paths
            </Button>
          </div>
          <div className="relative w-56">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search nodes..."
              className="w-full rounded-md border bg-background py-2 pl-8 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <div className="flex items-center gap-2 rounded-md border px-2 py-1">
            <span className="text-[11px] text-muted-foreground">Min conf</span>
            <input
              type="range"
              min={0}
              max={90}
              step={5}
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="w-20"
            />
            <span className="w-8 text-right text-[11px] tabular-nums text-muted-foreground">{minConfidence}%</span>
          </div>
          {viewMode === 'graph' && (
            <>
              <Button size="sm" variant={focusMode ? 'default' : 'outline'} onClick={() => setFocusMode((v) => !v)}>
                Focus
              </Button>
              <Button size="sm" variant="outline" onClick={() => fitView({ padding: 0.22, duration: 250 })}>
                Fit
              </Button>
            </>
          )}
        </div>
      </div>

      {viewMode === 'graph' ? (
        <div className="h-[calc(100%-57px)]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            fitViewOptions={{ padding: 0.22 }}
            minZoom={0.3}
            maxZoom={1.6}
            nodesDraggable={false}
            elementsSelectable
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#e2e8f0" gap={24} size={1} />
            <MiniMap
              pannable
              zoomable
              nodeColor={(n) => (n.id === selectedNodeId ? '#06b6d4' : '#94a3b8')}
              nodeStrokeWidth={2}
            />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      ) : (
        <div className="h-[calc(100%-57px)] overflow-auto">
          {leafPathRows.rows.length === 0 ? (
            <div className="flex h-full items-center justify-center p-6">
              <p className="text-sm text-muted-foreground">No root-to-leaf paths match the current filters.</p>
            </div>
          ) : (
            <div className="min-w-[900px] p-3">
              <div
                className="grid gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                style={{ gridTemplateColumns: `40px repeat(${leafPathRows.maxDepth}, minmax(220px, 1fr))` }}
              >
                <div className="px-1">#</div>
                {Array.from({ length: leafPathRows.maxDepth }).map((_, idx) => (
                  <div key={idx} className="px-1">
                    Depth {idx}
                  </div>
                ))}
              </div>

              <div className="mt-2 space-y-2">
                {leafPathRows.rows.map((path, rowIdx) => (
                  <div
                    key={path.map((node) => node.id).join('-')}
                    className="grid items-stretch gap-2"
                    style={{ gridTemplateColumns: `40px repeat(${leafPathRows.maxDepth}, minmax(220px, 1fr))` }}
                  >
                    <div className="flex items-center justify-center rounded-md border bg-card text-xs tabular-nums text-muted-foreground">
                      {rowIdx + 1}
                    </div>
                    {Array.from({ length: leafPathRows.maxDepth }).map((_, colIdx) => {
                      const node = path[colIdx];
                      if (!node) {
                        return <div key={colIdx} className="rounded-md border border-dashed bg-muted/30" />;
                      }

                      const isSelected = selectedNodeId === node.id;
                      const isInSelectedPath = selectedNodeId ? path.some((item) => item.id === selectedNodeId) : false;

                      return (
                        <button
                          key={node.id}
                          onClick={() => selectNode(node.id)}
                          className={`relative rounded-md border p-2 text-left transition-colors hover:bg-muted/50 ${
                            isSelected
                              ? 'border-cyan-500 bg-cyan-500/10'
                              : isInSelectedPath
                                ? 'border-slate-400 bg-slate-100/60'
                                : 'bg-card'
                          }`}
                          title={node.claim}
                        >
                          <p className="line-clamp-2 text-sm leading-snug">{node.claim}</p>
                          <div className="mt-1 flex items-center justify-between gap-2">
                            <span className={`text-[11px] font-semibold ${getConfidenceColor(node.confidence)}`}>
                              {(node.confidence * 100).toFixed(0)}%
                            </span>
                            {colIdx < path.length - 1 && (
                              <span className="text-[11px] font-semibold text-muted-foreground">→</span>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ResearchMap: React.FC = () => (
  <ReactFlowProvider>
    <ResearchMapCanvas />
  </ReactFlowProvider>
);

export default ResearchMap;
