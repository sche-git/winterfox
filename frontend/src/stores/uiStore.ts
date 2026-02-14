/**
 * UI state store using Zustand.
 */

import { create } from 'zustand';

export type Page = 'overview' | 'graph' | 'history';

interface UIState {
  // State
  currentPage: Page;
  sidebarOpen: boolean;
  selectedView: 'graph' | 'list' | 'tree';
  showEventFeed: boolean;
  darkMode: boolean;
  selectedCycleId: number | null;

  // Actions
  setCurrentPage: (page: Page) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setSelectedView: (view: 'graph' | 'list' | 'tree') => void;
  toggleEventFeed: () => void;
  toggleDarkMode: () => void;
  setSelectedCycleId: (id: number | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  // Initial state
  currentPage: 'overview',
  sidebarOpen: true,
  selectedView: 'graph',
  showEventFeed: true,
  darkMode: false,
  selectedCycleId: null,

  // Actions
  setCurrentPage: (page) => set({ currentPage: page }),

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  setSelectedView: (view) => set({ selectedView: view }),

  toggleEventFeed: () => set((state) => ({ showEventFeed: !state.showEventFeed })),

  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),

  setSelectedCycleId: (id) => set({ selectedCycleId: id }),
}));
