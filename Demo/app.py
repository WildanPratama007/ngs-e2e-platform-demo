import streamlit as st
import os
import subprocess
import glob
import pandas as pd

st.set_page_config(page_title="NGS E2E Analysis Platform", layout="wide")

st.title("🧬 NGS Secondary Analysis E2E Platform (Full Pipeline)")
st.write("Unggah berkas FASTQ *Single-End*, sistem akan menjalankan Quality Control, Trimming, Alignment, hingga Variant Calling secara otomatis.")

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.header("1. Input Data")

# Toggle mode input
input_mode = st.sidebar.radio(
    "Mode Input FASTQ",
    options=["📤 Upload File", "📂 Input Path (untuk file >100MB)"],
    help="Gunakan Input Path jika file lebih dari 100MB atau akses via port forward"
)

uploaded_file = None
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
        st.sidebar.success(f"✅ File ditemukan: {os.path.basename(fastq_path_manual)} ({os.path.getsize(fastq_path_manual)/1024/1024:.1f} MB)")
        fastq_path_input = fastq_path_manual
    elif fastq_path_manual:
        st.sidebar.error("❌ File tidak ditemukan di path tersebut")

st.sidebar.header("2. Referensi Genom")
ref_genome_default = "/mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa"
ref_genome_input = st.sidebar.text_input(
    "Path referensi genom (.fa)",
    value=ref_genome_default,
    help="Path absolut di WSL ke file chr22.fa beserta index BWA & samtools"
)

st.sidebar.header("3. Pengaturan Pipeline")
fastqc_path = "/mnt/c/Users/Mahasiswa/Fastt/FastQC/fastqc"

# ── Helper: parse wgsim mutation txt ─────────────────────────────────────────
def parse_wgsim_mutations(txt_content, max_lines=100000):
    """Parse wgsim stdout mutation list into a dict keyed by (chrom, pos).
    Limits to max_lines to avoid memory issues with large hg38 mutation files."""
    mutations = {}
    for i, line in enumerate(txt_content.strip().splitlines()):
        if i >= max_lines:
            break
        parts = line.split()
        if len(parts) < 4:
            continue
        chrom, pos, ref, alt = parts[0], int(parts[1]), parts[2], parts[3]
        mutations[(chrom, pos)] = {"chrom": chrom, "pos": pos, "ref": ref, "alt": alt}
    return mutations

# ── Helper: parse VCF ─────────────────────────────────────────────────────────
def parse_vcf(vcf_content):
    """Parse VCF file into a dict keyed by (chrom, pos)."""
    variants = {}
    for line in vcf_content.strip().splitlines():
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        chrom, pos, _, ref, alt = parts[0], int(parts[1]), parts[2], parts[3], parts[4]
        variants[(chrom, pos)] = {"chrom": chrom, "pos": pos, "ref": ref, "alt": alt, "info": parts[7] if len(parts) > 7 else ""}
    return variants

# ── Main App ──────────────────────────────────────────────────────────────────
# Tentukan active input dari salah satu mode
active_fastq  = None
active_sample = None

if uploaded_file is not None:
    active_sample = uploaded_file.name.split(".")[0]
    active_fastq  = "from_upload"
elif fastq_path_input is not None:
    active_sample = os.path.basename(fastq_path_input).replace(".fastq", "")
    active_fastq  = fastq_path_input

