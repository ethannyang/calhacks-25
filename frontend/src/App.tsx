import { useEffect } from 'react';
import CommandCard from './components/CommandCard';
import DirectiveCard from './components/DirectiveCard';
import ConnectionStatus from './components/ConnectionStatus';
import { useCoachingStore, CoachingCommand, DirectiveV1 } from './store/coachingStore';
import { connectWebSocket } from './services/websocket';
import { useAutoResize } from './hooks/useAutoResize';

// Type guard to check if command is DirectiveV1
function isDirectiveV1(command: any): command is DirectiveV1 {
  return command && 'primary' in command && 't' in command;
}

// Type guard to check if command is CoachingCommand
function isCoachingCommand(command: any): command is CoachingCommand {
  return command && 'message' in command && 'icon' in command;
}

function App() {
  const { currentCommand, isConnected } = useCoachingStore();
  const contentRef = useAutoResize(true);

  useEffect(() => {
    // Connect to backend WebSocket
    connectWebSocket('ws://localhost:8001/ws');

    // Listen for click-through toggle events and force show window
    if (window.electron) {
      // Force show the window on startup
      window.electron.forceShow();

      window.electron.onClickThroughToggled((isEnabled: boolean) => {
        console.log('Click-through toggled:', isEnabled);
      });
    }
  }, []);

  return (
    <div
      ref={contentRef}
      className="inline-flex flex-col items-center justify-start pt-4 px-4 min-h-fit"
      style={{
        minWidth: '300px',
        background: 'linear-gradient(135deg, rgba(0,0,0,0.7) 0%, rgba(20,20,20,0.5) 100%)',
        backdropFilter: 'blur(10px)',
        borderRadius: '12px',
        border: '1px solid rgba(255,255,255,0.1)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
      }}
    >
      {/* Connection status indicator */}
      <ConnectionStatus isConnected={isConnected} />

      {/* Main coaching command display */}
      {currentCommand && (
        <div className="w-full animate-fade-in">
          {isDirectiveV1(currentCommand) && <DirectiveCard directive={currentCommand} />}
          {isCoachingCommand(currentCommand) && <CommandCard command={currentCommand} />}
        </div>
      )}

      {/* Overlay status indicator */}
      {!currentCommand && (
        <div className="text-center">
          <div className="text-white/80 text-lg font-bold mb-2">
            LoL AI Coaching Overlay
          </div>
          <div className="text-white/60 text-sm font-mono bg-black/30 px-3 py-2 rounded">
            {isConnected ? 'Connected - Waiting for commands' : 'Connecting...'}
          </div>
          <div className="text-white/40 text-xs mt-3 space-y-1">
            <div>Ctrl+Shift+C: Toggle click-through</div>
            <div>Ctrl+Shift+V: Show/Hide overlay</div>
            <div>Ctrl+Alt+/- : Resize window</div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
