"""Main voice loop: wake â†’ rekam â†’ STT â†’ agent â†’ TTS + barge-in."""

import asyncio
import logging
import numpy as np
import sounddevice as sd
from typing import Optional
import time
from collections import deque

from yuna.voice.stt import get_stt
from yuna.voice.tts import get_tts
from yuna.voice.wake import get_wake_detector, get_push_to_talk, reset_wake_detector
from yuna.brain.agent import get_agent
from yuna.memory import ConversationHistory, ReminderManager
from yuna.config import get_config

logger = logging.getLogger(__name__)


def play_chime(sample_rate: int = 16000):
    """Play a simple chime sound (two-tone beep)."""
    try:
        # Generate two-tone chime: 880Hz (A5) then 1320Hz (E6)
        duration = 0.1  # seconds per tone
        t = np.linspace(0, duration, int(sample_rate * duration), False)

        # First tone: 880Hz
        tone1 = 0.3 * np.sin(2 * np.pi * 880 * t)
        # Second tone: 1320Hz
        tone2 = 0.3 * np.sin(2 * np.pi * 1320 * t)

        # Combine with a small gap
        gap = np.zeros(int(sample_rate * 0.05))
        chime = np.concatenate([tone1, gap, tone2]).astype(np.float32)

        sd.play(chime, sample_rate)
        sd.wait()
    except Exception as e:
        logger.debug(f"Chime playback failed: {e}")


