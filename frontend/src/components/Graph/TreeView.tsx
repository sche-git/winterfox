/**
 * Tree view with search and recursive collapsible nodes.
 */

import React, { useState, useEffect } from 'react';
import { Search, GitFork } from 'lucide-react';
import { useGraphStore } from '../../stores/graphStore';
import { api } from '../../services/api';
import { ScrollArea } from '@/components/ui/scroll-area';
import { NODE_TYPE_CONFIG } from '@/lib/nodeTypes';
import TreeNode from './TreeNode';
import type { NodeTreeItem } from '../../types/api';

const TreeView: React.FC = () => {
  const tree = useGraphStore((s) => s.tree);
  const treeLoading = useGraphStore((s) => s.treeLoading);
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const selectNode = useGraphStore((s) => s.selectNode);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<NodeTreeItem[] | null>(null);

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const response = await api.searchNodes(searchQuery, 20);
        const results: NodeTreeItem[] = response.results.map((r) => ({
          id: r.node_id,
          claim: r.claim,
          description: null,
          status: 'active',
          confidence: r.relevance_score,
          importance: 0.5,
          node_type: null,
          children: [],
        }));
        setSearchResults(results);
      } catch {
        setSearchResults(null);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const displayNodes = searchResults ?? tree;

  // Count total nodes in tree (recursive)
  const countNodes = (nodes: NodeTreeItem[]): number =>
    nodes.reduce((sum, n) => sum + 1 + countNodes(n.children), 0);

  if (treeLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading tree...</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header + Search */}
      <div className="border-b p-3 space-y-2 shrink-0">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Research Map
          </span>
          <span className="text-xs tabular-nums text-muted-foreground">
            {countNodes(tree)} nodes
          </span>
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border bg-background py-2 pl-8 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        {/* Direction legend */}
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          <div className="flex items-center gap-1">
            <NODE_TYPE_CONFIG.direction.icon className={`h-3 w-3 ${NODE_TYPE_CONFIG.direction.color}`} />
            <span className="text-[10px] text-muted-foreground">{NODE_TYPE_CONFIG.direction.label}</span>
          </div>
        </div>
      </div>

      {/* Tree */}
      <ScrollArea className="flex-1">
        <div className="py-1">
          {displayNodes.length === 0 ? (
            <div className="py-8 text-center">
              <GitFork className="mx-auto h-6 w-6 text-muted-foreground" />
              <p className="mt-2 text-sm text-muted-foreground">
                {searchQuery ? 'No results found' : 'No nodes yet'}
              </p>
            </div>
          ) : (
            displayNodes.map((node, i) => (
              <TreeNode
                key={node.id}
                node={node}
                depth={0}
                selectedId={selectedNodeId}
                onSelect={selectNode}
                isLast={i === displayNodes.length - 1}
                lineFlags={[]}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
};

export default TreeView;
