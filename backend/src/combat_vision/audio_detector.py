"""
Audio-based Ability Detection for League of Legends
Uses audio fingerprinting and pattern matching to detect ability casts
"""

import numpy as np
import pyaudio
from typing import Optional, Dict, List, Tuple
from loguru import logger
import time
from collections import deque
from scipy import signal
from scipy.fft import fft, fftfreq


class AudioAbilityDetector:
    """
    Detects champion abilities using audio signatures
    More reliable than visual detection as it's position-independent
    """

    def __init__(self, sample_rate: int = 44100, chunk_size: int = 2048):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        # PyAudio setup
        self.audio = pyaudio.PyAudio()
        self.stream = None

        # Audio buffer for analysis (5 seconds)
        self.buffer_duration = 5.0
        buffer_samples = int(self.sample_rate * self.buffer_duration)
        self.audio_buffer = deque(maxlen=buffer_samples)

        # Cooldown tracking
        self.last_q_time = 0
        self.last_w_time = 0
        self.last_e_time = 0
        self.last_r_time = 0

        # Detection thresholds
        self.detection_threshold = 0.75  # Confidence threshold

        # Garen ability audio signatures (frequency ranges in Hz)
        # These are approximate and will need tuning
        self.garen_signatures = {
            'Q': {  # Decisive Strike - metallic sword sound
                'freq_range': [(800, 1200), (2000, 3000)],
                'duration': 0.3,  # seconds
                'energy_threshold': 0.6
            },
            'W': {  # Courage - shield activation sound
                'freq_range': [(400, 800), (1500, 2500)],
                'duration': 0.2,
                'energy_threshold': 0.5
            },
            'E': {  # Judgment - spinning sword whoosh
                'freq_range': [(600, 1000), (1800, 2800)],
                'duration': 3.0,  # E lasts 3 seconds
                'energy_threshold': 0.7
            },
            'R': {  # Demacian Justice - dramatic sword drop
                'freq_range': [(200, 600), (3000, 5000)],
                'duration': 0.5,
                'energy_threshold': 0.8
            }
        }

        logger.info("Audio-based ability detector initialized")

    def start_capture(self, device_index: Optional[int] = None):
        """Start capturing system audio"""
        try:
            # If device_index is None, use default input
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,  # Mono
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            self.stream.start_stream()
            logger.info(f"Started audio capture (device: {device_index or 'default'})")
            return True
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            return False

    def stop_capture(self):
        """Stop capturing audio"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        logger.info("Stopped audio capture")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream"""
        if status:
            logger.warning(f"Audio callback status: {status}")

        # Convert bytes to numpy array
        audio_data = np.frombuffer(in_data, dtype=np.float32)

        # Add to buffer
        self.audio_buffer.extend(audio_data)

        return (in_data, pyaudio.paContinue)

    def _compute_spectral_energy(self, audio_chunk: np.ndarray, freq_ranges: List[Tuple[int, int]]) -> float:
        """
        Compute energy in specific frequency bands
        Returns normalized energy (0-1)
        """
        # Compute FFT
        n = len(audio_chunk)
        fft_vals = fft(audio_chunk)
        fft_freq = fftfreq(n, 1 / self.sample_rate)

        # Get magnitude spectrum (only positive frequencies)
        magnitude = np.abs(fft_vals[:n // 2])
        freqs = fft_freq[:n // 2]

        # Calculate energy in specified frequency ranges
        total_energy = 0
        for freq_min, freq_max in freq_ranges:
            mask = (freqs >= freq_min) & (freqs <= freq_max)
            band_energy = np.sum(magnitude[mask] ** 2)
            total_energy += band_energy

        # Normalize by total spectrum energy
        total_spectrum_energy = np.sum(magnitude ** 2)
        if total_spectrum_energy > 0:
            normalized_energy = total_energy / total_spectrum_energy
        else:
            normalized_energy = 0

        return normalized_energy

    def _detect_ability_signature(self, ability: str) -> bool:
        """
        Detect if an ability signature is present in the audio buffer
        """
        if len(self.audio_buffer) < self.chunk_size:
            return False

        signature = self.garen_signatures[ability]
        duration_samples = int(signature['duration'] * self.sample_rate)

        # Get recent audio (ability duration)
        recent_audio = np.array(list(self.audio_buffer)[-duration_samples:])

        # Compute energy in signature frequency ranges
        energy = self._compute_spectral_energy(recent_audio, signature['freq_range'])

        # Check if energy exceeds threshold
        return energy >= signature['energy_threshold']

    def detect_garen_q(self) -> bool:
        """Detect Garen Q (Decisive Strike) audio"""
        now = time.time()

        # Debounce
        if now - self.last_q_time < 2.0:
            return False

        if self._detect_ability_signature('Q'):
            self.last_q_time = now
            logger.info("🗡️  GAREN Q DETECTED (Audio)")
            return True

        return False

    def detect_garen_w(self) -> bool:
        """Detect Garen W (Courage) audio"""
        now = time.time()

        if now - self.last_w_time < 2.0:
            return False

        if self._detect_ability_signature('W'):
            self.last_w_time = now
            logger.info("🛡️  GAREN W DETECTED (Audio)")
            return True

        return False

    def detect_garen_e(self) -> Dict[str, any]:
        """
        Detect Garen E (Judgment) audio
        Returns spinning state and duration
        """
        now = time.time()

        is_spinning = self._detect_ability_signature('E')

        if is_spinning:
            if now - self.last_e_time > 1.0:  # New E cast
                self.last_e_time = now
                logger.info("🌀 GAREN E DETECTED (Audio)")

            duration = now - self.last_e_time
            return {'spinning': True, 'duration': duration}

        return {'spinning': False, 'duration': 0}

    def detect_garen_r(self) -> bool:
        """Detect Garen R (Demacian Justice) audio"""
        now = time.time()

        if now - self.last_r_time < 5.0:
            return False

        if self._detect_ability_signature('R'):
            self.last_r_time = now
            logger.info("⚔️  GAREN R DETECTED (Audio)")
            return True

        return False

    def get_ability_cooldowns(self) -> Dict[str, float]:
        """Get estimated cooldowns (same as visual detector)"""
        now = time.time()

        # These are approximate cooldowns
        return {
            'Q': max(0, 8.0 - (now - self.last_q_time)),
            'W': max(0, 24.0 - (now - self.last_w_time)),
            'E': max(0, 9.0 - (now - self.last_e_time)),
            'R': max(0, 120.0 - (now - self.last_r_time))
        }

    @staticmethod
    def list_audio_devices():
        """List all available audio input devices"""
        audio = pyaudio.PyAudio()
        device_count = audio.get_device_count()

        print("\n=== Available Audio Devices ===")
        for i in range(device_count):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:  # Input device
                print(f"{i}: {info['name']}")
                print(f"   Sample Rate: {info['defaultSampleRate']}")
                print(f"   Input Channels: {info['maxInputChannels']}")

        audio.terminate()
