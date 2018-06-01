import sys
import re
import pprint
import mysql.connector

###################

def parse_cigar(start_pos,cigar):
        exons={}
        pattern=re.compile('\d+\D+')
        length=re.compile('\d+')
        operation=re.compile('\D+')
        blocks=pattern.findall(cigar)
        introns=re.findall('N',cigar)
        pos=start_pos
        count=int(0)
        for block in blocks:
                count+=1
                bases=length.search(block)
                op=operation.search(block)
                if (op.group() == 'M') or (op.group() == 'D') or (op.group() == '=') or (op.group() == 'X'):
                        pos=pos+int(bases.group())
                if (op.group() == 'N') or (count == len(blocks)):
                        exons[start_pos]=pos
                        pos=pos+int(bases.group())
                        start_pos=pos
        return exons


####################

def dump_gff(reads):
	for read_name in reads:
		scaffold=reads[read_name]['scaffold']
		strand=reads[read_name]['strand']
		transcript_start=min(reads[read_name]['exons'].keys())
		last_exon=max(reads[read_name]['exons'].keys())
		transcript_end=reads[read_name]['exons'][last_exon]
		print "{}\tisoseq\ttranscript\t{}\t{}\t.\t{}\t.\tID={};".format(scaffold,transcript_start,transcript_end,strand,read_name)
		i=1
		for exon in reads[read_name]['exons']:
			print "{}\tisoseq\texon\t{}\t{}\t.\t{}\t.\tID={}.exon{};Parent={};".format(scaffold,exon,reads[read_name]['exons'][exon],strand,read_name,i,read_name)
			i+=1	

