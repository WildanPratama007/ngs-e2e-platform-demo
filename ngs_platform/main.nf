#!/usr/bin/env nextflow

/*
 * NGS E2E Secondary Analysis Pipeline
 * Alur: FastQC → Trimmomatic SE → BWA MEM → Samtools → BCFTools
 */

nextflow.enable.dsl = 2

// ── Konstanta path tools ──────────────────────────────────────────────────────
def CONDA_BIN = "/home/mahasiswa/miniconda3/envs/ngs_platform/bin"


if (!params.reads) {
    error "Parameter --reads wajib diisi. Contoh: nextflow run main.nf --reads 'sample.fastq'"
}

// ── Proses 1: FastQC ──────────────────────────────────────────────────────────
process FASTQC {
    tag        "$sample_id"
    publishDir "${params.outdir}/${sample_id}/fastqc", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)

    output:
    tuple val(sample_id), path("*_fastqc.html"), path("*_fastqc.zip")

    script:
    def fastqc_bin = params.fastqc_path ?: 'fastqc'
    """
    ${fastqc_bin} ${reads} --outdir .
    """
}

// ── Proses 2: Trimmomatic SE ──────────────────────────────────────────────────
process TRIMMOMATIC_SE {
    tag        "$sample_id"
    publishDir "${params.outdir}/${sample_id}/trimmed", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)

    output:
    tuple val(sample_id), path("${sample_id}.trimmed.fastq")

    script:
    """
    ${params.bin_dir}/trimmomatic SE \
        ${reads} \
        ${sample_id}.trimmed.fastq \
        ${params.trimmer_opts} \
        2> trimmomatic.log

    # Fallback: jika trimmed kosong, gunakan file asli
    if [ ! -s ${sample_id}.trimmed.fastq ]; then
        cp ${reads} ${sample_id}.trimmed.fastq
    fi
    """
}

// ── Proses 3: BWA MEM + Samtools Sort & Index ─────────────────────────────────
process BWA_ALIGN {
    tag        "$sample_id"
    publishDir "${params.outdir}/${sample_id}/bwa", mode: 'copy'

    input:
    tuple val(sample_id), path(trimmed_reads)
    path ref_genome
    path ref_index   // semua file index (.amb .ann .bwt .pac .sa .fai)

    output:
    tuple val(sample_id), path("${sample_id}.aligned.sorted.bam"), path("${sample_id}.aligned.sorted.bam.bai")

    script:
    """
    ${params.bin_dir}/bwa mem ${ref_genome} ${trimmed_reads} \
        | ${params.samtools_bin} sort -o ${sample_id}.aligned.sorted.bam

    ${params.samtools_bin} index ${sample_id}.aligned.sorted.bam
    """
}

// ── Proses 4: Variant Calling (BCFTools) ──────────────────────────────────────
process VARIANT_CALLING {
    tag        "$sample_id"
    publishDir "${params.outdir}/${sample_id}/vcf", mode: 'copy'

    input:
    tuple val(sample_id), path(sorted_bam), path(bam_index)
    path ref_genome
    path ref_index   // semua file index

    output:
    tuple val(sample_id), path("${sample_id}.filtered.vcf")

    script:
    """
    ${params.bcftools_bin} mpileup \
        -O b \
        -o ${sample_id}.bcf \
        -f ${ref_genome} \
        ${sorted_bam}

    ${params.bcftools_bin} call \
        --ploidy ${params.ploidy} \
        -m -v \
        -o ${sample_id}.vcf \
        ${sample_id}.bcf

    ${params.bcftools_bin} filter \
        -s LOWQUAL \
        -e 'QUAL<20 || DP<5' \
        ${sample_id}.vcf \
        > ${sample_id}.filtered.vcf
    """
}

// ── Workflow Utama ─────────────────────────────────────────────────────────────
workflow {

    // Buat channel dari file FASTQ input
    reads_ch = Channel
        .fromPath(params.reads)
        .map { file ->
            def sample_id = file.baseName.replaceAll(/\.fastq$/, '')
            return tuple(sample_id, file)
        }

    // Channel referensi genom
    ref_ch = Channel.fromPath(params.ref_genome)

    // Channel semua file index BWA & samtools (*.amb *.ann *.bwt *.pac *.sa *.fai)
    ref_index_ch = Channel.fromPath("${params.ref_genome}.*").collect()

    // Eksekusi pipeline
    fastqc_out  = FASTQC(reads_ch)
    trimmed_out = TRIMMOMATIC_SE(reads_ch)
    aligned_out = BWA_ALIGN(trimmed_out, ref_ch.first(), ref_index_ch)
    vcf_out     = VARIANT_CALLING(aligned_out, ref_ch.first(), ref_index_ch)

    // Emit path output
    vcf_out.map { sample_id, vcf -> "${params.outdir}/${sample_id}/vcf/${vcf.name}" }
           .view { "VCF Output: $it" }
}
