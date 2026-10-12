"""Speech-to-Text menggunakan faster-whisper dengan VAD."""

import logging
import numpy as np
from typing import Optional
import io

logger = logging.getLogger(__name__)


class STT:
    """Speech-to-Text handler menggunakan faster-whisper."""

    def __init__(
        self,
        model_size: str = "small",
        language: str = "id",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        """
        Initialize STT.

        Args:
            model_size: Model size (tiny, base, small, medium, large)
            language: Language code (id untuk Indonesia)
            device: cpu atau cuda
            compute_type: int8, float16, float32
        """
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._vad = None

    def _load_model(self):
        """Lazy load model faster-whisper."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Loading faster-whisper model: {self.model_size}")
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                logger.info("Faster-whisper model loaded")
            except Exception as e:
                logger.error(f"Failed to load faster-whisper: {e}")
                raise

    def _load_vad(self):
        """Load VAD (Voice Activity Detection)."""
        if self._vad is None:
            try:
                import webrtcvad
                self._vad = webrtcvad.Vad(3)  # aggressiveness 0-3, 3 = most aggressive
                logger.info("WebRTC VAD loaded")
            except Exception as e:
                logger.warning(f"Failed to load WebRTC VAD: {e}")
                self._vad = None

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio ke teks.

        Args:
            audio_data: Audio array (float32, mono)
            sample_rate: Sample rate audio

        Returns:
            Teks transkrip
        """
        self._load_model()

        try:
            # Faster-whisper expects float32 audio
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Transcribe
            segments, info = self._model.transcribe(
                audio_data,
                language=self.language,
                beam_size=5,
                vad_filter=True,  # built-in VAD
                vad_parameters={
                    "threshold": 0.5,
                    "min_speech_duration_ms": 250,
                    "max_speech_duration_s": 30,
                    "min_silence_duration_ms": 500,
                    "speech_pad_ms": 400,
                },
            )

            # Combine all segments
            text = " ".join([segment.text for segment in segments]).strip()

            logger.info(f"Transcribed: {text}")
            return text

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    def is_speech(self, audio_chunk: bytes, sample_rate: int = 16000) -> bool:
        """
        Deteksi apakah audio chunk mengandung speech (VAD).

        Args:
            audio_chunk: Raw audio bytes (PCM 16-bit)
            sample_rate: Sample rate (8000, 16000, 32000, 48000)

        Returns:
            True jika terdeteksi speech
        """
        self._load_vad()

        if self._vad is None:
            return True  # fallback: assume speech

        try:
            # WebRTC VAD needs specific sample rates and frame sizes
            # Frame size: 10, 20, 30 ms
            # For 16kHz: 320 bytes (20ms), 160 bytes (10ms)
            return self._vad.is_speech(audio_chunk, sample_rate)
        except Exception as e:
            logger.debug(f"VAD error: {e}")
            return True  # fallback


# Global instance
_stt: Optional[STT] = None


def get_stt(model_size: str = "small") -> STT:
    """Get global STT instance."""
    global _stt
    if _stt is None:
        _stt = STT(model_size=model_size)
    return _stt