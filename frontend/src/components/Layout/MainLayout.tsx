/**
 * Main layout wrapper with sidebar + content area.
 */

import React from 'react';
import Sidebar from './Sidebar';
import { useUIStore } from '../../stores/uiStore';
import OverviewPage from '../Overview/OverviewPage';
import GraphPage from '../Graph/GraphPage';
import HistoryPage from '../History/HistoryPage';

const MainLayout: React.FC = () => {
  const currentPage = useUIStore((s) => s.currentPage);

  const renderPage = () => {
    switch (currentPage) {
      case 'overview':
        return <OverviewPage />;
      case 'graph':
        return <GraphPage />;
      case 'history':
        return <HistoryPage />;
      default:
        return <OverviewPage />;
    }
  };

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {renderPage()}
      </main>
    </div>
  );
};

export default MainLayout;
