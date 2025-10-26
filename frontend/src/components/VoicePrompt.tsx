import { useEffect, useState } from 'react';

export default function VoicePrompt() {
  const [isListening, setIsListening] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '`') {
        e.preventDefault();
        setIsListening(true);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === '`') {
        e.preventDefault();
        setIsListening(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  if (isListening) {
    return (
      <div className="w-full mt-3 animate-fade-in">
        <button
          className="w-full py-3 px-4 rounded-lg font-bold text-white text-sm uppercase tracking-wider transition-all"
          style={{
            backgroundColor: 'rgba(220, 38, 38, 0.9)',
            boxShadow: '0 4px 16px rgba(220, 38, 38, 0.4)',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}
        >
          LISTENING...
        </button>
      </div>
    );
  }

  return (
    <div className="w-full mt-3 animate-fade-in">
      <div
        className="py-3 px-4 rounded-lg text-white/70 text-xs text-center transition-all hover:bg-white/5"
        style={{
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        <div className="font-medium mb-1">
          Press <kbd className="px-1.5 py-0.5 bg-white/20 rounded text-white/90 font-mono text-xs">`</kbd> to ask questions:
        </div>
        <div className="text-white/50 text-xs space-y-0.5">
          <div>"Should I recall?"</div>
          <div>"When to roam?"</div>
          <div>"How do I beat Garen?"</div>
        </div>
      </div>
    </div>
  );
}
