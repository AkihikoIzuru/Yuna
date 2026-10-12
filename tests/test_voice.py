"""Tests for voice module: wake word detection, STT, TTS."""

import logging
import numpy as np
from unittest.mock import MagicMock, patch

logger = logging.getLogger(__name__)


class TestWhisperWakeBackend:
    """Test Whisper wake word backend."""

    def test_fuzzy_match_exact(self):
        """Test exact match returns 1.0."""
        from yuna.voice.wake import WhisperWakeBackend
        backend = WhisperWakeBackend(phrases=["hey yuna", "yuna"])
        score, phrase = backend._fuzzy_match("hey yuna")
        assert score == 1.0
        assert phrase == "hey yuna"

    def test_fuzzy_match_partial(self):
        """Test partial match returns high score."""
        from yuna.voice.wake import WhisperWakeBackend
        backend = WhisperWakeBackend(phrases=["yuna"])
        score, phrase = backend._fuzzy_match("yu na")
        # Check substring match (should match with similarity)
        assert score >= 0.5  # word overlap gives 1.0/2 = 0.5
        assert phrase == "yuna"

    def test_fuzzy_match_no_match(self):
        """Test no match returns 0.0."""
        from yuna.voice.wake import WhisperWakeBackend
        backend = WhisperWakeBackend(phrases=["yuna"])
        score, phrase = backend._fuzzy_match("random noise")
        # Word overlap should be 0
        assert score < 0.5

    def test_is_available(self):
        """Test is_available returns True."""
        from yuna.voice.wake import WhisperWakeBackend
        backend = WhisperWakeBackend()
        assert backend.is_available() is True

    def test_detect_no_speech(self):
        """Test detect returns False when no speech."""
        from yuna.voice.wake import WhisperWakeBackend
        backend = WhisperWakeBackend(phrases=["yuna"])
        # Mock model loading to avoid actually loading Whisper
        backend._load_model = lambda: None
        backend._model = MagicMock()
        backend._vad = None  # Force volume-based VAD

        # Generate silent audio (volume < 0.01)
        silent_audio = np.zeros(16000, dtype=np.float32)
        result = backend.detect(silent_audio)
        assert result.detected is False

        # Generate very quiet audio
        quiet_audio = np.ones(16000, dtype=np.float32) * 0.001
        result = backend.detect(quiet_audio)
        assert result.detected is False

    def test_detect_with_speech_mock(self):
        """Test detect with mocked whisper."""
        from yuna.voice.wake import WhisperWakeBackend
        backend = WhisperWakeBackend(phrases=["hey yuna"])

        # Mock whisper model
        mock_segment = MagicMock()
        mock_segment.text = "hey yuna"

        # Setup mock before calling detect
        backend._load_model = lambda: None
        backend._model = MagicMock()
        backend._model.transcribe.return_value = ([mock_segment], None)

        # Generate some audio
        audio = np.random.randn(16000).astype(np.float32) * 0.5
        result = backend.detect(audio)
        assert result.detected is True
        assert result.phrase == "hey yuna"
        assert result.score >= 0.7


class TestTTS:
    """Test TTS module."""

    def test_split_sentences(self):
        """Test sentence splitting."""
        from yuna.voice.tts import TTS
        tts = TTS()

        text = "Hello world. How are you? I am fine!"
        sentences = tts._split_sentences(text)
        assert len(sentences) >= 2
        assert any("Hello" in s for s in sentences)
        assert any("fine" in s.lower() for s in sentences)

    def test_split_sentences_single(self):
        """Test single sentence."""
        from yuna.voice.tts import TTS
        tts = TTS()

        text = "Just one sentence."
        sentences = tts._split_sentences(text)
        assert len(sentences) == 1
        assert "sentence" in sentences[0]

    def test_default_voice(self):
        """Test default voice settings."""
        from yuna.voice.tts import TTS
        tts = TTS()
        assert tts.voice == "id-ID-GadisNeural"
        assert tts.rate == "+3%"
        assert tts.pitch == "+3Hz"

    def test_custom_voice(self):
        """Test custom voice settings."""
        from yuna.voice.tts import TTS
        tts = TTS(voice="id-ID-GadisNeural", rate="+3%", pitch="+3Hz")
        assert tts.voice == "id-ID-GadisNeural"
        assert tts.rate == "+3%"
        assert tts.pitch == "+3Hz"


class TestSTT:
    """Test STT module."""

    def test_default_model(self):
        """Test default STT model size."""
        from yuna.voice.stt import STT
        stt = STT()
        assert stt.model_size == "small"
        assert stt.language == "id"
        assert stt.device == "cpu"

    def test_custom_model(self):
        """Test custom model size."""
        from yuna.voice.stt import STT
        stt = STT(model_size="tiny")
        assert stt.model_size == "tiny"

    def test_is_speech_fallback(self):
        """Test is_speech returns True when VAD not available."""
        from yuna.voice.stt import STT
        stt = STT()
        # Mock _load_vad to prevent it from loading webrtcvad
        stt._load_vad = lambda: None
        stt._vad = None  # Force no VAD
        # Should return True (fallback)
        result = stt.is_speech(b"\x00" * 320, sample_rate=16000)
        assert result is True


class TestWakeDetectorFactory:
    """Test wake detector factory functions."""

    def test_get_wake_detector_whisper(self):
        """Test getting whisper backend."""
        from yuna.voice.wake import get_wake_detector, reset_wake_detector
        reset_wake_detector()
        detector = get_wake_detector(backend="whisper", phrases=["yuna"])
        assert detector is not None
        assert detector.get_name() == "whisper"
        reset_wake_detector()

    def test_get_wake_detector_auto(self):
        """Test auto backend selects whisper."""
        from yuna.voice.wake import get_wake_detector, reset_wake_detector
        reset_wake_detector()
        detector = get_wake_detector(backend="auto", phrases=["yuna"])
        assert detector is not None
        assert detector.get_name() == "whisper"
        reset_wake_detector()

    def test_reset_wake_detector(self):
        """Test reset clears global."""
        from yuna.voice.wake import get_wake_detector, reset_wake_detector
        reset_wake_detector()
        detector = get_wake_detector(backend="whisper")
        assert detector is not None
        reset_wake_detector()
        # After reset, should create new instance
        detector2 = get_wake_detector(backend="whisper")
        assert detector2 is not None

    def test_push_to_talk_creation(self):
        """Test push-to-talk creation."""
        from yuna.voice.wake import get_push_to_talk
        ptt = get_push_to_talk(hotkey="space")
        assert ptt is not None
        assert ptt.hotkey == "space"


class TestVoiceLoopInit:
    """Test VoiceLoop initialization."""

    def test_init_wake_mode(self):
        """Test voice loop init in wake mode."""
        from yuna.voice.loop import VoiceLoop
        loop = VoiceLoop(mode="wake", wake_word="hey yuna")
        assert loop.mode == "wake"
        assert loop.wake_word == "hey yuna"
        assert loop.wake_detector is not None
        assert loop.push_to_talk is None

    def test_init_push_mode(self):
        """Test voice loop init in push mode."""
        from yuna.voice.loop import VoiceLoop
        loop = VoiceLoop(mode="push", hotkey="space")
        assert loop.mode == "push"
        assert loop.wake_detector is None
        assert loop.push_to_talk is not None

    def test_default_sample_rate(self):
        """Test default sample rate."""
        from yuna.voice.loop import VoiceLoop
        loop = VoiceLoop()
        assert loop.sample_rate == 16000
        assert loop.chunk_size == 8000  # 0.5s at 16kHz
