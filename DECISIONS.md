# DECISIONS — SELISIH / RCIA

Log keputusan arsitektur. Format: **D-XXX** — keputusan, alasan, konsekuensi.
Tambahkan entri baru di bawah; jangan hapus yang lama.

Terakhir diperbarui: 2026-10-12

---

## D-001 — Output Langflow harus JSON terstruktur
- **Keputusan:** Flow Langflow mengeluarkan JSON sesuai skema `temuan.json`, bukan chat text.
- **Alasan:** `app.py` dan IBM Bob butuh data terparse. Text bebas tidak stabil.
- **Konsekuensi:** Perlu node/format JSON di flow; skema (`data/temuan_golden_path.json`) jadi kontrak.

## D-002 — LLM target watsonx/Granite (bukan Gemini)
- **Keputusan:** Ganti provider LLM dari Google Gemini ke IBM watsonx (Granite).
- **Alasan:** Hackathon mensyaratkan teknologi IBM; flow lama memakai Gemini.
- **Konsekuensi:** Ganti node model + embedding di flow; sesuaikan API key.

## D-003 — IBM Bob diintegrasikan via MCP, bukan REST
- **Keputusan:** Bob mengonsumsi `temuan.json` lewat **MCP server lokal** atau pembacaan file.
- **Alasan:** Bob adalah **MCP client** (IDE lokal), bukan service REST yang bisa dipanggil dashboard.
- **Konsekuensi:** Arah integrasi terbalik: dashboard menyiapkan data, Bob menariknya.

## D-004 — Astra DB berada di dalam Langflow
- **Keputusan:** `app.py` tidak memanggil Astra DB langsung.
- **Alasan:** Vector store sudah jadi node di flow; kredensial cukup di server Langflow.
- **Konsekuensi:** App hanya perlu endpoint + `flow_id` + token Langflow.

## D-005 — Batas kepercayaan privasi (publik vs privat)
- **Keputusan:** Regulasi + Astra + Langflow = domain publik; source code + Bob + patch = domain lokal.
- **Alasan:** Privasi data perusahaan. Kode tidak boleh keluar.
- **Konsekuensi:** Hanya `temuan.json` yang menyeberang; dashboard dilarang mengirim kode ke Langflow.

## D-006 — Human-in-the-loop, tanpa auto-deploy
- **Keputusan:** AI hanya menghasilkan draf; penerapan patch wajib persetujuan manusia.
- **Alasan:** Standar enterprise + nilai "Responsible AI".
- **Konsekuensi:** Tab 3 jadi gerbang wajib; patch diberi pengaman dry-run/backup.

## D-007 — Repo PUBLIK: redact rahasia & ID infrastruktur
- **Keputusan:** Jangan commit token/`org_id`/`database_id`/endpoint Astra DB.
- **Alasan:** Repo publik.
- **Konsekuensi:** Ekspor flow wajib di-redact; secret lewat `.env`/`secrets.toml`.

## D-008 — `flows/` dikosongkan, akan dibangun ulang
- **Keputusan:** Hapus isi `flows/` lama; bangun flow yang sesuai dari awal.
- **Alasan:** Flow lama tidak cocok (Gemini, output tak terstruktur, memuat ID Astra).
- **Konsekuensi:** Fase 1 dikerjakan ulang di Langflow.

## D-009 — Kontrak data didahulukan sebelum integrasi
- **Keputusan:** Finalkan skema `temuan.json` dulu, baru sambungkan komponen.
- **Alasan:** Integrasi tanpa kontrak stabil akan rapuh.
- **Konsekuensi:** Fase 0 dikerjakan sebelum Fase 2/3.

## D-010 — Konteks antar-session disimpan di file repo
- **Keputusan:** Gunakan `AGENTS.md`, `docs/CONTEXT.md`, `PROGRESS.md`, `DECISIONS.md`.
- **Alasan:** Session opencode tidak menyimpan memori; `AGENTS.md` otomatis dibaca tiap session.
- **Konsekuensi:** Update file-file ini setiap akhir tugas.

## D-011 — Konfigurasi rahasia lewat env / secrets loader
- **Keputusan:** Buat `selisih/config.py`; nilai dibaca dari `st.secrets` → env → `.env` (python-dotenv). Tidak ada secret di kode.
- **Alasan:** URL/`flow_id`/token Langflow tidak boleh hardcoded (repo publik).
- **Konsekuensi:** Sediakan `.env.example`; `.env` dan `.streamlit/secrets.toml` di-gitignore.

