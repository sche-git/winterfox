/**
 * Node detail panel with type badge, metrics, evidence, support/oppose grouping,
 * and child nodes.
 */

import React, { useEffect, useState, useMemo } from 'react';
import { useGraphStore } from '../../stores/graphStore';
import { api } from '../../services/api';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { getNodeTypeConfig } from '@/lib/nodeTypes';
import type { Node } from '../../types/api';
import {
  FileText,
  ExternalLink,
  ShieldCheck,
  ArrowUp,
  ChevronRight,
  Loader2,
} from 'lucide-react';

const NodeDetail: React.FC = () => {
  const selectedNode = useGraphStore((s) => s.selectedNode);
  const nodeLoading = useGraphStore((s) => s.nodeLoading);
  const selectNode = useGraphStore((s) => s.selectNode);
  const nodes = useGraphStore((s) => s.nodes);
  const [childNodes, setChildNodes] = useState<Node[]>([]);
  const [parentNode, setParentNode] = useState<Node | null>(null);

  // Load child and parent details when selection changes
  useEffect(() => {
    if (!selectedNode) {
      setChildNodes([]);
      setParentNode(null);
      return;
    }

    // Load parent
    if (selectedNode.parent_id) {
      const cached = nodes.get(selectedNode.parent_id);
      if (cached) {
        setParentNode(cached);
      } else {
        api.getNode(selectedNode.parent_id).then(setParentNode).catch(() => setParentNode(null));
      }
    } else {
      setParentNode(null);
    }

    // Load children
    if (selectedNode.children_ids.length > 0) {
      Promise.all(
        selectedNode.children_ids.map(async (id) => {
          const cached = nodes.get(id);
          if (cached) return cached;
          try {
            return await api.getNode(id);
          } catch {
            return null;
          }
        })
      ).then((results) => setChildNodes(results.filter((n): n is Node => n !== null)));
    } else {
      setChildNodes([]);
    }
  }, [selectedNode?.id]);

  // Group children by type for hypothesis nodes
  const groupedChildren = useMemo(() => {
    if (!selectedNode || selectedNode.node_type !== 'hypothesis') return null;

    const supporting = childNodes.filter((c) => c.node_type === 'supporting');
    const opposing = childNodes.filter((c) => c.node_type === 'opposing');
    const other = childNodes.filter((c) => c.node_type !== 'supporting' && c.node_type !== 'opposing');

    // Only group if there are typed children
    if (supporting.length === 0 && opposing.length === 0) return null;
    return { supporting, opposing, other };
  }, [childNodes, selectedNode?.node_type]);

  // Calculate support/oppose ratio for hypothesis nodes
  const supportOpposeRatio = useMemo(() => {
    if (!groupedChildren) return null;
    const { supporting, opposing } = groupedChildren;
    if (supporting.length === 0 && opposing.length === 0) return null;

    const supportAvg = supporting.length > 0
      ? supporting.reduce((sum, c) => sum + c.confidence, 0) / supporting.length
      : 0;
    const opposeAvg = opposing.length > 0
      ? opposing.reduce((sum, c) => sum + c.confidence, 0) / opposing.length
      : 0;
    const total = supportAvg + opposeAvg;
    const supportPct = total > 0 ? (supportAvg / total) * 100 : 50;

    return { supportPct, supportAvg, opposeAvg, supportCount: supporting.length, opposeCount: opposing.length };
  }, [groupedChildren]);

  if (nodeLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!selectedNode) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <FileText className="mx-auto h-8 w-8 text-muted-foreground" />
          <p className="mt-3 text-sm text-muted-foreground">
            Select a node to view details
          </p>
        </div>
      </div>
    );
  }

  const typeConfig = getNodeTypeConfig(selectedNode.node_type);

  return (
    <div className="h-full overflow-auto">
      <div className="p-6">
        {/* Parent breadcrumb */}
        {parentNode && (
          <button
            onClick={() => selectNode(parentNode.id)}
            className="mb-3 flex items-center gap-1.5 rounded px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <ArrowUp className="h-3 w-3" />
            <span className="truncate max-w-[300px]">{parentNode.claim}</span>
          </button>
        )}

        {/* Claim */}
        <p className="text-base leading-relaxed">{selectedNode.claim}</p>

        {/* Type badge */}
        {typeConfig && (
          <div className="mt-2">
            <Badge variant="outline" className={`text-[11px] ${typeConfig.bg}`}>
              <typeConfig.icon className="mr-1 h-3 w-3" />
              {typeConfig.label}
            </Badge>
          </div>
        )}

        {/* Support/Oppose ratio bar for hypotheses */}
        {supportOpposeRatio && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
              <span className="text-emerald-400">{supportOpposeRatio.supportCount} supporting</span>
              <span className="text-rose-400">{supportOpposeRatio.opposeCount} opposing</span>
            </div>
            <div className="flex h-2 overflow-hidden rounded-full bg-border">
              <div
                className="h-full bg-emerald-400 transition-all"
                style={{ width: `${supportOpposeRatio.supportPct}%` }}
              />
              <div
                className="h-full bg-rose-400 transition-all"
                style={{ width: `${100 - supportOpposeRatio.supportPct}%` }}
              />
            </div>
          </div>
        )}

        {/* Metrics */}
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Confidence</span>
              <span className="tabular-nums font-medium">
                {(selectedNode.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <Progress value={selectedNode.confidence * 100} className="mt-1.5 h-1.5" />
          </div>
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Importance</span>
              <span className="tabular-nums font-medium">
                {(selectedNode.importance * 100).toFixed(0)}%
              </span>
            </div>
            <Progress value={selectedNode.importance * 100} className="mt-1.5 h-1.5" />
          </div>
        </div>

        {/* Meta badges */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          <Badge variant="outline" className="text-[11px]">
            Depth {selectedNode.depth}
          </Badge>
          <Badge variant="outline" className="text-[11px]">
            {selectedNode.status}
          </Badge>
        </div>

        {/* Evidence */}
        {selectedNode.evidence.length > 0 && (
          <>
            <Separator className="my-5" />
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Evidence ({selectedNode.evidence.length})
            </p>
            <div className="mt-3 space-y-3">
              {selectedNode.evidence.map((e, i) => (
                <div key={i} className="rounded-md border p-3">
                  <p className="text-sm leading-relaxed">{e.text}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {e.source && (
                      <a
                        href={e.source.startsWith('http') ? e.source : undefined}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink className="h-3 w-3" />
                        {e.source.length > 50 ? e.source.substring(0, 50) + '...' : e.source}
                      </a>
                    )}
                    {e.verified_by.length > 0 && (
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <ShieldCheck className="h-3 w-3" />
                        {e.verified_by.join(', ')}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Child nodes — grouped by type for hypothesis, flat otherwise */}
        {childNodes.length > 0 && (
          <>
            <Separator className="my-5" />
            {groupedChildren ? (
              <>
                {/* Supporting children */}
                {groupedChildren.supporting.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-emerald-400">
                      Supporting Evidence ({groupedChildren.supporting.length})
                    </p>
                    <div className="mt-2 space-y-1">
                      {groupedChildren.supporting.map((child) => (
                        <ChildNodeRow key={child.id} child={child} onSelect={selectNode} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Opposing children */}
                {groupedChildren.opposing.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-rose-400">
                      Opposing Evidence ({groupedChildren.opposing.length})
                    </p>
                    <div className="mt-2 space-y-1">
                      {groupedChildren.opposing.map((child) => (
                        <ChildNodeRow key={child.id} child={child} onSelect={selectNode} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Other (untyped) children */}
                {groupedChildren.other.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Other ({groupedChildren.other.length})
                    </p>
                    <div className="mt-2 space-y-1">
                      {groupedChildren.other.map((child) => (
                        <ChildNodeRow key={child.id} child={child} onSelect={selectNode} />
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Child Nodes ({childNodes.length})
                </p>
                <div className="mt-3 space-y-1">
                  {childNodes.map((child) => (
                    <ChildNodeRow key={child.id} child={child} onSelect={selectNode} />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};

/** Reusable child node row with type indicator */
function ChildNodeRow({ child, onSelect }: { child: Node; onSelect: (id: string) => void }) {
  const typeConfig = getNodeTypeConfig(child.node_type);

  return (
    <button
      onClick={() => onSelect(child.id)}
      className="flex w-full items-center gap-2 rounded px-2.5 py-2 text-left transition-colors hover:bg-muted/60"
    >
      {typeConfig ? (
        <typeConfig.icon className={`h-3 w-3 shrink-0 ${typeConfig.color}`} />
      ) : (
        <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
      )}
      <span className="flex-1 min-w-0 text-sm leading-snug line-clamp-2">
        {child.claim}
      </span>
      <span className={`shrink-0 text-[11px] tabular-nums ${typeConfig ? typeConfig.color : 'text-muted-foreground'}`}>
        {(child.confidence * 100).toFixed(0)}%
      </span>
    </button>
  );
}

export default NodeDetail;
