import sys
import re
import pprint
import mysql.connector
import config
import json

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
                        exons[start_pos]=pos-1
                        pos=pos+int(bases.group())
                        start_pos=pos
        return exons

########################
def parse_gff(gff,gff_type):
	transcripts={}
	for line in gff:
		line.rstrip()
		temp = line.split("\t")
		if len(temp) != 9:
			continue
		if not (re.match('exon',temp[2]) or re.match('CDS',temp[2]) or re.match('mRNA',temp[2])):
			continue
		if gff_type == 'wb':
			m = re.search('(TMUE_M?[0-9]+)',temp[8])
		if gff_type == 'transdecoder':
			m = re.search('Parent=([0-9]+)',temp[8])
		t = re.search('ORF%20type%3A(.+)%20len',temp[8])
                s = re.search('score%3D(.+)$',temp[8])
		if m:
			transcript = m.group(1)
		else:
			print 'error parsing gff'
			sys.exit()
		if transcript not in transcripts:
			transcripts[transcript] = {}
		transcripts[transcript]['scaffold'] = temp[0]
		transcripts[transcript]['strand'] = temp[6]
		if t:
			 transcripts[transcript]['type'] = t.group(1)
		if s:
			transcripts[transcript]['score'] = s.group(1)
		if re.match('exon',temp[2]):
			if 'exons' not in  transcripts[transcript]:
				 transcripts[transcript]['exons'] = {}
			transcripts[transcript]['exons'][temp[3]]=temp[4]
                if re.match('CDS',temp[2]):
                        if 'cds' not in  transcripts[transcript]:
                                 transcripts[transcript]['cds'] = {}
			if temp[3] not in transcripts[transcript]['cds']:
				 transcripts[transcript]['cds'][temp[3]] = {}
                        transcripts[transcript]['cds'][temp[3]]['end_coord']=temp[4]
			transcripts[transcript]['cds'][temp[3]]['frame']=temp[7]

	return transcripts
		




####################
def parse_introns_bed(illumina_bed):
	illumina=open(illumina_bed,"r")
	if not illumina:
		return None
	valid_introns={}
	for line in illumina:
		fields=line.split("\t")
		scaffold=fields[0]
		start=int(fields[1])
		end=int(fields[2])+1
		if scaffold not in valid_introns:
			valid_introns[scaffold]={}
		if start not in valid_introns[scaffold]:
			valid_introns[scaffold][start]=[]
		valid_introns[scaffold][start].append(end)
	return valid_introns
		
#####################
def validate_read(read,valid_introns):
	exon_starts=read['exons'].keys()
	exon_starts.sort(key=int)
	introns={}
	scaffold=read['scaffold']
	if scaffold not in valid_introns:
		return None
	for i in range(0,len(exon_starts)-1):
		intron_start=read['exons'][exon_starts[i]]
		intron_end=exon_starts[i+1]
		introns[intron_start]=intron_end
#	print(json.dumps(introns,indent=4))
	for start in introns:
		if start in valid_introns[scaffold]:
			i=0
			for end in valid_introns[scaffold][start]:
				i+=1
				if end == introns[start]:
					break
				if i==len(valid_introns[scaffold][start]):
					return None
		else:	
			 return None
	return 1

