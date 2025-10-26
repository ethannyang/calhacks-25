/**
 * WebSocket proxy server for Deepgram speech-to-text
 * Keeps API keys secure and handles audio streaming
 */

const WebSocket = require('ws');
const http = require('http');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

const PORT = 8787;
const DEEPGRAM_API_KEY = process.env.DEEPGRAM_API_KEY;

if (!DEEPGRAM_API_KEY) {
  console.error('❌ ERROR: DEEPGRAM_API_KEY not found in environment');
  console.error('   Please add DEEPGRAM_API_KEY=your_key_here to your .env file');
  process.exit(1);
}

// Create HTTP server
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Deepgram Voice Proxy Running\n');
});

// Create WebSocket server
const wss = new WebSocket.Server({ server, path: '/stt' });

console.log(`🎤 Voice proxy server starting on port ${PORT}...`);

wss.on('connection', (clientWs) => {
  console.log('📱 Client connected');

  let deepgramWs = null;
  let format = null;
  let sampleRate = 16000;

  clientWs.on('message', async (data) => {
    // Debug: Log all incoming messages
    console.log('📨 Received message, type:', typeof data, 'isBuffer:', data instanceof Buffer, 'length:', data.length);

    // Handle control messages (JSON) vs audio data (binary)
    if (data instanceof Buffer || data instanceof ArrayBuffer) {
      // Check if this might be a JSON message in a buffer
      if (data.length < 1000) {
        // Small messages are likely JSON, try to parse
        try {
          const text = data.toString();
          const message = JSON.parse(text);
          console.log('📋 Parsed JSON from buffer:', message);

          // Handle format message
          if (message.type === 'format') {
            format = message.format;
            sampleRate = message.sampleRate || 16000;
            const channels = message.channels || 1;

            console.log(`🎧 Format configured: ${format}, ${sampleRate}Hz, ${channels} channel(s)`);

            // Connect to Deepgram
            const deepgramUrl = buildDeepgramUrl(format, sampleRate, channels);
            console.log('🔗 Connecting to Deepgram...');

            deepgramWs = new WebSocket(deepgramUrl, {
              headers: {
                Authorization: `Token ${DEEPGRAM_API_KEY}`,
              },
            });

            deepgramWs.on('open', () => {
              console.log('✅ Deepgram connected');
            });

            deepgramWs.on('message', (dgData) => {
              try {
                const result = JSON.parse(dgData.toString());

                // Deepgram sends results in this format:
                // { type: 'Results', channel: { alternatives: [{ transcript, confidence }] }, is_final }
                if (result.type === 'Results' && result.channel) {
                  const alternative = result.channel.alternatives[0];
                  if (alternative && alternative.transcript) {
                    const transcript = alternative.transcript.trim();

                    if (transcript.length > 0) {
                      const messageType = result.is_final ? 'final' : 'partial';
                      console.log(`📝 ${messageType.toUpperCase()}: "${transcript}"`);

                      // Forward to client
                      clientWs.send(
                        JSON.stringify({
                          type: messageType,
                          text: transcript,
                          confidence: alternative.confidence,
                        })
                      );
                    }
                  }
                } else if (result.type === 'Metadata') {
                  console.log('ℹ️ Deepgram metadata:', result);
                }
              } catch (err) {
                console.error('❌ Error parsing Deepgram response:', err);
              }
            });

            deepgramWs.on('error', (error) => {
              console.error('❌ Deepgram error:', error);
              clientWs.send(
                JSON.stringify({
                  type: 'error',
                  message: 'Speech recognition service error',
                })
              );
            });

            deepgramWs.on('close', (code, reason) => {
              console.log(`🔌 Deepgram disconnected: ${code} ${reason}`);
            });
          } else if (message.type === 'end') {
            console.log('🛑 Client requested end of stream');
            if (deepgramWs && deepgramWs.readyState === WebSocket.OPEN) {
              // Send close frame to finalize transcription
              deepgramWs.send(JSON.stringify({ type: 'CloseStream' }));
              setTimeout(() => deepgramWs.close(), 500);
            }
          }
          return; // Don't treat as audio data
        } catch (e) {
          // Not JSON, must be audio data
          console.log('🎵 Audio data (small buffer)');
        }
      }

      // Binary audio data - forward to Deepgram
      if (deepgramWs && deepgramWs.readyState === WebSocket.OPEN) {
        deepgramWs.send(data);
      }
    } else {
      // JSON control message
      try {
        const message = JSON.parse(data.toString());

        if (message.type === 'format') {
          format = message.format;
          sampleRate = message.sampleRate || 16000;
          const channels = message.channels || 1;

          console.log(`🎧 Format configured: ${format}, ${sampleRate}Hz, ${channels} channel(s)`);

          // Connect to Deepgram
          const deepgramUrl = buildDeepgramUrl(format, sampleRate, channels);
          console.log('🔗 Connecting to Deepgram...');

          deepgramWs = new WebSocket(deepgramUrl, {
            headers: {
              Authorization: `Token ${DEEPGRAM_API_KEY}`,
            },
          });

          deepgramWs.on('open', () => {
            console.log('✅ Deepgram connected');
          });

          deepgramWs.on('message', (dgData) => {
            try {
              const result = JSON.parse(dgData.toString());

              // Deepgram sends results in this format:
              // { type: 'Results', channel: { alternatives: [{ transcript, confidence }] }, is_final }
              if (result.type === 'Results' && result.channel) {
                const alternative = result.channel.alternatives[0];
                if (alternative && alternative.transcript) {
                  const transcript = alternative.transcript.trim();

                  if (transcript.length > 0) {
                    const messageType = result.is_final ? 'final' : 'partial';
                    console.log(`📝 ${messageType.toUpperCase()}: "${transcript}"`);

                    // Forward to client
                    clientWs.send(
                      JSON.stringify({
                        type: messageType,
                        text: transcript,
                        confidence: alternative.confidence,
                      })
                    );
                  }
                }
              } else if (result.type === 'Metadata') {
                console.log('ℹ️ Deepgram metadata:', result);
              }
            } catch (err) {
              console.error('❌ Error parsing Deepgram response:', err);
            }
          });

          deepgramWs.on('error', (error) => {
            console.error('❌ Deepgram error:', error);
            clientWs.send(
              JSON.stringify({
                type: 'error',
                message: 'Speech recognition service error',
              })
            );
          });

          deepgramWs.on('close', (code, reason) => {
            console.log(`🔌 Deepgram disconnected: ${code} ${reason}`);
          });
        } else if (message.type === 'end') {
          console.log('🛑 Client requested end of stream');
          if (deepgramWs && deepgramWs.readyState === WebSocket.OPEN) {
            // Send close frame to finalize transcription
            deepgramWs.send(JSON.stringify({ type: 'CloseStream' }));
            setTimeout(() => deepgramWs.close(), 500);
          }
        }
      } catch (err) {
        console.error('❌ Error parsing client message:', err);
      }
    }
  });

  clientWs.on('close', () => {
    console.log('📱 Client disconnected');
    if (deepgramWs) {
      deepgramWs.close();
    }
  });

  clientWs.on('error', (error) => {
    console.error('❌ Client WebSocket error:', error);
  });
});

