# 🧬 NGS Secondary Analysis E2E Platform

Platform End-to-End (E2E) untuk analisis sekunder Next-Generation Sequencing (NGS) data genom manusia **Human GRCh38 Chromosome 22**. Dibangun dengan tiga arsitektur berbeda menggunakan **Streamlit** sebagai Web UI.

---

## 📋 Deskripsi Proyek

Platform ini mengimplementasikan pipeline bioinformatika standar untuk analisis sekunder NGS:

```
FASTQ Input
    │
    ▼
FastQC          (Quality Control)
    │
    ▼
Trimmomatic SE  (Adapter & Quality Trimming)
    │
    ▼
BWA MEM         (Read Alignment ke GRCh38 chr22)
    │
    ▼
Samtools        (Sort, Index, MarkDuplicates)
    │
    ▼
BCFTools        (Variant Calling → VCF)
    │
    ▼
Filtered VCF    (Output)
```

---

## 🏗️ Tiga Arsitektur Platform

### 1. 📁 `Demo/` — Pipeline Manual (Subprocess)
Pipeline dieksekusi langsung via Python `subprocess` tanpa workflow manager.

- **Backend:** Python subprocess (BCFTools)
- **Frontend:** Streamlit
- **Fitur tambahan:** Validasi VCF vs Ground Truth, Perbandingan VCF antar pipeline
- **Cocok untuk:** Eksplorasi cepat, belajar, prototyping

### 2. 📁 `ngs_platform/` — Nextflow Pipeline
Pipeline dieksekusi oleh **Nextflow DSL2** — workflow manager berbasis data-flow.

- **Backend:** Nextflow DSL2 v24.10.6 + BCFTools
- **Frontend:** Streamlit
- **Fitur:** Resume otomatis, eksekusi paralel, pipeline report HTML
- **Cocok untuk:** Pipeline production, reproducibility

### 3. 📁 `ngs_platform_human/` — Snakemake Pipeline
Pipeline dieksekusi oleh **Snakemake** — workflow manager berbasis rule/file-driven.

- **Backend:** Snakemake v9.27.1 + BCFTools
- **Frontend:** Streamlit
- **Fitur:** Dry run, resume, DAG visualisasi, log per rule
- **Cocok untuk:** Pipeline akademik/riset, reproducibility

---

## 🔀 Perbedaan Ketiga Platform

| Aspek | Demo (Manual) | Nextflow | Snakemake |
|---|---|---|---|
| Workflow Manager | ❌ Tidak ada | ✅ Nextflow DSL2 | ✅ Snakemake |
| Bahasa Konfigurasi | Python (hardcode) | Groovy (`nextflow.config`) | YAML (`config.yaml`) |
| Paradigma Eksekusi | Prosedural (sequential) | Data-flow (channel-based) | Rule-based (file-driven) |
| Resume Pipeline | ❌ | ✅ `-resume` | ✅ `--rerun-incomplete` |
| Dry Run | ❌ | ❌ | ✅ `--dry-run` |
| Eksekusi Paralel | ❌ Sequential | ✅ FastQC + Trimmomatic paralel | ✅ Configurable `--cores` |
| Log per Proses | ❌ Error dict saja | ✅ work dir per proses | ✅ `results/logs/` per rule |
| DAG Visualisasi | ❌ | ❌ | ✅ `--dag \| dot` |
| Scale ke Cluster | ❌ | ✅ Ganti profile | ✅ Cluster config |
| Fitur Validasi GT | ✅ Ada | ❌ | ❌ |
| Setup Kompleksitas | ⭐ Mudah | ⭐⭐⭐ Kompleks | ⭐⭐ Sedang |

---

## 📊 Benchmarking Hasil Pengujian

> **Setup pengujian:** `sim_chr22.fastq` — 500K reads sintetis wgsim, GRCh38 chr22, coverage ~1.5x  
> **Mesin:** WSL2 Ubuntu, RAM 64GB, 6 CPU cores

### ⏱️ Execution Time

| Tahap | Demo | Nextflow | Snakemake |
|---|---|---|---|
| FastQC | ~30 detik | ~18 detik | ~18 detik |
| Trimmomatic SE | ~13 detik | ~13 detik | ~14 detik |
| BWA MEM + Sort | ~5-10 menit | ~5 menit | ~5 menit |
| BCFTools Variant Call | ~5-10 menit | ~3 menit | ~3 menit |
| **Total** | **~15-20 menit** | **6m 19s ✅** | **~8 menit** |

> Nextflow tercepat karena FastQC dan Trimmomatic berjalan **paralel**.

### 🔬 Validasi VCF vs Ground Truth

| Metrik | Demo | Nextflow | Snakemake |
|---|---|---|---|
| Total Mutasi GT | 39,227 | 39,227 | 39,227 |
| Total Variant VCF | 12,269 | ~12,200 | ~12,200 |
| ✅ True Positive | 8,930 | ~8,900 | ~8,900 |
| ❌ False Negative | 30,297 | ~30,327 | ~30,327 |
| ⚠️ False Positive | 3,339 | ~3,300 | ~3,300 |
| **Sensitivity** | **22.8%** | **~22.7%** | **~22.7%** |
| **Precision** | **72.8%** | **~73.0%** | **~73.0%** |

> Ketiga pipeline menghasilkan nilai hampir identik karena menggunakan tools yang sama.  
> Sensitivity rendah (22.8%) disebabkan coverage hanya ~1.5x — butuh minimal 10 juta reads (~30x) untuk Sensitivity >80%.

### 📁 Ukuran Output

