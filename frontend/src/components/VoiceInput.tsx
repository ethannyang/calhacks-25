/**
 * Voice input component for push-to-talk ability tracking
 * Uses cloud ASR (Deepgram) via AudioWorklet streaming
 */

import { useEffect, useState, useCallback } from 'react';
import { sendMessage } from '../services/websocket';
import { voiceStreamingService } from '../services/voiceStreaming';

// Ability mappings for voice recognition
const ABILITY_MAPPINGS: { [key: string]: string } = {
  // Basic abilities (with common misrecognitions)
  'q': 'Q',
  'queue': 'Q',
  'cute': 'Q',
  'cue': 'Q',
  'w': 'W',
  'double you': 'W',
  'double u': 'W',
  'e': 'E',
  'he': 'E',
  'r': 'R',
  'are': 'R',
  'our': 'R',
  'ult': 'R',
  'ultimate': 'R',
  'ulti': 'R',

  // Summoner spells
  'flash': 'Flash',
  'flashed': 'Flash',
  'flashes': 'Flash',
  'ignite': 'Ignite',
  'ignited': 'Ignite',
  'ignites': 'Ignite',
  'teleport': 'Teleport',
  'teleported': 'Teleport',
  'tp': 'Teleport',
  'tped': 'Teleport',
  'heal': 'Heal',
  'healed': 'Heal',
  'heals': 'Heal',
  'barrier': 'Barrier',
  'exhaust': 'Exhaust',
  'exhausted': 'Exhaust',
  'ghost': 'Ghost',
  'ghosted': 'Ghost',
  'cleanse': 'Cleanse',
  'cleansed': 'Cleanse',
  'smite': 'Smite',
  'smited': 'Smite',
};

// Target mappings - focused on Garen and common variations
const TARGET_MAPPINGS: { [key: string]: string } = {
  'garen': 'Garen',
  'garrett': 'Garen',
  'karen': 'Garen',
  'garden': 'Garen',
  'garren': 'Garen',
  'enemy': 'Garen',  // Default enemy to Garen since we're tracking him
  'opponent': 'Garen',
  'their': 'Garen',
  'they': 'Garen',
  'he': 'Garen',
};

// Action words that indicate ability use
const ACTION_WORDS = [
  'used', 'use', 'uses', 'using',
  'cast', 'casted', 'casting', 'casts',
  'pressed', 'press', 'presses',
  'activated', 'activate', 'activates',
  'did', 'does', 'just',
  'popped', 'pop', 'pops'
];

interface VoiceInputProps {
  isListening: boolean;
  onListeningChange?: (listening: boolean) => void;
}

