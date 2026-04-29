# Tracer Alumni UMM — v2.0

Sistem pelacakan alumni berbasis pseudocode multi-platform.

## Link Publish Website

```
https://trackalumni--alsaputra0912.replit.app

```

## Cara Menjalankan

```bash
pip install -r requirements.txt
python app.py
```

Buka: http://127.0.0.1:8000

Login default: `admin` / `admin123`

## Pseudocode yang Diimplementasikan

```
FOR setiap alumni dalam database:
  1. Buat profil target (nama + prodi + universitas = kata_kunci)
  2. FOR setiap platform [LinkedIn, Google Scholar, ResearchGate, Instagram, Facebook]:
       hasil = cari_profil(platform, kata_kunci)
       IF hasil ditemukan:
         validasi = cek_kesesuaian(hasil, target)  ← skor 0-100
         IF validasi >= 50:
           simpan: nama, platform, link, pekerjaan, institusi, lokasi, tahun_update
           status = "Ditemukan"
           BREAK  ← berhenti cek platform berikutnya
  3. IF status != "Ditemukan": status = "Tidak Ditemukan"
  4. Simpan ke tracer_alumni + trace_log (log per platform)
Buat laporan: jumlah ditemukan, distribusi platform, distribusi pekerjaan
```

## Struktur Direktori

```
tracer_system/
├── app.py                    # Backend Flask + engine pseudocode
├── requirements.txt
├── instance/
│   └── alumni_system.db      # Database SQLite (142.292 alumni)
├── static/
│   ├── css/style.css         # Light mode theme
│   └── js/main.js
└── templates/
    ├── base.html
    ├── login.html
    ├── index.html            # Dashboard
    ├── alumni.html           # Daftar alumni
    ├── add_alumni.html       # Tambah alumni
    ├── detail.html           # Detail + log platform
    ├── tracer.html           # Halaman pelacak (pipeline UI)
    ├── laporan.html          # Laporan step 7
    └── settings.html         # Manajemen user
```

## Tabel Database Baru

- `tracer_alumni` — hasil pelacakan (platform_ditemukan, link_profil, pekerjaan, institusi, lokasi, skor_validasi)
- `trace_log` — log per platform per alumni (skor_kesesuaian, detail_validasi, durasi_ms)
