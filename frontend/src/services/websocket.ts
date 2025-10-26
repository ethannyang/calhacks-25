/**
 * WebSocket service for real-time coaching commands
 */

import { useCoachingStore, CoachingCommand, DirectiveV1 } from '../store/coachingStore';

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

    // Send initial config
    ws?.send(JSON.stringify({
      type: 'config',
      data: {
        clientVersion: '0.1.0',
        timestamp: Date.now(),
      }
    }));

    // Start monitoring automatically
    setTimeout(() => {
      console.log('Starting game monitoring...');
      ws?.send(JSON.stringify({
        type: 'start_monitoring'
      }));
    }, 500);
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
        case 'directive':
          handleDirective(message.data);
          break;
        case 'status':
          console.log('Status:', message.message);
          break;
        case 'ack':
          console.log('Server acknowledged:', message);
          break;
        case 'debug':
          console.log('Debug info:', message.data);
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
    if (currentCommand && 'timestamp' in currentCommand && currentCommand.timestamp === data.timestamp) {
      store.clearCommand();
    }
  }, data.duration * 1000);
}

function handleDirective(data: DirectiveV1) {
  console.log('New LLM directive:', data);

  const store = useCoachingStore.getState();

  // Set as current command
  store.setCommand(data);

  // Add to history
  store.addToHistory(data);

  // Auto-clear after 8 seconds (directives are more complex, need more time)
  setTimeout(() => {
    const currentCommand = useCoachingStore.getState().currentCommand;
    if (currentCommand && 'ts_ms' in currentCommand && currentCommand.ts_ms === data.ts_ms) {
      store.clearCommand();
    }
  }, 8000);
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
