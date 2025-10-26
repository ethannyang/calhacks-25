import { useEffect, useState } from 'react';
import CommandCard from './components/CommandCard';
import ConnectionStatus from './components/ConnectionStatus';
import VoiceInput from './components/VoiceInput';
import CooldownDisplay from './components/CooldownDisplay';
import { useCoachingStore } from './store/coachingStore';
import { connectWebSocket } from './services/websocket';

function App() {
  const { currentCommand, isConnected } = useCoachingStore();
  const [isVoiceListening, setIsVoiceListening] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState<string>('');

  useEffect(() => {
    // Connect to backend WebSocket
    connectWebSocket('ws://localhost:8000/ws');

    // Listen for click-through toggle events
    if (window.electron) {
      window.electron.onClickThroughToggled((isEnabled: boolean) => {
        console.log('Click-through toggled:', isEnabled);
      });

      // Listen for voice input toggle events from Electron
      window.electron.onVoiceInputToggle((isActive: boolean) => {
        console.log('Voice input toggled:', isActive);
        setIsVoiceListening(isActive);
      });
    }
  }, []);

  return (
    <div className="w-full h-full relative">
      {/* Coach output - Top Center with explicit inline styles */}
      <div
        className="absolute top-4 flex flex-col items-center gap-2"
        style={{
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10
        }}
      >
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

        {/* Voice input indicator - show when listening */}
        {isVoiceListening && (
          <div className="bg-red-500/90 text-white px-4 py-2 rounded-lg shadow-lg mt-3">
            <div className="flex items-center gap-2 animate-pulse">
              <div className="w-3 h-3 bg-white rounded-full"></div>
              <span className="font-semibold text-sm">LISTENING...</span>
            </div>
            {/* Show live transcript */}
            {voiceTranscript && (
              <div className="mt-2 text-sm text-white/90 italic">
                "{voiceTranscript}"
              </div>
            )}
          </div>
        )}

        {/* Voice examples box - always below coach output */}
        {!isVoiceListening && (
          <div className="bg-black/70 text-white/80 px-3 py-2 rounded-lg mt-3 text-xs">
            <div className="opacity-60">
              Press ` to ask questions: "Should I recall?", "When to roam?", "How do I beat Garen?"
            </div>
          </div>
        )}
      </div>

      {/* Voice input component - rendered but not visible (still needs to be mounted) */}
      <div style={{ position: 'absolute', left: '-9999px' }}>
        <VoiceInput
          isListening={isVoiceListening}
          onListeningChange={setIsVoiceListening}
          onTranscriptChange={setVoiceTranscript}
        />
      </div>

      {/* Cooldown tracker - Bottom (existing position) */}
      <CooldownDisplay />
    </div>
  );
}

export default App;
