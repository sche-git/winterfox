/**
 * Knowledge Graph page with 40/60 split: tree + node detail.
 */

import React, { useEffect } from 'react';
import { useGraphStore } from '../../stores/graphStore';
import TreeView from './TreeView';
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
    <div className="flex h-full">
      {/* Tree panel (40%) */}
      <div className="w-[40%] border-r h-full overflow-hidden">
        <TreeView />
      </div>

      {/* Detail panel (60%) */}
      <div className="w-[60%]">
        <NodeDetail />
      </div>
    </div>
  );
};

export default GraphPage;
