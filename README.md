# SHAGO AI

**SHAGO AI** adalah local agentic coding CLI untuk membantu membaca, menganalisis, menjalankan command, dan mengubah file project langsung dari terminal.


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

## Installation

Dari root project:

```cmd
> pipx uninstall shagoai 2>/dev/null || true
> python -m pip uninstall -y shagoai 2>/dev/null || true
> rm -f ~/.local/bin/shagoai
> hash -r
> curl -fsSL https://shagoai.shagya-tech.my.id/install.sh | sh
```

---

## Run

Setelah install, kamu bisa langsung jalankan:

```bash
shagoai
```


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

Menampilkan workspace aktif.

```txt
/workspace
```

Mengganti workspace aktif.

```txt
/workspace <path>
```

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
cd ~/go/src/main-project
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