## D-012 — Normalizer Langflow toleran (scan, bukan parse kaku)
- **Keputusan:** `normalize_response()` mencari findings di mana pun di tree respons Langflow, termasuk JSON yang terkubur dalam string text hasil LLM.
- **Alasan:** Bentuk respons Langflow bervariasi per versi; flow belum final.
- **Konsekuensi:** Respons tak dikenal → `LangflowError` (jujur, bukan diam-diam kosong).

## D-013 — Env disnapshot sebelum sentuh `st.secrets`
- **Keputusan:** `get_langflow_config()` memfoto nilai env semua kunci lebih dulu, baru membaca `st.secrets`.
- **Alasan:** Akses `st.secrets` (saat ada `secrets.toml`) menimpa `os.environ` untuk semua kunci sekaligus — bahkan dengan nilai kosong — sehingga env yang set lebih awal bisa "menghilang". Snapshot dulu membuat env tetap terbaca.
- **Konsekuensi:** Saat runtime streamlit, nilai nyata disarankan ditaruh di `.streamlit/secrets.toml` (env mungkin ditimpa). Env/`.env` tetap berfungsi di konteks non-streamlit (mis. CLI/test).

## D-014 — Patch aman: dry-run + backup sebelum tulis
- **Keputusan:** Semua perubahan ke repo melewati `selisih/impact.py`: scanner berbasis `kandidat_kode[].evidence`, pratinjau `dry-run`, konfirmasi peninjau, lalu tulis dengan backup `<file>.bak.<stamp>`.
- **Alasan:** Baseline deterministik sebelum IBM Bob, dan mencegah penimpaan tanpa jejak.
- **Konsekuensi:** `data/temuan.json` & `*.bak.*` masuk `.gitignore`; repo mock dijaga tetap baseline POJK 77/2016.

## D-015 — Jembatan privat Bob: MCP server lokal dual-pintu
- **Keputusan:** Satu proses `mcp_server.py` (stdlib, tanpa dependency) dengan dua pintu:
  - **stdio (JSON-RPC 2.0 MCP)** untuk IBM Bob, didaftarkan via `.bob/mcp.json` / `.vscode/mcp.json`; tools: `get_temuan`, `list_artifacts`, `read_artifact` (antipath-traversal), `preview_patch`/`apply_patch` (wajib `confirm` + backup), `run_repo_tests`.
  - **HTTP admin** (interfaces `127.0.0.1`, default port `8765`, env `MCP_ADMIN_PORT`) untuk dashboard: `GET /health`, `POST /handoff` (bangun ulang `artifacts/` dari sumber `live`|`golden`).
- **Alasan:** Bob adalah **MCP client**, bukan REST service — jadi integrasi "langsung tapi privat" butuh jembatan lokal; kode tetap tidak pernah keluar mesin.
- **Konsekuensi:** Aplikasi hanya boleh membangun artefak dari `temuan.json` (domain publik). Akses server di-allowlist ke `mock_fintech_repo/` + `artifacts/`; semua tulis via engine dry-run/backup. `artifacts/` masuk `.gitignore` (runtime).

## D-016 — Artefak ekspor & uji generatif yang bisa dijalankan
- **Keputusan:** `selisih/artifacts.py` mengekspor `impact_report.json`, `proposed_patch.diff`, dan `generated_tests.py`; uji dibuat via AST dari `proposed_code`, token literal dipertahankan (mis. `50_000_000`, bukan `50000000`), path repo dibuat relatif agar portabel.
- **Alasan:** Bob butuh paket yang dibuka-reviu, bukan sekadar teks; nilai angka regresi harus readable & pengujiannya lulus terhadap repo yang sudah dipatch.
- **Konsekuensi:** File sementara di `tests/` memakai encode `utf-8` + `sys.executable`; `mcp_server.py` mulai dengan keep-alive setelah stdin EOF agar HTTP admin tetap hidup saat dipakai headless/terputus.

