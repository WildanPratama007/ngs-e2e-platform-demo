import streamlit as st
import os
import subprocess
import glob
import time
import pandas as pd

st.set_page_config(page_title="NGS E2E Platform (Nextflow)", layout="wide")

st.title("🧬 NGS E2E Analysis Platform")
st.caption("Powered by Nextflow · FastQC → Trimmomatic → BWA MEM → Samtools → BCFTools")

# ── Konstanta path ────────────────────────────────────────────────────────────
PROJECT_DIR  = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(PROJECT_DIR, "results")
UPLOAD_DIR   = os.path.join(PROJECT_DIR, "uploads")
NF_SCRIPT    = os.path.join(PROJECT_DIR, "main.nf")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("1. Input Data")

input_mode = st.sidebar.radio(
    "Mode Input FASTQ",
    options=["📤 Upload File", "📂 Input Path (untuk file >100MB)"],
    help="Gunakan Input Path jika file lebih dari 100MB atau akses via port forward"
)

uploaded_file   = None
fastq_path_input = None

if input_mode == "📤 Upload File":
    uploaded_file = st.sidebar.file_uploader(
        "Pilih berkas FASTQ (*.fastq)", type=["fastq"]
    )
else:
    fastq_path_manual = st.sidebar.text_input(
        "Path FASTQ di WSL",
        value="/mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq",
        help="Path absolut ke file FASTQ di WSL — file tidak dikirim lewat jaringan"
    )
    if fastq_path_manual and os.path.exists(fastq_path_manual):
        st.sidebar.success(f"✅ {os.path.basename(fastq_path_manual)} ({os.path.getsize(fastq_path_manual)/1024/1024:.1f} MB)")
        fastq_path_input = fastq_path_manual
    elif fastq_path_manual:
        st.sidebar.error("❌ File tidak ditemukan")

st.sidebar.header("2. Konfigurasi Pipeline")
ref_genome = st.sidebar.text_input(
    "Path Referensi Genom",
    value="/mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa",
    help="Path absolut di WSL ke file FASTA referensi"
)

ploidy = st.sidebar.selectbox(
    "Ploidy Organisme",
    options=[
        ("Diploid - Manusia hg38/GRCh38", "GRCh38"),
        ("Diploid - Manusia hg19/GRCh37", "GRCh37"),
    ],
    format_func=lambda x: x[0]
)
ploidy_value = ploidy[1]

profile = st.sidebar.selectbox(
    "Nextflow Profile",
    options=["conda_env", "standard", "docker"],
    help="conda_env: pakai env datacarpentry yang sudah ada"
)

st.sidebar.header("3. Nextflow")
nextflow_bin = st.sidebar.text_input(
    "Path Nextflow Binary",
    value="/home/mahasiswa/miniconda3/envs/ngs_platform/bin/nextflow",
    help="Isi path lengkap jika nextflow tidak ada di PATH"
)

# ── Main Area ─────────────────────────────────────────────────────────────────
# Tentukan active input
active_fastq  = None
active_sample = None

if uploaded_file is not None:
    active_sample = uploaded_file.name.replace(".fastq", "")
    active_fastq  = "from_upload"
elif fastq_path_input is not None:
    active_sample = os.path.basename(fastq_path_input).replace(".fastq", "")
    active_fastq  = fastq_path_input

