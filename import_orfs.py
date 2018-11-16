import sys
import config
import json
import isoseq
import argparse

parser=argparse.ArgumentParser(description='Load TransDecoder ORFs into an existing IsoSeq database; cluster transcripts into genes')
parser.add_argument('--gff', action='store',help='the TransDecoder GFF to process')
args=parser.parse_args()

if args.gff is not None:
	gff=open(args.gff,"r")
	(genes,transcripts)=isoseq.parse_gff(gff)
	#print(json.dumps(transcripts,indent=4))
	isoseq.insert_cds(transcripts)
#get orphan transcripts
orphan_transcripts=isoseq.retrieve_orphan_transcripts()
#assign orphan transcripts to a gene
isoseq.assign_transcripts_to_genes(orphan_transcripts)



	

