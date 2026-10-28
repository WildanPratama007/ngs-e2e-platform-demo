# 🧬 NGS E2E Platform Human — Snakemake Pipeline

Platform analisis sekunder NGS berbasis **Snakemake** khusus data **Human GRCh38 chr22** dengan Streamlit sebagai Web UI. Pipeline menggunakan paradigma rule-based (file-driven) dengan konfigurasi terpusat di `config.yaml`.

---

## 📁 Struktur Direktori

```
ngs_platform_human/
├── Snakefile           ← Pipeline rules (4 rules)
├── config.yaml         ← Konfigurasi parameter & path
├── app.py              ← Streamlit web application
├── requirements.txt    ← Python dependencies
├── README.md           ← Dokumentasi ini
├── uploads/            ← FASTQ input (auto-dibuat)
├── results/
│   └── <sample_name>/
│       ├── fastqc/     ← Output FastQC
│       ├── trimmed/    ← Trimmed FASTQ
│       ├── bwa/        ← Sorted BAM + BAI
│       ├── vcf/        ← BCF, VCF, Filtered VCF
│       └── logs/       ← Log tiap rule
└── ref_genome/         ← Placeholder referensi genom
```

---

## ⚙️ Prasyarat Sistem

- Windows 10/11 dengan **WSL2 Ubuntu**
- **Miniconda** terinstall di WSL
- RAM minimal 16GB (rekomendasi 32GB+ untuk chr22 full coverage)

---

## 🔧 Instalasi Dependencies

### 1. Buat conda environment baru

```bash
conda create -n snakemake_human python=3.11 -y
conda activate snakemake_human
```

### 2. Install mamba (solver lebih cepat)

```bash
conda install -c conda-forge mamba -y
```

### 3. Install tools bioinformatika

```bash
# Install snakemake, bwa, trimmomatic via mamba
mamba install -c bioconda -c conda-forge snakemake bwa trimmomatic -y

# Install samtools & bcftools via apt (menghindari masalah libcrypto)
sudo apt update && sudo apt install -y samtools bcftools
```

### 4. Install Python dependencies

```bash
pip install streamlit pandas pyyaml
```

### 5. Verifikasi instalasi

```bash
snakemake --version     # minimal 7.x, tested pada 9.27.1
which bwa trimmomatic
/usr/bin/samtools --version
/usr/bin/bcftools --version
streamlit --version
python -c "import yaml; print('pyyaml OK')"
```

---

## 📥 Persiapan Referensi Genom GRCh38 chr22

### Jika chr22.fa belum ada

```bash
# Download chr22 GRCh38 dari UCSC (~51MB)
curl -L -o /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa.gz \
  https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz

# Ekstrak
gunzip /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa.gz

# Build BWA index (~3-5 menit)
bwa index /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa

# Build samtools index
samtools faidx /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa
```

### Verifikasi index lengkap

```bash
ls -lh /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa*
# Harus ada 7 file:
# chr22.fa  chr22.fa.amb  chr22.fa.ann  chr22.fa.bwt
# chr22.fa.pac  chr22.fa.sa  chr22.fa.fai
```

---

## 📥 Generate Data Sintetis (opsional, untuk testing)

```bash
# Generate 500K reads dari chr22
wgsim -N 500000 -1 150 -S 42 \
  /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa \
  /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq \
  /dev/null \
  > /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22_mutations.txt

# Cek hasil
wc -l /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq
# Harus: 2000000 (500K reads x 4 baris)
```

---

## 🚀 Menjalankan Aplikasi

### Via Streamlit UI

```bash
conda activate snakemake_human
cd /mnt/c/Users/Mahasiswa/Fastt/ngs_platform_human
streamlit run app.py
```

Buka browser di: **http://localhost:8501** (atau port yang muncul di terminal)

### Via Terminal (tanpa UI)