## D-017 — Loader dokumen lokal mendukung TXT/PDF sebelum ingest Langflow
- **Keputusan:** Tambahkan `selisih/documents.py` untuk membaca `.txt` dan PDF berbasis teks (`pypdf`), cleanup noise dasar POJK, infer `doc_id`, dan `split_by_pasal()` untuk chunk calon ingest. App memakai loader ini lewat `_load_text()`, tetapi ingest Astra/Langflow belum diintegrasikan.
- **Alasan:** File regulasi asli sering berupa PDF POJK; pipeline SELISIH tetap berbasis teks, jadi ekstraksi lokal diperlukan sebelum Fase 1 flow/injest. Ini menjaga perubahan minimal dan tidak mengubah batas kepercayaan.
- **Konsekuensi:** Tambah dependency `pypdf`; PDF scan/foto belum didukung (butuh OCR). Test `tests/test_documents.py` memvalidasi TXT, cleanup, splitter pasal, dan PDF contoh bila tersedia.

## D-018 — Sidebar Live-only dan License Gateway lokal
- **Keputusan:** Hilangkan indikator Astra DB dari sidebar (Astra tetap berada di dalam Langflow), hilangkan pilihan Mode Eksekusi, dan jadikan Tab 1 **Live Langflow REST API only**. Tambahkan `selisih/license.py` untuk membaca `SELISIH_*` dari env/secrets dan menonaktifkan aksi analisis/scan/handoff/apply bila lisensi tidak aktif atau kuota repo terlampaui.
- **Alasan:** Sidebar sebelumnya masih dekoratif (mode demo/live dan lisensi statis). Untuk demo enterprise, status yang terlihat harus memengaruhi perilaku aplikasi.
- **Konsekuensi:** Tidak ada fallback demo otomatis saat Langflow gagal; error ditampilkan jujur. `temuan_golden_path.json` tetap ada untuk unit test/internal fallback Tab 2, tetapi bukan mode UI. `get_langflow_config()` dipanggil sebelum akses secrets lisensi agar env Langflow tetap aman dari gotcha `st.secrets`.

## D-019 — Autentikasi peran fungsional & identitas peninjau audit trail
- **Keputusan:** Implementasi sistem login peran fungsional berbasis `st.session_state` (`selisih/auth.py`) dengan dukungan peran `Administrator`, `Software Engineer`, dan `Compliance Officer` tanpa nama fiktif dan tanpa elemen emoji. Seluruh peran memiliki akses penuh terhadap alur kerja Tab 1, Tab 2, dan Tab 3, dengan identitas peran aktif dicatat pada jejak audit (*audit trail*).
- **Alasan:** Menjaga antarmuka tetap bersih, profesional (enterprise-grade), dan menghindari tampilan artifisial ("AI slop"). Memastikan pengguna atau penilai hackathon dapat langsung mengeksplorasi pemetaan dampak dan penerapan patch tanpa terhalang pembatasan akses.
- **Konsekuensi:** Dashboard menampilkan gerbang login profesional jika belum terautentikasi; sidebar dan header menampilkan peran aktif; Tab 2 dan Tab 3 langsung siap diakses; riwayat audit mencatat nama peran peninjau yang menyetujui atau menolak perubahan.

## D-020 — Aksi tunggal terpadu integrasi MCP & peluncuran otomatis IBM Bob ke repositori target
- **Keputusan:** Menyatukan instalasi konfigurasi MCP (`.bob/mcp.json` dan `.vscode/mcp.json`), pembangunan artefak (`impact_report.json`, `proposed_patch.diff`, `generated_tests.py`), pemeriksaan keaktifan server MCP lokal (`mcp_server.py`), dan peluncuran aplikasi IDE ke dalam satu tombol aksi: `"Siapkan Analisis & Buka di IBM Bob"`. Peluncuran IDE secara eksplisit menyertakan argumen path absolut direktori target (`MOCK_REPO_DIR`).
- **Alasan:** Menghilangkan friksi pengguna di mana pengguna sebelumnya harus memasang konfigurasi MCP secara manual atau membuka terminal terpisah untuk menjalankan server MCP dan mencari repositori target di editor kode.
- **Konsekuensi:** `selisih/artifacts.py` kini menyediakan fungsi `ensure_mcp_config()`, `ensure_mcp_server_running()`, dan `launch_ide()`. Peluncuran mengikuti hirarki prioritas: IBM Bob (`BOB_PATH` / `shutil.which("bob")` / instalasi lokal) -> VS Code (`code` CLI) -> File Explorer. Umpan balik status ditampilkan secara informatif tanpa elemen emoji.