/**
 * Build Deepgram WebSocket URL with configuration parameters
 */
function buildDeepgramUrl(format, sampleRate, channels) {
  // Deepgram streaming endpoint
  const baseUrl = 'wss://api.deepgram.com/v1/listen';

  const params = new URLSearchParams({
    // Audio format
    encoding: format === 'pcm_s16le' ? 'linear16' : 'opus',
    sample_rate: sampleRate.toString(),
    channels: channels.toString(),

    // Recognition settings
    model: 'nova-2', // Latest, most accurate model
    language: 'en-US',
    punctuate: 'false', // Disable punctuation for faster responses
    interim_results: 'true', // Enable partial results for live transcription
    endpointing: '300', // Wait 300ms of silence before finalizing (good for short commands)
    vad_events: 'true', // Voice activity detection events

    // Gaming-specific optimizations
    keywords: 'Q:2,W:2,E:2,R:2,flash:2,ignite:2', // Boost ability keywords (weight 2 = 2x more likely)
    smart_format: 'true', // Auto-format numbers, dates, etc.
  });

  return `${baseUrl}?${params.toString()}`;
}

// Start server
server.listen(PORT, () => {
  console.log(`✅ Voice proxy server listening on http://localhost:${PORT}`);
  console.log(`   WebSocket endpoint: ws://localhost:${PORT}/stt`);
  console.log(`   Deepgram API key: ${DEEPGRAM_API_KEY.substring(0, 10)}...`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down voice proxy server...');
  wss.close(() => {
    server.close(() => {
      console.log('✅ Server stopped');
      process.exit(0);
    });
  });
});

process.on('uncaughtException', (error) => {
  console.error('❌ Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Unhandled rejection at:', promise, 'reason:', reason);
});
