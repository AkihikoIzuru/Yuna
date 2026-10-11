"""Main entrypoint - CLI mode."""

import argparse
import asyncio
import logging
import sys

from jarvis.brain.agent import get_agent
from jarvis.config import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def text_mode():
    """Mode teks interaktif (REPL)."""
    print("=" * 60)
    print("JARVIS - Asisten AI Rumah")
    print("=" * 60)
    print("Mode: Teks")
    print("Ketik 'exit' atau 'quit' untuk keluar")
    print("=" * 60)
    print()

    agent = get_agent()
    history = []

    while True:
        try:
            user_input = input("Anda: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "keluar"):
                print("\nSampai jumpa!")
                break

            # Get response from agent
            print("Jarvis: ", end="", flush=True)

            response = await agent.run(user_input, history=history)
            print(response)
            print()

            # Update history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})

            # Keep history limited (last 10 messages)
            if len(history) > 20:
                history = history[-20:]

        except KeyboardInterrupt:
            print("\n\nSampai jumpa!")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"\nError: {e}\n")


async def voice_mode():
    """Mode suara (Fase 2)."""
    print("Mode suara belum tersedia. Tunggu Fase 2!")
    sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Jarvis - Asisten AI Rumah")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Mode teks interaktif (default untuk Fase 1)",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Mode suara (tersedia di Fase 2)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

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
        from jarvis.tools import system
        logger.info("Tools loaded successfully")
    except Exception as e:
        logger.error(f"Gagal load tools: {e}")
        sys.exit(1)

    # Pilih mode
    if args.voice:
        asyncio.run(voice_mode())
    else:
        # Default ke text mode
        asyncio.run(text_mode())


if __name__ == "__main__":
    main()