# 🧬 NGS E2E Platform — Nextflow Pipeline

Platform analisis sekunder NGS berbasis **Nextflow** (DSL2) dengan Streamlit sebagai Web UI. Pipeline dieksekusi oleh Nextflow untuk reproducibility, resume otomatis, dan kemudahan scale ke cluster.

---

## 📁 Struktur Direktori

```
ngs_platform/
├── main.nf             ← Nextflow pipeline script (DSL2)
├── nextflow.config     ← Konfigurasi executor & profil
├── app.py              ← Streamlit web application
├── requirements.txt    ← Python dependencies
├── README.md           ← Dokumentasi ini
├── uploads/            ← FASTQ input (auto-dibuat)
├── results/
│   └── <sample_name>/
│       ├── fastqc/     ← Output FastQC
│       ├── trimmed/    ← Trimmed FASTQ
│       ├── bwa/        ← Sorted BAM + BAI
│       └── vcf/        ← BCF, VCF, Filtered VCF
└── work/               ← Nextflow work directory (auto-dibuat)
```

---

## ⚙️ Prasyarat Sistem

- Windows 10/11 dengan **WSL2 Ubuntu**
- **Miniconda** terinstall di WSL
- **Java 11+** (dibutuhkan Nextflow)
- RAM minimal 16GB (rekomendasi 32GB+ untuk chr22)

---

## 🔧 Instalasi Dependencies

### 1. Buat conda environment baru

```bash
conda create -n ngs_platform python=3.11 -y
conda activate ngs_platform
```

### 2. Install tools bioinformatika

```bash
# Install via conda
conda install -c bioconda -c conda-forge bwa trimmomatic nextflow -y

# Install samtools & bcftools via apt (menghindari masalah libcrypto)
sudo apt update && sudo apt install -y samtools bcftools
```

### 3. Install Python dependencies

```bash
pip install streamlit pandas
```

### 4. Verifikasi instalasi

```bash
nextflow -version
which bwa trimmomatic
/usr/bin/samtools --version
/usr/bin/bcftools --version
streamlit --version
```

---

## 📥 Persiapan Referensi Genom

### Human GRCh38 chr22 (default)

```bash
# chr22 sudah tersedia di:
# /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa

# Verifikasi index sudah lengkap
ls -lh /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa*
# Harus ada: .amb .ann .bwt .pac .sa .fai
```

Jika index belum ada:
```bash
bwa index /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa
samtools faidx /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa
```

---

## 🚀 Menjalankan Aplikasi

### Via Streamlit UI

```bash
conda activate ngs_platform
cd /mnt/c/Users/Mahasiswa/Fastt/ngs_platform
streamlit run app.py
```

Buka browser di: **http://localhost:8502**

### Via Terminal (tanpa UI)

```bash
conda activate ngs_platform
cd /mnt/c/Users/Mahasiswa/Fastt/ngs_platform

nextflow run main.nf \
  -profile conda_env \
  --reads '/mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq' \
  --ref_genome '/mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa' \
  --ploidy GRCh38 \
  --outdir results
```

---

## 📋 Cara Penggunaan di UI

1. Buka **http://localhost:8502**
2. Upload file FASTQ di sidebar
3. Pastikan **Path Referensi Genom**: `/mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa`
4. Pilih **Ploidy**: `GRCh38`
5. Pilih **Profile**: `conda_env`
6. Pastikan **Path Nextflow**: `/home/mahasiswa/miniconda3/envs/ngs_platform/bin/nextflow`
7. Klik **🚀 Jalankan Pipeline via Nextflow**
8. Download hasil dari tombol yang tersedia setelah selesai

---

## 🔬 Alur Pipeline (Nextflow DSL2)

```
FASTQ Input (Channel)
    │
    ▼
[FASTQC]          → QC report (.html, .zip)
    │
    ▼
[TRIMMOMATIC_SE]  → Trimmed FASTQ
    │
    ▼
[BWA_ALIGN]       → Sorted BAM + BAI
    │
    ▼
[VARIANT_CALLING] → Filtered VCF
```

---

## 🔧 Konfigurasi (`nextflow.config`)

| Parameter | Default | Keterangan |
|---|---|---|
| `ref_genome` | `chr22.fa` | Path referensi genom |
| `ploidy` | `GRCh38` | Diploid human |
| `fastqc_path` | Path FastQC | Binary FastQC |
| `bin_dir` | `ngs_platform/bin` | Tools conda |
| `samtools_bin` | `/usr/bin/samtools` | Samtools dari apt |
| `bcftools_bin` | `/usr/bin/bcftools` | BCFTools dari apt |

---

## 🔄 Resume Pipeline

Jika pipeline terputus di tengah jalan:

```bash
nextflow run main.nf -profile conda_env \
  --reads '...' --ref_genome '...' \
  -resume
```

Nextflow akan skip proses yang sudah selesai dan melanjutkan dari titik terakhir.

---

## 🗑️ Reset Pipeline

```bash
rm -rf work .nextflow .nextflow.log results
```

---

## ⚠️ Catatan

- `samtools` dan `bcftools` menggunakan versi dari **apt** (`/usr/bin/`) karena versi conda mengalami konflik `libcrypto.so.1.0.0`
- Pipeline di-test dengan **Nextflow 24.10.6** di WSL2 Ubuntu
- Work directory (`work/`) bisa mencapai beberapa GB — hapus setelah pipeline selesai jika disk terbatas