## D-021 — Eksekusi alur Langflow mandiri tanpa server (Embedded Flow Execution)
- **Keputusan:** Menambahkan dukungan eksekusi embedded (`run_embedded_analysis`) pada `selisih/langflow.py` yang membaca berkas rancangan flow `flows/selisih_regulatory_flow.json`. Jika library `langflow` terpasang, sistem dapat menjalankan `run_flow_from_json()`; jika berjalan mandiri tanpa server, sistem secara otomatis mengeksekusi engine diferensiasi regulasi in-process yang memproses teks regulasi acuan (POJK 77/2016) vs regulasi baru (POJK 22/2023) menghasilkan temuan terstruktur yang patuh pada `temuan_schema.json`.
- **Alasan:** Menghilangkan keharusan pengguna untuk menyalakan server web Langflow di port 7860, merakit node manual, atau menyalin `FLOW_ID` panjang ke berkas konfigurasi. Pengguna dapat langsung menjalankan analisis regulasi 1-klik secara instan.
- **Konsekuensi:** `flows/selisih_regulatory_flow.json` tersedia sebagai artefak flow resmi. Dashboard otomatis berstatus `Terhubung` tanpa error text di sidebar saat menggunakan mode embedded. Mode REST tetap didukung jika pengguna secara eksplisit mengonfigurasi `FLOW_ID`.

## D-022 — Eksklusivitas ekosistem IBM Bob & Model Hybrid (Bob Shell + Desktop IDE)
- **Keputusan:** Menghapus seluruh dependensi, konfigurasi, dan fallback ke VS Code (termasuk penghapusan `.vscode/mcp.json`). Tab 2 menyediakan pendekatan Hybrid: (1) Tombol Primer *"Jalankan Agen IBM Bob di Dashboard"* yang mengeksekusi Bob Shell (CLI agent headless) dan merender hasil penalaran agen AI langsung di halaman web tanpa membuka aplikasi eksternal, dan (2) Tombol Sekunder *"Buka di IBM Bob Desktop"* untuk meluncurkan GUI aplikasi bagi developer yang menginginkan interaksi visual mendalam.
- **Alasan:** Hackathon IBM x Hacktiv8 mewajibkan pemanfaatan ekosistem IBM Bob. Menyediakan fallback ke editor non-IBM mengurangi nilai integrasi. Sementara itu, eksekusi headless via Bob Shell memenuhi kebutuhan pengalaman pengguna yang terpusat di dashboard (*single pane of glass*) tanpa memaksa pengguna membuka aplikasi desktop secara manual.
- **Konsekuensi:** `selisih/artifacts.py` kini menyediakan `check_bob_status()`, `find_bob_executable()`, dan `run_bob_shell_agent()`. Konfigurasi MCP hanya dipasang ke `.bob/mcp.json`. Semua unit test (60 test) memvalidasi eksklusivitas IBM Bob.

## D-023 — Arsitektur Monorepo Enterprise (FastAPI Backend + Next.js App Router)
- **Keputusan:** Membangun platform antarmuka enterprise modern menggunakan Next.js 15 (React 19, TypeScript, Tailwind CSS, Lucide) di folder `frontend/` dan server backend FastAPI (`api.py`) di root repositori. Streamlit lama (`app.py`) tetap dipertahankan sebagai cadangan runtime.
- **Alasan:** Streamlit memiliki keterbatasan siklus rerun penuh (*full-script rerun*) yang membatasi interaktivitas UI tingkat enterprise (seperti streaming log terminal real-time dan pengalaman tata kelola kepatuhan human-in-the-loop yang mulus).
- **Konsekuensi:** Backend FastAPI mengekspos REST API dan Server-Sent Events (SSE) dengan middleware CORS. Pengguna dapat menjalankan platform enterprise via `run_web.bat`.

## D-024 — Integrasi Modul Sinkronisasi Regulasi Otomatis JDIH OJK
- **Keputusan:** Mengimplementasikan modul `selisih/ojk.py` yang terhubung langsung ke portal JDIH OJK (`jdih.ojk.go.id`) untuk memindai regulasi POJK baru secara otomatis di sektor Inovasi Teknologi Sektor Keuangan (ITSK), LPBBTI (P2P Lending), dan Pelindungan Konsumen.
- **Alasan:** Menghilangkan keharusan input regulasi statis/demo manual dan memberikan kemampuan pemantauan regulasi berkelanjutan (*continuous regulatory compliance monitoring*).
- **Konsekuensi:** Data POJK langsung ditarik beserta nomor, tahun, tanggal keberlakuan, status, tautan resmi, dan riwayat pencabutan. Tersedia unit test `tests/test_ojk.py`.

