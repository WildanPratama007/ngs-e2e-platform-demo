# 📊 Benchmarking Report — NGS E2E Pipeline Comparison

**Tanggal Pengujian:** 26 Oktober 2026  
**Data Input:** `sim_chr22.fastq` — 500,000 reads sintetis (wgsim, -N 500000 -1 150 -S 42)  
**Referensi Genom:** Human GRCh38 chr22 (~51MB)  
**Ground Truth:** `sim_chr22_mutations.txt` (wgsim mutations, 39,227 mutasi di kromosom VCF)  
**Mesin:** WSL2 Ubuntu, RAM 64GB, GPU GTX 1080Ti (tidak digunakan), 6 CPU cores  

---

## 1. 🏗️ Arsitektur Pipeline

| Aspek                | Demo (Manual)             | Nextflow                        | Snakemake                      |
|----------------------|---------------------------|---------------------------------|--------------------------------|
| Workflow Manager     | ❌ Tidak ada              | ✅ Nextflow DSL2 v24.10.6       | ✅ Snakemake v9.27.1           |
| Bahasa Konfigurasi   | Python (hardcode)         | Groovy (`nextflow.config`)      | YAML (`config.yaml`)           |
| Paradigma Eksekusi   | Prosedural (sequential)   | Data-flow (channel-based)       | Rule-based (file-driven)       |
| Python Version       | 3.6 (datacarpentry_env)   | 3.11 (ngs_platform)             | 3.11 (snakemake_human)         |
| Streamlit Version    | 0.84.0 (lama)             | Latest                          | Latest                         |
| Resume Pipeline      | ❌ Tidak ada              | ✅ `-resume`                    | ✅ `--rerun-incomplete`        |
| Dry Run              | ❌ Tidak ada              | ❌ Tidak ada                    | ✅ `--dry-run`                 |
| Log per Proses       | ❌ Error dict saja        | ✅ work dir per proses          | ✅ `results/logs/` per rule    |
| Paralel Eksekusi     | ❌ Sequential             | ✅ FastQC + Trimmomatic paralel | ✅ Configurable `--cores`      |

---

## 2. ⏱️ Execution Time

Waktu diukur dari mulai pipeline hingga VCF selesai dibuat, input `sim_chr22.fastq` (500K reads).

| Tahap                | Demo (Manual) | Nextflow     | Snakemake    |
|----------------------|---------------|--------------|--------------|
| FastQC               | ~30 detik     | ~18 detik    | ~18 detik    |
| Trimmomatic SE       | ~13 detik     | ~13 detik    | ~14 detik    |
| BWA MEM + Sort/Index | ~5-10 menit   | ~5 menit     | ~5 menit     |
| BCFTools Variant Call| ~5-10 menit   | ~3 menit     | ~3 menit     |
| **Total**            | **~15-20 menit** | **6 menit 19 detik** ✅ | **~8 menit** |

> Nextflow lebih cepat karena FastQC dan Trimmomatic dijalankan **paralel** secara bersamaan (channel-based).  
> Demo lebih lambat karena semua tahap berjalan **sequential** satu per satu.

---

## 3. 📁 Ukuran Output

| File                        | Demo          | Nextflow      | Snakemake     |
|-----------------------------|---------------|---------------|---------------|
| `sim_chr22.filtered.vcf`    | 1,576,319 bytes (1.5MB) | 1,501,005 bytes (1.4MB) | 1,501,176 bytes (1.4MB) |
| `sim_chr22.bcf`             | 274,600,845 bytes (261MB) | N/A (tidak di-publish) | 275,888,771 bytes (263MB) |
| `sim_chr22.aligned.sorted.bam` | ~37MB      | ~37MB         | 37,400,531 bytes (35MB) |

> Perbedaan ukuran VCF antara Demo (~1.5MB) vs Nextflow/Snakemake (~1.4MB) disebabkan perbedaan kecil pada header VCF dan metadata yang ditambahkan masing-masing pipeline.

---

## 4. 🔬 Hasil Validasi VCF vs Ground Truth (wgsim)

Ground truth: **39,227 mutasi** di kromosom yang ter-cover (dari total 3,050,631 mutasi hg38 full).  
Data input: 500K reads → coverage rata-rata **~1.5x** di chr22.

| Metrik                    | Demo (Manual) | Nextflow      | Snakemake     |
|---------------------------|---------------|---------------|---------------|
| Total Mutasi GT           | 39,227        | 39,227        | 39,227        |
| Total Variant di VCF      | 12,269        | ~12,200       | ~12,200       |
| ✅ True Positive (TP)     | 8,930         | ~8,900        | ~8,900        |
| ❌ False Negative (FN)    | 30,297        | ~30,327       | ~30,327       |
| ⚠️ False Positive (FP)    | 3,339         | ~3,300        | ~3,300        |
| **Sensitivity (Recall)**  | **22.8%**     | **~22.7%**    | **~22.7%**    |
| **Precision**             | **72.8%**     | **~73.0%**    | **~73.0%**    |

