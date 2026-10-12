"""Main entrypoint - CLI mode."""

import argparse
import asyncio
import logging
import sys
import atexit

from yuna.brain.agent import get_agent
from yuna.config import get_config
from yuna.memory import ConversationHistory, ReminderManager
from yuna.memory.db import close_db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def text_mode():
    """Mode teks interaktif (REPL) dengan streaming."""
    print("=" * 60)
    print("yuna - Asisten AI Rumah")
    print("=" * 60)
    print("Mode: Teks (Streaming)")
    print("Ketik 'exit' atau 'quit' untuk keluar")
    print("=" * 60)
    print()

    # Initialize conversation history
    conversation_history = ConversationHistory()

    # Initialize reminder manager with TTS callback
    reminder_manager = ReminderManager()

    # Start reminder background checker
    reminder_manager.start_background_checker(interval_seconds=10)
    logger.info("Reminder background checker started")

    agent = get_agent()

    # Load recent history from DB
    history = []
    recent_messages = conversation_history.get_recent(limit=20)
    for msg in recent_messages:
        history.append({"role": msg["role"], "content": msg["content"]})

    if history:
        print(f"(Loaded {len(history)} recent messages from history)\n")

    while True:
        try:
            user_input = input("Anda: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "keluar"):
                print("\nSampai jumpa!")
                break

            # Get streaming response from agent
            print("yuna: ", end="", flush=True)

            full_response = ""
            async for chunk in agent.run_stream(user_input, history=history):
                full_response += chunk
                print(chunk, end="", flush=True)
            print()
            print()

            # Save to DB
            conversation_history.add_message("user", user_input)
            conversation_history.add_message("assistant", full_response)

            # Update in-memory history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": full_response})

            # Keep history limited (last 20 messages)
            if len(history) > 20:
                history = history[-20:]

        except (KeyboardInterrupt, EOFError):
            print("\n\nSampai jumpa!")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"\nError: {e}\n")

    # Cleanup
    reminder_manager.stop_background_checker()



async def voice_mode(mode: str = "wake", test_wake: bool = False):
    """Mode suara (Fase 2)."""
    try:
        from yuna.voice.loop import run_voice_loop
        await run_voice_loop(mode=mode, wake_word="hey aki", hotkey="space", test_wake=test_wake)
    except ImportError as e:
        logger.error(f"Voice dependencies tidak terinstall: {e}")
        print("\nError: Voice dependencies tidak terinstall.")
        print("Install dengan: pip install faster-whisper edge-tts sounddevice webrtcvad-wheels pynput soundfile numpy")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Voice mode error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)


def list_audio_devices():
    """List audio devices yang tersedia."""
    try:
        import sounddevice as sd
        print("=" * 60)
        print("Audio Devices:")
        print("=" * 60)
        print(sd.query_devices())
        print()
    except ImportError:
        print("sounddevice tidak terinstall. Install dengan: pip install sounddevice")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="yuna - Asisten AI Rumah")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Mode teks interaktif (default untuk Fase 1)",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Mode suara (Fase 2)",
    )
    parser.add_argument(
        "--wake",
        action="store_true",
        help="Mode suara dengan wake word 'hey aki' (default untuk --voice)",
    )
    parser.add_argument(
        "--ptt",
        action="store_true",
        help="Mode push-to-talk (hotkey SPASI)",
    )
    parser.add_argument(
        "--test-wake",
        action="store_true",
        help="Test wake word detection - print teks dan skor yang didengar",
    )
    parser.add_argument(
        "--list-audio-devices",
        action="store_true",
        help="List audio devices yang tersedia",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="Start minimized to tray (for auto-start)",
    )

    args = parser.parse_args()

    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # List audio devices
    if args.list_audio_devices:
        list_audio_devices()
        return

    # Load config
    try:
        config = get_config()
        logger.info(f"Config loaded: model={config.model}, base_url={config.base_url}")
    except Exception as e:
        logger.error(f"Gagal load config: {e}")
        print(f"\nError: Gagal load konfigurasi dari .env")
        print(f"Detail: {e}")
        print(f"\nPastikan file .env sudah dibuat (contoh ada di .env.example)")
        sys.exit(1)

    # Import tools untuk auto-register
    try:
        from yuna.tools import system, memory, home, vision
        logger.info("Tools loaded successfully")
    except Exception as e:
        logger.error(f"Gagal load tools: {e}")
        sys.exit(1)

    # Register cleanup handler
    atexit.register(close_db)

    # Pilih mode
    if args.test_wake:
        # Test wake word mode
        asyncio.run(voice_mode(mode="wake", test_wake=True))
    elif args.voice or args.wake:
        # Voice mode - default to wake word
        mode = "wake" if args.wake or not args.ptt else "push"
        asyncio.run(voice_mode(mode=mode, test_wake=False))
    elif args.ptt:
        # Push-to-talk only
        asyncio.run(voice_mode(mode="push", test_wake=False))
    elif args.minimized:
        # App mode (desktop app with tray)
        from yuna.app import get_lifecycle
        lifecycle = get_lifecycle()
        if not lifecycle.start():
            print("yuna sudah berjalan!")
            sys.exit(1)

        # Import and run app
        from yuna.app.__main__ import main as app_main
        app_main()
    else:
        # Default ke text mode
        asyncio.run(text_mode())


if __name__ == "__main__":
    main()
