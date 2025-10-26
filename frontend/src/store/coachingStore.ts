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

// DirectiveV1 format (LLM-powered coaching)
export interface DirectivePrimary {
  window: string;
  text: string;
  setup: string;
  requirements: string;
  success: string;
  risk: string;
  confidence: number;
}

export interface DirectiveV1 {
  t: 'directive.v1';
  ts_ms: number;
  primary: DirectivePrimary;
  backupA: string;
  backupB: string;
  micro: Record<string, string>;
  timers: Record<string, number>;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

// Union type for both command formats
export type Command = CoachingCommand | DirectiveV1;

interface CoachingStore {
  // State
  currentCommand: Command | null;
  commandHistory: Command[];
  isConnected: boolean;
  wsConnection: WebSocket | null;

  // Actions
  setCommand: (command: Command | null) => void;
  addToHistory: (command: Command) => void;
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