```bash
conda activate snakemake_human
cd /mnt/c/Users/Mahasiswa/Fastt/ngs_platform_human

# Copy FASTQ ke folder uploads
cp /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq uploads/

# Jalankan pipeline
snakemake --cores 4 --rerun-incomplete --printshellcmds
```

---

## 📋 Cara Penggunaan di UI

1. Buka browser di URL yang tertera di terminal
2. Upload file FASTQ (Human chr22) di sidebar
3. Pastikan **Path Referensi Genom**: `/mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa`
4. Atur jumlah **CPU Cores** (rekomendasi: 4)
5. Pastikan **Path Snakemake**: `/home/mahasiswa/miniconda3/envs/snakemake_human/bin/snakemake`
6. Opsional: centang **Dry Run** untuk cek rencana pipeline tanpa eksekusi
7. Klik **🚀 Jalankan Pipeline via Snakemake**
8. Download hasil dari tombol yang tersedia

---

## 🔬 Alur Pipeline (Snakemake Rules)

```
FASTQ Input (uploads/)
    │
    ▼
[fastqc]          → results/<sample>/fastqc/
    │
    ▼
[trimmomatic_se]  → results/<sample>/trimmed/
    │
    ▼
[bwa_align]       → results/<sample>/bwa/
    │
    ▼
[variant_calling] → results/<sample>/vcf/
                    ├── <sample>.bcf
                    ├── <sample>.vcf
                    └── <sample>.filtered.vcf  ← Output utama
```

---

## 🔧 Konfigurasi (`config.yaml`)

```yaml
ref_genome:  path ke chr22.fa
input_dir:   uploads/
output_dir:  results/
tools:
  fastqc:      path ke fastqc binary
  trimmomatic: path ke trimmomatic binary
  bwa:         path ke bwa binary
  samtools:    /usr/bin/samtools
  bcftools:    /usr/bin/bcftools
bcftools:
  ploidy:    GRCh38   ← diploid human
  min_qual:  20
  min_depth: 5
cores: 4
```

---

## 🔄 Resume Pipeline

Jika pipeline terputus:

```bash
snakemake --cores 4 --rerun-incomplete
```

Snakemake akan skip file output yang sudah ada dan melanjutkan dari rule yang belum selesai.

---

## 🔍 Dry Run (Cek Rencana Tanpa Eksekusi)

```bash
snakemake --cores 4 --dry-run --printshellcmds
```

Menampilkan semua perintah yang akan dijalankan tanpa benar-benar mengeksekusinya.

---

## 📊 Visualisasi DAG Pipeline

```bash
snakemake --dag | dot -Tpng > pipeline_dag.png
```

Membutuhkan `graphviz`: `sudo apt install graphviz -y`

---

## 🗑️ Reset Pipeline

```bash
rm -rf results .snakemake
```

---

## 🔀 Perbandingan dengan Pipeline Lain

| Fitur | Demo (Manual) | Nextflow | Snakemake |
|---|---|---|---|
| Workflow manager | ❌ | ✅ Nextflow DSL2 | ✅ Snakemake |
| Resume otomatis | ❌ | ✅ `-resume` | ✅ `--rerun-incomplete` |
| Dry run | ❌ | ❌ | ✅ `--dry-run` |
| Config terpisah | ❌ | `nextflow.config` | `config.yaml` |
| Log per proses | ❌ | work dir | `results/logs/` |
| Scale ke cluster | ❌ | ✅ mudah | ✅ tersedia |
| Paradigma | Prosedural | Data-flow | Rule-based |

---

## ⚠️ Catatan

- `samtools` dan `bcftools` menggunakan versi dari **apt** (`/usr/bin/`) karena versi conda mengalami konflik `libcrypto.so.1.0.0`
- Pipeline di-test dengan **Snakemake 9.27.1** di WSL2 Ubuntu
- Ploidy default adalah **GRCh38** (diploid) sesuai standar Human GRCh38
- Log setiap rule tersimpan di `results/<sample>/logs/` untuk debugging
