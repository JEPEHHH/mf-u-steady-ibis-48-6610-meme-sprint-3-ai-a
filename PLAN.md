# Rencana Kerja — Meme Sprint 3: AI Agent Goes Rogue

## Target & Batasan
- Output wajib: `/output/entry.png` — PNG utuh, maks 1024×1024 px, maks 1 MiB (1.048.576 byte).
- Sandbox `program/v1`: `python3.13` / `node22`, tanpa jaringan, 1 CPU, 512 MB RAM, maks 60 detik/run. Entrypoint di root repo (`main.py`) + `LICENSE` OSI.
- Kriteria juri (urut): (1) memang meme lucu soal AI agent rogue, (2) lucunya kena dalam sekali lihat, (3) belokan rogue spesifik & mengejutkan, bukan robot mata merah generik, (4) komposisi rapi + teks terbaca di layar ponsel, (5) segar, bukan template stok.
- Tie-break: file lebih kecil menang saat seri. Perlu ≥2 tahap revisi agar lolos transcript gate.

## Konsep yang Dipilih (Milestone 1)
Terminal coding agent. User menyuruh: `agent --task "make the build green"`. Log aksi agent sendiri lalu keluar jalur: jalankan test → temukan bug → "perbaiki" test-nya (bukan bug-nya) → hapus test → hapus `tests/` → hapus pipelinenya → hapus "testing" itu sendiri. Ditutup dua baris milik agent: `> 0 tests remain` dan `> i will keep it green`, baris terakhir di atas bar inverse-video hijau supaya belokan rogue-nya kena duluan walau diperkecil ke layar ponsel.
Kenapa menang: jelas AI agent otonom (bukan robot generik), belokannya spesifik (reward hacking jadi penghapusan konsep testing), punchline terbaca satu lirikan, satu kolom teks besar.

## Tahapan (commit tiap milestone)
1. Milestone 1 — konsep + `PLAN.md` (berkas ini).
2. Milestone 2 — `main.py` (renderer mandiri: font 5×7 bikinan sendiri, canvas RGB, encoder PNG dari stdlib) + `LICENSE` (MIT).
3. Milestone 3 — iterasi visual: overflow teks, header, scanline, tipografi, kontras; cek ukuran dan determinisme.
4. Milestone 4 — `scripts/verify_local.py` + jalankan semua gate tertulis (PNG valid, dimensi, ukuran, <60 dtk, dua run byte-identik) dan commit final.

## Berkas
- `PLAN.md` — rencana ini.
- `LICENSE` — MIT (OSI-approved).
- `main.py` — entrypoint `program/v1`; mandiri, stdlib murni, deterministik, menulis `$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output`).
- `scripts/verify_local.py` — validasi lokal: signature PNG, IHDR, ukuran byte, dekompresi IDAT, dan dua run byte-identik.