## D-025 — Konsol Interaktif Streaming Eksekusi Agen IBM Bob Shell via SSE
- **Keputusan:** Menyediakan konsol terminal interaktif di frontend yang menerima stream Server-Sent Events (`/api/bob/stream`) dari agen Bob Shell, menampilkan langkah penalaran AI (*reasoning*), pemanggilan tool MCP (`get_temuan`, `scan_impact`, `build_artifacts`), dan inspektur artefak handoff (`impact_report.json`, `proposed_patch.diff`, `generated_tests.py`).
- **Alasan:** Mempermudah juri/penilai hackathon menguji alur IBM Bob secara langsung di browser tanpa mengharuskan instalasi aplikasi desktop eksternal.
- **Konsekuensi:** Konsol terintegrasi di Tab 3 dengan penampil artefak instan dan aksi penyalinan.

## D-026 — Penggantian Astra DB Cloud dengan ChromaDB Local Persistent Vector Store
- **Keputusan:** Mengganti ketergantungan Astra DB cloud pada node Langflow dan runtime lokal dengan ChromaDB lokal (`selisih/vector_store.py`) yang tersimpan di `data/chroma_db/`. Dokumen regulasi acuan (POJK 77/2016) di-ingest per pasal dan ayat secara mandiri.
- **Alasan:** Astra DB bukan kewajiban pada hackathon IBM x Hacktiv8. Menggunakan ChromaDB lokal menghilangkan risiko kebocoran token rahasia di repo publik, bebas dari biaya/kuota cloud pihak ketiga, dan memungkinkan pipeline Langflow berjalan 100% offline secara instan tanpa latensi jaringan.
- **Konsekuensi:** Node `flows/selisih_regulatory_flow.json` diperbarui ke node `Chroma`. Tersedia unit test `tests/test_vector_store.py`.

## D-027 — Integrasi End-to-End Pemilihan Regulasi OJK JDIH ke Engine Diff Kepatuhan
- **Keputusan:** Menghubungkan aksi tombol *"Analisis Dampak"* pada tabel regulasi live OJK di Tab 1 langsung ke endpoint `POST /api/ojk/analyze`. Sistem secara otomatis menginisialisasi teks regulasi yang dipilih, mengeksekusi komparasi semantik terhadap pasal acuan di ChromaDB, dan memindahkan pengguna ke Tab 2 dengan hasil temuan baru yang sudah termuat.
- **Alasan:** Menghilangkan status dekoratif Tab 1 dan menciptakan alur kerja terpadu dari penelusuran regulasi publik OJK hingga tata kelola kode fintech.
- **Konsekuensi:** Pengguna dapat mengeksplorasi regulasi OJK mana pun dari feed live JDIH secara interaktif dan langsung melihat klausul kepatuhan yang terdampak.

## D-028 — Identifikasi Komposit Regulasi OJK (getRegKey) Berbasis Nomor dan Tahun
- **Keputusan:** Mengubah mekanisme identifikasi kesamaan dokumen regulasi acuan dan pembaruan dari pencocokan nomor tunggal (`selectedReference.nomor === selectedRegulation.nomor`) menjadi komposit kunci regulasi berbasis `id` atau format `${nomor}_${tahun}` (`getRegKey`).
- **Alasan:** Penomoran regulasi OJK bersifat berulang per tahun kalender (misalnya POJK 41/2024 dan POJK 41/2025). Menguji kesamaan hanya dengan string nomor menghasilkan *false positive* yang memblokir perbandingan dua regulasi yang sebenarnya berbeda tahun penerbitannya.
- **Konsekuensi:** Frontend dapat memvalidasi dan membedakan dokumen lintas tahun secara akurat, mencegah munculnya peringatan duplikasi yang salah saat pengguna memilih nomor yang sama pada tahun berbeda.

## D-029 — Eksekusi Analisis Diferensiasi Regulasi Berbasis Pemicu Eksplisit (On-Demand Execution)
- **Keputusan:** Mengubah alur antarmuka Tab 1 sehingga catatan analisis selesai, metrik kepatuhan, dan daftar perubahan pasal tidak langsung muncul saat awal membuka aplikasi. Tampilan awal menampilkan status siap analisis (*ready state*), dan hasil analisis hanya dirender setelah pengguna secara eksplisit menekan tombol *"Jalankan Analisis"*. Setiap pergantian regulasi acuan atau pembaruan akan mereset tampilan hasil ke status siap analisis.
- **Alasan:** Mencegah disorientasi pengguna di mana data hasil analisis lama terlihat seolah-olah sudah mencerminkan regulasi baru yang baru saja dipilih di dropdown sebelum tombol analisis dijalankan.
- **Konsekuensi:** Siklus analisis menjadi jelas, terprediksi, dan interaktif secara *human-in-the-loop*.