####################
def dump_gff(reads, usage):
	for read_name in reads:
		scaffold=reads[read_name]['scaffold']
		strand=reads[read_name]['strand']
		transcript_start=min(reads[read_name]['exons'].keys())
		last_exon=max(reads[read_name]['exons'].keys())
		transcript_end=reads[read_name]['exons'][last_exon]
		if 'libraries' in reads[read_name]:
			libraries=reads[read_name]['libraries']
		if 'read_support' in reads[read_name]:
			read_support=reads[read_name]['read_support']
		if usage == 'apollo':
			print "{}\tisoseq\ttranscript\t{}\t{}\t.\t{}\t.\tID={};supporting_reads={};libraries={};".format(scaffold,transcript_start,transcript_end,strand,read_name,read_support,",".join(libraries))
			i=1
			for exon in reads[read_name]['exons']:
				print "{}\tisoseq\texon\t{}\t{}\t.\t{}\t.\tID={}.exon{};Parent={};".format(scaffold,exon,reads[read_name]['exons'][exon],strand,read_name,i,read_name)
				i+=1
		if usage == 'transdecoder':
			print '{}\tisoseq\ttranscript\t{}\t{}\t.\t{}\t.\tgene_id "{}"; transcript_id "{}"; supporting_reads={};libraries={};'.format(scaffold,transcript_start,transcript_end,strand,read_name,read_name,read_support,",".join(libraries))
			i=1
			exons=reads[read_name]['exons'].keys()
			exons.sort(key=int)
			for exon in exons:
				print '{}\tisoseq\texon\t{}\t{}\t.\t{}\t.\tgene_id "{}"; transcript_id "{}"; exon_number "{}";'.format(scaffold,exon,reads[read_name]['exons'][exon],strand,read_name,read_name,i)
				i+=1
		if usage == 'apollo_cds':
			print "{}\tisoseq\ttranscript\t{}\t{}\t.\t{}\t.\tID={};cluster={};".format(scaffold,transcript_start,transcript_end,strand,read_name,reads[read_name]['isoseq_id'])
			i=1
			for exon in reads[read_name]['exons']:
				print "{}\tisoseq\texon\t{}\t{}\t.\t{}\t.\tID={}.exon{};Parent={};".format(scaffold,exon,reads[read_name]['exons'][exon],strand,read_name,i,read_name)
				i+=1
			i=1
			for cds in reads[read_name]['cds']:
				print "{}\tisoseq\tCDS\t{}\t{}\t.\t{}\t{}\tID={}.cds{};Parent={};".format(scaffold,cds,reads[read_name]['cds'][cds]['end_coord'],strand,reads[read_name]['cds'][cds]['frame'],read_name,i,read_name )	
				i+=1					 


######################

def retrieve_clusters(collapsed):
	cnx=mysql.connector.connect(**config.config)
	cursor=cnx.cursor()
	select_clusters=("SELECT DISTINCT isoseq_reads.cluster, isoseq_reads.scaffold, isoseq_reads.strand, exon_clusters.start, exon_clusters.end "
			"FROM isoseq_reads "
			"LEFT JOIN exon_clusters ON isoseq_reads.cluster = exon_clusters.cluster")
	if collapsed=='collapsed':
		select_clusters=("SELECT DISTINCT isoseq_reads.5_prime_cluster, isoseq_reads.scaffold, isoseq_reads.strand, exon_clusters.start, exon_clusters.end "
                        "FROM isoseq_reads "
                        "LEFT JOIN exon_clusters ON isoseq_reads.5_prime_cluster = exon_clusters.cluster")
	select_read_libraries=("SELECT COUNT(*), library FROM isoseq_reads WHERE cluster = %s GROUP BY library")
	cursor.execute(select_clusters)
	clusters={}	
	for (cluster,scaffold,strand,start,end) in cursor:
		if cluster is None:
			continue
		if cluster not in clusters:
			clusters[cluster]={}
		if 'scaffold' not in clusters[cluster]:
			clusters[cluster]['scaffold']=scaffold
		if 'strand' not in clusters[cluster]:
			clusters[cluster]['strand']=strand
		if 'exons' not in clusters[cluster]:
			clusters[cluster]['exons']={}
		clusters[cluster]['exons'][start]=end
	for cluster in clusters:
		data=(cluster,)
		if 'read_support' not in clusters[cluster]:
			clusters[cluster]['read_support']=0
		if 'libraries' not in clusters[cluster]:
			clusters[cluster]['libraries']=set()
		cursor.execute(select_read_libraries,data)
		for (count,library) in cursor:
			clusters[cluster]['read_support']+=int(count)
			clusters[cluster]['libraries'].add(library)
	cursor.close
	cnx.close
	#print(json.dumps(clusters, indent=4))
	return clusters

########################
def retrieve_reads(level):
        cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()
	select_reads=("SELECT isoseq_reads.read_id, isoseq_reads.scaffold, isoseq_reads.strand, exons.start, exons.end, isoseq_reads.library "
			"FROM isoseq_reads "
			"LEFT JOIN exons ON isoseq_reads.read_id = exons.read_id")
	if level == 'non_clustered_only':
		select_reads=select_reads+" WHERE isoseq_reads.cluster IS NULL"
	cursor.execute(select_reads)
	reads={}
	for (read_id,scaffold,strand,start,end,library) in cursor:
		if read_id not in reads:
			reads[read_id]={}
		if 'scaffold' not in reads[read_id]:
			reads[read_id]['scaffold']=scaffold
		if 'strand' not in reads[read_id]:
			reads[read_id]['strand']=strand
		if 'exons' not in reads[read_id]:
			reads[read_id]['exons']={}
		reads[read_id]['exons'][start]=end
		if 'libraries' not in reads[read_id]:
			reads[read_id]['libraries']=set()
		reads[read_id]['libraries'].add(library)
		if 'read_support' not in reads[read_id]:
			reads[read_id]['read_support']=1
	return reads

