import { useEffect } from 'react';
import CommandCard from './components/CommandCard';
import ConnectionStatus from './components/ConnectionStatus';
import { useCoachingStore } from './store/coachingStore';
import { connectWebSocket } from './services/websocket';

function App() {
  const { currentCommand, isConnected } = useCoachingStore();

  useEffect(() => {
    // Connect to backend WebSocket
    connectWebSocket('ws://localhost:8000/ws');

    // Listen for click-through toggle events
    if (window.electron) {
      window.electron.onClickThroughToggled((isEnabled: boolean) => {
        console.log('Click-through toggled:', isEnabled);
      });
    }
  }, []);

  return (
    <div className="w-full h-full flex flex-col items-center justify-start pt-4 px-4">
      {/* Connection status indicator */}
      <ConnectionStatus isConnected={isConnected} />

      {/* Main coaching command display */}
      {currentCommand && <CommandCard command={currentCommand} />}

      {/* Demo mode indicator (remove in production) */}
      {!currentCommand && (
        <div className="text-white/50 text-sm font-mono bg-black/30 px-3 py-2 rounded">
          Waiting for coaching data...
        </div>
      )}
    </div>
  );
}

export default App;
