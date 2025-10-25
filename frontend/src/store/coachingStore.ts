/**
 * Zustand store for coaching state management
 */

import { create } from 'zustand';

export interface CoachingCommand {
  priority: 'low' | 'medium' | 'high' | 'critical';
  category: 'safety' | 'wave' | 'trade' | 'objective' | 'rotation' | 'recall' | 'vision' | 'position';
  icon: string;
  message: string;
  duration: number;
  timestamp: number;
}

interface CoachingStore {
  // State
  currentCommand: CoachingCommand | null;
  commandHistory: CoachingCommand[];
  isConnected: boolean;
  wsConnection: WebSocket | null;

  // Actions
  setCommand: (command: CoachingCommand | null) => void;
  addToHistory: (command: CoachingCommand) => void;
  setConnected: (connected: boolean) => void;
  setWsConnection: (ws: WebSocket | null) => void;
  clearCommand: () => void;
}

export const useCoachingStore = create<CoachingStore>((set) => ({
  // Initial state
  currentCommand: null,
  commandHistory: [],
  isConnected: false,
  wsConnection: null,

  // Actions
  setCommand: (command) => set({ currentCommand: command }),

  addToHistory: (command) =>
    set((state) => ({
      commandHistory: [command, ...state.commandHistory].slice(0, 10), // Keep last 10
    })),

  setConnected: (connected) => set({ isConnected: connected }),

  setWsConnection: (ws) => set({ wsConnection: ws }),

  clearCommand: () => set({ currentCommand: null }),
}));
