/**
 * Cycle history list showing past research cycles.
 */

import React from 'react';
import { useCycleStore } from '../../stores/cycleStore';
import {
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  DollarSign,
} from 'lucide-react';

const CycleHistory: React.FC = () => {
  const recentCycles = useCycleStore((state) => state.recentCycles);

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const formatDate = (dateStr: string) => {
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

  if (recentCycles.length === 0) {
    return (
      <div className="rounded-lg border bg-card">
        <div className="p-8 text-center">
          <Search className="mx-auto h-8 w-8 text-muted-foreground" />
          <p className="mt-4 text-sm text-muted-foreground">
            No research cycles yet.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card">
      <div className="divide-y">
        {recentCycles.map((cycle) => (
          <div
            key={cycle.id}
            className="flex items-center gap-4 p-4 transition-colors hover:bg-muted/50"
          >
            {/* Status icon */}
            <div className="shrink-0">
              {cycle.status === 'completed' ? (
                <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
              ) : cycle.status === 'failed' ? (
                <XCircle className="h-4 w-4 text-destructive" />
              ) : (
                <Clock className="h-4 w-4 text-muted-foreground animate-spin" />
              )}
            </div>

            {/* Cycle info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2">
                <span className="text-sm font-medium">
                  Cycle {cycle.id}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatDate(cycle.started_at)}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                <span>{cycle.directions_count} directions</span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDuration(cycle.duration_seconds)}
                </span>
                <span className="flex items-center gap-1">
                  <DollarSign className="h-3 w-3" />
                  {cycle.total_cost_usd.toFixed(4)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CycleHistory;