export default function VoiceInput({ isListening, onListeningChange }: VoiceInputProps) {
  const [lastCommand, setLastCommand] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [interimTranscript, setInterimTranscript] = useState<string>('');
  const [isStreamingActive, setIsStreamingActive] = useState(false);

  // No initialization needed - voiceStreamingService is a singleton

  // Parse voice command and send to backend
  const parseAndSendCommand = useCallback((transcript: string) => {
    console.log('🎤 Raw transcript:', transcript);

    const lowerTranscript = transcript.toLowerCase();
    const words = lowerTranscript.split(' ');

    // Try to find ability and target in the transcript
    let ability: string | null = null;
    let target = 'Garen'; // Default to Garen since we're tracking him
    let hasActionWord = false;

    // First pass: Look for multi-word matches (like "double you")
    if (lowerTranscript.includes('double you') || lowerTranscript.includes('double u')) {
      ability = 'W';
    }

    // Check for action words to confirm this is an ability use command
    for (const actionWord of ACTION_WORDS) {
      if (lowerTranscript.includes(actionWord)) {
        hasActionWord = true;
        break;
      }
    }

    // Second pass: Check each word for ability or target
    for (let i = 0; i < words.length; i++) {
      const cleanWord = words[i].replace(/[.,!?]/g, '');

      // Check for abilities
      if (!ability && ABILITY_MAPPINGS[cleanWord]) {
        ability = ABILITY_MAPPINGS[cleanWord];
      }

      // Check for targets
      if (TARGET_MAPPINGS[cleanWord]) {
        target = 'Garen'; // Always Garen for now
      }

      // Special handling for phrases like "used his Q" or "pressed Q"
      if ((cleanWord === 'his' || cleanWord === 'her' || cleanWord === 'their') && i + 1 < words.length) {
        const nextWord = words[i + 1].replace(/[.,!?]/g, '');
        if (ABILITY_MAPPINGS[nextWord]) {
          ability = ABILITY_MAPPINGS[nextWord];
        }
      }
    }

    // If we found an ability word but no action word, still accept it if it's a single letter
    if (ability && !hasActionWord) {
      // For single ability letters/words, assume it's a command even without action word
      if (transcript.length <= 15) { // Short commands like "Q" or "Garen Q"
        hasActionWord = true;
      }
    }

    // Debug logging
    console.log('🔍 Parsed:', {
      ability,
      target,
      hasActionWord,
      words: words.join(', ')
    });

    if (ability && (hasActionWord || transcript.length <= 15)) {
      // Send ability_used message to backend
      const message = {
        ability: ability,
        target: target,
        timestamp: Date.now(),
      };

      console.log('📤 Sending ability command to backend:', message);

      try {
        sendMessage('ability_used', message);
        console.log('✅ Message sent successfully');
        setLastCommand(`${target} ${ability} tracked`);
        setError('');

        // Clear last command after 3 seconds
        setTimeout(() => setLastCommand(''), 3000);
      } catch (err) {
        console.error('❌ Failed to send message:', err);
        setError('Not connected to backend');
        setTimeout(() => setError(''), 3000);
      }
    } else {
      console.warn(`⚠️ No ability recognized in: "${transcript}"`);
      console.log('  Expected format: "Enemy Garen used Q" or "Garen Q" or just "Q"');
      setError(`Say something like: "Garen used Q"`);
      setTimeout(() => setError(''), 3000);
    }
  }, []);

  // Start/stop streaming based on isListening prop
  useEffect(() => {
    if (isListening && !isStreamingActive) {
      // Start streaming
      setError('');
      setLastCommand('');
      setInterimTranscript('');

      voiceStreamingService
        .startStreaming({
          onPartial: (text) => {
            console.log('🔄 Partial:', text);
            setInterimTranscript(text);
          },
          onFinal: (text) => {
            console.log('✅ Final:', text);
            setInterimTranscript('');
            parseAndSendCommand(text);
          },
          onError: (errorMsg) => {
            console.error('❌ Error:', errorMsg);
            setError(errorMsg);
            setTimeout(() => setError(''), 3000);
            setIsStreamingActive(false);
            onListeningChange?.(false);
          },
        })
        .then(() => {
          setIsStreamingActive(true);
        })
        .catch((err) => {
          console.error('Failed to start streaming:', err);
          setIsStreamingActive(false);
          onListeningChange?.(false);
        });
    } else if (!isListening && isStreamingActive) {
      // Stop streaming
      voiceStreamingService.stopStreaming();
      setIsStreamingActive(false);
      setInterimTranscript('');
    }
  }, [isListening, isStreamingActive, onListeningChange, parseAndSendCommand]);

  return (
    <div className="fixed bottom-4 right-4 flex flex-col items-end gap-2">
      {/* Listening indicator with interim transcript */}
      {isListening && (
        <div className="bg-red-500/90 text-white px-4 py-2 rounded-lg shadow-lg">
          <div className="flex items-center gap-2 animate-pulse">
            <div className="w-3 h-3 bg-white rounded-full"></div>
            <span className="font-semibold">LISTENING...</span>
          </div>
          {/* Show live interim transcript */}
          {interimTranscript && (
            <div className="mt-1 text-sm text-white/80 italic">
              "{interimTranscript}"
            </div>
          )}
        </div>
      )}

      {/* Last command feedback */}
      {lastCommand && (
        <div className="bg-green-500/90 text-white px-4 py-2 rounded-lg shadow-lg">
          ✓ {lastCommand}
        </div>
      )}

      {/* Error feedback */}
      {error && (
        <div className="bg-yellow-500/90 text-white px-3 py-2 rounded-lg shadow-lg text-sm">
          {error}
        </div>
      )}

      {/* Instructions (when not listening) */}
      {!isListening && !lastCommand && !error && (
        <div className="bg-black/60 text-white/70 px-3 py-2 rounded-lg">
          <div className="text-xs font-semibold mb-1">Hold T to speak</div>
          <div className="text-xs opacity-60">
            Examples: "Garen used Q", "Enemy R", "Flash"
          </div>
        </div>
      )}
    </div>
  );
}
