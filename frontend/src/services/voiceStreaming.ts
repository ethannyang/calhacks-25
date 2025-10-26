/**
 * Voice streaming service using AudioWorklet + WebSocket proxy
 * Replaces Web Speech API (which doesn't work in Electron)
 */

export interface TranscriptCallback {
  onPartial?: (text: string) => void;
  onFinal?: (text: string) => void;
  onError?: (error: string) => void;
}

class VoiceStreamingService {
  private audioCtx: AudioContext | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private mediaStream: MediaStream | null = null;
  private ws: WebSocket | null = null;
  private callbacks: TranscriptCallback = {};
  private isStreaming = false;

  private readonly PROXY_URL = 'ws://localhost:8787/stt';

  constructor() {
    console.log('[VoiceStreaming] Service initialized');
  }

  /**
   * Start streaming audio to ASR service
   */
  async startStreaming(callbacks: TranscriptCallback): Promise<void> {
    if (this.isStreaming) {
      console.warn('[VoiceStreaming] Already streaming');
      return;
    }

    this.callbacks = callbacks;
    console.log('[VoiceStreaming] Starting audio streaming...');

    try {
      // 1. Get microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000, // Request high sample rate, will resample to 16kHz
        },
        video: false,
      });

      console.log('[VoiceStreaming] Microphone access granted');

      // 2. Create AudioContext
      this.audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 48000,
      });

      // 3. Load AudioWorklet processor
      await this.audioCtx.audioWorklet.addModule('/pcm-resampler-worklet.js');
      console.log('[VoiceStreaming] AudioWorklet loaded');

      // 4. Create worklet node
      const source = this.audioCtx.createMediaStreamSource(this.mediaStream);
      this.workletNode = new AudioWorkletNode(this.audioCtx, 'pcm-resampler', {
        processorOptions: {
          inSampleRate: this.audioCtx.sampleRate,
          outSampleRate: 16000,
          frameMs: 20, // 20ms frames for low latency
        },
      });

      // 5. Connect audio pipeline (source → worklet → destination)
      // Note: We connect to destination to keep the graph alive, but actual output is sent via port messages
      source.connect(this.workletNode);
      this.workletNode.connect(this.audioCtx.destination);

      console.log('[VoiceStreaming] Audio pipeline connected');

      // 6. Connect to WebSocket proxy
      await this.connectWebSocket();

      // 7. Forward audio frames from worklet to WebSocket
      let frameCount = 0;
      this.workletNode.port.onmessage = (event) => {
        frameCount++;
        if (frameCount === 1 || frameCount % 50 === 0) {
          console.log(`[VoiceStreaming] Received audio frame ${frameCount}, size: ${event.data.byteLength} bytes`);
        }
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(event.data); // Send PCM16 binary data
          if (frameCount === 1) {
            console.log('[VoiceStreaming] First audio frame sent to WebSocket');
          }
        } else {
          if (frameCount === 1) {
            console.warn('[VoiceStreaming] WebSocket not open, cannot send audio. State:', this.ws?.readyState);
          }
        }
      };

      this.isStreaming = true;
      console.log('[VoiceStreaming] ✅ Streaming started successfully');
    } catch (error: any) {
      console.error('[VoiceStreaming] ❌ Failed to start streaming:', error);
      this.cleanup();

      // Map common errors to user-friendly messages
      let errorMessage = 'Failed to start voice input';
      if (error.name === 'NotAllowedError') {
        errorMessage = 'Microphone permission denied';
      } else if (error.name === 'NotFoundError') {
        errorMessage = 'No microphone found';
      } else if (error.message && error.message.includes('WebSocket')) {
        errorMessage = 'Cannot connect to voice service';
      }

      this.callbacks.onError?.(errorMessage);
      throw error;
    }
  }

  /**
   * Stop streaming and cleanup resources
   */
  stopStreaming(): void {
    if (!this.isStreaming) {
      console.warn('[VoiceStreaming] Not streaming');
      return;
    }

    console.log('[VoiceStreaming] Stopping streaming...');

    // Send end signal to proxy
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'end' }));
    }

    this.cleanup();
    this.isStreaming = false;
    console.log('[VoiceStreaming] ✅ Streaming stopped');
  }

  /**
   * Check if currently streaming
   */
  isActive(): boolean {
    return this.isStreaming;
  }

  /**
   * Connect to WebSocket proxy server
   */
  private connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log('[VoiceStreaming] Connecting to WebSocket proxy:', this.PROXY_URL);

      this.ws = new WebSocket(this.PROXY_URL);
      this.ws.binaryType = 'arraybuffer';

      // Connection timeout
      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'));
        this.ws?.close();
      }, 5000);

      this.ws.onopen = () => {
        clearTimeout(timeout);
        console.log('[VoiceStreaming] WebSocket connected');

        // Send format configuration
        try {
          const formatMessage = JSON.stringify({
            type: 'format',
            format: 'pcm_s16le',
            sampleRate: 16000,
            channels: 1,
          });
          console.log('[VoiceStreaming] Sending format config:', formatMessage);
          this.ws!.send(formatMessage);
          console.log('[VoiceStreaming] Format config sent successfully');
        } catch (error) {
          console.error('[VoiceStreaming] Failed to send format config:', error);
          reject(error);
          return;
        }

        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('[VoiceStreaming] Received:', message);

          if (message.type === 'partial' && message.text) {
            this.callbacks.onPartial?.(message.text);
          } else if (message.type === 'final' && message.text) {
            this.callbacks.onFinal?.(message.text);
          } else if (message.type === 'error') {
            this.callbacks.onError?.(message.message || 'Speech recognition error');
          }
        } catch (error) {
          console.error('[VoiceStreaming] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        clearTimeout(timeout);
        console.error('[VoiceStreaming] WebSocket error:', error);
        console.error('[VoiceStreaming] WebSocket state:', this.ws?.readyState);
        console.error('[VoiceStreaming] Error type:', error.type);
        console.error('[VoiceStreaming] Error target:', error.target);
        this.callbacks.onError?.('Connection error');
        reject(error);
      };

      this.ws.onclose = (event) => {
        console.log('[VoiceStreaming] WebSocket closed');
        console.log('[VoiceStreaming] Close code:', event.code);
        console.log('[VoiceStreaming] Close reason:', event.reason);
        console.log('[VoiceStreaming] Was clean:', event.wasClean);
        if (this.isStreaming) {
          this.callbacks.onError?.('Connection lost');
          this.stopStreaming();
        }
      };
    });
  }

  /**
   * Cleanup all resources
   */
  private cleanup(): void {
    // Disconnect worklet
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }

    // Close AudioContext
    if (this.audioCtx) {
      this.audioCtx.close();
      this.audioCtx = null;
    }

    // Stop media tracks
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    // Close WebSocket
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Export singleton instance
export const voiceStreamingService = new VoiceStreamingService();
