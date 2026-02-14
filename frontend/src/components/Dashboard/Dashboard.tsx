/**
 * Main Dashboard component.
 */

import React from 'react';
import StatsCards from './StatsCards';
import EventFeed from '../CycleMonitor/EventFeed';
import { useGraphStore } from '../../stores/graphStore';
import { useCycleStore } from '../../stores/cycleStore';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const summary = useGraphStore((state) => state.summary);
  const loading = useGraphStore((state) => state.loading);
  const error = useGraphStore((state) => state.error);
  const activeCycle = useCycleStore((state) => state.activeCycle);

  if (loading && !summary) {
    return (
      <div className="dashboard loading">
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard error">
        <p>Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Winterfox Research Dashboard</h1>
        {activeCycle && activeCycle.status === 'running' && (
          <div className="active-cycle-indicator">
            <span className="pulse"></span>
            Cycle {activeCycle.cycle_id} Running ({activeCycle.progress_percent}%)
          </div>
        )}
      </header>

      <main className="dashboard-main">
        <section className="stats-section">
          <StatsCards />
        </section>

        <section className="content-section">
          <div className="graph-placeholder">
            {summary && summary.total_nodes === 0 ? (
              <>
                <h2>No Research Data Yet</h2>
                <p style={{ marginBottom: '1rem', color: '#6b7280' }}>
                  Start your first research cycle to build the knowledge graph.
                </p>
                <p style={{ fontSize: '0.9rem', color: '#9ca3af' }}>
                  Run: <code style={{ background: '#f3f4f6', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>winterfox run -n 1</code>
                </p>
              </>
            ) : summary ? (
              <>
                <h2>Knowledge Graph</h2>
                <p>Graph visualization coming soon...</p>
                <div className="graph-stats">
                  <p>Total Nodes: {summary.total_nodes}</p>
                  <p>Average Confidence: {(summary.avg_confidence * 100).toFixed(0)}%</p>
                  <p>Root Nodes: {summary.root_nodes}</p>
                </div>
              </>
            ) : (
              <p>Loading...</p>
            )}
          </div>
        </section>

        <aside className="events-sidebar">
          <EventFeed />
        </aside>
      </main>
    </div>
  );
};

export default Dashboard;
