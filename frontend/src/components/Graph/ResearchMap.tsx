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
  selected: boolean;
  focused: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
};

type FlattenedItem = {
  node: NodeTreeItem;
  depth: number;
  order: number;
  parentId: string | null;
};

const nodeTypes: NodeTypes = {
  bubble: BubbleMapNode,
};

const DEPTH_GAP = 360;
const ROW_GAP = 186;

function flattenTree(roots: NodeTreeItem[]): FlattenedItem[] {
  const rowsByDepth: Record<number, number> = {};
  const out: FlattenedItem[] = [];

  const walk = (node: NodeTreeItem, depth: number, parentId: string | null) => {
    rowsByDepth[depth] = (rowsByDepth[depth] ?? 0) + 1;
    const order = rowsByDepth[depth] - 1;
    out.push({ node, depth, order, parentId });
    node.children.forEach((child) => walk(child, depth + 1, node.id));
  };

  roots.forEach((root) => walk(root, 0, null));
  return out;
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

const ResearchMapCanvas: React.FC = () => {
  const tree = useGraphStore((s) => s.tree);
  const treeLoading = useGraphStore((s) => s.treeLoading);
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const selectNode = useGraphStore((s) => s.selectNode);
  const [query, setQuery] = useState('');
  const [minConfidence, setMinConfidence] = useState(0);
  const [focusMode, setFocusMode] = useState(true);
  const { fitView, setCenter, getZoom } = useReactFlow();

  const queryLower = query.trim().toLowerCase();

  const computed = useMemo(() => {
    const flat = flattenTree(tree);
    const parentMap = buildParentMap(flat);
    const upstreamSet = buildUpstreamSet(selectedNodeId, parentMap);

    const depthCounts: Record<number, number> = {};
    flat.forEach((item) => {
      depthCounts[item.depth] = (depthCounts[item.depth] ?? 0) + 1;
    });

    const nodes: Node<BubbleNodeData>[] = flat
      .filter(({ node }) => node.confidence >= minConfidence / 100)
      .map(({ node, depth, order }) => {
        const count = depthCounts[depth] ?? 1;
        const y = (order - (count - 1) / 2) * ROW_GAP;
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

  const [nodes, setNodes, onNodesChange] = useNodesState<BubbleNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    setNodes(computed.nodes);
    setEdges(computed.edges);
  }, [computed.nodes, computed.edges, setNodes, setEdges]);

  useEffect(() => {
    if (!selectedNodeId || computed.nodes.length === 0) return;
    const target = computed.nodes.find((n) => n.id === selectedNodeId);
    if (!target) return;
    const zoom = Math.max(getZoom(), 0.72);
    setCenter(target.position.x + 150, target.position.y + 30, { duration: 220, zoom });
  }, [selectedNodeId, computed.nodes, setCenter, getZoom]);

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
          <p className="text-[11px] text-muted-foreground">{nodes.length} nodes</p>
        </div>

        <div className="flex items-center gap-2">
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
          <Button size="sm" variant={focusMode ? 'default' : 'outline'} onClick={() => setFocusMode((v) => !v)}>
            Focus
          </Button>
          <Button size="sm" variant="outline" onClick={() => fitView({ padding: 0.22, duration: 250 })}>
            Fit
          </Button>
        </div>
      </div>

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
    </div>
  );
};

const ResearchMap: React.FC = () => (
  <ReactFlowProvider>
    <ResearchMapCanvas />
  </ReactFlowProvider>
);

export default ResearchMap;
