# Contributing to Yuna

Terima kasih sudah mau berkontribusi! 🎉

---

## 🚀 Cara Memulai

1. **Cek Issues & Roadmap** — lihat apakah yang mau dikerjakan sudah ada di [Issues](https://github.com/AkihikoIzuru/Yuna/issues) atau [Roadmap](README.md#roadmap).
2. **Satu PR = Satu Fase/Issue** — jangan gabung fitur tidak terkait dalam satu PR.
3. **Fitur besar → buka Issue dulu** — diskusikan desain sebelum coding.

---

## 🛠 Setup Development

```bash
# Clone
git clone https://github.com/AkihikoIzuru/Yuna.git
cd Yuna

# Virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install deps
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-voice.txt
pip install -r requirements-wake-oww.txt  # opsional

# Config
cp .env.example .env
# Edit .env (minimal: YUNA_BASE_URL, YUNA_MODEL, YUNA_FAST_MODEL, ROUTER_API_KEY)

# Git hook (wajib)
git config core.hooksPath .githooks

# Tes
pytest tests/ -v
```

---

## 📏 Aturan Kode

| Aturan | Detail |
|--------|--------|
| **Python** | 3.11+, type hints wajib untuk fungsi publik |
| **Sederhana** | Hindari over-engineering, satu kemampuan = satu tool |
| **Tes** | Tes unit untuk logika inti (registry, safety, memory, config) |
| **Secret** | **TIDAK ADA** secret di kode, log, atau commit. Pakai `.env` (dev) atau Windows Credential Manager (prod) |
| **MikroTik** | **Hanya baca** sampai Fase 5 selesai. Tidak ada tool yang mengubah state router. |
| **TTS Text** | Output TTS **tanpa emote/emoji/kaomoji/tanda bintang** (pakai `sanitize_for_tts`) |
| **Nama asisten** | Selalu dari config (`ASSISTANT_NAME`, `WAKE_PHRASES`), jangan hardcode "Yuna" |
| **Persona** | Orisinal — tidak ada dialog/asset/voice cloning dari karya/orang sungguhan |

---

## 📝 Commit & Pull Request

### Commit
- Kecil & bermakna per langkah
- Pesan jelas: `feat: ...`, `fix: ...`, `chore: ...`, `docs: ...`
- Contoh:
  ```
  feat: add get_weather tool (Fase 1)
  fix: registry filter kwargs for get_date
  docs: update README with voice setup
  ```

### PR
- Jelaskan **apa** yang diubah & **kenapa**
- Cantumkan **cara tes** (perintah, expected output)
- Sebutkan **bagian belum terverifikasi** dengan perangkat asli (router, mic, speaker)
- Tanpa file besar/model/data pribadi/README tambahan

---

## 🎭 Persona Orisinal (Wajib)

Yuna adalah karakter **orisinal** (inspirasi gaya Yui SAO, tapi bukan salinan):
- Tidak menyalin logo, gambar, kutipan dialog, nama skill, atau teks dari karya asli
- Tidak mengaku berafiliasi dengan franchise manapun
- Voice: `id-ID-GadisNeural` (sintetis, bukan cloning suara siapapun)
- Avatar: orb/ilustrasi orisinal buatan sendiri

---

## 🔒 Pelaporan Celah Keamanan

**JANGAN** buka Issue publik.
Hubungi **`@AkihikoIzuru`** lewat profil GitHub (DM atau email di profil).

---

## 📄 Lisensi

Kontribusi Anda akan di-lisensikan di bawah [MIT License](LICENSE) © 2026 AkihikoIzuru.