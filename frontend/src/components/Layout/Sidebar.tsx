/**
 * Navigation sidebar with page links and connection status.
 */

import React from 'react';
import { BarChart3, FileText, GitFork, History, Wifi } from 'lucide-react';
import { useUIStore, type Page } from '../../stores/uiStore';
import { useCycleStore } from '../../stores/cycleStore';
import { cn } from '@/lib/utils';

const navItems: { page: Page; label: string; icon: React.ElementType }[] = [
  { page: 'overview', label: 'Overview', icon: BarChart3 },
  { page: 'graph', label: 'Research Map', icon: GitFork },
  { page: 'history', label: 'Research Timeline', icon: History },
  { page: 'report', label: 'Report', icon: FileText },
];

const Sidebar: React.FC = () => {
  const currentPage = useUIStore((s) => s.currentPage);
  const setCurrentPage = useUIStore((s) => s.setCurrentPage);
  const activeCycle = useCycleStore((s) => s.activeCycle);

  const isRunning = activeCycle?.status === 'running';

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r bg-card">
      {/* Logo */}
      <div className="border-b px-6 py-5">
        <button
          type="button"
          onClick={() => setCurrentPage('overview')}
          className="flex items-center gap-2.5 text-left"
          aria-label="Go to Overview"
        >
          <img
            src="/fox-logo.png"
            alt="Winterfox"
            className="h-14 w-14 dark:invert"
          />
          <div>
            <h1 className="text-lg font-bold tracking-tight">Winterfox</h1>
          </div>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        <div className="space-y-1">
          {navItems.map(({ page, label, icon: Icon }) => (
            <button
              key={page}
              onClick={() => setCurrentPage(page)}
              className={cn(
                'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                currentPage === page
                  ? 'bg-secondary text-secondary-foreground'
                  : 'text-foreground hover:bg-muted'
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>
      </nav>

      {/* Status footer */}
      <div className="border-t px-6 py-4">
        {isRunning ? (
          <div className="flex items-center gap-2 text-xs">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-foreground opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-foreground" />
            </span>
            <span className="text-muted-foreground">
              Cycle {activeCycle.cycle_id} ({activeCycle.progress_percent}%)
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Wifi className="h-3 w-3" />
            <span>Connected</span>
          </div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
