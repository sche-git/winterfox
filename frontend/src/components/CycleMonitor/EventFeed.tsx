/**
 * Real-time event feed showing WebSocket events.
 */

import React from 'react';
import { useCycleStore } from '../../stores/cycleStore';
import './EventFeed.css';

const EventFeed: React.FC = () => {
  const events = useCycleStore((state) => state.events);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const getEventIcon = (type: string) => {
    if (type.startsWith('cycle.')) return '🔄';
    if (type.startsWith('agent.')) return '🤖';
    if (type.startsWith('node.')) return '📄';
    if (type.startsWith('synthesis.')) return '🔮';
    return '•';
  };

  const getEventColor = (type: string) => {
    if (type === 'cycle.started') return 'blue';
    if (type === 'cycle.completed') return 'green';
    if (type === 'cycle.failed') return 'red';
    if (type === 'agent.completed') return 'green';
    if (type === 'node.created') return 'cyan';
    return 'gray';
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
    <div className="event-feed">
      <h3>Live Events</h3>
      <div className="events-list">
        {events.length === 0 ? (
          <div className="no-events">
            <p>No events yet. Run a research cycle to see live updates.</p>
          </div>
        ) : (
          events.map((event, index) => (
            <div
              key={`${event.timestamp}-${index}`}
              className={`event-item event-${getEventColor(event.type)}`}
            >
              <div className="event-header">
                <span className="event-icon">{getEventIcon(event.type)}</span>
                <span className="event-type">{event.type}</span>
                <span className="event-time">{formatTimestamp(event.timestamp)}</span>
              </div>
              <div className="event-message">{formatEventMessage(event)}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default EventFeed;
