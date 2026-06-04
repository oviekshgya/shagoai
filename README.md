# SHAGO AI

**SHAGO AI** adalah local agentic coding CLI untuk membantu membaca, menganalisis, menjalankan command, dan mengubah file project langsung dari terminal.

Tampilan CLI menggunakan branding **SHAGO** dengan mode agentic:

```txt
╭─────────────── SHAGO//AGENT ───────────────╮
│                                            │
│ ███████╗██╗  ██╗ █████╗  ██████╗  ██████╗ │
│ ██╔════╝██║  ██║██╔══██╗██╔════╝ ██╔═══██╗│
│ ███████╗███████║███████║██║  ███╗██║   ██║│
│ ╚════██║██╔══██║██╔══██║██║   ██║██║   ██║│
│ ███████║██║  ██║██║  ██║╚██████╔╝╚██████╔╝│
│ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ │
│                                            │
│ local autonomous coding interface          │
│                                            │
│ AI        minimax-m3:cloud                 │
│ ROOT      ~/go/src/sch-ebor                │
│ MODE      plan → act → verify              │
│ GUARD     approval required                │
╰───────── type /help for commands ──────────╯
```

---

## Features

- Agentic coding assistant dari terminal.
- Bisa dipanggil dari directory project mana pun.
- Workspace otomatis mengikuti current directory.
- Bisa baca file project.
- Bisa list folder project.
- Bisa search text di project.
- Bisa menjalankan command dengan approval.
- Bisa menulis/mengubah file dengan approval.
- Bisa melihat `git diff`.
- Bisa undo perubahan terakhir dari `write_file`.
- Bisa switch model dari dalam CLI.
- Bisa menyimpan model default ke config lokal.

---

## Requirements

Pastikan Python sudah tersedia.

Direkomendasikan:

```bash
python --version
```

Minimal:

```txt
Python 3.10+
```

Install dependency:

```bash
pip install -U ollama rich prompt_toolkit
```

Pastikan AI runtime lokal/cloud sudah berjalan dan model tersedia.

Cek model:

```bash
ollama ls
```

Contoh output:

```txt
NAME                ID              SIZE    MODIFIED
minimax-m3:cloud    d03a959f45c0    -       9 minutes ago
gemma4:31b-cloud    c382fbfbc73b    -       27 minutes ago
```

---

## Project Structure

Struktur project yang direkomendasikan:

```txt
ollama-agent/
├── pyproject.toml
├── README.md
└── shagoai/
    ├── __init__.py
    └── cli.py
```

Contoh isi `shagoai/__init__.py`:

```python
__version__ = "0.1.0"
```

File `__init__.py` juga boleh kosong.

---

## Installation

Dari root project:

```bash
cd ~/project/python/ollama-agent
pip install -e .
```

Mode `-e` artinya editable install.

Jadi kalau kamu mengubah file:

```txt
shagoai/cli.py
```

kamu tidak perlu install ulang.

Cukup jalankan ulang:

```bash
shagoai
```

---

## pyproject.toml

Contoh isi `pyproject.toml`:

```toml
[project]
name = "shagoai"
version = "0.1.0"
description = "Shago local agentic coding CLI"
requires-python = ">=3.10"
dependencies = [
    "ollama",
    "rich",
    "prompt_toolkit",
]

[project.scripts]
shagoai = "shagoai.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

Setelah file ini dibuat, jalankan:

```bash
pip install -e .
```

---

## Run

Setelah install, kamu bisa langsung jalankan:

```bash
shagoai
```

Tidak perlu lagi:

```bash
python agent.py
```

---

## Workspace Usage

### 1. Workspace otomatis dari current directory

Kalau kamu masuk ke project tertentu:

```bash
cd ~/go/src/shago-engine-ollama
shagoai
```

Maka SHAGO otomatis menggunakan directory tersebut sebagai workspace.

Contoh banner:

```txt
ROOT      ~/go/src/shago-engine-ollama
```

Artinya semua tool seperti `read_file`, `list_dir`, `search_text`, `run_cmd`, dan `write_file` akan bekerja dari root tersebut.

---

### 2. Jalankan dari mana saja, target project tertentu

Kamu juga bisa menjalankan SHAGO dari directory mana pun dengan menentukan workspace manual:

```bash
shagoai -C ~/go/src/shago-engine-ollama
```

Contoh lain:

```bash
shagoai --workspace ~/go/src/sch-ebor
```

Hasilnya:

```txt
ROOT      ~/go/src/sch-ebor
```

---

### 3. Jalankan dengan model tertentu

```bash
shagoai -m gemma4:31b-cloud
```

Atau:

```bash
shagoai --model minimax-m3:cloud
```

---

### 4. Workspace + model sekaligus

```bash
shagoai -C ~/go/src/shago-engine-ollama -m gemma4:31b-cloud
```

Atau versi panjang:

```bash
shagoai --workspace ~/go/src/shago-engine-ollama --model gemma4:31b-cloud
```

---

## CLI Commands

Di dalam SHAGO, kamu bisa pakai command berikut:

```txt
/help
```

Menampilkan bantuan.

```txt
/models
```

Menampilkan model yang tersedia.

```txt
/model
```

Menampilkan model aktif dan daftar model.

```txt
/model <name>
```

Mengganti model aktif.

Contoh:

```txt
/model gemma4:31b-cloud
```

Jika sudah support pemilihan berdasarkan nomor:

```txt
/model 2
```

---

```txt
/workspace
```

Menampilkan workspace aktif.

```txt
/workspace <path>
```

Mengganti workspace aktif.

Contoh:

```txt
/workspace ~/go/src/sch-ebor
```

---

```txt
/safe
```

Mengaktifkan mode aman.

Pada mode ini, SHAGO akan meminta approval sebelum:

- menjalankan command
- menulis file
- mengubah file

---

```txt
/auto
```

Mengaktifkan mode lebih longgar.

Gunakan dengan hati-hati.

---

```txt
/diff
```

Menampilkan `git diff` dari workspace aktif.

---

```txt
/undo
```

Rollback perubahan terakhir yang dibuat lewat `write_file`.

---

```txt
/clear
```

Membersihkan layar terminal.

---

```txt
/exit
```

Keluar dari SHAGO.

Alias yang disarankan:

```txt
/quit
/q
```

---

## Example Usage

Masuk ke project:

```bash
cd ~/go/src/sch-ebor
shagoai
```

Lalu di dalam SHAGO:

```txt
shago ❯ cek struktur project ini
```

Contoh lain:

```txt
shago ❯ baca main.go lalu jelaskan flow aplikasinya
```

```txt
shago ❯ cari semua penggunaan function CreateUser
```

```txt
shago ❯ jalankan go test ./...
```

```txt
shago ❯ buatkan README dari isi project ini
```

```txt
shago ❯ cek error di project ini dan kasih saran perbaikannya
```

```txt
shago ❯ tambahkan validasi input di controller user
```

---

## Safety

Secara default SHAGO menggunakan guard:

```txt
approval required
```

Artinya SHAGO akan meminta konfirmasi sebelum melakukan aksi yang mengubah sistem/project.

Contoh saat menjalankan command:

```txt
Run this command? [y/N]
```

Contoh saat menulis file:

```txt
Apply this change? [y/N]
```

Command berbahaya seperti ini akan diblokir:

```bash
rm -rf
dd
mkfs
shutdown
reboot
chmod -R 777
```

---

## Model Configuration

SHAGO akan memilih model dengan urutan:

1. Environment variable `SHAGO_MODEL`
2. Environment variable `OLLAMA_MODEL`
3. Config tersimpan di `~/.config/shagoai/config.json`
4. Model pertama dari `ollama ls`

Contoh menjalankan dengan environment variable:

```bash
SHAGO_MODEL=gemma4:31b-cloud shagoai
```

Set model dari dalam CLI:

```txt
/model gemma4:31b-cloud
```

Jika sudah disimpan, config berada di:

```txt
~/.config/shagoai/config.json
```

Contoh isi:

```json
{
  "model": "gemma4:31b-cloud"
}
```

---

## Development

Kalau kamu mengubah code di:

```txt
shagoai/cli.py
```

tidak perlu install ulang jika sebelumnya sudah install editable:

```bash
pip install -e .
```

Cukup jalankan ulang:

```bash
shagoai
```

Kamu perlu menjalankan ulang:

```bash
pip install -e .
```

hanya jika mengubah:

- `pyproject.toml`
- dependency
- nama command di `[project.scripts]`
- struktur package besar

Ringkasnya:

```txt
Ubah cli.py             → tidak perlu reinstall
Ubah __init__.py        → tidak perlu reinstall
Ubah pyproject.toml     → pip install -e . lagi
Tambah dependency       → pip install -e . lagi
Ganti nama command      → pip install -e . lagi
```

---

## Troubleshooting

### Command `shagoai` tidak ditemukan

Pastikan sudah install:

```bash
pip install -e .
```

Cek command:

```bash
which shagoai
```

Kalau memakai `~/.local/bin`, pastikan PATH sudah benar:

```bash
echo $PATH
```

Tambahkan jika perlu:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

### Model not found

Cek model tersedia:

```bash
ollama ls
```

Lalu set model:

```txt
/model gemma4:31b-cloud
```

Atau jalankan langsung:

```bash
SHAGO_MODEL=gemma4:31b-cloud shagoai
```

---

### Workspace salah

Cek workspace aktif:

```txt
/workspace
```

Ganti workspace:

```txt
/workspace ~/go/src/project-kamu
```

Atau jalankan dari awal:

```bash
shagoai -C ~/go/src/project-kamu
```

---

## Recommended Workflow

Untuk project Go:

```bash
cd ~/go/src/project-kamu
shagoai
```

Lalu:

```txt
shago ❯ cek struktur project ini
shago ❯ baca go.mod dan main.go
shago ❯ jelaskan arsitektur project ini
shago ❯ jalankan go test ./...
shago ❯ kalau ada error, bantu perbaiki
```

Untuk project Python:

```bash
cd ~/project/python/project-kamu
shagoai
```

Lalu:

```txt
shago ❯ cek struktur project ini
shago ❯ baca pyproject.toml atau requirements.txt
shago ❯ jalankan test
shago ❯ bantu refactor module ini
```

---

## Notes

SHAGO dibuat untuk menjadi local agentic coding assistant yang bisa dipanggil dari project mana pun.

Prinsip utama:

```txt
cd project
shagoai
```

Lalu SHAGO bekerja di project tersebut.