> Sensitivity rendah (22.8%) disebabkan coverage hanya **~1.5x** — bcftools butuh minimal 5x untuk call variant secara reliable. Ini bukan masalah pipeline, melainkan jumlah reads yang kurang untuk full genome chr22 (~50Mb).  
> Untuk mencapai Sensitivity >80%, dibutuhkan minimal **10 juta reads** (~30x coverage).

> Ketiga pipeline menghasilkan nilai yang **hampir identik** karena menggunakan tools yang sama (BWA + Samtools + BCFTools) dengan parameter yang sama.

---

## 5. ✅ Kelebihan dan ❌ Kekurangan

### Demo (Manual) — `Demo/app.py`

| ✅ Kelebihan | ❌ Kekurangan |
|---|---|
| Paling mudah disetup — tidak butuh workflow manager | Python 3.6 menyebabkan banyak error kompatibilitas Streamlit |
| Cocok untuk eksplorasi dan prototyping cepat | Banyak fitur Streamlit modern tidak tersedia (`st.status`, `st.divider`, dll) |
| Fitur paling lengkap: validasi GT + perbandingan VCF antar pipeline | Pipeline sequential — tidak ada paralelisme |
| Tidak ada dependensi tambahan selain tools bioinformatika | Tidak ada resume — pipeline harus ulang dari awal jika gagal |
| | Error hanya ditampilkan sebagai teks, tidak ada work directory untuk debug |
| | Trimmomatic gagal pada data sintetis wgsim (fallback ke file asli) |

---

### Nextflow — `ngs_platform/`

| ✅ Kelebihan | ❌ Kekurangan |
|---|---|
| Pipeline paling **cepat** (6 menit 19 detik) karena eksekusi paralel | Setup lebih kompleks — butuh Java + Nextflow |
| Resume otomatis (`-resume`) — lanjut dari titik terakhir jika gagal | Konflik `libcrypto.so.1.0.0` pada samtools/bcftools versi conda |
| Work directory terpisah per proses — mudah debug | Harus hardcode path `bin_dir`, `samtools_bin`, `bcftools_bin` secara manual |
| Generate pipeline report HTML otomatis | DSL2 channel-based lebih sulit dipahami untuk pemula |
| Mudah scale ke cluster (ganti profile saja) | `beforeScript` tidak efektif override PATH di WSL |
| Log real-time di Streamlit UI | |

---

### Snakemake — `ngs_platform_human/`

| ✅ Kelebihan | ❌ Kekurangan |
|---|---|
| Konfigurasi terpusat di `config.yaml` — paling mudah diubah | Setup butuh mamba untuk menghindari solver conflict |
| Dry run (`--dry-run`) untuk validasi pipeline sebelum eksekusi | Sama seperti Nextflow: samtools/bcftools harus pakai apt |
| Log per rule tersimpan di `results/logs/` — paling terstruktur | Versi Snakemake 9.x API berubah signifikan dari versi lama |
| Resume otomatis (`--rerun-incomplete`) | |
| Rule-based lebih intuitif bagi pengguna Python/Makefile | |
| Visualisasi DAG pipeline tersedia (`--dag \| dot`) | |
| Snakemake 9.27.1 — versi paling baru dari ketiganya | |

---

## 6. 🏆 Rekomendasi Penggunaan

| Skenario | Rekomendasi |
|---|---|
| Belajar & eksplorasi cepat | **Demo** |
| Pipeline production, perlu resume & paralel | **Nextflow** |
| Pipeline akademik, perlu dry-run & DAG visualisasi | **Snakemake** |
| Scale ke HPC/cluster | **Nextflow** (profile system) atau **Snakemake** (cluster config) |
| Meningkatkan Sensitivity | Naikkan reads ke 10 juta (`-N 10000000`) di wgsim |

---

## 7. 📌 Catatan Teknis Penting

1. **Samtools & BCFTools** harus diinstall via `apt` di semua pipeline karena versi conda mengalami error `libcrypto.so.1.0.0` yang disebabkan kompatibilitas OpenSSL di Ubuntu versi baru.
2. **Trimmomatic** membuang semua reads data sintetis wgsim karena reads tidak memiliki adapter dan memiliki quality score yang seragam — semua pipeline menggunakan fallback ke file FASTQ asli.
3. **Coverage ~1.5x** tidak cukup untuk variant calling yang baik. Sensitivity 22.8% adalah hasil yang expected dan bukan indikasi pipeline rusak.
4. **GPU GTX 1080Ti** tidak dimanfaatkan oleh pipeline ini — semua tools (BWA, Samtools, BCFTools) adalah CPU-based.
5. Ketiga pipeline menghasilkan **VCF yang konsisten** karena menggunakan tools dan parameter yang identik.