| File | Demo | Nextflow | Snakemake |
|---|---|---|---|
| `filtered.vcf` | 1.5 MB | 1.4 MB | 1.4 MB |
| `sorted.bam` | ~37 MB | ~37 MB | ~35 MB |

### ✅ Kelebihan & ❌ Kekurangan

**Demo:**
- ✅ Paling mudah setup, fitur validasi GT lengkap, cocok untuk belajar
- ❌ Python 3.6, sequential, tidak ada resume, banyak fitur Streamlit lama tidak tersedia

**Nextflow:**
- ✅ Tercepat (paralel), resume otomatis, pipeline report HTML, mudah scale ke cluster
- ❌ Setup kompleks (butuh Java), konflik libcrypto conda, path tools harus hardcode

**Snakemake:**
- ✅ Config YAML bersih, dry run, log per rule, DAG visualisasi, versi terbaru
- ❌ Butuh mamba untuk install, samtools/bcftools harus pakai apt

### 🏆 Rekomendasi

| Skenario | Pilihan |
|---|---|
| Belajar & eksplorasi | **Demo** |
| Pipeline production & reproducible | **Nextflow** |
| Pipeline akademik & riset | **Snakemake** |
| Scale ke HPC/cluster | **Nextflow** atau **Snakemake** |

> Laporan benchmarking lengkap: [`BENCHMARKING.md`](BENCHMARKING.md)

---

## ⚙️ Referensi Genom yang Didukung

| Referensi | Status | Keterangan |
|---|---|---|
| GRCh38 chr22 (`chr22.fa`) | ✅ Tersedia | Default, direkomendasikan |
| GRCh38 Full (`hg38.fa`) | ✅ Tersedia | Untuk analisis whole genome |
| GRCh37 Full (`hg19.fa`) | 🔄 Download diperlukan | Untuk data lama |

---

## 🚀 Quick Start

### Prasyarat
- Windows 10/11 dengan **WSL2 Ubuntu**
- **Miniconda** terinstall di WSL
- RAM minimal 16GB (rekomendasi 32GB+)

### 1. Clone Repository
```bash
git clone https://github.com/WildanPratama007/ngs-e2e-platform-demo.git
cd ngs-e2e-platform-demo
```

### 2. Pilih Platform & Setup

**Demo (paling mudah):**
```bash
conda create -n ngs_demo python=3.11 -y
conda activate ngs_demo
conda install -c bioconda -c conda-forge bwa trimmomatic bcftools -y
sudo apt install -y samtools
pip install streamlit pandas
cd Demo && streamlit run app.py
```

**Nextflow:**
```bash
conda create -n ngs_platform python=3.11 -y
conda activate ngs_platform
conda install -c bioconda -c conda-forge bwa trimmomatic nextflow -y
sudo apt install -y samtools bcftools
pip install streamlit pandas
cd ngs_platform && streamlit run app.py
```

**Snakemake:**
```bash
conda create -n snakemake_human python=3.11 -y
conda activate snakemake_human
conda install -c conda-forge mamba -y
mamba install -c bioconda -c conda-forge snakemake bwa trimmomatic -y
sudo apt install -y samtools bcftools
pip install streamlit pandas pyyaml
cd ngs_platform_human && streamlit run app.py
```

### 3. Persiapan Referensi Genom
```bash
# Download chr22 GRCh38 (jika belum ada)
curl -L -o ref_genome/chr22.fa.gz \
  https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz
gunzip ref_genome/chr22.fa.gz
bwa index ref_genome/chr22.fa
samtools faidx ref_genome/chr22.fa
```

### 4. Generate Sample Data
```bash
# Generate 500K reads sintetis dari chr22 (~166MB)
wgsim -N 500000 -1 150 -S 42 \
  ref_genome/chr22.fa \
  datas/sim_chr22.fastq \
  /dev/null \
  > datas/sim_chr22_mutations.txt
```

---

## 📁 Struktur Repository

```
ngs-e2e-platform/
├── README.md                   ← Dokumentasi ini
├── BENCHMARKING.md             ← Laporan benchmarking lengkap
├── Demo/
│   ├── app.py                  ← Streamlit app (pipeline manual)
│   └── README.md
├── ngs_platform/
│   ├── app.py                  ← Streamlit app
│   ├── main.nf                 ← Nextflow pipeline DSL2
│   ├── nextflow.config         ← Konfigurasi Nextflow
│   └── README.md
└── ngs_platform_human/
    ├── app.py                  ← Streamlit app
    ├── Snakefile               ← Snakemake pipeline rules
    ├── config.yaml             ← Konfigurasi pipeline
    └── README.md
```

---

## 🔬 Tools yang Digunakan

| Tool | Versi | Fungsi |
|---|---|---|
| FastQC | 0.11.x | Quality control reads |
| Trimmomatic | 0.39 | Adapter trimming |
| BWA MEM | 0.7.19 | Read alignment |
| Samtools | 1.13 (apt) | BAM processing |
| BCFTools | 1.13 (apt) | Variant calling |
| Nextflow | 24.10.6 | Workflow manager |
| Snakemake | 9.27.1 | Workflow manager |
| Streamlit | 1.35.0 | Web UI |

---

## 📌 Catatan Teknis

- **Samtools & BCFTools** diinstall via `apt` (bukan conda) karena versi conda mengalami konflik `libcrypto.so.1.0.0` di Ubuntu versi baru
- **GPU tidak digunakan** — semua tools (BWA, Samtools, BCFTools) adalah CPU-based
- Pipeline fokus pada **Single-End** reads dan kromosom **chr22** GRCh38

---

## 👤 Author

**WildanPratama007**  
wildanmuh97@gmail.com
