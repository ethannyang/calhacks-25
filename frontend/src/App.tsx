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

    // Listen for click-through toggle events
    if (window.electron) {
      window.electron.onClickThroughToggled((isEnabled: boolean) => {
        console.log('Click-through toggled:', isEnabled);
      });
    }
  }, []);

  return (
    <div ref={contentRef} className="inline-flex flex-col items-center justify-start pt-4 px-4 min-h-fit">
      {/* Connection status indicator */}
      <ConnectionStatus isConnected={isConnected} />

      {/* Main coaching command display */}
      {currentCommand && (
        <>
          {isDirectiveV1(currentCommand) && <DirectiveCard directive={currentCommand} />}
          {isCoachingCommand(currentCommand) && <CommandCard command={currentCommand} />}
        </>
      )}

      {/* Demo mode indicator (remove in production) */}
      {!currentCommand && (
        <div className="text-white/50 text-sm font-mono bg-black/30 px-3 py-2 rounded">
          All good
        </div>
      )}
    </div>
  );
}

export default App;
