/**
 * Main Dashboard component - Sophisticated research console design.
 */

import React from 'react';
import StatsCards from './StatsCards';
import CycleHistory from '../CycleMonitor/CycleHistory';
import EventFeed from '../CycleMonitor/EventFeed';
import { useGraphStore } from '../../stores/graphStore';
import { useCycleStore } from '../../stores/cycleStore';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

const Dashboard: React.FC = () => {
  const summary = useGraphStore((state) => state.summary);
  const loading = useGraphStore((state) => state.loading);
  const error = useGraphStore((state) => state.error);
  const activeCycle = useCycleStore((state) => state.activeCycle);

  if (loading && !summary) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="max-w-md text-center">
          <p className="text-sm font-semibold text-destructive">Error</p>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Winterfox
              </h1>
              <p className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">
                Research Dashboard
              </p>
            </div>
            {activeCycle && activeCycle.status === 'running' && (
              <Badge variant="outline" className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-foreground opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-foreground"></span>
                </span>
                <span className="text-xs">
                  Cycle {activeCycle.cycle_id} Running ({activeCycle.progress_percent}%)
                </span>
              </Badge>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>
        {/* Stats Section */}
        <section className="border-b py-8">
          <div className="container mx-auto px-4">
            <StatsCards />
          </div>
        </section>

        {/* Graph Section */}
        <section className="border-b bg-muted/20 py-16">
          <div className="container mx-auto px-4">
            <div className="mx-auto max-w-4xl">
              {summary && summary.total_nodes === 0 ? (
                <div className="rounded-lg border-2 bg-card p-8 text-center">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Empty Graph
                  </p>
                  <h2 className="mt-2 text-3xl font-bold tracking-tight">
                    No Research Data Yet
                  </h2>
                  <p className="mt-4 text-base text-muted-foreground leading-relaxed">
                    Start your first research cycle to build the knowledge graph.
                  </p>
                  <Separator className="my-6" />
                  <div className="flex justify-center">
                    <div className="rounded bg-muted px-3 py-2 text-left">
                      <p className="text-xs font-semibold text-muted-foreground">
                        RUN COMMAND
                      </p>
                      <code className="mt-1 block text-sm">
                        winterfox run -n 1
                      </code>
                    </div>
                  </div>
                </div>
              ) : summary ? (
                <div className="rounded-lg border bg-card p-8">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Graph Visualization
                  </p>
                  <h2 className="mt-2 text-3xl font-bold tracking-tight">
                    Knowledge Graph
                  </h2>
                  <p className="mt-4 text-sm text-muted-foreground">
                    Interactive visualization coming soon...
                  </p>

                  <Separator className="my-6" />

                  <div className="grid grid-cols-3 gap-6 text-center">
                    <div>
                      <div className="text-2xl font-semibold tabular-nums">
                        {summary.total_nodes}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        Total Nodes
                      </div>
                    </div>
                    <div>
                      <div className="text-2xl font-semibold tabular-nums">
                        {(summary.avg_confidence * 100).toFixed(0)}%
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        Avg Confidence
                      </div>
                    </div>
                    <div>
                      <div className="text-2xl font-semibold tabular-nums">
                        {summary.root_nodes}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        Root Nodes
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Loading...</p>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Cycle History Section */}
        <section className="border-b py-16">
          <div className="container mx-auto px-4">
            <div className="mx-auto max-w-4xl">
              <div className="mb-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Research History
                </p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight">
                  Past Cycles
                </h2>
              </div>
              <CycleHistory />
            </div>
          </div>
        </section>

        {/* Events Section */}
        <section className="py-16">
          <div className="container mx-auto px-4">
            <div className="mx-auto max-w-4xl">
              <div className="mb-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Real-time Activity
                </p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight">
                  Cycle Events
                </h2>
              </div>
              <EventFeed />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default Dashboard;
