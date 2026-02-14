/**
 * Main App component with layout and routing.
 */

import { useEffect } from 'react';
import { api } from './services/api';
import { wsClient } from './services/websocket';
import { useGraphStore } from './stores/graphStore';
import { useCycleStore } from './stores/cycleStore';
import Dashboard from './components/Dashboard/Dashboard';
import './App.css';

function App() {
  const setSummary = useGraphStore((state) => state.setSummary);
  const setLoading = useGraphStore((state) => state.setLoading);
  const setError = useGraphStore((state) => state.setError);
  const handleEvent = useCycleStore((state) => state.handleEvent);

  useEffect(() => {
    // Initialize WebSocket connection
    wsClient.connect();

    // Subscribe to WebSocket events
    const unsubscribe = wsClient.subscribe((event) => {
      handleEvent(event);

      // Update graph store based on events
      if (event.type === 'node.created') {
        // Refetch summary when nodes are created
        loadSummary();
      }
    });

    // Load initial data
    loadSummary();

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

  return (
    <div className="App">
      <Dashboard />
    </div>
  );
}

export default App;
