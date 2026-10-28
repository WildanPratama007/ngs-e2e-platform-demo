import streamlit as st
import os
import subprocess
import glob
import yaml
import pandas as pd

st.set_page_config(page_title="NGS Human Platform (Snakemake)", layout="wide")

st.title("🧬 NGS E2E Platform — Human GRCh38 chr22")
st.caption("Powered by Snakemake · FastQC → Trimmomatic → BWA MEM → Samtools → BCFTools (Diploid)")

# ── Konstanta ─────────────────────────────────────────────────────────────────
PROJECT_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE   = os.path.join(PROJECT_DIR, "config.yaml")
SNAKEFILE     = os.path.join(PROJECT_DIR, "Snakefile")
UPLOAD_DIR    = os.path.join(PROJECT_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Load config.yaml ──────────────────────────────────────────────────────────
with open(CONFIG_FILE) as f:
    cfg = yaml.safe_load(f)

RESULTS_DIR = os.path.join(PROJECT_DIR, cfg["output_dir"])
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("1. Input Data")

input_mode = st.sidebar.radio(
    "Mode Input FASTQ",
    options=["📤 Upload File", "📂 Input Path (untuk file >100MB)"],
    help="Gunakan Input Path jika file lebih dari 100MB atau akses via port forward"
)

uploaded_file    = None
fastq_path_input = None

if input_mode == "📤 Upload File":
    uploaded_file = st.sidebar.file_uploader(
        "Pilih berkas FASTQ Human chr22 (*.fastq)", type=["fastq"]
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
    "Path Referensi Genom (chr22.fa)",
    value=cfg["ref_genome"],
    help="Path absolut di WSL ke file chr22.fa beserta index BWA & samtools"
)

cores = st.sidebar.slider(
    "Jumlah CPU Cores", min_value=1, max_value=16,
    value=cfg["cores"], step=1
)

st.sidebar.header("3. Snakemake")
snakemake_bin = st.sidebar.text_input(
    "Path Snakemake Binary",
    value="/home/mahasiswa/miniconda3/envs/snakemake_human/bin/snakemake",
    help="Path ke binary snakemake di env snakemake_human"
)

dry_run = st.sidebar.checkbox(
    "Dry Run (--dry-run)", value=False,
    help="Tampilkan rencana eksekusi tanpa menjalankan pipeline"
)

# ── Helper: parse VCF ─────────────────────────────────────────────────────────
def parse_vcf(vcf_content):
    variants = {}
    for line in vcf_content.strip().splitlines():
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        chrom, pos, _, ref, alt = parts[0], int(parts[1]), parts[2], parts[3], parts[4]
        filter_val = parts[6] if len(parts) > 6 else "."
        variants[(chrom, pos)] = {
            "chrom": chrom, "pos": pos,
            "ref": ref, "alt": alt, "filter": filter_val
        }
    return variants

# ── Main App ──────────────────────────────────────────────────────────────────
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
        # Mode path: symlink ke uploads/ agar Snakemake detect sampel
        fastq_dest = os.path.join(UPLOAD_DIR, os.path.basename(fastq_path_input))
        if not os.path.exists(fastq_dest):
            os.symlink(active_fastq, fastq_dest)
        fastq_path = fastq_dest
        st.sidebar.success(f"Berkas aktif: {os.path.basename(active_fastq)}")

    st.subheader(f"📄 Sampel Aktif: `{sample_name}`")

    # ── Info Konfigurasi ──────────────────────────────────────────────────────
    with st.expander("⚙️ Konfigurasi Pipeline Aktif"):
        st.json({
            "ref_genome":   ref_genome,
            "ploidy":       cfg["bcftools"]["ploidy"],
            "trimmomatic":  cfg["trimmomatic"]["options"],
            "min_qual":     cfg["bcftools"]["min_qual"],
            "min_depth":    cfg["bcftools"]["min_depth"],
            "cores":        cores,
        })

    # ── Tombol Eksekusi ───────────────────────────────────────────────────────
    btn_label = "🔍 Dry Run — Cek Rencana Pipeline" if dry_run else "🚀 Jalankan Pipeline via Snakemake"
    if st.button(btn_label):

        # Update config ref_genome dan cores secara dinamis via --config
        sm_cmd = [
            snakemake_bin,
            "--snakefile",  SNAKEFILE,
            "--cores",      str(cores),
            "--config",
                f"ref_genome={ref_genome}",
                f"cores={cores}",
            "--rerun-incomplete",
            "--printshellcmds",
        ]
        if dry_run:
            sm_cmd.append("--dry-run")

        st.info(f"Menjalankan: `{' '.join(sm_cmd)}`")

        progress_bar = st.progress(0)
        log_area     = st.empty()
        status_area  = st.empty()

        rule_progress = {
            "fastqc":          20,
            "trimmomatic_se":  40,
            "bwa_align":       70,
            "variant_calling": 95,
        }
        current_progress = 0

        try:
            process = subprocess.Popen(
                sm_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=PROJECT_DIR,
                universal_newlines=True
            )

            log_lines = []
            for line in process.stdout:
                line = line.rstrip()
                log_lines.append(line)

                # Update progress berdasarkan rule yang sedang berjalan
                for rule, pct in rule_progress.items():
                    if rule in line.lower() and pct > current_progress:
                        current_progress = pct
                        progress_bar.progress(current_progress)
                        status_area.info(f"⚙️ Menjalankan rule: `{rule}`")

                log_area.code("\n".join(log_lines[-20:]), language="bash")

            process.wait()

            if process.returncode == 0:
                progress_bar.progress(100)
                if dry_run:
                    status_area.info("📋 Dry run selesai — tidak ada file yang dibuat.")
                else:
                    status_area.success("✅ Pipeline Snakemake selesai!")
                    st.balloons()
            else:
                status_area.error("❌ Pipeline gagal. Lihat log di atas untuk detail error.")

        except FileNotFoundError:
            st.error(
                f"Snakemake tidak ditemukan: `{snakemake_bin}`\n\n"
                "Install Snakemake dengan:\n"
                "```bash\n"
                "conda create -n snakemake_human python=3.11 -y\n"
                "conda activate snakemake_human\n"
                "conda install -c bioconda -c conda-forge snakemake bwa trimmomatic -y\n"
                "```"
            )

        # ── Output Files ──────────────────────────────────────────────────────
        if not dry_run:
            st.markdown("---")
            st.subheader("📦 Berkas Hasil Luaran")
            sample_out = os.path.join(RESULTS_DIR, sample_name)

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown("### 0. FastQC")
                for f in glob.glob(f"{sample_out}/fastqc/*_fastqc.html"):
                    with open(f, "rb") as fh:
                        st.download_button("📥 FastQC HTML", fh,
                                           file_name=os.path.basename(f),
                                           mime="text/html")
                for f in glob.glob(f"{sample_out}/fastqc/*_fastqc.zip"):
                    with open(f, "rb") as fh:
                        st.download_button("📥 FastQC ZIP", fh,
                                           file_name=os.path.basename(f),
                                           mime="application/zip")

            with col2:
                st.markdown("### 1. Trimming")
                trimmed = f"{sample_out}/trimmed/{sample_name}.trimmed.fastq"
                if os.path.exists(trimmed):
                    with open(trimmed, "rb") as fh:
                        st.download_button("📥 Trimmed FASTQ", fh,
                                           file_name=f"{sample_name}.trimmed.fastq")

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

            with col4:
                st.markdown("### 3. Variant Calling")
                filtered_vcf = f"{sample_out}/vcf/{sample_name}.filtered.vcf"
                if os.path.exists(filtered_vcf):
                    with open(filtered_vcf, "rb") as fh:
                        st.download_button("📥 Filtered VCF", fh,
                                           file_name=f"{sample_name}.filtered.vcf")
                    # Ringkasan VCF
                    with open(filtered_vcf) as fh:
                        all_variants = [l for l in fh if not l.startswith("#")]
                        pass_variants = [l for l in all_variants if "\tPASS\t" in l]
                    st.metric("Total Variant",  len(all_variants))
                    st.metric("PASS Variant",   len(pass_variants))
                else:
                    st.warning("VCF belum tersedia.")

    # ── Snakemake Log ─────────────────────────────────────────────────────────
    log_file = os.path.join(PROJECT_DIR, ".snakemake/log")
    snk_logs = sorted(glob.glob(os.path.join(PROJECT_DIR, ".snakemake/log/*.snakemake.log")))
    if snk_logs:
        st.markdown("---")
        with st.expander("📋 Snakemake Log Terakhir"):
            with open(snk_logs[-1]) as f:
                st.code(f.read()[-5000:], language="bash")

    # ── Validasi VCF vs Ground Truth ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔬 Validasi VCF vs Ground Truth (wgsim)")

    vcol1, vcol2 = st.columns(2)
    with vcol1:
        gt_path = st.text_input(
            "📂 Path Ground Truth (.txt dari wgsim)",
            value="/mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22_mutations.txt"
        )
    with vcol2:
        vcf_preset = st.selectbox(
            "Preset Path VCF",
            options=[
                ("Snakemake Pipeline (ngs_platform_human)", f"{RESULTS_DIR}/{sample_name}/vcf/{sample_name}.filtered.vcf"),
                ("Nextflow Pipeline (ngs_platform)",        "/mnt/c/Users/Mahasiswa/Fastt/ngs_platform/results/sim_chr22/vcf/sim_chr22.filtered.vcf"),
                ("Demo Pipeline (manual)",                  "/mnt/c/Users/Mahasiswa/Fastt/Demo/results/sim_chr22/vcf/sim_chr22.filtered.vcf"),
                ("Custom (isi manual di bawah)",            ""),
            ],
            format_func=lambda x: x[0]
        )
        vcf_val_path = st.text_input(
            "📂 Path VCF untuk Validasi",
            value=vcf_preset[1]
        )

    if st.button("🔍 Jalankan Validasi"):
        if not os.path.exists(gt_path):
            st.error(f"Ground truth tidak ditemukan: `{gt_path}`")
        elif not os.path.exists(vcf_val_path):
            st.error(f"VCF tidak ditemukan: `{vcf_val_path}`")
        else:
            with open(gt_path) as f:
                gt_content = f.read()
            with open(vcf_val_path) as f:
                vcf_content = f.read()

            detected     = parse_vcf(vcf_content)
            vcf_chroms   = set(v["chrom"] for v in detected.values())

            # Parse ground truth, filter ke kromosom yang ada di VCF
            ground_truth = {}
            gt_total = 0
            for line in gt_content.strip().splitlines():
                parts = line.split()
                if len(parts) < 4:
                    continue
                gt_total += 1
                chrom, pos, ref, alt = parts[0], int(parts[1]), parts[2], parts[3]
                if chrom in vcf_chroms:
                    ground_truth[(chrom, pos)] = {"chrom": chrom, "pos": pos, "ref": ref, "alt": alt}

            gt_pos  = set(ground_truth.keys())
            vcf_pos = set(detected.keys())
            tp = gt_pos & vcf_pos
            fn = gt_pos - vcf_pos
            fp = vcf_pos - gt_pos

            sensitivity = (len(tp) / len(gt_pos) * 100) if gt_pos else 0
            precision   = (len(tp) / (len(tp) + len(fp)) * 100) if (len(tp) + len(fp)) > 0 else 0

            st.info(f"Ground truth: {gt_total:,} total mutasi → {len(gt_pos):,} di kromosom {', '.join(sorted(vcf_chroms))}")

            st.markdown("### 📊 Ringkasan Validasi")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Mutasi GT",         len(gt_pos))
            m2.metric("Variant VCF",        len(vcf_pos))
            m3.metric("✅ True Positive",   len(tp))
            m4.metric("❌ False Negative",  len(fn))
            m5.metric("⚠️ False Positive",  len(fp))

            r1, r2 = st.columns(2)
            r1.metric("Sensitivity (Recall)", f"{sensitivity:.1f}%")
            r2.metric("Precision",             f"{precision:.1f}%")
            st.caption("Sensitivity: % mutasi GT terdeteksi | Precision: % variant VCF yang valid")

else:
    st.info("👈 Unggah berkas FASTQ Human chr22 atau masukkan path file melalui panel sidebar untuk memulai.")

    st.markdown("---")
    st.subheader("💡 Cara Menjalankan dari Terminal WSL")
    st.code(
        "# 1. Aktifkan env\n"
        "conda activate snakemake_human\n\n"
        "# 2. Copy FASTQ ke folder uploads\n"
        "cp /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq uploads/\n\n"
        "# 3. Jalankan pipeline\n"
        "cd /mnt/c/Users/Mahasiswa/Fastt/ngs_platform_human\n"
        "snakemake --cores 4 --rerun-incomplete --printshellcmds",
        language="bash"
    )

    st.markdown("---")
    st.subheader("📥 Cara Download & Persiapkan chr22.fa (jika belum ada)")
    st.code(
        "# Download chr22 GRCh38\n"
        "curl -L -o /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa.gz \\\n"
        "  https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz\n"
        "gunzip /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa.gz\n\n"
        "# Build index\n"
        "bwa index /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa\n"
        "samtools faidx /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa",
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
        st.caption("Salin path ke sidebar — gunakan Input Path mode")
    else:
        st.warning("File tidak ditemukan di server")
