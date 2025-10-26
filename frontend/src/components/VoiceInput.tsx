/**
 * Voice input component for voice questions to AI coach
 * Uses cloud ASR (Deepgram) via AudioWorklet streaming
 */

import { useEffect, useState, useCallback } from 'react';
import { sendMessage } from '../services/websocket';
import { voiceStreamingService } from '../services/voiceStreaming';

interface VoiceInputProps {
  isListening: boolean;
  onListeningChange?: (listening: boolean) => void;
  onTranscriptChange?: (transcript: string) => void;
}

export default function VoiceInput({ isListening, onListeningChange, onTranscriptChange }: VoiceInputProps) {
  const [isStreamingActive, setIsStreamingActive] = useState(false);

  // No initialization needed - voiceStreamingService is a singleton

  // Send voice transcript to backend as a question
  const parseAndSendCommand = useCallback((transcript: string) => {
    console.log('🎤 Raw transcript:', transcript);

    // Always treat voice input as a question for the AI coach
    console.log('💬 Sending question to AI coach:', transcript);

    try {
      sendMessage('voice_question', {
        text: transcript,
        timestamp: Date.now(),
      });
      console.log('✅ Question sent to backend');
    } catch (err) {
      console.error('❌ Failed to send question:', err);
    }
  }, []);

  // Start/stop streaming based on isListening prop
  useEffect(() => {
    if (isListening && !isStreamingActive) {
      // Start streaming
      voiceStreamingService
        .startStreaming({
          onPartial: (text) => {
            console.log('🔄 Partial:', text);
            onTranscriptChange?.(text); // Update parent with partial transcript
          },
          onFinal: (text) => {
            console.log('✅ Final:', text);
            onTranscriptChange?.(text); // Update parent with final transcript
            parseAndSendCommand(text);
          },
          onError: (errorMsg) => {
            console.error('❌ Error:', errorMsg);
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
      onTranscriptChange?.(''); // Clear transcript in parent
    }
  }, [isListening, isStreamingActive, onListeningChange, onTranscriptChange, parseAndSendCommand]);

  // Return null - UI is now handled in App.tsx
  // This component only handles voice logic
  return null;
}