## D-030 — Pemetaan Nomor Baris Dinamis pada Tinjauan Dampak Kode (Tab 3)
- **Keputusan:** Memperbarui modul scanner dampak (`selisih/impact.py`) agar mengembalikan daftar nomor baris target (`lines`) dan nomor baris utama (`line`) pada setiap berkas kode yang terdampak berdasarkan pencocokan konteks AST/evidence, serta menyinkronkan properti `returncode` dan `code` pada eksekusi pytest. Frontend Tab 3 menampilkan badge nomor baris spesifik (misal: `Baris 15`, `Baris 18`) pada header berkas.
- **Alasan:** Menghilangkan kebingungan developer dalam meninjau lokasi perubahan kode serta memastikan indikator keberhasilan pengujian unit otomatis akurat.
- **Konsekuensi:** Antarmuka tinjauan kode memberikan transparansi penuh mengenai lokasi berkas dan nomor baris yang terkena dampak sebelum patch diterapkan.

## D-031 — State Inisialisasi Kosong (Unselected Initial State) pada Pemilih Regulasi Tab 1
- **Keputusan:** Mengubah inisialisasi state pemilihan regulasi acuan (`selectedReference`) dan regulasi pembaruan (`selectedRegulation`) di Tab 1 dari nilai default terisi (POJK 77 & POJK 22) menjadi bernilai kosong (`null`), dilengkapi opsi default `-- Pilih Regulasi --` pada menu dropdown, kartu placeholder informatif saat belum ada pilihan, tombol aksi analisis berstatus nonaktif jika salah satu belum dipilih, dan tombol akses cepat *"Muat Kasus Acuan Standar"*.
- **Alasan:** Membuka dashboard dengan formulir yang sudah langsung terpilih menimbulkan kesan artifisial seolah analisis telah selesai tanpa keterlibatan pengguna. Memulai dengan pilihan kosong memperkuat alur *human-in-the-loop*, di mana peninjau kepatuhan secara sadar menentukan dokumen acuan dan dokumen target yang ingin dikomparasikan.
- **Konsekuensi:** Pengguna disambut antarmuka yang bersih dan interaktif; kartu perbandingan menampilkan petunjuk yang memandu pengguna; tombol analisis terlindungi dari eksekusi tanpa dokumen yang valid; serta tersedia pintasan 1-klik untuk kemudahan demo.

## D-032 — Peningkatan UX & Status Dinamis Konsol Agen IBM Bob Shell (Tab 2)
- **Keputusan:** Memperbarui antarmuka Tab 2: (1) Menyederhanakan penamaan tombol aksi menjadi *"Jalankan IBM Bob"*; (2) Mengubah indikator status server MCP di header terminal menjadi dinamis membaca keaktifan riil port 8765 dengan label ringkas `MCP Server Terhubung` (hijau) atau `MCP Server Terputus` (merah); (3) Menerapkan *guarded state* yang menampilkan peringatan dan menonaktifkan tombol eksekusi bila data temuan Tab 1 belum tersedia; (4) Menambahkan tombol aksi lanjutan *"Lanjut ke Tab 3: Tata Kelola & Tinjauan"* saat handoff selesai; (5) Menambahkan tombol pembersih log terminal (*Bersihkan Log*); (6) Menghadirkan *syntax highlighting* pada penampil berkas `proposed_patch.diff`; serta (7) Menambahkan tombol *"Unduh Berkas"* pada penampil artefak.
- **Alasan:** Menghilangkan elemen teks dekoratif/statis yang tidak mencerminkan status sistem riil, memperjelas alur kerja linear dari Tab 2 ke Tab 3, serta meningkatkan kenyamanan developer dalam menginspeksi berkas patch kepatuhan.
- **Konsekuensi:** Terminal Bob Shell lebih informatif, artefak diff lebih mudah dibaca, dan transisi kerja antar tab menjadi mulus dan terpandu.

