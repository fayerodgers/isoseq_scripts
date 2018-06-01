import sys
import re
import pprint
import mysql.connector
import isoseq
import config

sam=open(sys.argv[1],"r")

reads={}
for line in sam:
	fields=line.split("\t")
	read_name=fields[0];
	reads[read_name]={}
	reads[read_name]['scaffold']=fields[2]
	start_pos=int(fields[3])
	cigar=fields[5]
	exons=isoseq.parse_cigar( start_pos, cigar )
	reads[read_name]['exons']=exons
	flag=fields[1]
	if flag == '0':
		reads[read_name]['strand']='+'
	elif flag == '16':
		reads[read_name]['strand']='-'
	else:
		del reads[read_name]

cnx=mysql.connector.connect(**config.config)
cursor=cnx.cursor()

insert_read=("INSERT INTO isoseq_reads "
        "(scaffold, strand, read_name) "
        "VALUES (%s, %s, %s)")

insert_exons=("INSERT INTO exons "
        "(read_id, start, end) "
        "VALUES (%s, %s, %s)")

for read_name in reads:
	read_data=(reads[read_name]['scaffold'], reads[read_name]['strand'], read_name)
	cursor.execute(insert_read,read_data)
	read_id=cursor.lastrowid
	for exon_start in reads[read_name]['exons']:
		exon_data=(read_id,exon_start,reads[read_name]['exons'][exon_start])
		cursor.execute(insert_exons,exon_data)

cnx.commit()
cursor.close()
cnx.close()