#########################
def cluster_reads(reads,clusters):
	cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()
	assign_to_cluster=("UPDATE isoseq_reads SET cluster=%s WHERE read_id=%s")
	update_exon_clusters=("INSERT INTO exon_clusters "
			"(cluster, start, end) "
			"VALUES (%s,%s,%s)")
	for read_id in reads:
#		print read_id
		match=0
		scaffold=reads[read_id]['scaffold']
		strand=reads[read_id]['strand']
		for cluster in clusters:
			cluster_scaffold=clusters[cluster]['scaffold']
			if scaffold != cluster_scaffold:
				continue
			cluster_strand=clusters[cluster]['strand']
			if strand != cluster_strand:
				continue
			if len(reads[read_id]['exons']) != len(clusters[cluster]['exons']):
				continue
			result=compare_equal_length_transcripts(reads[read_id]['exons'], clusters[cluster]['exons'], len(reads[read_id]['exons']))
			if result:
				#assign read to cluster
				data=(cluster,read_id)
				cursor.execute(assign_to_cluster,data)
				match=1
				break
		if match==0:
			#make a new cluster
			data=(read_id,read_id)
			cursor.execute(assign_to_cluster,data)
			for start,end in reads[read_id]['exons'].items():
				data=(read_id,start,end)
				cursor.execute(update_exon_clusters,data)
			clusters[read_id]=reads[read_id]
	cnx.commit()
	cursor.close()
	cnx.close()
	return clusters	


###########################

def extend_ends(clusters):		#given clusters, choose the longest 5' and 3' ends
        cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()
	get_start=("SELECT MIN(exons.start) FROM exons LEFT JOIN isoseq_reads ON isoseq_reads.read_id = exons.read_id WHERE isoseq_reads.cluster=%s")
	get_end=("SELECT MAX(exons.end) FROM exons LEFT JOIN isoseq_reads ON isoseq_reads.read_id = exons.read_id WHERE isoseq_reads.cluster=%s")
	update_start=("UPDATE exon_clusters SET start=%s WHERE cluster=%s and start=%s")
	update_end=("UPDATE exon_clusters SET end=%s WHERE cluster=%s and end=%s")
	for cluster in clusters:
		exons = clusters[cluster]['exons'].keys() 
		exons.sort(key=int)
		current_start=min(exons,key=int)
		start_exon_end=clusters[cluster]['exons'][current_start]
		end_exon_start=max(exons,key=int)
		current_end=clusters[cluster]['exons'][max(exons,key=int)]
		data = (cluster,)
		cursor.execute(get_start,data)
		for (start,) in cursor:
			data = (start,cluster,current_start)
			cursor.execute(update_start,data)
			clusters[cluster]['exons'][start]=start_exon_end
		data=(cluster,)
		cursor.execute(get_end,data)
		for (end,) in cursor:
			data = (end,cluster,current_end)
			cursor.execute(update_end,data)
			clusters[cluster]['exons'][end_exon_start]=end
		if current_start != start:
			del clusters[cluster]['exons'][current_start]
	cnx.commit()
        cursor.close()
        cnx.close()
	return clusters		
		


##########################

def collapse_ends(clusters, collapsed_clusters):
        cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()
	assign_to_collapsed_cluster=("UPDATE isoseq_reads SET 5_prime_cluster=%s WHERE cluster=%s")
	reassign_collapsed_cluster=("UPDATE isoseq_reads SET 5_prime_cluster=%s WHERE 5_prime_cluster=%s")
	for cluster in clusters:	
		scaffold=clusters[cluster]['scaffold']
		strand=clusters[cluster]['strand']
		cluster_exon_number=len(clusters[cluster]['exons'])
		match=0
		result_b=None
		for collapsed in collapsed_clusters:
			collapsed_scaffold=collapsed_clusters[collapsed]['scaffold']
			if scaffold != collapsed_scaffold:
				continue
			collapsed_strand=collapsed_clusters[collapsed]['strand']	
			if strand != collapsed_strand:
				continue
			collapsed_exon_number=len(collapsed_clusters[collapsed]['exons'])
                        if collapsed_exon_number > cluster_exon_number: #simple case where the cluster fits inside an existing collapsed cluster
                                result_a=compare_5_prime_ends(clusters[cluster]['exons'],collapsed_clusters[collapsed]['exons'], cluster_exon_number, strand)
                                if result_a:
                                        data=(collapsed,cluster)
                                        cursor.execute(assign_to_collapsed_cluster,data)		
					match=1
					break	
			elif cluster_exon_number > collapsed_exon_number:
				result_b=compare_5_prime_ends(collapsed_clusters[collapsed]['exons'], clusters[cluster]['exons'], collapsed_exon_number, strand)
				if result_b:
					data=(cluster,cluster)
					cursor.execute(assign_to_collapsed_cluster,data)
					data=(cluster,collapsed)
					cursor.execute(reassign_collapsed_cluster,data)
					old_collapsed=collapsed		#so that we can update collapsed_clusters
					match=1
					break
		if result_b:
			del collapsed_clusters[old_collapsed]  	
			collapsed_clusters[cluster]=clusters[cluster]

		if match != 1:		#make a new collapsed cluster
			data=(cluster,cluster)
			cursor.execute(assign_to_collapsed_cluster,data)
			collapsed_clusters[cluster]=clusters[cluster]
	cnx.commit()
	cursor.close()
	cnx.close()
	return collapsed_clusters

								
