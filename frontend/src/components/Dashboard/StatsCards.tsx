/**
 * Statistics cards showing key metrics.
 * Following the console metric card pattern from design guide.
 */

import React from 'react';
import { useGraphStore } from '../../stores/graphStore';

const StatsCards: React.FC = () => {
  const summary = useGraphStore((state) => state.summary);

  if (!summary) {
    return null;
  }

  const cards = [
    {
      title: 'Total Nodes',
      value: summary.total_nodes.toLocaleString(),
      color: 'text-foreground',
    },
    {
      title: 'Avg Confidence',
      value: `${(summary.avg_confidence * 100).toFixed(0)}%`,
      color: 'text-foreground',
    },
    {
      title: 'Root Nodes',
      value: summary.root_nodes.toLocaleString(),
      color: 'text-foreground',
    },
    {
      title: 'Low Confidence',
      value: summary.low_confidence_count.toLocaleString(),
      color: summary.low_confidence_count > 10 ? 'text-muted-foreground' : 'text-muted-foreground',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.title}
          className="rounded-lg border bg-card p-4"
        >
          <div className={`text-2xl font-semibold tabular-nums ${card.color}`}>
            {card.value}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {card.title}
          </div>
        </div>
      ))}
    </div>
  );
};

export default StatsCards;
