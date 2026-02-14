/**
 * UI state store using Zustand.
 */

import { create } from 'zustand';

interface UIState {
  // State
  sidebarOpen: boolean;
  selectedView: 'graph' | 'list' | 'tree';
  showEventFeed: boolean;
  darkMode: boolean;

  // Actions
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setSelectedView: (view: 'graph' | 'list' | 'tree') => void;
  toggleEventFeed: () => void;
  toggleDarkMode: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  // Initial state
  sidebarOpen: true,
  selectedView: 'graph',
  showEventFeed: true,
  darkMode: false,

  // Actions
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  setSelectedView: (view) => set({ selectedView: view }),

  toggleEventFeed: () => set((state) => ({ showEventFeed: !state.showEventFeed })),

  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
}));