###########################

def compare_equal_length_transcripts(read_1_exons,read_2_exons, exon_count):
	read_1_starts=read_1_exons.keys()
	read_1_starts.sort(key=int)
	read_2_starts=read_2_exons.keys()
	read_2_starts.sort(key=int)
	#check all but the first and last exons match exactly
	if exon_count > 2:
		for i in range(1,(exon_count-2)):
			if read_1_starts[i]!=read_2_starts[i] or read_1_exons[read_1_starts[i]]!=read_2_exons[read_2_starts[i]]:
					return None
	#check that the first exon and last exon match and calculate difference in extension 
	if exon_count>1:
		if read_1_exons[read_1_starts[0]]!=read_2_exons[read_2_starts[0]]:
			return None
		if read_1_starts[(exon_count-1)]!=read_2_starts[(exon_count-1)]:
			return None
	if exon_count==1:
	#check that the reads overlap
		if read_2_starts[0]>read_1_exons[read_1_starts[0]]:
			return None
		if read_2_exons[read_2_starts[0]]<read_1_starts[0]:
			return None
	return 1


###############################

def compare_5_prime_ends(shorter_transcript_exons,longer_transcript_exons,exon_count,strand):		#returns true if the shorter transcript matches the longer transcript but is 5' truncated
	short_starts=shorter_transcript_exons.keys()
	longer_starts=longer_transcript_exons.keys()
	if strand == '+':
		short_starts.sort(reverse=True,key=int)
		longer_starts.sort(reverse=True,key=int)
		if exon_count > 1 and short_starts[0] != longer_starts[0]:
			return None
		if exon_count > 1 and shorter_transcript_exons[short_starts[(exon_count-1)]]!=longer_transcript_exons[longer_starts[(exon_count-1)]]:
			return None
		if exon_count >= 1 and short_starts[(exon_count-1)] < longer_starts[(exon_count-1)]:
			return None
		if exon_count == 1 and shorter_transcript_exons[short_starts[0]] > longer_transcript_exons[longer_starts[0]]:
			return None
	elif strand == '-':
                short_starts.sort(key=int)
                longer_starts.sort(key=int)
		if exon_count > 1 and shorter_transcript_exons[short_starts[0]] != longer_transcript_exons[longer_starts[0]]:
			return None
		if exon_count >1 and short_starts[(exon_count-1)] != longer_starts[(exon_count-1)]:
			return None 
		if exon_count >= 1 and short_starts[0] < longer_starts[0]:
			return None
		if exon_count == 1 and shorter_transcript_exons[short_starts[0]] > longer_transcript_exons[longer_starts[0]]:
			return None
	if exon_count > 2:
		for i in range (1,(exon_count-2)):
			if short_starts[i]!=longer_starts[i] or shorter_transcript_exons[short_starts[i]]!=longer_transcript_exons[longer_starts[i]]:
				return None 
	return 1	
		
				
	
#####################################
def compare_cds(cds_1,cds_2):	#give it two dictionaries of cds 
	cds_1_count = 0
	cds_2_count = 0
	for start_1 in cds_1.keys():
		if start_1 not in cds_2.keys():
			continue
		if cds_1[start_1]['end_coord'] == cds_2[start_1]['end_coord'] and cds_1[start_1]['frame'] == cds_2[start_1]['frame']:
			cds_1_count += 1
			cds_2_count += 1
	cds_1_score = float(cds_1_count)/float(len(cds_1.keys()))
	cds_2_score = float(cds_2_count)/float(len(cds_2.keys()))
	return (cds_1_score,cds_2_score)
	



