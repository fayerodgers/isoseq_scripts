import mysql.connector
import isoseq
import config
import json
import argparse
import sys


parser=argparse.ArgumentParser(description='Write an Apollo compliant GFF from the T muris IsoSeq database')
parser.add_argument('--clustering_level',action='store',help='specify "clustered" or "5_prime_collapsed". Leaving out clustering_level will return raw reads')
parser.add_argument('--supporting_reads', action='store',default=1,help='a number. Only print transcripts that have at least this number of supporting reads')
parser.add_argument('--library',action='store',help='only print transcripts (or clusters) that are exclusive to the specified library')
parser.add_argument('--gene_list',action='store',help='a file listing the IsoSeq transcript IDs that should be printed')
parser.add_argument('gff_format',action='store',help='"apollo" or "transdecoder" (slightly different GFF formatting)')
args=parser.parse_args()

#if args.gene_list is not None:
	
if args.clustering_level is None:
	transcripts=isoseq.retrieve_reads('full')
elif args.clustering_level=='clustered':
	transcripts=isoseq.retrieve_clusters('clustered')
elif args.clustering_level=='5_prime_collapsed':
	transcripts=isoseq.retrieve_clusters('collapsed')
else:
	parser.print_help()
	sys.exit() 

transcripts_to_delete=set()


for transcript in transcripts:
	if transcripts[transcript]['read_support'] < int(args.supporting_reads):
		transcripts_to_delete.add(transcript)
	if args.library is not None:
		if len(transcripts[transcript]['libraries'])>1 or transcripts[transcript]['libraries'][0]!=args.library:
			transcripts_to_delete.add(transcript)

for transcript in transcripts_to_delete:
	del transcripts[transcript]

#print(transcripts)	

isoseq.dump_gff(transcripts,args.gff_format)

