/**
 * AudioWorklet processor for real-time audio resampling to 16kHz PCM
 * Captures microphone input and converts it to format suitable for ASR
 */

class PcmResampler extends AudioWorkletProcessor {
  constructor(options) {
    super();

    const { inSampleRate, outSampleRate, frameMs } = options.processorOptions || {};
    this.inSR = inSampleRate || 48000;
    this.outSR = outSampleRate || 16000;
    this.frameSamples = Math.round((this.outSR * (frameMs || 20)) / 1000);
    this.tail = new Float32Array(0);

    console.log(`[PCM Resampler] Initialized: ${this.inSR}Hz → ${this.outSR}Hz, ${frameMs}ms frames (${this.frameSamples} samples)`);
  }

  static get parameterDescriptors() {
    return [];
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) {
      return true;
    }

    // Get mono channel (take first channel if stereo)
    const chunk = input[0];

    // Concatenate with tail from previous process call
    const mono = new Float32Array(this.tail.length + chunk.length);
    mono.set(this.tail, 0);
    mono.set(chunk, this.tail.length);

    // Resample using linear interpolation
    const ratio = this.outSR / sampleRate;
    const outLen = Math.floor(mono.length * ratio);
    const resampled = new Float32Array(outLen);

    for (let i = 0; i < outLen; i++) {
      const idx = i / ratio;
      const i0 = Math.floor(idx);
      const i1 = Math.min(i0 + 1, mono.length - 1);
      const t = idx - i0;
      resampled[i] = mono[i0] * (1 - t) + mono[i1] * t;
    }

    // Split resampled audio into frames and convert to PCM16
    let offset = 0;
    while (offset + this.frameSamples <= resampled.length) {
      const frame = resampled.subarray(offset, offset + this.frameSamples);

      // Convert Float32 to Int16 PCM
      const pcm = new ArrayBuffer(frame.length * 2);
      const view = new DataView(pcm);

      for (let i = 0; i < frame.length; i++) {
        // Clamp to [-1, 1] and convert to 16-bit integer
        let s = Math.max(-1, Math.min(1, frame[i]));
        view.setInt16(i * 2, (s * 0x7fff) | 0, true); // little-endian
      }

      // Send PCM frame to main thread
      this.port.postMessage(pcm, [pcm]);
      offset += this.frameSamples;
    }

    // Keep leftover samples for next process call
    this.tail = resampled.subarray(offset);

    return true; // Keep processor alive
  }
}

registerProcessor('pcm-resampler', PcmResampler);
