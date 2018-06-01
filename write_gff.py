import mysql.connector
import isoseq
import config
import json

cnx=mysql.connector.connect(**config.config)
cursor=cnx.cursor()

select_reads=("SELECT isoseq_reads.read_name, isoseq_reads.scaffold, isoseq_reads.strand, exons.start, exons.end "
			"FROM isoseq_reads "
			"LEFT JOIN exons ON isoseq_reads.read_id = exons.read_id")

cursor.execute(select_reads)

reads={}

for (read_name,scaffold,strand,start,end) in cursor:
	if read_name not in reads:
		reads[read_name]={}
	if 'scaffold' not in reads[read_name]:
		reads[read_name]['scaffold']=scaffold
	if 'strand' not in reads[read_name]:
		reads[read_name]['strand']=strand
	if 'exons' not in reads[read_name]:
		reads[read_name]['exons']={}
	reads[read_name]['exons'][start]=end

cursor.close
cnx.close

#print(json.dumps(reads, indent=4))

isoseq.dump_gff(reads)