if active_fastq is not None:
    sample_name = active_sample

    raw_dir       = "data/untrimmed_fastq"
    trim_dir      = "data/trimmed_fastq"
    results_base  = f"results/{sample_name}"
    qc_dir        = f"{results_base}/fastqc"
    bwa_dir       = f"{results_base}/bwa"
    vcf_dir       = f"{results_base}/vcf"

    for d in [raw_dir, trim_dir, qc_dir, bwa_dir, vcf_dir]:
        os.makedirs(d, exist_ok=True)

    # Handle kedua mode input
    if active_fastq == "from_upload":
        input_fastq_path = os.path.join(raw_dir, uploaded_file.name)
        with open(input_fastq_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success(f"Berkas dimuat: {uploaded_file.name}")
    else:
        # Mode path — symlink atau copy ke raw_dir agar pipeline konsisten
        input_fastq_path = active_fastq
        st.sidebar.success(f"Berkas aktif: {os.path.basename(active_fastq)}")

    st.subheader(f"📄 Sampel Aktif: `{sample_name}`")

    # ── Pipeline ──────────────────────────────────────────────────────────────
    if st.button("🚀 Jalankan Full Pipeline (Trimming -> Alignment -> VCF)"):

        progress_bar = st.progress(0)
        log_area     = st.empty()
        errors       = {}

        def run_step(msg, cmd, progress):
            log_area.info(msg)
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            progress_bar.progress(progress)
            if result.returncode != 0:
                errors[msg] = result.stderr.decode("utf-8", errors="replace")

        # Tahap 1 – FastQC
        run_step("🔍 Tahap 1/5: Menganalisis kualitas dengan FastQC...",
                 f"{fastqc_path} {input_fastq_path} -o {qc_dir}", 20)

        # Tahap 2 – Trimmomatic
        trimmed_fastq = f"{trim_dir}/{sample_name}.trimmed.fastq"
        run_step("✂️ Tahap 2/5: Membersihkan adapter dengan Trimmomatic SE...",
                 f"trimmomatic SE {input_fastq_path} {trimmed_fastq} SLIDINGWINDOW:4:20 MINLEN:25 LEADING:3 TRAILING:3", 40)

        # Jika trimmed kosong, gunakan file asli langsung (data sintetis tanpa adapter)
        if not os.path.exists(trimmed_fastq) or os.path.getsize(trimmed_fastq) == 0:
            import shutil
            shutil.copy(input_fastq_path, trimmed_fastq)
            st.warning("⚠️ Trimmomatic tidak menghasilkan output — menggunakan file FASTQ asli untuk alignment.")

        # Tahap 3 – BWA MEM
        ref_genome = ref_genome_input
        sam_output = f"{bwa_dir}/{sample_name}.sam"
        run_step("🗺️ Tahap 3/5: Memetakan reads ke genom rujukan (BWA MEM)...",
                 f"bwa mem {ref_genome} {trimmed_fastq} > {sam_output}", 60)

        # Tahap 4 – Samtools
        sorted_bam = f"{bwa_dir}/{sample_name}.aligned.sorted.bam"
        run_step("📦 Tahap 4/5: Konversi SAM ke BAM & Sorting (Samtools)...",
                 f"samtools view -bS {sam_output} | samtools sort -o {sorted_bam} && samtools index {sorted_bam}", 80)

        # Tahap 5 – BCFtools
        bcf_output  = f"{vcf_dir}/{sample_name}.bcf"
        vcf_output  = f"{vcf_dir}/{sample_name}.vcf"
        filtered_vcf = f"{vcf_dir}/{sample_name}.filtered.vcf"
        cmd_bcftools = (
            f"bcftools mpileup -O b -o {bcf_output} -f {ref_genome} {sorted_bam} && "
            f"bcftools call --ploidy GRCh38 -m -v -o {vcf_output} {bcf_output} && "
            f"bcftools filter -s LOWQUAL -e 'QUAL<20 || DP<5' {vcf_output} > {filtered_vcf}"
        )
        run_step("🧬 Tahap 5/5: Variant Calling & Filtering (BCFTools)...", cmd_bcftools, 100)

        log_area.success("✅ Seluruh tahapan pipeline berhasil diselesaikan!")
        st.balloons()

        if errors:
            st.warning("⚠️ Beberapa tahap pipeline mengalami error. Lihat detail di bawah:")
            for step, err in errors.items():
                with st.expander(f"❌ Error pada: {step}"):
                    st.code(err, language="bash")

        # ── Output Files ──────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("📦 Berkas Hasil Luaran (Output Files)")
        st.write(f"Semua berkas hasil analisis tersimpan di folder lokal: `results/{sample_name}/`")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("### 0. FastQC")
            qc_html = f"{qc_dir}/{sample_name}_fastqc.html"
            qc_zip  = f"{qc_dir}/{sample_name}_fastqc.zip"
            if not os.path.exists(qc_html):
                html_matches = glob.glob(f"{qc_dir}/*_fastqc.html")
                zip_matches  = glob.glob(f"{qc_dir}/*_fastqc.zip")
                if html_matches: qc_html = html_matches[0]
                if zip_matches:  qc_zip  = zip_matches[0]
            if os.path.exists(qc_html):
                with open(qc_html, "rb") as f:
                    st.download_button("📥 Unduh FastQC Report (HTML)", f,
                                       file_name=f"{sample_name}_fastqc.html", mime="text/html")
            if os.path.exists(qc_zip):
                with open(qc_zip, "rb") as f:
                    st.download_button("📥 Unduh FastQC Data (ZIP)", f,
                                       file_name=f"{sample_name}_fastqc.zip", mime="application/zip")
            if not os.path.exists(qc_html) and not os.path.exists(qc_zip):
                st.warning("FastQC output tidak ditemukan.")

        with col2:
            st.markdown("### 1. Trimming")
            if os.path.exists(trimmed_fastq):
                with open(trimmed_fastq, "rb") as f:
                    st.download_button("📥 Unduh Trimmed FASTQ", f, file_name=f"{sample_name}.trimmed.fastq")

        with col3:
            st.markdown("### 2. Alignment")
            if os.path.exists(sorted_bam):
                with open(sorted_bam, "rb") as f:
                    st.download_button("📥 Unduh Sorted BAM", f, file_name=f"{sample_name}.aligned.sorted.bam")
            bam_index = f"{sorted_bam}.bai"
            if os.path.exists(bam_index):
                with open(bam_index, "rb") as f:
                    st.download_button("📥 Unduh BAM Index (.bai)", f, file_name=f"{sample_name}.aligned.sorted.bam.bai")

        with col4:
            st.markdown("### 3. Variant Calling")
            if os.path.exists(filtered_vcf):
                with open(filtered_vcf, "rb") as f:
                    st.download_button("📥 Unduh Filtered VCF", f, file_name=f"{sample_name}.filtered.vcf")

    # ── Validation Section ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔬 Validasi VCF vs Ground Truth (wgsim)")
    st.write("Masukkan path file mutasi wgsim dan VCF hasil pipeline untuk dibandingkan.")

    vcol1, vcol2 = st.columns(2)
    with vcol1:
        gt_path = st.text_input(
            "📂 Path Ground Truth Mutations (.txt dari wgsim)",
            value="/mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22_mutations.txt",
            help="Path absolut di WSL ke file mutasi wgsim"
        )
    with vcol2:
        vcf_preset = st.selectbox(
            "Preset Path VCF",
            options=[
                ("Nextflow Pipeline (ngs_platform)", "/mnt/c/Users/Mahasiswa/Fastt/ngs_platform/results/sim_chr22/vcf/sim_chr22.filtered.vcf"),
                ("Demo Pipeline (manual)", "results/sim_chr22/vcf/sim_chr22.filtered.vcf"),
                ("Custom (isi manual di bawah)", ""),
            ],
            format_func=lambda x: x[0]
        )
        vcf_path_input = st.text_input(
            "📂 Path VCF Hasil Pipeline (.vcf)",
            value=vcf_preset[1],
            help="Path absolut atau relatif ke file VCF hasil pipeline — bisa diubah manual"
        )

    if st.button("🔍 Jalankan Validasi"):
        if not os.path.exists(gt_path):
            st.error(f"File ground truth tidak ditemukan: `{gt_path}`")
        elif not os.path.exists(vcf_path_input):
            st.error(f"File VCF tidak ditemukan: `{vcf_path_input}`")
        else:
            with open(gt_path, "r") as f:
                gt_content = f.read()
            with open(vcf_path_input, "r") as f:
                vcf_content = f.read()

            gt_total_lines = len([l for l in gt_content.splitlines() if l.strip()])
            detected       = parse_vcf(vcf_content)

            # Ambil kromosom yang ada di VCF untuk filter ground truth
            vcf_chroms = set(v["chrom"] for v in detected.values())

            # Parse ground truth, filter hanya kromosom yang ada di VCF
            ground_truth = {}
            for line in gt_content.strip().splitlines():
                parts = line.split()
                if len(parts) < 4:
                    continue
                chrom, pos, ref, alt = parts[0], int(parts[1]), parts[2], parts[3]
                if chrom in vcf_chroms:
                    ground_truth[(chrom, pos)] = {"chrom": chrom, "pos": pos, "ref": ref, "alt": alt}

            if gt_total_lines > 0:
                st.info(f"ℹ️ Ground truth: {gt_total_lines:,} total mutasi — difilter ke {len(ground_truth):,} mutasi pada kromosom yang ada di VCF ({', '.join(sorted(vcf_chroms))})")

            gt_positions  = set(ground_truth.keys())
            vcf_positions = set(detected.keys())

            true_positive  = gt_positions & vcf_positions
            false_negative = gt_positions - vcf_positions
            false_positive = vcf_positions - gt_positions

            tp = len(true_positive)
            fn = len(false_negative)
            fp = len(false_positive)
            sensitivity = (tp / len(gt_positions) * 100) if gt_positions else 0
            precision   = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0

            # ── Ringkasan Metrik ──────────────────────────────────────────────
            st.markdown("### 📊 Ringkasan Validasi")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Mutasi (GT)",   len(gt_positions))
            m2.metric("Total Variant (VCF)", len(vcf_positions))
            m3.metric("✅ True Positive",     tp)
            m4.metric("❌ False Negative",    fn)
            m5.metric("⚠️ False Positive",    fp)

            st.markdown("---")
            r1, r2 = st.columns(2)
            r1.metric("Sensitivity (Recall)", f"{sensitivity:.1f}%")
            r2.metric("Precision",            f"{precision:.1f}%")
            st.caption("Sensitivity: % mutasi ground truth yang berhasil dideteksi | Precision: % variant di VCF yang memang benar ada di ground truth")

            # ── Tabel True Positive ───────────────────────────────────────────
            st.markdown("---")
            st.markdown("### ✅ Mutasi yang Sama Terdeteksi (True Positive)")
            if true_positive:
                tp_rows = []
                for key in sorted(true_positive):
                    g = ground_truth[key]
                    d = detected[key]
                    tp_rows.append({
                        "Kromosom":  g["chrom"],
                        "Posisi":    g["pos"],
                        "REF (GT)":  g["ref"],
                        "ALT (GT)":  g["alt"],
                        "REF (VCF)": d["ref"],
                        "ALT (VCF)": d["alt"],
                        "Match REF": "✅" if g["ref"].upper() == d["ref"].upper() else "⚠️",
                        "Match ALT": "✅" if g["alt"].upper() == d["alt"].upper() else "⚠️",
                    })
                st.dataframe(pd.DataFrame(tp_rows))
            else:
                st.info("Tidak ada mutasi yang cocok.")

            # ── Tabel False Negative ──────────────────────────────────────────
            st.markdown("### ❌ Mutasi Tidak Terdeteksi (False Negative / Missed)")
            if false_negative:
                fn_rows = []
                for key in sorted(false_negative):
                    g = ground_truth[key]
                    fn_rows.append({
                        "Kromosom":   g["chrom"],
                        "Posisi":     g["pos"],
                        "REF":        g["ref"],
                        "ALT":        g["alt"],
                        "Keterangan": "Ada di ground truth, tidak ditemukan di VCF"
                    })
                st.dataframe(pd.DataFrame(fn_rows))
            else:
                st.success("Semua mutasi ground truth berhasil dideteksi!")

            # ── Tabel False Positive ──────────────────────────────────────────
            st.markdown("### ⚠️ Variant Tambahan di VCF (False Positive)")
            if false_positive:
                fp_rows = []
                for key in sorted(false_positive):
                    d = detected[key]
                    fp_rows.append({
                        "Kromosom":   d["chrom"],
                        "Posisi":     d["pos"],
                        "REF":        d["ref"],
                        "ALT":        d["alt"],
                        "Keterangan": "Ada di VCF, tidak ada di ground truth"
                    })
                st.dataframe(pd.DataFrame(fp_rows))
            else:
                st.success("Tidak ada false positive — semua variant di VCF valid!")

else:
    st.info("👈 Silakan unggah berkas FASTQ atau masukkan path file melalui panel di sebelah kiri untuk memulai platform.")

# ── Sample Data untuk Testing ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("📦 Sample Data untuk Testing")
st.write("Download file FASTQ contoh untuk mencoba pipeline tanpa perlu data sendiri.")

samp1, samp2 = st.columns(2)

with samp1:
    st.markdown("#### 🧬 Human chr22 Sintetis (500K reads)")
    st.caption("Generated oleh wgsim dari GRCh38 chr22. ~166MB, single-end, coverage ~1.5x.")
    chr22_path = "/mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq"
    if os.path.exists(chr22_path):
        with open(chr22_path, "rb") as f:
            st.download_button(
                "📥 Download sim_chr22.fastq",
                f, file_name="sim_chr22.fastq",
                mime="text/plain"
            )
        st.caption(f"Ukuran: {os.path.getsize(chr22_path)/1024/1024:.1f} MB")
    else:
        st.warning("File tidak ditemukan di server")

with samp2:
    st.markdown("#### 🧬 Human chr22 Sintetis (10M reads)")
    st.caption("Generated oleh wgsim dari GRCh38 chr22. ~2.2GB, single-end, coverage ~30x.")
    chr22_10m_path = "/mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22_10M.fastq"
    if os.path.exists(chr22_10m_path):
        size_gb = os.path.getsize(chr22_10m_path)/1024/1024/1024
        st.info(f"Ukuran: {size_gb:.1f} GB — gunakan **Input Path** di sidebar")
        st.code(chr22_10m_path)
        st.caption("File terlalu besar untuk download via browser. Salin path di atas ke sidebar.")
    else:
        st.warning("File tidak ditemukan di server")

st.markdown("---")
st.subheader("🔧 Generate Sample Data Sendiri")
st.caption("Jalankan perintah berikut di terminal WSL untuk membuat data sintetis:")
st.code(
    "# Generate 500K reads dari chr22 (~166MB)\n"
    "wgsim -N 500000 -1 150 -S 42 \\\n"
    "  /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa \\\n"
    "  /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22.fastq \\\n"
    "  /dev/null \\\n"
    "  > /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22_mutations.txt\n\n"
    "# Generate 10M reads dari chr22 (~2.2GB, untuk GATK ~30x coverage)\n"
    "wgsim -N 10000000 -1 150 -S 42 \\\n"
    "  /mnt/c/Users/Mahasiswa/Fastt/ref_genome/chr22.fa \\\n"
    "  /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22_10M.fastq \\\n"
    "  /dev/null \\\n"
    "  > /mnt/c/Users/Mahasiswa/Fastt/datas/sim_chr22_10M_mutations.txt",
    language="bash"
)
