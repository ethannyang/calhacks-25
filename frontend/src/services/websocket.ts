/**
 * WebSocket service for real-time coaching commands
 */

import { useCoachingStore } from '../store/coachingStore';
import { CoachingCommand, AbilityCooldowns } from '../store/coachingStore';

let ws: WebSocket | null = null;
let reconnectTimeout: NodeJS.Timeout | null = null;

export function connectWebSocket(url: string) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    console.log('WebSocket already connected');
    return;
  }

  console.log('Connecting to WebSocket:', url);
  ws = new WebSocket(url);

  ws.onopen = () => {
    console.log('WebSocket connected');
    useCoachingStore.getState().setConnected(true);
    useCoachingStore.getState().setWsConnection(ws);

    // Send initial config after a small delay to ensure connection is ready
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'config',
          data: {
            clientVersion: '0.1.0',
            timestamp: Date.now(),
          }
        }));
      }
    }, 100);
  };

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      console.log('Received message:', message);

      // Handle different message types
      switch (message.type) {
        case 'command':
          handleCoachingCommand(message.data);
          break;
        case 'cooldowns':
          handleCooldownUpdate(message.data);
          break;
        case 'ack':
          console.log('Server acknowledged:', message);
          break;
        default:
          console.log('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
    useCoachingStore.getState().setConnected(false);
    useCoachingStore.getState().setWsConnection(null);

    // Attempt reconnection after 5 seconds
    reconnectTimeout = setTimeout(() => {
      console.log('Attempting to reconnect...');
      connectWebSocket(url);
    }, 5000);
  };
}

function handleCoachingCommand(data: CoachingCommand) {
  console.log('New coaching command:', data);

  const store = useCoachingStore.getState();

  // Set as current command
  store.setCommand(data);

  // Add to history
  store.addToHistory(data);

  // Auto-clear after duration
  setTimeout(() => {
    const currentCommand = useCoachingStore.getState().currentCommand;
    if (currentCommand && currentCommand.timestamp === data.timestamp) {
      store.clearCommand();
    }
  }, data.duration * 1000);
}

function handleCooldownUpdate(data: AbilityCooldowns) {
  console.log('Cooldown update:', data);

  const store = useCoachingStore.getState();
  store.setEnemyCooldowns(data);
}

export function disconnectWebSocket() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }

  if (ws) {
    ws.close();
    ws = null;
  }
}

export function sendMessage(type: string, data: any) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type, data }));
  } else {
    console.warn('WebSocket not connected, cannot send message');
  }
}
