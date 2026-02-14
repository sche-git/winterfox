/**
 * Research History page - compact cycle list on left, report on right.
 */

import React, { useState, useEffect } from 'react';
import { useCycleStore } from '../../stores/cycleStore';
import CycleTable from './CycleTable';
import CycleDetailSheet from './CycleDetailSheet';

const HistoryPage: React.FC = () => {
  const recentCycles = useCycleStore((s) => s.recentCycles);
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);

  // Auto-select first cycle when list loads
  useEffect(() => {
    if (!selectedCycleId && recentCycles.length > 0) {
      setSelectedCycleId(recentCycles[0].id);
    }
  }, [recentCycles]);

  return (
    <div className="flex h-full">
      {/* Compact cycle list */}
      <div className="w-72 shrink-0 overflow-auto border-r">
        <div className="px-4 py-4">
          <h2 className="text-sm font-semibold">Research Cycles</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {recentCycles.length} cycles
          </p>
        </div>
        <CycleTable
          selectedCycleId={selectedCycleId}
          onSelectCycle={(id) => setSelectedCycleId(id)}
        />
      </div>

      {/* Report panel - takes remaining space */}
      <div className="flex-1 min-w-0">
        {selectedCycleId ? (
          <CycleDetailSheet
            cycleId={selectedCycleId}
            onClose={() => setSelectedCycleId(null)}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Select a cycle to view its report
          </div>
        )}
      </div>
    </div>
  );
};

export default HistoryPage;
