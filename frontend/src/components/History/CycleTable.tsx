/**
 * Compact cycle list for the sidebar.
 */

import React from 'react';
import { useCycleStore } from '../../stores/cycleStore';
import {
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface CycleTableProps {
  selectedCycleId: number | null;
  onSelectCycle: (cycleId: number) => void;
}

const CycleTable: React.FC<CycleTableProps> = ({ selectedCycleId, onSelectCycle }) => {
  const recentCycles = useCycleStore((s) => s.recentCycles);

  const formatTimestamp = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '';
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  if (recentCycles.length === 0) {
    return (
      <div className="px-4 py-8 text-center">
        <Clock className="mx-auto h-6 w-6 text-muted-foreground" />
        <p className="mt-3 text-xs text-muted-foreground">No cycles yet</p>
      </div>
    );
  }

  return (
    <div className="divide-y">
      {recentCycles.map((cycle) => (
        <button
          key={cycle.id}
          onClick={() => onSelectCycle(cycle.id)}
          className={cn(
            'flex w-full flex-col gap-1 px-4 py-2.5 text-left transition-colors hover:bg-muted/50',
            selectedCycleId === cycle.id && 'bg-secondary'
          )}
        >
          {/* Top row: status + id + timestamp */}
          <div className="flex items-center gap-1.5">
            {cycle.status === 'completed' ? (
              <CheckCircle2 className="h-3 w-3 shrink-0 text-muted-foreground" />
            ) : cycle.status === 'failed' ? (
              <XCircle className="h-3 w-3 shrink-0 text-destructive" />
            ) : (
              <Clock className="h-3 w-3 shrink-0 animate-spin text-muted-foreground" />
            )}
            <span className="text-xs font-medium">#{cycle.id}</span>
            <span className="ml-auto text-[11px] tabular-nums text-muted-foreground">
              {formatTimestamp(cycle.started_at)}
            </span>
          </div>

          {/* Focus claim */}
          {cycle.target_claim && (
            <p className="truncate text-xs text-muted-foreground pl-[18px]">
              {cycle.target_claim}
            </p>
          )}

          {/* Stats row */}
          <div className="flex items-center gap-2 pl-[18px] text-[11px] tabular-nums text-muted-foreground">
            <span>{cycle.directions_count} directions</span>
            <span>{formatDuration(cycle.duration_seconds)}</span>
          </div>
        </button>
      ))}
    </div>
  );
};

export default CycleTable;
