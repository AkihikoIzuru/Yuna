"""Tests untuk system prompt dan sanitizer."""

import pytest
from yuna.brain.prompts import sanitize_for_tts, get_system_prompt


def test_sanitize_stars():
    """Hapus teks dalam tanda bintang."""
    # Sanitizer also cleans up extra spaces
    assert sanitize_for_tts("Halo *senyum* apa kabar?") == "Halo apa kabar?"
    assert sanitize_for_tts("*tersenyum* aku senang") == "aku senang"


def test_sanitize_emote():
    """Hapus emote dalam kurung."""
    assert "blush" not in sanitize_for_tts("Aku senang (blush) sekali!")
    assert "senyum" not in sanitize_for_tts("Dia (tersenyum) jawab")
    assert "(emote)" in sanitize_for_tts("Test (emote) text")  # bukan pattern yang dikenal


def test_sanitize_kaomoji():
    """Hapus kaomoji."""
    assert "^_^" not in sanitize_for_tts("Halo (^_^)")
    # Sanitizer also cleans up extra spaces
    assert "text" in sanitize_for_tts("Test (^_^) text")


def test_sanitize_preserves_normal_text():
    """Teks normal tidak berubah."""
    assert sanitize_for_tts("Halo apa kabar?") == "Halo apa kabar?"
    assert sanitize_for_tts("") == ""


def test_get_system_prompt_contains_persona():
    """System prompt harus mengandung identitas Yuna."""
    prompt = get_system_prompt()
    assert "Yuna" in prompt
    assert "Project Hearth" in prompt
    assert "YNA-HRT-001" in prompt
    assert "Yui SAO" in prompt


def test_get_system_prompt_neutral():
    """Persona netral harus berbeda."""
    neutral = get_system_prompt(persona="netral")
    assert "Yuna" not in neutral
    assert "asisten AI rumah" in neutral


def test_get_system_prompt_includes_time_greeting():
    """System prompt harus menyertakan sapaan waktu."""
    prompt = get_system_prompt()
    hour = __import__("datetime").datetime.now().hour
    if hour < 11:
        assert "pagi" in prompt
    elif hour < 15:
        assert "siang" in prompt
    elif hour < 18:
        assert "sore" in prompt
    else:
        assert "malam" in prompt
