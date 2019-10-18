import sys
import re
import pprint
import mysql.connector
import isoseq
import config
import argparse
import json

parser=argparse.ArgumentParser(description='Load IsoSeq reads from a SAM file into an IsoSeq database')
parser.add_argument('sam', action='store',help='the SAM file to load reads from')
parser.add_argument('library', action='store', help ='the name of the IsoSeq library')
parser.add_argument('--illumina_bed',action='store',help='A BED file of Illumina supported introns. If provided, the valid_introns field will be given a value of 1 if all of their introns are supported by spanning Illumina reads')
args=parser.parse_args()

sam=open(args.sam,"r")

reads={}
for line in sam:
	if re.match('@',line):
#		print line
		continue
	fields=line.split("\t")
	read_name=fields[0];
	reads[read_name]={}
	reads[read_name]['scaffold']=fields[2]
	start_pos=int(fields[3])
	cigar=fields[5]
	#replace any 'deletions' that are > 10 bp with introns.
	cigar=re.sub(r'(\d\d+)D',r'\1N',cigar)
	exons=isoseq.parse_cigar( start_pos, cigar )
	reads[read_name]['exons']=exons
	flag=fields[1]
	if flag == '0':
		reads[read_name]['strand']='+'
	elif flag == '16':
		reads[read_name]['strand']='-'
	else:
		del reads[read_name]

if args.illumina_bed is not None:
	valid_introns=isoseq.parse_introns_bed(args.illumina_bed) 
	if not valid_introns:
		print 'Problem parsing illumina BED file'
		sys.exit()		
	#print(json.dumps(valid_introns, indent=4))

cnx=mysql.connector.connect(**config.config)
cursor=cnx.cursor()

insert_read=("INSERT INTO isoseq_reads "
        "(scaffold, strand, read_name, library, intron_validation) "
        "VALUES (%s, %s, %s, %s, %s)")

insert_exons=("INSERT INTO exons "
        "(read_id, start, end) "
        "VALUES (%s, %s, %s)")

for read_name in reads:
#	validation = 1
	if valid_introns and len(reads[read_name]['exons']) > 1:
		validation=isoseq.validate_read(reads[read_name], valid_introns)
	elif len(reads[read_name]['exons']) == 1:
		validation = 1
	read_data=(reads[read_name]['scaffold'], reads[read_name]['strand'], read_name, args.library, validation)
	cursor.execute(insert_read,read_data)
	read_id=cursor.lastrowid
	for exon_start in reads[read_name]['exons']:
		exon_data=(read_id,exon_start,reads[read_name]['exons'][exon_start])
		cursor.execute(insert_exons,exon_data)

cnx.commit()
cursor.close()
cnx.close()



