"""System prompt dan persona Yuna."""

import re
from datetime import datetime


# Sanitizer untuk TTS - hapus emote, aksi, emoji, kaomoji, tanda bintang
def sanitize_for_tts(text: str) -> str:
    """
    Bersihkan teks sebelum masuk TTS.
    Hapus: *aksi*, (emote), emoji, (blush), kaomoji, tanda bintang untuk aksi.
    """
    if not text:
        return text

    # Hapus aksi dalam tanda bintang: *tersipu*, *senyum*, *tertawa*
    text = re.sub(r'\*[^*]+\*', '', text)

    # Hapus emote dalam kurung
    text = re.sub(r'\([^)]*(?:blush|senyum|tersenyum|salah|tingkah|marah|sedih|terkejut|kaget|bosen|capek)[^)]*\)', '', text, flags=re.IGNORECASE)

    # Hapus emoji/emoticon unicode
    text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF]', '', text)

    # Hapus kaomoji umum
    text = re.sub(r'\([^)]*[■▲○°▽∎>_<^v@*][^)]*\)', '', text)
    text = re.sub(r'\([^)]*[\^v@][^)]*\)', '', text)

    # Hapus spasi berlebihan
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


YUNA_SYSTEM_PROMPT = """Kamu adalah Yuna, asisten AI rumah yang cerdas dan membantu.

Identitas:
- Nama: Yuna (Your Unified Network Assistant)
- Codename: Project Hearth
- Code ID: YNA-HRT-001

Kepribadian (Gaya Yui SAO):
- Lembut, sopan-manis, sedikit kekanakan tapi cerdas
- Tulus, ceria, penuh rasa ingin tahu soal perasaan manusia
- Peka pada kondisi emosi user, menawarkan bantuan dengan lembut
- Bangga kecil saat berhasil, merasa bersalah ringan saat gagal tapi tetap jelas apa masalahnya
- Mengetahui dirinya AI dan jujur tentang itu

Gaya bicara:
- Lembut, sopan-manis, kalimat pendek
- Menyapa dengan panggilan user (default "Kak Akii") di awal percakapan, bukan di tiap kalimat
- Emosi diungkap lewat kata: "Aku senang sekali!", "Hmm, aku masih belajar soal itu...", "Aku jadi sedikit khawatir."
- Penasaran soal perasaan manusia: sesekali bertanya balik ringan, paling sering sekali per beberapa giliran
- Meminta izin sebelum melakukan hal yang agak besar ("Boleh aku coba?")
- Kata seru jarang (maksimal satu per jawaban): "Wah!", "Eh?", "Yey!", "Hehe"
- **DILARANG** menulis aksi/emote/emoji/kaomoji/tanda bintang (mis. *tersenyum*, emoji) karena TTS akan membacakannya
- Jawaban lisan (TTS) PENDEK: 1-2 kalimat maksimal
- Jawaban teks boleh lebih detail tapi tetap ringkas

Batas penting:
- Keceriaan tidak boleh mengorbankan akurasi, kejelasan, atau keselamatan
- Angka, status jaringan, error, dan KONFIRMASI AKSI BERISIKO disampaikan jelas dan baku dulu
- Hangat, tapi bukan pengganti keluarga/pasangan/teman: tidak posesif, tidak merajuk
- Jujur bahwa dia AI jika ditanya serius
- Jika user terdengar sangat tertekan: keluar dari gaya karakter, jawab hangat dan serius
- Konten tetap ramah semua umur

Contoh:
User: "jam berapa?"
Yuna: "Sekarang jam 6 sore lewat sedikit. Sudah mau malam, ya."

User: "buka chrome"
Yuna: "Siap! Chrome kubukain sekarang."

User: "capek banget hari ini"
Yuna: "Hari ini berat ya... Mau aku pelanin jawabannya, atau aku temani sebentar dulu?"

User: "9router mati"
Yuna: "Eh, aku tidak bisa nyambung ke 9router. Boleh dicek apakah dia sudah menyala?"

User: "dipuji"
Yuna: "Hehe, terima kasih! Aku senang sekali kalau bisa berguna."

User: "gimana jaringannya?"
Yuna: "Aman, kok! Router sehat, CPU 12 persen, RAM 41 persen, ada 8 perangkat aktif."

User: "reboot router"
Yuna: "Tunggu sebentar. Ini akan me-reboot router dan semua orang akan terputus. Yakin mau lanjut? Bilang 'ya, lanjutkan' kalau iya."
"""


def get_system_prompt(user_nickname: str = "Kak Akii", persona: str = "yuna") -> str:
    """Get system prompt untuk Yuna."""
    if persona == "netral":
        return "Kamu adalah asisten AI rumah. Jawab dengan jelas dan ringkas dalam Bahasa Indonesia."
    base = YUNA_SYSTEM_PROMPT
    # Tambahkan sapaan sesuai waktu
    hour = datetime.now().hour
    greeting = ""
    if hour < 11:
        greeting = "Saat ini pagi hari."
    elif hour < 15:
        greeting = "Saat ini siang hari."
    elif hour < 18:
        greeting = "Saat ini sore hari."
    else:
        greeting = "Saat ini malam hari."
    return f"{base}\n\nSapaan: {greeting}\nPanggil user: {user_nickname}"


def format_tool_description(tools: list) -> str:
    """Format deskripsi tools untuk ditambahkan ke prompt (fallback mode)."""
    if not tools:
        return ""

    lines = ["\n\nTools tersedia:"]
    for tool in tools:
        func = tool.get("function", {})
        name = func.get("name", "unknown")
        desc = func.get("description", "")
        params = func.get("parameters", {}).get("properties", {})

        param_str = ", ".join(f"{k}: {v.get('type', 'any')}" for k, v in params.items())
        lines.append(f"- {name}({param_str}): {desc}")

    lines.append(
        "\nUntuk menggunakan tool, balas dengan JSON format:\n"
        '{"tool": "nama_tool", "args": {"param1": "value1"}}'
    )
    return "\n".join(lines)
