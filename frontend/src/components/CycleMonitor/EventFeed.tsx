/**
 * Real-time event feed showing WebSocket events.
 * Following the list pattern from design guide.
 */

import React from 'react';
import { useCycleStore } from '../../stores/cycleStore';
import {
  RefreshCw,
  Bot,
  FileText,
  Sparkles,
  CheckCircle2,
  XCircle,
  Clock
} from 'lucide-react';

const EventFeed: React.FC = () => {
  const events = useCycleStore((state) => state.events);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const getEventIcon = (type: string) => {
    if (type.startsWith('cycle.')) return RefreshCw;
    if (type.startsWith('agent.')) return Bot;
    if (type.startsWith('node.')) return FileText;
    if (type.startsWith('synthesis.')) return Sparkles;
    if (type === 'cycle.completed') return CheckCircle2;
    if (type === 'cycle.failed') return XCircle;
    return Clock;
  };

  const formatEventMessage = (event: any) => {
    switch (event.type) {
      case 'cycle.started':
        return `Cycle ${event.data.cycle_id} started on "${event.data.focus_claim.substring(0, 50)}..."`;
      case 'cycle.step':
        return `Step: ${event.data.step} (${event.data.progress_percent}%)`;
      case 'cycle.completed':
        return `Cycle ${event.data.cycle_id} completed: ${event.data.findings_created} created, ${event.data.findings_updated} updated ($${event.data.total_cost_usd.toFixed(4)})`;
      case 'cycle.failed':
        return `Cycle ${event.data.cycle_id} failed: ${event.data.error_message}`;
      case 'agent.started':
        return `Agent ${event.data.agent_name} started`;
      case 'agent.completed':
        return `Agent ${event.data.agent_name} completed: ${event.data.findings_count} findings ($${event.data.cost_usd.toFixed(4)})`;
      case 'node.created':
        return `Node created: "${event.data.claim.substring(0, 50)}..." (${(event.data.confidence * 100).toFixed(0)}% confidence)`;
      case 'node.updated':
        return `Node updated: confidence ${(event.data.old_confidence * 100).toFixed(0)}% → ${(event.data.new_confidence * 100).toFixed(0)}%`;
      case 'synthesis.started':
        return `Synthesis started with ${event.data.agent_count} agents`;
      case 'synthesis.completed':
        return `Synthesis complete: ${event.data.consensus_count} consensus, ${event.data.divergent_count} divergent`;
      default:
        return JSON.stringify(event.data);
    }
  };

  return (
    <div className="rounded-lg border bg-card">
      {events.length === 0 ? (
        <div className="p-8 text-center">
          <Clock className="mx-auto h-8 w-8 text-muted-foreground" />
          <p className="mt-4 text-sm text-muted-foreground">
            No events yet. Run a research cycle to see live updates.
          </p>
          <div className="mt-4 rounded bg-muted px-3 py-2 text-left inline-block">
            <p className="text-xs font-semibold text-muted-foreground">
              RUN COMMAND
            </p>
            <code className="mt-1 block text-sm">
              winterfox run -n 1
            </code>
          </div>
        </div>
      ) : (
        <div className="divide-y">
          {events.map((event, index) => {
            const Icon = getEventIcon(event.type);
            return (
              <div
                key={`${event.timestamp}-${index}`}
                className="flex gap-3 p-4 transition-colors hover:bg-muted/50"
              >
                <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                <div className="flex-1 space-y-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      {event.type}
                    </span>
                    <span className="text-xs tabular-nums text-muted-foreground">
                      {formatTimestamp(event.timestamp)}
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed">
                    {formatEventMessage(event)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default EventFeed;
