"""
Template-based Audio Detection for Garen Abilities
Uses cross-correlation with actual ability sound files for accurate detection
"""

import numpy as np
import pyaudio
from typing import Optional, Dict, Tuple
from loguru import logger
import time
from collections import deque
from scipy import signal
from scipy.io import wavfile
import os


class AudioTemplateDetector:
    """
    Detects Garen abilities using template matching with actual ability audio files
    Much more accurate than frequency-based detection
    """

    def __init__(self,
                 audio_files: Dict[str, str],
                 sample_rate: int = 44100,
                 chunk_size: int = 2048,
                 threshold: float = 0.6):
        """
        Initialize detector with audio template files

        Args:
            audio_files: Dict mapping ability name to audio file path
                        e.g. {'Q': 'path/to/q.wav', 'W': 'path/to/w.wav', ...}
            sample_rate: Audio capture sample rate
            chunk_size: Audio buffer chunk size
            threshold: Correlation threshold for detection (0-1)
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.threshold = threshold

        # PyAudio setup
        self.audio = pyaudio.PyAudio()
        self.stream = None

        # Load audio templates
        self.templates = {}
        self.template_durations = {}
        self._load_templates(audio_files)

        # Audio buffer for analysis (store 10 seconds)
        self.buffer_duration = 10.0
        buffer_samples = int(self.sample_rate * self.buffer_duration)
        self.audio_buffer = deque(maxlen=buffer_samples)

        # Cooldown tracking
        self.last_q_time = 0
        self.last_w_time = 0
        self.last_e_time = 0
        self.last_r_time = 0

        # Minimum cooldowns to prevent spam detection
        self.min_cooldowns = {
            'Q': 1.0,  # At least 1 second between Q detections
            'W': 1.0,
            'E': 2.0,  # E lasts 3 seconds
            'R': 2.0
        }

        logger.info(f"Audio template detector initialized with {len(self.templates)} templates")

    def _load_templates(self, audio_files: Dict[str, str]):
        """Load audio templates from WAV files"""
        for ability, file_path in audio_files.items():
            try:
                if not os.path.exists(file_path):
                    logger.error(f"Audio file not found: {file_path}")
                    continue

                # Load WAV file
                template_rate, template_data = wavfile.read(file_path)

                # Convert to mono if stereo
                if len(template_data.shape) > 1:
                    template_data = np.mean(template_data, axis=1)

                # Convert to float32 and normalize
                if template_data.dtype == np.int16:
                    template_data = template_data.astype(np.float32) / 32768.0
                elif template_data.dtype == np.int32:
                    template_data = template_data.astype(np.float32) / 2147483648.0
                else:
                    template_data = template_data.astype(np.float32)

                # Resample if needed
                if template_rate != self.sample_rate:
                    num_samples = int(len(template_data) * self.sample_rate / template_rate)
                    template_data = signal.resample(template_data, num_samples)
                    logger.info(f"Resampled {ability} from {template_rate}Hz to {self.sample_rate}Hz")

                # Normalize template
                template_data = template_data / (np.max(np.abs(template_data)) + 1e-10)

                self.templates[ability] = template_data
                self.template_durations[ability] = len(template_data) / self.sample_rate

                logger.info(f"Loaded template for {ability}: {len(template_data)} samples ({self.template_durations[ability]:.2f}s)")

            except Exception as e:
                logger.error(f"Failed to load template {ability} from {file_path}: {e}")

    def start_capture(self, device_index: Optional[int] = None):
        """Start capturing system audio"""
        try:
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
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

    def _cross_correlate(self, template: np.ndarray) -> Tuple[float, int]:
        """
        Perform cross-correlation between template and audio buffer
        Returns (max_correlation, position)
        """
        if len(self.audio_buffer) < len(template):
            return 0.0, 0

        # Get recent audio
        buffer_array = np.array(list(self.audio_buffer))

        # Normalize buffer
        buffer_array = buffer_array / (np.max(np.abs(buffer_array)) + 1e-10)

        # Compute cross-correlation using FFT (much faster)
        correlation = signal.correlate(buffer_array, template, mode='valid', method='fft')

        # Normalize correlation
        template_energy = np.sum(template ** 2)
        buffer_energy = np.array([
            np.sum(buffer_array[i:i + len(template)] ** 2)
            for i in range(len(correlation))
        ])

        normalized_correlation = correlation / (np.sqrt(template_energy * buffer_energy) + 1e-10)

        # Find maximum correlation
        max_idx = np.argmax(normalized_correlation)
        max_corr = normalized_correlation[max_idx]

        return max_corr, max_idx

    def _detect_ability(self, ability: str, last_time: float) -> bool:
        """
        Detect if an ability is present in the audio buffer
        """
        now = time.time()

        # Check cooldown
        if now - last_time < self.min_cooldowns[ability]:
            return False

        # Check if template exists
        if ability not in self.templates:
            return False

        template = self.templates[ability]

        # Perform cross-correlation
        max_corr, position = self._cross_correlate(template)

        # Check if correlation exceeds threshold
        if max_corr >= self.threshold:
            # Check if this is a recent match (within last 0.5 seconds of buffer)
            buffer_len = len(self.audio_buffer)
            samples_per_sec = self.sample_rate
            recent_threshold = buffer_len - int(0.5 * samples_per_sec)

            if position >= recent_threshold:
                logger.info(f"Detected {ability} with correlation {max_corr:.3f} at position {position}")
                return True

        return False

    def detect_garen_q(self) -> bool:
        """Detect Garen Q (Decisive Strike)"""
        if self._detect_ability('Q', self.last_q_time):
            self.last_q_time = time.time()
            logger.info("🗡️  GAREN Q DETECTED (Template Match)")
            return True
        return False

    def detect_garen_w(self) -> bool:
        """Detect Garen W (Courage)"""
        if self._detect_ability('W', self.last_w_time):
            self.last_w_time = time.time()
            logger.info("🛡️  GAREN W DETECTED (Template Match)")
            return True
        return False

    def detect_garen_e(self) -> Dict[str, any]:
        """Detect Garen E (Judgment) - spinning state"""
        now = time.time()

        # Check if E was recently detected and still spinning
        e_duration = now - self.last_e_time

        if e_duration < 3.0 and self.last_e_time > 0:
            # E is still active (lasts 3 seconds)
            return {'spinning': True, 'duration': e_duration}

        # Try to detect new E cast
        if self._detect_ability('E', self.last_e_time):
            self.last_e_time = now
            logger.info("🌀 GAREN E DETECTED (Template Match)")
            return {'spinning': True, 'duration': 0.0}

        return {'spinning': False, 'duration': 0}

    def detect_garen_r(self) -> bool:
        """Detect Garen R (Demacian Justice)"""
        if self._detect_ability('R', self.last_r_time):
            self.last_r_time = time.time()
            logger.info("⚔️  GAREN R DETECTED (Template Match)")
            return True
        return False

    def get_ability_cooldowns(self) -> Dict[str, float]:
        """Get estimated cooldowns (approximate game values)"""
        now = time.time()
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
            if info['maxInputChannels'] > 0:
                print(f"{i}: {info['name']}")
                print(f"   Sample Rate: {info['defaultSampleRate']}")
                print(f"   Input Channels: {info['maxInputChannels']}")

        audio.terminate()
