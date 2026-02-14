/**
 * Overview page - Enhanced stats + recent activity + top findings + type breakdown.
 */

import React, { useEffect, useState } from 'react';
import { useGraphStore } from '../../stores/graphStore';
import { useCycleStore } from '../../stores/cycleStore';
import { useUIStore } from '../../stores/uiStore';
import { api } from '../../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { NODE_TYPE_CONFIG } from '@/lib/nodeTypes';
import {
  CheckCircle2,
  XCircle,
  Clock,
  DollarSign,
  GitFork,
  Target,
  TrendingUp,
} from 'lucide-react';
import type { Node as GraphNode, OverviewStats } from '../../types/api';

const OverviewPage: React.FC = () => {
  const summary = useGraphStore((s) => s.summary);
  const recentCycles = useCycleStore((s) => s.recentCycles);
  const setCurrentPage = useUIStore((s) => s.setCurrentPage);
  const selectNode = useGraphStore((s) => s.selectNode);
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [topNodes, setTopNodes] = useState<GraphNode[]>([]);

  useEffect(() => {
    api.getOverviewStats().then(setStats).catch(console.error);
    api.getNodes({ sort: 'confidence', limit: 5 }).then((r) => setTopNodes(r.nodes)).catch(console.error);
  }, []);

  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  // Type breakdown data
  const hypothesisCount = stats?.graph.hypothesis_count ?? 0;
  const supportingCount = stats?.graph.supporting_count ?? 0;
  const opposingCount = stats?.graph.opposing_count ?? 0;
  const typedTotal = hypothesisCount + supportingCount + opposingCount;
  const hasTypeBreakdown = typedTotal > 0;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold tracking-tight">Overview</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Research progress and key metrics
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <GitFork className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Total Nodes</span>
            </div>
            <div className="mt-2 text-2xl font-semibold tabular-nums">
              {summary?.total_nodes ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Avg Confidence</span>
            </div>
            <div className="mt-2 text-2xl font-semibold tabular-nums">
              {summary ? `${(summary.avg_confidence * 100).toFixed(0)}%` : '0%'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Cycles Run</span>
            </div>
            <div className="mt-2 text-2xl font-semibold tabular-nums">
              {stats?.cycles.total ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Total Cost</span>
            </div>
            <div className="mt-2 text-2xl font-semibold tabular-nums">
              ${stats?.cost.total_usd?.toFixed(2) ?? '0.00'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Knowledge Breakdown */}
      {hasTypeBreakdown && (
        <Card className="mt-8">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Knowledge Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              {([
                ['hypothesis', hypothesisCount],
                ['supporting', supportingCount],
                ['opposing', opposingCount],
              ] as const).map(([type, count]) => {
                const cfg = NODE_TYPE_CONFIG[type];
                return (
                  <div key={type} className="flex items-center gap-2">
                    <cfg.icon className={`h-4 w-4 ${cfg.color}`} />
                    <span className="text-lg font-semibold tabular-nums">{count}</span>
                    <span className="text-xs text-muted-foreground">{cfg.label}</span>
                  </div>
                );
              })}
            </div>
            {/* Stacked bar */}
            <div className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-border">
              {hypothesisCount > 0 && (
                <div
                  className="h-full bg-amber-400 transition-all"
                  style={{ width: `${(hypothesisCount / typedTotal) * 100}%` }}
                  title={`${hypothesisCount} hypotheses`}
                />
              )}
              {supportingCount > 0 && (
                <div
                  className="h-full bg-emerald-400 transition-all"
                  style={{ width: `${(supportingCount / typedTotal) * 100}%` }}
                  title={`${supportingCount} supporting`}
                />
              )}
              {opposingCount > 0 && (
                <div
                  className="h-full bg-rose-400 transition-all"
                  style={{ width: `${(opposingCount / typedTotal) * 100}%` }}
                  title={`${opposingCount} opposing`}
                />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        {/* Recent Cycles */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold">Recent Cycles</CardTitle>
              <button
                onClick={() => setCurrentPage('history')}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                View all
              </button>
            </div>
          </CardHeader>
          <CardContent>
            {recentCycles.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No cycles yet. Run <code className="rounded bg-muted px-1 py-0.5 text-xs">winterfox run -n 1</code>
              </p>
            ) : (
              <div className="divide-y">
                {recentCycles.slice(0, 5).map((cycle) => (
                  <button
                    key={cycle.id}
                    onClick={() => setCurrentPage('history')}
                    className="flex w-full items-center gap-3 py-2.5 text-left transition-colors hover:bg-muted/50 -mx-2 px-2 rounded"
                  >
                    {cycle.status === 'completed' ? (
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    ) : cycle.status === 'failed' ? (
                      <XCircle className="h-3.5 w-3.5 shrink-0 text-destructive" />
                    ) : (
                      <Clock className="h-3.5 w-3.5 shrink-0 text-muted-foreground animate-spin" />
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium">Cycle {cycle.id}</span>
                      <span className="ml-2 text-xs text-muted-foreground">
                        {formatTimeAgo(cycle.started_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>{cycle.findings_count} findings</span>
                      <span className="tabular-nums">${cycle.total_cost_usd.toFixed(3)}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Findings */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold">Top Findings</CardTitle>
              <button
                onClick={() => setCurrentPage('graph')}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Browse graph
              </button>
            </div>
          </CardHeader>
          <CardContent>
            {topNodes.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No findings yet
              </p>
            ) : (
              <div className="divide-y">
                {topNodes.map((node) => {
                  const nodeTypeCfg = node.node_type ? NODE_TYPE_CONFIG[node.node_type as keyof typeof NODE_TYPE_CONFIG] : null;
                  return (
                    <button
                      key={node.id}
                      onClick={() => {
                        selectNode(node.id);
                        setCurrentPage('graph');
                      }}
                      className="flex w-full items-start gap-3 py-2.5 text-left transition-colors hover:bg-muted/50 -mx-2 px-2 rounded"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm leading-snug line-clamp-2">{node.claim}</p>
                        <div className="mt-1 flex items-center gap-2">
                          {nodeTypeCfg && (
                            <span className={`flex items-center gap-1 text-xs ${nodeTypeCfg.color}`}>
                              <nodeTypeCfg.icon className="h-3 w-3" />
                              {nodeTypeCfg.label}
                            </span>
                          )}
                          <span className="text-xs tabular-nums text-muted-foreground">
                            {(node.confidence * 100).toFixed(0)}% confidence
                          </span>
                          {node.evidence.length > 0 && (
                            <span className="text-xs text-muted-foreground">
                              {node.evidence.length} evidence
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Cost Breakdown */}
      {stats && Object.keys(stats.cost.by_agent).length > 0 && (
        <Card className="mt-8">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Cost by Agent</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {Object.entries(stats.cost.by_agent).map(([agent, cost]) => (
                <div key={agent}>
                  <div className="text-xs text-muted-foreground truncate">{agent}</div>
                  <div className="mt-1 text-lg font-semibold tabular-nums">
                    ${cost.toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default OverviewPage;
