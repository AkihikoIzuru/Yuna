# JARVIS - Asisten AI Rumah Modular

Asisten AI ala JARVIS yang bisa ngobrol pakai suara (Bahasa Indonesia utama), ngendaliin komputer, ngontrol perangkat rumah, dan monitor jaringan.

## Status Pengembangan

✅ **Fase 1: Otak + Tool (Teks)** - SELESAI  
⬜ Fase 2: Suara  
⬜ Fase 3: Memori & Personalisasi  
⬜ Fase 4: Kontrol Rumah & Jaringan  
⬜ Fase 5: Keamanan & Konfirmasi  
⬜ Fase 6: Dashboard  
⬜ Fase 7: Polishing & Deploy  

## Fase 1: Fitur yang Tersedia

- ✅ Chat interaktif di terminal
- ✅ Tool calling (native + fallback JSON)
- ✅ Retry & fallback model otomatis
- ✅ Tools dasar:
  - `get_time` - Cek waktu sekarang
  - `get_date` - Cek tanggal hari ini
  - `get_system_info` - Info sistem (OS, CPU, RAM, disk)
  - `open_app` - Buka aplikasi (kalkulator, notepad, chrome, dll)
  - `set_volume` - Set volume sistem (0-100)
  - `set_timer` - Set timer/alarm
  - `list_timers` - Lihat timer aktif
  - `clear_timers` - Hapus semua timer

## Instalasi

### Requirements

- Python 3.11+
- 9Router running di `localhost:20128` (atau URL lain)
- Windows atau Linux

### Setup

1. Clone repo:
```bash
git clone <repo-url>
cd jarvis
```

2. Install dependencies:
```bash
pip install -e .
# atau manual:
pip install openai python-dotenv psutil pyyaml
```

3. Copy `.env.example` ke `.env` dan edit:
```bash
cp .env.example .env
```

4. Edit `.env`:
```env
JARVIS_BASE_URL=http://localhost:20128/v1
JARVIS_MODEL=jarvis
JARVIS_FAST_MODEL=jarvis
ROUTER_API_KEY=sk-your-api-key-here
```

## Cara Pakai

### Mode Teks (Fase 1)

```bash
python -m jarvis.main --text
```

Contoh percakapan:
```
Anda: jam berapa?
Jarvis: Sekarang jam 4 sore lewat 28 menit.

Anda: buka kalkulator
Jarvis: Aplikasi 'kalkulator' berhasil dibuka.

Anda: gimana kondisi sistem?
Jarvis: OS: Windows 10, CPU: 15.2%, RAM: 45.8%, Disk: 62.3%

Anda: exit
```

### Mode Suara (Fase 2 - belum tersedia)

```bash
python -m jarvis.main --voice
```

## Testing

Jalankan semua tes:
```bash
python -m pytest tests/ -v
```

Tes spesifik:
```bash
python -m pytest tests/test_registry.py -v
python -m pytest tests/test_client.py -v
```

## Struktur Kode

```
jarvis/
├── jarvis/
│   ├── main.py              # Entrypoint CLI
│   ├── config.py            # Konfigurasi (.env loader)
│   ├── brain/
│   │   ├── client.py        # RouterClient (OpenAI-compatible)
│   │   ├── agent.py         # Agent loop (tool calling)
│   │   └── prompts.py       # System prompt Jarvis
│   └── tools/
│       ├── registry.py      # @tool decorator + auto JSON schema
│       └── system.py        # Tools sistem (time, app, volume, timer)
└── tests/
    ├── test_registry.py     # Tes tool registry
    └── test_client.py       # Tes RouterClient
```

## Cara Menambah Tool Baru

1. Buat fungsi baru di `jarvis/tools/` (atau buat file baru):

```python
from jarvis.tools.registry import tool

@tool(risk="low")  # low, medium, high
def nama_tool(param1: str, param2: int = 10) -> str:
    """Deskripsi tool (muncul di prompt LLM)."""
    # Implementasi tool
    return "hasil"
```

2. Import tool di `jarvis/main.py`:

```python
from jarvis.tools import system, nama_file_baru
```

3. Tool otomatis terdaftar dan bisa dipanggil LLM!

### Type Hints untuk JSON Schema

Tool registry otomatis bikin JSON schema dari type hints:

- `str` → `{"type": "string"}`
- `int` → `{"type": "integer"}`
- `float` → `{"type": "number"}`
- `bool` → `{"type": "boolean"}`
- `list[str]` → `{"type": "array", "items": {"type": "string"}}`
- `dict` → `{"type": "object"}`
- Parameter dengan default value = optional
- Parameter tanpa default = required

## Konfigurasi 9Router

Jarvis pakai 9Router sebagai proxy ke berbagai LLM. Pastikan:

1. 9Router running di `localhost:20128` (atau ubah `JARVIS_BASE_URL`)
2. Model `jarvis` (atau apapun di `JARVIS_MODEL`) tersedia
3. API key valid di `ROUTER_API_KEY`

Cek model tersedia:
```bash
curl http://localhost:20128/v1/models
```

## Troubleshooting

### "Config load gagal"
- Pastikan `.env` ada dan berisi variabel required
- Cek `JARVIS_BASE_URL`, `JARVIS_MODEL`, `JARVIS_FAST_MODEL`, `ROUTER_API_KEY`

### "Connection error" saat chat
- Pastikan 9Router running: `curl http://localhost:20128/v1/models`
- Cek firewall/antivirus tidak block port 20128
- Coba ubah `JARVIS_BASE_URL` ke IP lokal: `http://127.0.0.1:20128/v1`

### Tool tidak dipanggil
- Model mungkin tidak support native tool calling
- Agent akan otomatis fallback ke JSON mode
- Cek log dengan `--debug`: `python -m jarvis.main --text --debug`

### "Model tidak support tools"
- Fallback ke `JARVIS_FAST_MODEL` otomatis
- Atau ubah model ke yang support function calling
- Contoh: `gemini/gemini-3.8-flash`, `kr/claude-sonnet-4.5`

## Fase Berikutnya

### Fase 2: Suara
- faster-whisper untuk STT (Bahasa Indonesia)
- edge-tts untuk TTS (suara Indonesia)
- Wake word detection (openWakeWord)
- Push-to-talk alternatif
- Barge-in (interupsi saat Jarvis ngomong)

### Fase 3: Memori & Personalisasi
- SQLite untuk riwayat percakapan
- Fakta tentang user (key-value)
- Reminder/alarm yang betulan bunyi
- Auto-summarize riwayat lama

### Fase 4: Kontrol Rumah & Jaringan
- Home Assistant API integration
- MQTT untuk ESP32
- Mikrotik RouterOS monitoring (read-only)
- Alert proaktif

### Fase 5: Keamanan & Konfirmasi
- Risk level per tool
- Konfirmasi eksplisit untuk high-risk
- Audit log
- Prompt injection protection

### Fase 6: Dashboard
- FastAPI + WebSocket
- Frontend futuristik (orb visualizer)
- Real-time status & transkrip
- Responsif (bisa dibuka dari HP)

### Fase 7: Polishing & Deploy
- Service background (systemd/Task Scheduler)
- Auto-start saat boot
- Health check
- Multi-room mode (opsional)

## Kontributor

- **Akii** - Owner & pemula-menengah coder dengan bantuan AI
- Built with ❤️ menggunakan Claude Code

## Lisensi

[Sesuaikan dengan lisensi yang dipilih]