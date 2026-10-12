"""Wake word detection dengan multiple backend: whisper-first (default), porcupine, openwakeword.
Push-to-talk sebagai fallback."""

import logging
import numpy as np
from typing import Optional, Callable, List
import threading
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WakeWordResult:
    """Hasil deteksi wake word."""
    detected: bool
    phrase: str = ""
    score: float = 0.0
    backend: str = ""


class WakeWordBackend(ABC):
    """Abstract base class untuk wake word backend."""

    @abstractmethod
    def detect(self, audio_chunk: np.ndarray) -> WakeWordResult:
        """Deteksi wake word dalam audio chunk."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Nama backend."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Apakah backend tersedia (dependencies terinstall)."""
        pass


class WhisperWakeBackend(WakeWordBackend):
    """Wake word detection menggunakan faster-whisper (tanpa dependency baru).

    Alur: VAD -> transkripsi chunk suara -> fuzzy match ke WAKE_PHRASES.
    """

    def __init__(
        self,
        phrases: List[str] = None,
        threshold: float = 0.7,
        sample_rate: int = 16000,
    ):
        self.phrases = [p.lower() for p in phrases] if phrases else ["hey aki", "hey Yuna", "yuna"]
        self.threshold = threshold
        self.sample_rate = sample_rate

        self._model = None
        self._vad = None
        self._buffer = []
        self._buffer_duration = 0
        self._max_buffer_duration = 3.0  # detik
        self._last_text = ""  # For test mode

    def _load_model(self):
        """Lazy load faster-whisper."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info("Loading Whisper model for wake word (tiny)...")
                self._model = WhisperModel("tiny", device="cpu", compute_type="int8")
                logger.info("Whisper model loaded")
            except Exception as e:
                logger.error(f"Failed to load Whisper: {e}")
                raise

    def _load_vad(self):
        """Load VAD."""
        if self._vad is None:
            try:
                import webrtcvad
                self._vad = webrtcvad.Vad(2)
                logger.info("WebRTC VAD loaded")
            except Exception as e:
                logger.warning(f"WebRTC VAD not available: {e}")
                self._vad = None

    def is_available(self) -> bool:
        return True  # faster-whisper sudah terinstall

    def get_name(self) -> str:
        return "whisper"

    def _fuzzy_match(self, text: str) -> tuple[float, str]:
        """Fuzzy match teks ke wake phrases."""
        text = text.lower().strip()
        best_score = 0.0
        best_phrase = ""

        for phrase in self.phrases:
            # Simple fuzzy match: common subsequence
            score = self._similarity(text, phrase)
            if score > best_score:
                best_score = score
                best_phrase = phrase

        return best_score, best_phrase

    def _similarity(self, a: str, b: str) -> float:
        """Simple similarity ratio."""
        if a == b:
            return 1.0

        # Check if b is substring of a or vice versa
        if b in a or a in b:
            return 0.8

        # Normalize: remove spaces for comparison
        a_no_space = a.replace(" ", "")
        b_no_space = b.replace(" ", "")
        if a_no_space == b_no_space:
            return 0.9
        if b_no_space in a_no_space or a_no_space in b_no_space:
            return 0.75

        # Word overlap
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def detect(self, audio_chunk: np.ndarray) -> WakeWordResult:
        """Deteksi wake word menggunakan Whisper + VAD."""
        self._load_model()
        self._load_vad()

        # Convert to float32
        if audio_chunk.dtype == np.int16:
            audio_chunk = audio_chunk.astype(np.float32) / 32768.0

        # VAD check
        has_speech = False
        if self._vad:
            try:
                # WebRTC VAD needs 16-bit PCM at specific rates
                pcm16 = (audio_chunk * 32768).astype(np.int16)
                frame_size = 320  # 20ms at 16kHz
                for i in range(0, len(pcm16) - frame_size, frame_size):
                    frame = pcm16[i:i+frame_size].tobytes()
                    if self._vad.is_speech(frame, self.sample_rate):
                        has_speech = True
                        break
            except:
                has_speech = True  # fallback
        else:
            # Simple volume-based VAD
            volume = np.abs(audio_chunk).mean()
            has_speech = volume > 0.01

        if not has_speech:
            return WakeWordResult(detected=False)

        # Add to buffer
        self._buffer.append(audio_chunk)
        self._buffer_duration += len(audio_chunk) / self.sample_rate

        # Keep buffer limited
        while self._buffer_duration > self._max_buffer_duration:
            removed = self._buffer.pop(0)
            self._buffer_duration -= len(removed) / self.sample_rate

        # Only transcribe if we have enough audio
        if self._buffer_duration < 0.5:  # at least 500ms
            return WakeWordResult(detected=False)

        # Transcribe buffer
        try:
            combined = np.concatenate(self._buffer)
            segments, _ = self._model.transcribe(
                combined,
                language="id",
                beam_size=1,
                vad_filter=False,
            )

            text = " ".join([s.text for s in segments]).strip()

            if not text:
                return WakeWordResult(detected=False)

            self._last_text = text  # Store for test mode
            logger.debug(f"Whisper heard: '{text}'")

            score, phrase = self._fuzzy_match(text)

            if score >= self.threshold:
                logger.info(f"Wake word detected: '{phrase}' (score: {score:.2f}, text: '{text}')")
                # Clear buffer after detection
                self._buffer = []
                self._buffer_duration = 0
                return WakeWordResult(detected=True, phrase=phrase, score=score, backend="whisper")

            return WakeWordResult(detected=False)

        except Exception as e:
            logger.debug(f"Whisper detection error: {e}")
            return WakeWordResult(detected=False)


class PorcupineWakeBackend(WakeWordBackend):
    """Wake word detection menggunakan pvporcupine (opsional)."""

    def __init__(self, access_key: str = None, keywords: List[str] = None):
        self.access_key = access_key
        self.keywords = keywords or ["yuna", "hey Yuna", "hey aki"]
        self._handle = None
        self._sample_rate = 16000

    def is_available(self) -> bool:
        try:
            import pvporcupine
            return True
        except ImportError:
            return False

    def get_name(self) -> str:
        return "porcupine"

    def _load_model(self):
        if self._handle is None:
            try:
                import pvporcupine
                if not self.access_key:
                    logger.warning("Porcupine access key not provided")
                    return False

                self._handle = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=self.keywords,
                )
                self._sample_rate = self._handle.sample_rate
                logger.info(f"Porcupine loaded: {self.keywords}")
                return True
            except Exception as e:
                logger.error(f"Failed to load Porcupine: {e}")
                return False

    def detect(self, audio_chunk: np.ndarray) -> WakeWordResult:
        if not self._load_model():
            return WakeWordResult(detected=False)

        try:
            if audio_chunk.dtype == np.float32:
                audio_chunk = (audio_chunk * 32768).astype(np.int16)

            keyword_index = self._handle.process(audio_chunk)
            if keyword_index >= 0:
                keyword = self._handle.keyword_labels[keyword_index]
                logger.info(f"Wake word detected: '{keyword}' (porcupine)")
                return WakeWordResult(detected=True, phrase=keyword, score=1.0, backend="porcupine")

            return WakeWordResult(detected=False)
        except Exception as e:
            logger.error(f"Porcupine detection error: {e}")
            return WakeWordResult(detected=False)


class OpenWakeWordBackend(WakeWordBackend):
    """Wake word detection menggunakan openWakeWord (opsional)."""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self._model = None

    def is_available(self) -> bool:
        try:
            import openwakeword
            return True
        except ImportError:
            return False

    def get_name(self) -> str:
        return "openwakeword"

    def _load_model(self):
        if self._model is None:
            try:
                from openwakeword.model import Model
                logger.info("Loading openWakeWord model...")
                self._model = Model(wakeword_models=["hey_Yuna"])
                logger.info("openWakeWord model loaded")
            except Exception as e:
                logger.error(f"Failed to load openWakeWord: {e}")
                raise

    def detect(self, audio_chunk: np.ndarray) -> WakeWordResult:
        self._load_model()

        try:
            if audio_chunk.dtype == np.int16:
                audio_chunk = audio_chunk.astype(np.float32) / 32768.0

            predictions = self._model.predict(audio_chunk)

            for model_name, score in predictions.items():
                if score >= self.threshold:
                    logger.info(f"Wake word detected: {model_name} (score: {score:.2f})")
                    return WakeWordResult(detected=True, phrase=model_name, score=score, backend="openwakeword")

            return WakeWordResult(detected=False)
        except Exception as e:
            logger.error(f"openWakeWord detection error: {e}")
            return WakeWordResult(detected=False)


class PushToTalk:
    """Push-to-talk mode dengan hotkey."""

    def __init__(self, hotkey: str = "space"):
        self.hotkey = hotkey
        self._pressed = False
        self._callbacks = []
        self._listener_thread = None
        self._running = False

    def start(self, on_press: Optional[Callable] = None, on_release: Optional[Callable] = None):
        if on_press:
            self._callbacks.append(("press", on_press))
        if on_release:
            self._callbacks.append(("release", on_release))

        self._running = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()
        logger.info(f"Push-to-talk started (hotkey: {self.hotkey})")

    def _listen_loop(self):
        try:
            from pynput import keyboard

            def on_press(key):
                try:
                    key_str = str(key).replace("'", "").lower()
                    if self.hotkey in key_str or (hasattr(key, 'char') and key.char == self.hotkey):
                        if not self._pressed:
                            self._pressed = True
                            for event, callback in self._callbacks:
                                if event == "press":
                                    callback()
                except Exception as e:
                    logger.debug(f"Key press error: {e}")

            def on_release(key):
                try:
                    key_str = str(key).replace("'", "").lower()
                    if self.hotkey in key_str or (hasattr(key, 'char') and key.char == self.hotkey):
                        if self._pressed:
                            self._pressed = False
                            for event, callback in self._callbacks:
                                if event == "release":
                                    callback()
                except Exception as e:
                    logger.debug(f"Key release error: {e}")

            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                while self._running:
                    time.sleep(0.1)
        except ImportError:
            logger.error("pynput not installed. Push-to-talk tidak tersedia.")
        except Exception as e:
            logger.error(f"Push-to-talk listener error: {e}")

    def stop(self):
        self._running = False
        if self._listener_thread:
            self._listener_thread.join(timeout=2)
        logger.info("Push-to-talk stopped")

    @property
    def is_pressed(self) -> bool:
        return self._pressed


# Global instances
_wake_detector = None
_wake_backend = None
_push_to_talk = None


def get_wake_detector(
    backend: str = "auto",
    phrases: List[str] = None,
    threshold: float = 0.7,
    porcupine_key: str = None,
) -> Optional[WakeWordBackend]:
    """Get wake word detector dengan backend yang dipilih."""
    global _wake_detector, _wake_backend

    if _wake_detector is not None:
        return _wake_detector

    # Determine backend
    if backend == "auto":
        # Try whisper first (always available)
        _wake_backend = "whisper"
    elif backend in ("whisper", "porcupine", "openwakeword"):
        _wake_backend = backend
    else:
        _wake_backend = "whisper"

    logger.info(f"Selected wake word backend: {_wake_backend}")

    if _wake_backend == "whisper":
        _wake_detector = WhisperWakeBackend(phrases=phrases, threshold=threshold)
    elif _wake_backend == "porcupine":
        if PorcupineWakeBackend().is_available():
            _wake_detector = PorcupineWakeBackend(access_key=porcupine_key, keywords=phrases)
        else:
            logger.warning("Porcupine not available, falling back to Whisper")
            _wake_detector = WhisperWakeBackend(phrases=phrases, threshold=threshold)
    elif _wake_backend == "openwakeword":
        if OpenWakeWordBackend().is_available():
            _wake_detector = OpenWakeWordBackend(threshold=threshold)
        else:
            logger.warning("openWakeWord not available, falling back to Whisper")
            _wake_detector = WhisperWakeBackend(phrases=phrases, threshold=threshold)

    return _wake_detector


def get_push_to_talk(hotkey: str = "space") -> PushToTalk:
    """Get global push-to-talk instance."""
    global _push_to_talk
    if _push_to_talk is None:
        _push_to_talk = PushToTalk(hotkey=hotkey)
    return _push_to_talk


# For testing
def reset_wake_detector():
    global _wake_detector, _wake_backend
    _wake_detector = None
    _wake_backend = None
