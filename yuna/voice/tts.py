"""Text-to-Speech menggunakan edge-tts dengan streaming."""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional, AsyncIterator
import re

logger = logging.getLogger(__name__)


class TTS:
    """Text-to-Speech handler menggunakan edge-tts."""

    def __init__(
        self,
        voice: str = "id-ID-ArdiNeural",
        rate: str = "+5%",
        pitch: str = "+2Hz",
        volume: str = "+0%",
    ):
        """
        Initialize TTS.

        Args:
            voice: Suara edge-tts (id-ID-ArdiNeural atau id-ID-GadisNeural)
            rate: Kecepatan bicara (-50% sampai +50%)
            pitch: Pitch suara (mis. +2Hz, -5Hz)
            volume: Volume suara (-50% sampai +50%)
        """
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume

    def _split_sentences(self, text: str) -> list[str]:
        """
        Split teks ke kalimat untuk streaming.

        Args:
            text: Teks input

        Returns:
            List of sentences
        """
        # Split by sentence terminators
        sentences = re.split(r'([.!?]\s+)', text)

        # Recombine sentence with its terminator
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])

        # Add last sentence if no terminator
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])

        return [s.strip() for s in result if s.strip()]

    async def speak(self, text: str, output_file: Optional[Path] = None) -> Path:
        """
        Convert teks ke audio file.

        Args:
            text: Teks yang akan diucapkan
            output_file: Path output (temp file kalau None)

        Returns:
            Path ke audio file
        """
        try:
            import edge_tts

            if output_file is None:
                # Create temp file
                fd, temp_path = tempfile.mkstemp(suffix=".mp3")
                import os
                os.close(fd)
                output_file = Path(temp_path)

            # Generate speech
            communicate = edge_tts.Communicate(
                text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
                volume=self.volume,
            )

            await communicate.save(str(output_file))

            logger.info(f"TTS generated: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise

    async def speak_stream(self, text: str) -> AsyncIterator[Path]:
        """
        Stream TTS per kalimat untuk respons lebih cepat.

        Args:
            text: Teks yang akan diucapkan

        Yields:
            Path ke audio file per kalimat
        """
        sentences = self._split_sentences(text)

        for sentence in sentences:
            if sentence:
                audio_file = await self.speak(sentence)
                yield audio_file

    async def play(self, audio_file: Path) -> None:
        """
        Play audio file.

        Args:
            audio_file: Path ke audio file
        """
        try:
            import sounddevice as sd
            import soundfile as sf

            # Load audio
            data, samplerate = sf.read(str(audio_file))

            # Play
            sd.play(data, samplerate)
            sd.wait()

        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            raise

    async def speak_and_play(self, text: str) -> None:
        """
        Generate dan play audio langsung.

        Args:
            text: Teks yang akan diucapkan
        """
        audio_file = await self.speak(text)
        try:
            await self.play(audio_file)
        finally:
            # Cleanup temp file
            try:
                audio_file.unlink()
            except:
                pass

    async def speak_stream_and_play(self, text: str) -> None:
        """
        Stream per kalimat dan play langsung untuk respons cepat.

        Args:
            text: Teks yang akan diucapkan
        """
        async for audio_file in self.speak_stream(text):
            try:
                await self.play(audio_file)
            finally:
                # Cleanup temp file
                try:
                    audio_file.unlink()
                except:
                    pass


# Global instance
_tts: Optional[TTS] = None


def get_tts(voice: str = "id-ID-ArdiNeural", rate: str = "+5%", pitch: str = "+2Hz") -> TTS:
    """Get global TTS instance."""
    global _tts
    if _tts is None:
        _tts = TTS(voice=voice, rate=rate, pitch=pitch)
    return _tts