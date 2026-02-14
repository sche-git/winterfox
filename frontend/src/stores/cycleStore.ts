/**
 * Cycle state store using Zustand.
 */

import { create } from 'zustand';
import type { Cycle, ActiveCycle, WinterFoxEvent } from '../types/api';

interface CycleState {
  // State
  activeCycle: ActiveCycle | null;
  recentCycles: Cycle[];
  events: WinterFoxEvent[];
  maxEvents: number;

  // Actions
  setActiveCycle: (cycle: ActiveCycle | null) => void;
  setRecentCycles: (cycles: Cycle[]) => void;
  addEvent: (event: WinterFoxEvent) => void;
  clearEvents: () => void;
  handleEvent: (event: WinterFoxEvent) => void;
}

export const useCycleStore = create<CycleState>((set) => ({
  // Initial state
  activeCycle: null,
  recentCycles: [],
  events: [],
  maxEvents: 100, // Keep last 100 events

  // Actions
  setActiveCycle: (cycle) => set({ activeCycle: cycle }),

  setRecentCycles: (cycles) => set({ recentCycles: cycles }),

  addEvent: (event) =>
    set((state) => {
      const newEvents = [event, ...state.events].slice(0, state.maxEvents);
      return { events: newEvents };
    }),

  clearEvents: () => set({ events: [] }),

  handleEvent: (event) =>
    set((state) => {
      // Add to events list
      const newEvents = [event, ...state.events].slice(0, state.maxEvents);

      // Update active cycle based on event type
      let newActiveCycle = state.activeCycle;

      switch (event.type) {
        case 'cycle.started':
          newActiveCycle = {
            cycle_id: event.data.cycle_id,
            status: 'running',
            focus_node_id: event.data.focus_node_id,
            current_step: 'started',
            progress_percent: 0,
          };
          break;

        case 'cycle.step':
          if (newActiveCycle?.cycle_id === event.data.cycle_id) {
            newActiveCycle = {
              ...newActiveCycle,
              current_step: event.data.step,
              progress_percent: event.data.progress_percent,
            };
          }
          break;

        case 'cycle.completed':
        case 'cycle.failed':
          if (newActiveCycle?.cycle_id === event.data.cycle_id) {
            newActiveCycle = {
              cycle_id: null,
              status: 'idle',
              focus_node_id: null,
              current_step: null,
              progress_percent: 0,
            };
          }
          break;
      }

      return {
        events: newEvents,
        activeCycle: newActiveCycle,
      };
    }),
}));