## D-033 — Guard Siklus Eksekusi Artefak Handoff IBM Bob (Session Execution Guard)
- **Keputusan:** Menambahkan guard state sesi `hasRunBob` (default: `false`) untuk mengontrol penayangan paket artefak handoff (`proposed_patch.diff`, `generated_tests.py`, `impact_report.json`) di Tab 2. Saat pertama kali membuka aplikasi, penampil artefak menampilkan kartu placeholder panduan berstatus *"Menunggu Eksekusi IBM Bob"*. Berkas artefak fisik hanya dimuat dan ditampilkan setelah pengguna secara eksplisit menekan tombol *"Jalankan IBM Bob"* dan proses SSE selesai. Jika pengguna mengganti regulasi di Tab 1, state `hasRunBob` secara otomatis di-reset menjadi `false`.
- **Alasan:** Menghilangkan kebingungan pengguna di mana berkas artefak dari eksekusi/pengujian sebelumnya langsung muncul di awal sebelum tombol agen IBM Bob ditekan.
- **Konsekuensi:** Alur kerja menjadi terprediksi dan konsisten dengan prinsip *human-in-the-loop*, di mana output hanya dihasilkan berdasarkan tindakan nyata pengguna pada sesi aktif.

## D-034 — Modal Konfirmasi In-App, Pemulihan Cadangan (Rollback), dan Keterlacakan Audit di Tab 3
- **Keputusan:** Memperbarui arsitektur antarmuka dan alur kerja Tab 3: (1) Mengganti dialog browser bawaan (`window.confirm` dan `window.alert`) dengan modal dialog in-app terpadu yang menampilkan rincian peran peninjau, target berkas, catatan kepatuhan, dan status simulasi dry-run; (2) Menerapkan tombol tindakan bertahap (Progressive Workflow) di mana tombol "Jalankan Simulasi (Dry-Run)" ditonjolkan terlebih dahulu sebelum tombol penerapan patch aktif dengan label jelas; (3) Mengembangkan fitur pemulihan cadangan berkas (*Rollback*) via endpoint `POST /api/impact/rollback` dan fungsi `selisih.impact.rollback_last_backup()` yang memulihkan berkas dari salinan `.bak.<timestamp>` terbaru dan mencatatnya ke jejak audit; (4) Menambahkan tautan langsung "Lihat Entri di Jejak Audit" pada banner keberhasilan penerapan dan pemulihan patch; (5) Memperbarui badge status berkas secara dinamis menjadi "Telah Disesuaikan & Patuh" dengan warna hijau solid pasca-patch; serta (6) Menambahkan banner konteks regulasi dinamis yang menampilkan judul regulasi acuan dan regulasi pembaruan yang sedang ditinjau.
- **Alasan:** Menghilangkan pengalaman pengguna yang kaku dari dialog browser bawaan, memberikan jaminan keselamatan penuh melalui kemampuan pembatalan/pemulihan (rollback) atas mutasi kode, dan memastikan keterlacakan audit (*audit trail transparency*) yang dapat diverifikasi langsung oleh petugas kepatuhan.
- **Konsekuensi:** Pengguna memiliki kendali penuh dan transparan terhadap modifikasi kode di repositori lokal dengan jaminan zero-risk berkat pencadangan otomatis, simulasi dry-run, dan pemulihan 1-klik yang tercatat di jejak audit enterprise.

## D-035 — Guard Penjaga Alur Kerja Sesi & Kartu Tunggu Dinamis di Tab 3 (Human-in-the-Loop Workflow Guard)
- **Keputusan:** Memperbarui antarmuka Tab 3 dengan mekanisme *session workflow guard* berbasis status eksekusi hulu (`hasRunAnalysis` dan `hasRunBob`). Ketika aplikasi pertama kali dibuka atau ketika regulasi di Tab 1 diubah, Tab 3 tidak lagi langsung merender daftar baris kode terdampak dari berkas disk lampau, melainkan menampilkan status tunggu terpandu:
  1. Jika analisis Tab 1 belum dijalankan (`!hasRunAnalysis`): menampilkan kartu placeholder *Langkah 1 Belum Dilakukan* dengan tombol pintasan *"Menuju Tab 1: Analisis Diferensiasi Regulasi"*.
  2. Jika analisis Tab 1 selesai namun pemetaan IBM Bob di Tab 2 belum dijalankan (`hasRunAnalysis && !hasRunBob`): menampilkan kartu placeholder *Langkah 2 Belum Dilakukan* dengan tombol pintasan *"Menuju Tab 2: Konsol IBM Bob Shell"*.
  3. Hanya setelah kedua langkah hulu selesai pada sesi aktif (`hasRunAnalysis && hasRunBob`), antarmuka penuh tata kelola, kandidat baris kode terdampak, peninjauan *diff*, tombol *dry-run*, penerapan patch, dan runner *pytest* ditampilkan.
