# isoseq_scripts

The data that should be processed are aligned (non clustered) full length non-chimeric (flnc) reads from the SMRT pipeline.

Create a database to store the data, eg:

```
mysql -h mysql-wormbase-pipelines -u wormadmin -P 4331 -p

create database ttre_isoseq

exit

mysql -h mysql-wormbase-pipelines -u wormadmin -P 4331 -p ttre_isoseq < isoseq.sql
```

Update ```config.py``` with the name of the database

Load the reads:

```
python load_reads_as_transcripts.py flnc.sam library_name --illumina_bed introns.bed
```
"library_name" is an identifier for the sample and introns.bed is a BED file of introns with support from bridging Illumina reads.

Cluster the reads:

```
python cluster.py
```

cluster.py: 

* clusters reads that have the same exon/intron structure.
* for each of those clustered transcript structures, extends the ends of the first and last exons as far as there is evidence from any read.
* if any clusters are 5' truncated versions of another cluster, collapse the shorter clusters into the longer ones.

Use TransDecoder (https://github.com/TransDecoder) to identify ORFs:

```
python write_gff.py transdecoder --clustering_level 5_prime_collapsed --supporting_reads 2 > isoseq_transcripts.gff

gtf_genome_to_cdna_fasta.pl isoseq_transcripts.gff TTRE.fa > transcripts.fa

gtf_to_alignment_gff3.pl isoseq_transcripts.gff > transcripts.gff3

TransDecoder.LongOrfs -t transcripts.fa

TransDecoder.Predict -t transcripts.fa

cdna_alignment_orf_to_genome_orf.pl transcripts.fa.transdecoder.gff3 transcripts.gff3 transcripts.fa > transcripts.fasta.transdecoder.genome.gff3
```
Put the ORFs into the database and cluster the transcripts into genes:

```
python import_orfs.py --gff transcripts.fasta.transdecoder.genome.gff3
```

To visualise each stage in Apollo:

```
python write_gff.py apollo --clustering_level 5_prime_collapsed --supporting_reads 2 > isoseq_transcripts.gff
```