class VoiceLoop:
    """Main voice loop untuk Yuna."""

    def __init__(
        self,
        mode: str = "wake",  # "wake" atau "push"
        sample_rate: int = 16000,
        chunk_duration: float = 0.5,  # detik
        silence_duration: float = 1.5,  # detik untuk deteksi akhir bicara
        wake_word: str = "hey aki",
        hotkey: str = "space",
        test_wake: bool = False,
    ):
        """
        Initialize voice loop.

        Args:
            mode: Mode operasi ("wake" untuk wake word, "push" untuk push-to-talk)
            sample_rate: Sample rate audio (16000 Hz recommended)
            chunk_duration: Durasi per chunk audio
            silence_duration: Durasi silence untuk deteksi akhir bicara
            wake_word: Wake word phrase
            hotkey: Hotkey untuk push-to-talk
            test_wake: Test mode - print detected text and scores without processing
        """
        self.mode = mode
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * chunk_duration)
        self.silence_chunks = int(silence_duration / chunk_duration)
        self.wake_word = wake_word
        self.hotkey = hotkey
        self.test_wake = test_wake

        # Load config for TTS and wake settings
        config = get_config()
        self.tts_voice = config.tts_voice
        self.tts_rate = config.tts_rate
        self.tts_pitch = config.tts_pitch
        self.wake_backend = config.wake_backend
        self.wake_phrases = config.wake_phrases

        # Components
        self.stt = get_stt()
        self.tts = get_tts(voice=self.tts_voice, rate=self.tts_rate, pitch=self.tts_pitch)

        # Parse wake phrases from config
        phrases = [p.strip() for p in self.wake_phrases.split(",")] if self.wake_phrases else None
        if phrases is None:
            phrases = [wake_word, "hey Yuna", "yuna"]

        self.wake_detector = get_wake_detector(
            backend=self.wake_backend,
            phrases=phrases,
            threshold=0.7,
        ) if mode == "wake" else None

        self.push_to_talk = get_push_to_talk(hotkey) if mode == "push" else None
        self.agent = get_agent()

        # Memory components
        self.conversation_history = ConversationHistory()
        self.reminder_manager = ReminderManager()

        # State
        self._running = False
        self._recording = False
        self._audio_buffer = deque(maxlen=100)  # buffer untuk deteksi wake word
        self._speech_buffer = []
        self._is_speaking = False
        self._history = []
        self._tts_task = None  # For barge-in support

    async def start(self):
        """Start voice loop."""
        self._running = True

        print("=" * 60)
        print("yuna - Mode Suara")
        print("=" * 60)

        if self.mode == "wake":
            print(f"Mode: Wake Word ('{self.wake_word}')")
            print(f"Ucapkan '{self.wake_word}' untuk aktifkan")
        else:
            print(f"Mode: Push-to-Talk")
            print(f"Tekan dan tahan [{self.hotkey.upper()}] untuk bicara")

        print("Tekan Ctrl+C untuk keluar")
        print("=" * 60)
        print()

        # Load recent history
        recent_messages = self.conversation_history.get_recent(limit=20)
        for msg in recent_messages:
            self._history.append({"role": msg["role"], "content": msg["content"]})

        if self._history:
            print(f"(Loaded {len(self._history)} recent messages from history)\n")

        # Setup reminder notification callback dengan TTS
        def reminder_notification_callback(message: str):
            """Callback untuk reminder - play TTS notification."""
            logger.info(f"Reminder notification: {message}")
            notification_text = f"Reminder: {message}"
            print(f"\nðŸ”” {notification_text}\n")
            # Play TTS secara async
            asyncio.create_task(self.tts.speak_stream_and_play(notification_text))

        self.reminder_manager.set_notification_callback(reminder_notification_callback)
        self.reminder_manager.start_background_checker(interval_seconds=10)
        logger.info("Reminder background checker started")

        try:
            if self.mode == "wake":
                await self._wake_word_loop()
            else:
                await self._push_to_talk_loop()
        except KeyboardInterrupt:
            print("\n\nSampai jumpa!")
        finally:
            self._running = False
            self.reminder_manager.stop_background_checker()

    async def _wake_word_loop(self):
        """Loop untuk wake word mode."""
        logger.info("Starting wake word loop")

        while self._running:
            # Listen untuk wake word
            print("Mendengarkan wake word...")

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=self.chunk_size,
            ) as stream:
                while self._running:
                    audio_chunk, _ = stream.read(self.chunk_size)
                    audio_chunk = audio_chunk.flatten()

                    # Skip wake word detection while TTS is speaking (prevent self-trigger)
                    if self._is_speaking:
                        await asyncio.sleep(0.01)
                        continue

                    # Check wake word
                    result = self.wake_detector.detect(audio_chunk)

                    # Test wake mode: print detected text and score
                    if self.test_wake and result.detected:
                        print(f"[TEST] Wake detected: '{result.phrase}' (score: {result.score:.2f}, backend: {result.backend})")
                    elif self.test_wake and hasattr(self.wake_detector, '_last_text') and self.wake_detector._last_text:
                        print(f"[TEST] Heard: '{self.wake_detector._last_text}'")

                    if result.detected:
                        print(f"\nðŸŽ¤ Wake word terdeteksi: '{result.phrase}' (score: {result.score:.2f})")
                        # Play chime
                        play_chime(self.sample_rate)
                        await self._handle_voice_command()
                        break

                    await asyncio.sleep(0.01)

    async def _push_to_talk_loop(self):
        """Loop untuk push-to-talk mode."""
        logger.info("Starting push-to-talk loop")

        recording_task = None

        def on_press():
            nonlocal recording_task
            if recording_task is None or recording_task.done():
                print(f"\nðŸŽ¤ Recording... (lepas [{self.hotkey.upper()}] untuk selesai)")
                recording_task = asyncio.create_task(self._record_and_process())

        def on_release():
            pass  # Recording akan berhenti otomatis setelah silence

        self.push_to_talk.start(on_press=on_press, on_release=on_release)

        try:
            while self._running:
                await asyncio.sleep(0.1)
        finally:
            self.push_to_talk.stop()

    async def _record_and_process(self):
        """Record audio dan proses."""
        # Record audio
        audio_data = await self._record_until_silence()

        if len(audio_data) == 0:
            print("Tidak ada audio terdeteksi.")
            return

        await self._handle_voice_command(audio_data)

    async def _record_until_silence(self) -> np.ndarray:
        """
        Record audio sampai silence terdeteksi.

        Returns:
            Audio array
        """
        self._speech_buffer = []
        silence_count = 0
        has_speech = False

        start_time = time.time()

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32,
            blocksize=self.chunk_size,
        ) as stream:
            while True:
                audio_chunk, _ = stream.read(self.chunk_size)
                audio_chunk = audio_chunk.flatten()

                self._speech_buffer.append(audio_chunk)

                # Simple voice activity detection (volume-based)
                volume = np.abs(audio_chunk).mean()

                if volume > 0.01:  # threshold
                    has_speech = True
                    silence_count = 0
                else:
                    if has_speech:
                        silence_count += 1

                # Stop recording after silence
                if has_speech and silence_count >= self.silence_chunks:
                    break

                # Timeout after 30 seconds
                if time.time() - start_time > 30:
                    break

                await asyncio.sleep(0.01)

        if not has_speech:
            return np.array([])

        return np.concatenate(self._speech_buffer)

    async def _handle_voice_command(self, audio_data: Optional[np.ndarray] = None):
        """
        Process voice command.

        Args:
            audio_data: Audio array (jika sudah direkam), atau None untuk rekam baru
        """
        try:
            # Barge-in: stop TTS if currently speaking
            if self._is_speaking and self._tts_task and not self._tts_task.done():
                logger.info("Barge-in: stopping TTS")
                self._tts_task.cancel()
                try:
                    await self._tts_task
                except asyncio.CancelledError:
                    pass
                self._is_speaking = False
                print("\nðŸ›‘ TTS dihentikan (barge-in)")

            # Record jika belum ada audio
            if audio_data is None:
                print("ðŸŽ¤ Mendengarkan...")
                audio_data = await self._record_until_silence()

                if len(audio_data) == 0:
                    print("Tidak ada audio terdeteksi.")
                    return

            # STT
            print("ðŸ§  Memproses...")
            start_time = time.time()

            text = self.stt.transcribe(audio_data, self.sample_rate)

            if not text:
                print("Tidak ada teks terdeteksi.")
                return

            print(f"Anda: {text}")

            # Agent with history
            response = await self.agent.run(text, history=self._history)

            stt_time = time.time() - start_time

            # Save to DB
            self.conversation_history.add_message("user", text)
            self.conversation_history.add_message("assistant", response)

            # Update in-memory history
            self._history.append({"role": "user", "content": text})
            self._history.append({"role": "assistant", "content": response})

            # Keep history limited
            if len(self._history) > 20:
                self._history = self._history[-20:]

            # TTS + Play
            print(f"yuna: {response}")

            tts_start = time.time()
            self._is_speaking = True
            self._tts_task = asyncio.create_task(self.tts.speak_stream_and_play(response))
            await self._tts_task
            self._is_speaking = False
            tts_time = time.time() - tts_start

            total_time = time.time() - start_time
            print(f"\nâ±ï¸  Latensi: {total_time:.2f}s (STT: {stt_time:.2f}s, TTS: {tts_time:.2f}s)\n")

        except asyncio.CancelledError:
            logger.info("Voice command cancelled")
            self._is_speaking = False
            raise
        except Exception as e:
            logger.error(f"Voice command error: {e}", exc_info=True)
            print(f"Error: {e}")
            self._is_speaking = False

    def stop(self):
        """Stop voice loop."""
        self._running = False
        if self.push_to_talk:
            self.push_to_talk.stop()


async def run_voice_loop(mode: str = "push", wake_word: str = "hey aki", hotkey: str = "space", test_wake: bool = False):
    """
    Run voice loop.

    Args:
        mode: "wake" atau "push"
        wake_word: Wake word phrase
        hotkey: Hotkey untuk push-to-talk
        test_wake: Test mode - print detected text and scores without processing
    """
    loop = VoiceLoop(mode=mode, wake_word=wake_word, hotkey=hotkey, test_wake=test_wake)
    await loop.start()