if active_fastq is not None:
    sample_name = active_sample

    # Handle kedua mode input
    if active_fastq == "from_upload":
        fastq_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(fastq_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success(f"Berkas dimuat: {uploaded_file.name}")
    else:
        fastq_path = active_fastq
        st.sidebar.success(f"Berkas aktif: {os.path.basename(active_fastq)}")

    st.subheader(f"📄 Sampel Aktif: `{sample_name}`")

    # ── Info Konfigurasi ──────────────────────────────────────────────────────
    if st.button("🚀 Jalankan Pipeline via Nextflow"):

        # Susun perintah nextflow
        nf_cmd = [
            nextflow_bin, "run", NF_SCRIPT,
            "-profile", profile,
            "--reads",      fastq_path,
            "--ref_genome", ref_genome,
            "--outdir",     RESULTS_DIR,
            "--ploidy",     ploidy_value,
            "-resume",
        ]

        st.info(f"Menjalankan: `{' '.join(nf_cmd)}`")

        # Container progress
        progress_bar = st.progress(0)
        log_area     = st.empty()
        status_area  = st.empty()

        # Jalankan nextflow sebagai subprocess
        try:
            process = subprocess.Popen(
                nf_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=PROJECT_DIR,
                universal_newlines=True
            )

            log_lines  = []
            step_map   = {
                "FASTQC":          ("🔍 FastQC - Quality Control",           20),
                "TRIMMOMATIC_SE":  ("✂️ Trimmomatic - Adapter Trimming",      40),
                "BWA_ALIGN":       ("🗺️ BWA MEM + Samtools - Alignment",      70),
                "VARIANT_CALLING": ("🧬 BCFTools - Variant Calling",          90),
            }
            current_progress = 0

            # Baca output Nextflow secara real-time
            for line in process.stdout:
                line = line.rstrip()
                log_lines.append(line)

                # Update progress berdasarkan proses yang sedang berjalan
                for key, (label, pct) in step_map.items():
                    if key in line and ("Submitted" in line or "Cached" in line or "Completed" in line):
                        current_progress = pct
                        status_area.info(f"⚙️ {label}")
                        progress_bar.progress(current_progress)

                # Tampilkan log terakhir
                log_area.code("\n".join(log_lines[-15:]), language="bash")

            process.wait()

            if process.returncode == 0:
                progress_bar.progress(100)
                status_area.success("✅ Pipeline Nextflow selesai!")
                st.balloons()
            else:
                status_area.error("❌ Pipeline gagal. Lihat log di atas untuk detail error.")

        except FileNotFoundError:
            st.error(
                f"Nextflow tidak ditemukan di path: `{nextflow_bin}`\n\n"
                "Install Nextflow dengan perintah berikut di WSL:\n"
                "```bash\n"
                "curl -s https://get.nextflow.io | bash\n"
                "mv nextflow /home/mahasiswa/\n"
                "```\n"
                "Lalu isi path di sidebar: `/home/mahasiswa/nextflow`"
            )

        # ── Output Files ──────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("📦 Berkas Hasil Luaran")
        st.write(f"Hasil tersimpan di: `{RESULTS_DIR}/{sample_name}/`")

        sample_out = os.path.join(RESULTS_DIR, sample_name)
        col1, col2, col3, col4 = st.columns(4)

        # FastQC
        with col1:
            st.markdown("### 0. FastQC")
            for f in glob.glob(f"{sample_out}/fastqc/*_fastqc.html"):
                with open(f, "rb") as fh:
                    st.download_button("📥 FastQC HTML", fh,
                                       file_name=os.path.basename(f), mime="text/html")
            for f in glob.glob(f"{sample_out}/fastqc/*_fastqc.zip"):
                with open(f, "rb") as fh:
                    st.download_button("📥 FastQC ZIP", fh,
                                       file_name=os.path.basename(f), mime="application/zip")

        # Trimmed FASTQ
        with col2:
            st.markdown("### 1. Trimming")
            trimmed = f"{sample_out}/trimmed/{sample_name}.trimmed.fastq"
            if os.path.exists(trimmed):
                with open(trimmed, "rb") as fh:
                    st.download_button("📥 Trimmed FASTQ", fh,
                                       file_name=f"{sample_name}.trimmed.fastq")

        # BAM & BAI
        with col3:
            st.markdown("### 2. Alignment")
            bam = f"{sample_out}/bwa/{sample_name}.aligned.sorted.bam"
            bai = f"{bam}.bai"
            if os.path.exists(bam):
                with open(bam, "rb") as fh:
                    st.download_button("📥 Sorted BAM", fh,
                                       file_name=f"{sample_name}.aligned.sorted.bam")
            if os.path.exists(bai):
                with open(bai, "rb") as fh:
                    st.download_button("📥 BAM Index (.bai)", fh,
                                       file_name=f"{sample_name}.aligned.sorted.bam.bai")

        # VCF
        with col4:
            st.markdown("### 3. Variant Calling")
            vcf = f"{sample_out}/vcf/{sample_name}.filtered.vcf"
            if os.path.exists(vcf):
                with open(vcf, "rb") as fh:
                    st.download_button("📥 Filtered VCF", fh,
                                       file_name=f"{sample_name}.filtered.vcf")
                # Tampilkan ringkasan VCF
                with open(vcf) as fh:
                    lines = [l for l in fh if not l.startswith("#")]
                st.metric("Total Variant", len(lines))
            else:
                st.warning("VCF belum tersedia.")

    # ── Nextflow Report ───────────────────────────────────────────────────────
    report_html = os.path.join(RESULTS_DIR, "pipeline_report.html")
    if os.path.exists(report_html):
        st.markdown("---")
        with open(report_html, "rb") as f:
            st.download_button("📊 Unduh Nextflow Pipeline Report", f,
                               file_name="pipeline_report.html", mime="text/html")

else:
    st.info("👈 Unggah berkas FASTQ atau masukkan path file melalui panel sidebar untuk memulai.")

    # Tampilkan contoh perintah manual
    st.markdown("---")
    st.subheader("💡 Atau jalankan pipeline langsung dari terminal WSL:")
    st.code(
        "cd /mnt/c/Users/Mahasiswa/Fastt/ngs_platform\n"
        "nextflow run main.nf \\\n"
        "  -profile conda_env \\\n"
        "  --reads '/mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq' \\\n"
        "  --ref_genome '/mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa' \\\n"
        "  --ploidy GRCh38 \\\n"
        "  --outdir results",
        language="bash"
    )

# ── Sample Data untuk Testing ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("📦 Sample Data untuk Testing")
st.write("Download atau gunakan file FASTQ contoh untuk mencoba pipeline.")

samp1, samp2 = st.columns(2)

with samp1:
    st.markdown("#### 🧬 Human chr22 (500K reads)")
    st.caption("Sintetis wgsim GRCh38 chr22. ~166MB, coverage ~1.5x.")
    chr22_path = "/mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq"
    if os.path.exists(chr22_path):
        with open(chr22_path, "rb") as f:
            st.download_button("📥 Download sim_chr22.fastq", f,
                               file_name="sim_chr22.fastq", mime="text/plain")
        st.caption(f"Ukuran: {os.path.getsize(chr22_path)/1024/1024:.1f} MB")
    else:
        st.warning("File tidak ditemukan di server")

with samp2:
    st.markdown("#### 🧬 Human chr22 (10M reads)")
    st.caption("Sintetis wgsim GRCh38 chr22. ~2.2GB, coverage ~30x.")
    chr22_10m = "/mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22_10M.fastq"
    if os.path.exists(chr22_10m):
        st.info(f"Ukuran: {os.path.getsize(chr22_10m)/1024/1024/1024:.1f} GB")
        st.code(chr22_10m)
        st.caption("Salin path ke sidebar — Input Path mode")
    else:
        st.warning("File tidak ditemukan di server")
