# 🧬 NGS E2E Analysis Platform — Demo (Pipeline Manual)

Platform analisis sekunder NGS berbasis Streamlit dengan pipeline yang dieksekusi langsung menggunakan `subprocess` tanpa workflow manager. Mendukung data **E. coli REL606** maupun **Human GRCh38 chr22**.

---

## 📁 Struktur Direktori

```
Demo/
├── app.py                  ← Streamlit web application
├── README.md               ← Dokumentasi ini
├── data/
│   ├── untrimmed_fastq/    ← FASTQ input (auto-dibuat)
│   └── trimmed_fastq/      ← FASTQ setelah trimming (auto-dibuat)
└── results/
    └── <sample_name>/
        ├── fastqc/         ← Output FastQC
        ├── bwa/            ← SAM, BAM, BAI
        └── vcf/            ← BCF, VCF, filtered VCF
```

---

## ⚙️ Prasyarat Sistem

- Windows 10/11 dengan **WSL2 Ubuntu**
- **Miniconda** terinstall di WSL
- RAM minimal 8GB (rekomendasi 16GB+)

---

## 🔧 Instalasi Dependencies

### 1. Buat conda environment baru (Python 3.11)

```bash
conda create -n ngs_demo python=3.11 -y
conda activate ngs_demo
```

### 2. Install tools bioinformatika

```bash
# Install bwa, trimmomatic, bcftools via conda
conda install -c bioconda -c conda-forge bwa trimmomatic bcftools -y

# Install samtools via apt (menghindari masalah libcrypto)
sudo apt update && sudo apt install -y samtools fastqc
```

### 3. Install Python dependencies

```bash
pip install streamlit pandas
```

### 4. Verifikasi instalasi

```bash
which bwa trimmomatic samtools bcftools
streamlit --version
python -c "import pandas; print(pandas.__version__)"
```

---

## 📥 Persiapan Referensi Genom

### Opsi A — E. coli REL606 (sudah tersedia)

```
C:\Users\Mahasiswa\Fastt\ref_genome\ecoli_rel606.fasta
```

Pastikan index BWA sudah ada (`.amb`, `.ann`, `.bwt`, `.pac`, `.sa`, `.fai`).

### Opsi B — Human GRCh38 chr22

```bash
# Download chr22
curl -L -o /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa.gz \
  https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz
gunzip /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa.gz

# Build index
bwa index /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa
samtools faidx /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa
```

---

## 🚀 Menjalankan Aplikasi

```bash
conda activate ngs_demo
cd /mnt/c/Users/Mahasiswa/Fastt/Demo
streamlit run app.py
```

Buka browser di: **http://localhost:8501**

---

## 📋 Cara Penggunaan

### Menjalankan Pipeline

1. Upload file FASTQ melalui sidebar kiri
2. Atur **Path Referensi Genom** di sidebar:
   - E. coli: `/mnt/c/Users/Mahasiswa/Fastt/ref_genome/ecoli_rel606.fasta`
   - Human: `/mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa`
3. Pilih **Ploidy Organisme**:
   - E. coli → `Haploid (1)`
   - Human → `GRCh38`
4. Klik **🚀 Jalankan Full Pipeline**
5. Tunggu hingga selesai (~5 menit untuk E. coli, ~15 menit untuk chr22)
6. Download hasil dari tombol yang tersedia

### Validasi VCF vs Ground Truth (wgsim)

1. Generate data sintetis dengan wgsim:
```bash
wgsim -N 500000 -1 150 -S 42 \
  /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa \
  /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq \
  /dev/null \
  > /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22_mutations.txt
```
2. Jalankan pipeline dengan `sim_chr22.fastq`
3. Scroll ke bagian **"🔬 Validasi VCF vs Ground Truth"**
4. Path ground truth sudah terisi default, klik **Jalankan Validasi**

### Perbandingan VCF antar Pipeline

1. Scroll ke bagian **"🔀 Perbandingan VCF"**
2. Pilih preset path untuk Demo dan Nextflow pipeline
3. Klik **🔀 Bandingkan Dua VCF**

---

## 🔬 Alur Pipeline

```
FASTQ Input
    │
    ▼
[1] FastQC          → QC report (.html, .zip)
    │
    ▼
[2] Trimmomatic SE  → Trimmed FASTQ
    │
    ▼
[3] BWA MEM         → SAM
    │
    ▼
[4] Samtools        → Sorted BAM + BAI
    │
    ▼
[5] BCFTools        → BCF → VCF → Filtered VCF
```

---

## ⚠️ Catatan

- Jika muncul warning **"Trimmomatic tidak menghasilkan output"** saat menggunakan data sintetis wgsim, itu **normal** — pipeline akan otomatis menggunakan file FASTQ asli
- Untuk data manusia (chr22), pipeline bisa memakan waktu **10–20 menit** tergantung jumlah reads dan kecepatan CPU
- FastQC menggunakan path: `/mnt/c/Users/Mahasiswa/Fastt/FastQC/fastqc`
