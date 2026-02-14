/**
 * Statistics cards showing key metrics.
 */

import React from 'react';
import { useGraphStore } from '../../stores/graphStore';
import './StatsCards.css';

const StatsCards: React.FC = () => {
  const summary = useGraphStore((state) => state.summary);

  if (!summary) {
    return null;
  }

  const cards = [
    {
      title: 'Total Nodes',
      value: summary.total_nodes,
      color: 'blue',
    },
    {
      title: 'Avg Confidence',
      value: `${(summary.avg_confidence * 100).toFixed(0)}%`,
      color: summary.avg_confidence >= 0.7 ? 'green' : 'yellow',
    },
    {
      title: 'Root Nodes',
      value: summary.root_nodes,
      color: 'purple',
    },
    {
      title: 'Low Confidence',
      value: summary.low_confidence_count,
      color: summary.low_confidence_count > 10 ? 'red' : 'gray',
    },
  ];

  return (
    <div className="stats-cards">
      {cards.map((card) => (
        <div key={card.title} className={`stat-card stat-card-${card.color}`}>
          <div className="stat-value">{card.value}</div>
          <div className="stat-title">{card.title}</div>
        </div>
      ))}
    </div>
  );
};

export default StatsCards;
