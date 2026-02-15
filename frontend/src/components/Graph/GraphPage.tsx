/**
 * Research Map page with interactive bubble graph + node detail.
 */

import React, { useEffect } from 'react';
import { useGraphStore } from '../../stores/graphStore';
import ResearchMap from './ResearchMap';
import NodeDetail from './NodeDetail';

const GraphPage: React.FC = () => {
  const loadTree = useGraphStore((s) => s.loadTree);
  const tree = useGraphStore((s) => s.tree);

  useEffect(() => {
    if (tree.length === 0) {
      loadTree();
    }
  }, []);

  return (
    <div className="flex h-full gap-3 p-3">
      {/* Map panel */}
      <div className="h-full w-[58%] overflow-hidden">
        <ResearchMap />
      </div>

      {/* Detail panel */}
      <div className="h-full w-[42%] overflow-hidden rounded-xl border bg-card">
        <NodeDetail />
      </div>
    </div>
  );
};

export default GraphPage;