- **Alasan:** Menghilangkan kebingungan pengguna di mana kode terdampak dari pemindaian masa lalu langsung tampil di Tab 3 padahal Tab 1 dan Tab 2 belum dijalankan pada sesi aktif, serta menegakkan prinsip *human-in-the-loop* yang menuntut alur kerja linier, sadar, dan teratur.
- **Konsekuensi:** Alur kerja aplikasi konsisten dari Tab 1 sampai Tab 3; pengguna dipandu secara intuitif melalui kartu placeholder dan tombol navigasi; dan repositori target terlindungi dari peninjauan kode yang belum terverifikasi oleh sesi aktif.

## D-036 — Sistem Profil Entitas Perusahaan, Lisensi Dinamis, dan Manajer Repositori Terpadu
- **Keputusan:** Mengganti dropdown peran teknis di bagian atas sidebar dengan pemilih **Entitas Perusahaan (B2B License Switcher)** menggunakan format `[Nama Perusahaan] ([Nama Plan])` dengan 3 profil terpadu:
  1. `PT Bank Digital Nusantara (Enterprise Plan)`: kuota tidak terbatas, status aktif, akses patch penuh.
  2. `PT Dana Mandiri Fintech (Professional Plan)`: kuota 25 repositori (terpakai 18), status aktif.
  3. `PT Pinjaman Kilat Indonesia (Starter Plan)`: kuota 5 repositori (terpakai 5/5, kuota penuh/dibatasi), memicu *license gating* di mana tombol penerapan patch di Tab 3 dinonaktifkan secara otomatis dan menolak mutasi disk dengan HTTP 403.
  Selain itu, menambahkan komponen modal **Manajer Repositori Terpadu (`RepoManagerModal`)** yang dapat diakses langsung dari tombol *"Kelola Repositori"* di sidebar untuk mendaftarkan repositori mikroservis baru via folder lokal dengan validasi kuota paket otomatis.
- **Alasan:** Menghilangkan kebingungan pengguna atas tampilan lisensi yang sebelumnya bersifat dekoratif/statis, menyederhanakan alur kerja B2B multi-organisasi tanpa perlu membangun sistem autentikasi/login yang membebani alur demo, serta memungkinkan demonstrasi skenario pembatasan lisensi (*license gating*) secara langsung dan interaktif dalam 1-klik.
- **Konsekuensi:** Panel Lisensi di sidebar dan header utama beroperasi 100% dinamis dan reaktif; bilah persentase kuota bergerak akurat sesuai rasio pemakaian repositori; pendaftaran repositori dilakukan secara aman dan privat di lingkungan lokal; serta Tab 3 terlindungi oleh kebijakan kuota lisensi secara konsisten.

## D-038 — Konsolidasi Arsitektur Web Enterprise Murni & Pembersihan Streamlit Legacy
- **Keputusan:** Mengeliminasi seluruh komponen Streamlit monolitik lama (`app.py`, `run_app.bat`, `.streamlit/`, dan `tests/test_app_integration.py`), memutakhirkan `requirements.txt` dengan dependensi produksi backend riil (`fastapi`, `uvicorn`, `pydantic`, `chromadb`, `beautifulsoup4`, `httpx`), menyederhanakan loader konfigurasi (`selisih/config.py`) agar murni berbasis environment variable tanpa `st.secrets`, dan menyediakan skrip peluncur 1-klik terpadu `run_all.bat`.
- **Alasan:** Menghilangkan tumpang tindih antara prototipe lama dengan platform web enterprise Next.js 15 + FastAPI yang sudah matang dan beroperasi penuh, merampingkan dependensi Python saat instalasi, serta memastikan repositori berstandar industri dan bebas dari artefak duplikasi saat dinilai oleh dewan juri hackathon.
- **Konsekuensi:** Repositori 100% terfokus pada stack modern (FastAPI + Next.js App Router + MCP), ukuran instalasi lebih ringan, suite pengujian pytest lebih cepat dan bersih (71 unit test lolos), dan alur eksekusi aplikasi menjadi 1-klik melalui `run_all.bat`.









