/**
 * Main App component with layout and data initialization.
 */

import { useEffect } from 'react';
import { api } from './services/api';
import { wsClient } from './services/websocket';
import { useGraphStore } from './stores/graphStore';
import { useCycleStore } from './stores/cycleStore';
import MainLayout from './components/Layout/MainLayout';
import './App.css';

function App() {
  const setSummary = useGraphStore((s) => s.setSummary);
  const setLoading = useGraphStore((s) => s.setLoading);
  const setError = useGraphStore((s) => s.setError);
  const loadTree = useGraphStore((s) => s.loadTree);
  const handleEvent = useCycleStore((s) => s.handleEvent);
  const setRecentCycles = useCycleStore((s) => s.setRecentCycles);

  useEffect(() => {
    // Initialize WebSocket connection
    wsClient.connect();

    // Subscribe to WebSocket events
    const unsubscribe = wsClient.subscribe((event) => {
      handleEvent(event);

      // Update graph store based on events
      if (event.type === 'node.created') {
        loadSummary();
        loadTree();
      }

      // Refresh cycle list when a cycle completes
      if (event.type === 'cycle.completed' || event.type === 'cycle.failed') {
        loadCycles();
      }
    });

    // Load initial data
    loadSummary();
    loadCycles();
    loadTree();

    // Cleanup on unmount
    return () => {
      unsubscribe();
      wsClient.disconnect();
    };
  }, []);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const summary = await api.getGraphSummary();
      setSummary(summary);
      setError(null);
    } catch (error) {
      console.error('Failed to load summary:', error);
      setError('Failed to load graph summary');
    } finally {
      setLoading(false);
    }
  };

  const loadCycles = async () => {
    try {
      const response = await api.getCycles(20, 0);
      setRecentCycles(response.cycles);
    } catch (error) {
      console.error('Failed to load cycles:', error);
    }
  };

  return <MainLayout />;
}

export default App;
