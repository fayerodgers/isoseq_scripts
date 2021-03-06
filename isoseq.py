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
def parse_gff(gff):
	transcripts={}
	genes={}
	for line in gff:
		line=line.rstrip()
		temp = line.split("\t")
		if len(temp) != 9:
			continue
		if not (re.match('exon',temp[2]) or re.match('CDS',temp[2]) or re.match('mRNA',temp[2]) or re.match('gene',temp[2])):
			continue
		if re.match('gene',temp[2]):
			m = re.search('ID=(?:Gene:)?(.[^;]+)',temp[8])
			if m:
				gene=m.group(1)
				genes[gene]={}
				genes[gene]['start']=int(temp[3])
				genes[gene]['end']=int(temp[4])
				genes[gene]['scaffold']=temp[0]
				genes[gene]['strand']=temp[6]
			else:
				print 'error parsing gff (genes)'
				sys.exit()
			#adding these options for transdecoder GFFs so can extract score and CDS type
			t = re.search('ORF%20type%3A(.+)%20len',temp[8])
                        if t:
                                genes[gene]['type'] = t.group(1)
		elif re.match('mRNA',temp[2]):
			m = re.search('ID=(?:Transcript:)?(.[^;]+)',temp[8])
			p = re.search('Parent=(?:Gene:)?(.[^;]+)',temp[8])
			if m and p:
				transcript=m.group(1)
				parent=p.group(1)
			else:
                                print 'error parsing gff (mRNA)'
                                sys.exit()
			if transcript not in transcripts:
                        	transcripts[transcript]={}
			transcripts[transcript]['parent']=parent
			#adding these options for transdecoder GFFs so can extract score and CDS type
			t = re.search('ORF%20type%3A(.+)%20len',temp[8])
			s = re.search('score%3D(.+)$',temp[8])
			if t:
				transcripts[transcript]['type'] = t.group(1)
			if s:
				transcripts[transcript]['score'] = s.group(1)
		elif re.match('exon',temp[2]):
			p = re.search('Parent=(?:Transcript:)?(.[^;]+)',temp[8])
			if p:	
				transcript=p.group(1)
			else:
                                print 'error parsing gff (exons)'
                                sys.exit()
			if transcript not in transcripts:
				transcripts[transcript]={}
			if 'exons' not in  transcripts[transcript]:
				transcripts[transcript]['exons'] = {}
			transcripts[transcript]['exons'][int(temp[3])]=int(temp[4])
		elif re.match('CDS',temp[2]):
			p = re.search('Parent=(?:Transcript:)?(.[^;]+)',temp[8])
                        if p:
                                transcript=p.group(1)
                        else:
                                print 'error parsing gff (CDS)'
                                sys.exit()
			i = re.search(',',temp[8])  #WB GFFs sometimes have CDS features with multiple parents (annoyingly).
			if i:
				transcripts_list=transcript.split(',Transcript:')
			else:
				transcripts_list=[transcript]
			for transcript in transcripts_list:
				if transcript not in transcripts:
					transcripts[transcript]={}
				if 'cds' not in  transcripts[transcript]:
					transcripts[transcript]['cds'] = {}
				if temp[3] not in  transcripts[transcript]['cds']:
					transcripts[transcript]['cds'][int(temp[3])] = {}
				transcripts[transcript]['cds'][int(temp[3])]['end_coord']=int(temp[4])
				if temp[6] == '+':
					frame = (int(temp[3]) + int(temp[7])) % 3
				elif temp[6] == '-':
					frame = (int(temp[4]) - int(temp[7])) % 3 
				transcripts[transcript]['cds'][int(temp[3])]['frame']=frame

	return (genes,transcripts)
		




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
	select_clusters=("SELECT clusters.cluster, clusters.scaffold, clusters.strand, exon_clusters.start, exon_clusters.end "
			"FROM clusters "
			"LEFT JOIN exon_clusters ON clusters.cluster = exon_clusters.cluster")
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
	select_reads=("SELECT isoseq_reads.read_id, isoseq_reads.scaffold, isoseq_reads.strand, exons.start, exons.end, isoseq_reads.library, isoseq_reads.intron_validation "
			"FROM isoseq_reads "
			"LEFT JOIN exons ON isoseq_reads.read_id = exons.read_id")
	if level == 'non_clustered_only':
		select_reads=select_reads+" WHERE isoseq_reads.cluster IS NULL"
	cursor.execute(select_reads)
	reads={}
	for (read_id,scaffold,strand,start,end,library,intron_validation) in cursor:
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
		if 'intron_validation' not in reads[read_id]:
			reads[read_id]['intron_validation']=intron_validation
	return reads

#########################
def cluster_reads(reads,clusters):
	cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()
	assign_to_cluster=("UPDATE isoseq_reads SET cluster=%s WHERE read_id=%s")
	create_cluster=("INSERT INTO clusters "
		"(cluster,scaffold,strand) "	
		"VALUES (%s,%s,%s)")
	update_exon_clusters=("INSERT INTO exon_clusters "
			"(cluster, start, end) "
			"VALUES (%s,%s,%s)")
	for read_id in reads:
		if reads[read_id]['intron_validation'] != 1:
			continue
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
			data=(read_id,scaffold,strand)
			cursor.execute(create_cluster,data)
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
	


#######################################
def feature_level_clustering(features):
	blocks={}
	for feature in features:
        	feature_coords={}
        	strand = features[feature]['strand']
        	scaffold = features[feature]['scaffold']
		try:
			start=features[feature]['start']
		except:
        		start = min(features[feature]['exons'].keys())
        	try:
			end=features[feature]['end']
		except:
			end = max(features[feature]['exons'].values())
        	feature_coords[start]=end
		match = 0
        	for block in blocks:
                	block_coords = {}
                	block_coords[blocks[block]['start']]=blocks[block]['end']
                	if scaffold != blocks[block]['scaffold']:
                        	continue
                	if strand != blocks[block]['strand']:
                        	continue
                	match= compare_equal_length_transcripts(feature_coords, block_coords,1)
                	if match :
                        	b=block
                        	break
			else:
				 match = 0
        	if match == 1:
                	block_start= min(start,blocks[b]['start'])
                	block_end= max(end,blocks[b]['end'])
                	blocks[b]['start'] = block_start
			blocks[b]['end']=block_end
        	#no match, make a new block
        	elif match == 0:	
                	blocks[feature]={}
                	blocks[feature]['scaffold']=scaffold
                	blocks[feature]['strand']=strand
                	blocks[feature]['start']=start
                	blocks[feature]['end']=end

	return blocks

######################################
def insert_cds(transcripts):
	cnx=mysql.connector.connect(**config.config)
	cursor=cnx.cursor()
	insert_transcript = ("INSERT INTO transcripts "
        "(transcript, cluster, score, type) "
        "VALUES (%s, %s, %s, %s)")

	insert_cds = ("INSERT INTO cds "
        "(transcript, start, end, frame) "
        "VALUES (%s, %s, %s, %s)")

	for transcript in transcripts:
        	cluster=transcripts[transcript]['parent']
        	score=transcripts[transcript]['score']
        	t_type=transcripts[transcript]['type']
        	data=(transcript,cluster,score,t_type)
	       	cursor.execute(insert_transcript,data)
        	for start in transcripts[transcript]['cds']:
                	end=transcripts[transcript]['cds'][start]['end_coord']
                	frame=transcripts[transcript]['cds'][start]['frame']
                	data=(transcript,start,end,frame)
	               	cursor.execute(insert_cds,data)
	cnx.commit()
	cursor.close()
	cnx.close()

#######################################
def retrieve_orphan_transcripts():
        cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()

	get_orphan_transcripts= ("SELECT transcripts.transcript,transcripts.type,"
        "clusters.scaffold,clusters.strand,"
        "cds.start,cds.end,cds.frame "
        "FROM transcripts "
        "LEFT JOIN clusters ON transcripts.cluster = clusters.cluster "
        "LEFT JOIN cds ON transcripts.transcript = cds.transcript "
        "WHERE transcripts.gene is NULL")

	transcripts={}
	cursor.execute(get_orphan_transcripts)
	for(transcript,t_type,scaffold,strand,start,end,frame) in cursor:
        	if transcript not in transcripts:
                	transcripts[transcript]={}
        	transcripts[transcript]['type']=t_type
        	transcripts[transcript]['scaffold']=scaffold
        	transcripts[transcript]['strand']=strand
        	if 'cds' not in transcripts[transcript]:
                	transcripts[transcript]['cds']={}
        	if start not in transcripts[transcript]['cds']:
               		transcripts[transcript]['cds'][start]={}
        	transcripts[transcript]['cds'][start]['end']=end
        	transcripts[transcript]['cds'][start]['frame']=frame

        cursor.close()
        cnx.close()
	return(transcripts)

#######################################
def assign_transcripts_to_genes(transcripts):
	cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()
	query_for_gene =("SELECT gene from transcripts "
                "LEFT JOIN clusters ON transcripts.cluster = clusters.cluster "
                "LEFT JOIN cds ON transcripts.transcript = cds.transcript "
                "WHERE clusters.scaffold = %s AND clusters.strand = %s "
                "AND cds.frame = %s "
                "AND ((cds.start <= %s AND cds.end >= %s) OR (cds.start <= %s AND cds.end >= %s))")

	assign_to_gene = ("UPDATE transcripts SET gene = %s WHERE transcript = %s")

	reassign_gene = ("UPDATE transcripts SET gene = %s WHERE gene = %s")

	get_gene_name = ("SELECT MAX(gene) FROM transcripts")
	for transcript in transcripts:
        	genes=set()
        	scaffold=transcripts[transcript]['scaffold']
        	strand=transcripts[transcript]['strand']
        	for start in transcripts[transcript]['cds'].keys():
                	end=transcripts[transcript]['cds'][start]['end']
                	frame=transcripts[transcript]['cds'][start]['frame']
                	data=(scaffold,strand,frame,start,start,end,end)
                	cursor.execute(query_for_gene,data)
                	for (gene,) in cursor:
                        	if gene is None:
                                	continue
                        	else:
                                	genes.add(gene)
        	if len(genes) == 1:
                	data=(genes.pop(),transcript)
                	cursor.execute(assign_to_gene,data)
                	cnx.commit()
                	continue
        	cursor.execute(get_gene_name)
        	for (gene,) in cursor:
                	if gene is None:
                        	gene = 1
                	else:
                        	gene += 1
        	if len(genes) > 1:
                	print "transcript "+transcript+" overlaps more than one gene!"
                	#give all of those genes the same id
                	for gene_to_merge in genes:
                        	data=(gene,gene_to_merge)
                        	cursor.execute(reassign_gene,data)
                        	data=(gene,transcript)
                        	cursor.execute(assign_to_gene,data)
                        	cnx.commit()
                	continue
        	if len(genes) < 1:
                	data=(gene,transcript)
                	cursor.execute(assign_to_gene,data)
                	cnx.commit()
	cursor.close()
	cnx.close()
	
#########################################

def retrieve_overlapping_transcripts(transcript,strand,scaffold):

	cnx=mysql.connector.connect(**config.config)
	cursor=cnx.cursor()

	cds_match_query = ("SELECT transcripts.transcript, cds.start, cds.end FROM transcripts "
                "LEFT JOIN clusters ON transcripts.cluster = clusters.cluster "
                "LEFT JOIN cds ON transcripts.transcript = cds.transcript "
                "WHERE clusters.scaffold = %s AND clusters.strand = %s AND transcripts.type = 'complete' "
                "AND cds.frame = %s "
                "AND ((cds.start <= %s AND cds.end >= %s) OR (cds.start <= %s AND cds.end >= %s) OR (cds.start > %s AND cds.end < %s))")
	
	cds_matches={}

        for start in transcript['cds']:
                end=transcript['cds'][start]['end_coord']
                data = (scaffold,strand,transcript['cds'][start]['frame'],start,start,end,end,start,end)
                cursor.execute(cds_match_query,data)
                for (iso_transcript,iso_start,iso_end) in cursor:
                        if iso_transcript not in cds_matches:
                                cds_matches[iso_transcript] = 0
                        if (iso_start == start) and (iso_end == end):
                                cds_matches[iso_transcript] += 1

	exon_match_query = ("SELECT transcripts.transcript, exon_clusters.start, exon_clusters.end FROM transcripts "
                "LEFT JOIN clusters ON transcripts.cluster = clusters.cluster "
                "LEFT JOIN exon_clusters ON transcripts.cluster = exon_clusters.cluster "
                "WHERE clusters.scaffold = %s AND clusters.strand = %s AND transcripts.type = 'complete' "
                "AND ((exon_clusters.start <= %s AND exon_clusters.end >= %s) OR (exon_clusters.start <= %s AND exon_clusters.end >= %s) OR (exon_clusters.start > %s AND exon_clusters.end < %s))")

        exon_matches={}
	
	for start in transcript['exons']:
		end=transcript['exons'][start]
		data = (scaffold,strand,start,start,end,end,start,end)
		cursor.execute(exon_match_query,data)
		for (iso_transcript,iso_start,iso_end) in cursor:
                        if iso_transcript not in exon_matches:
                                exon_matches[iso_transcript] = 0
                        if (iso_start == start) and (iso_end == end):
                                exon_matches[iso_transcript] += 1
	
	return(cds_matches,exon_matches)

	cursor.close()
	cnx.close()


##############################################

def quantify_transcript_overlap(transcript,cds_matches,exon_matches): #calculate the 
	
        cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()

	get_cds_number = ("SELECT COUNT(*) FROM cds WHERE transcript = %s" )

	get_exon_number = ("SELECT COUNT(*) FROM exon_clusters "
                "LEFT JOIN clusters ON exon_clusters.cluster = clusters.cluster "
                "LEFT JOIN transcripts ON clusters.cluster = transcripts.cluster "
                "WHERE transcripts.transcript = %s")

	insert_gene_iso_relation = ("INSERT INTO wb_genes (wb_transcript,isoseq_transcript,wb_gene,wb_coverage_exons,iso_coverage_exons,wb_coverage_cds,iso_coverage_cds) VALUES (%s,%s,%s,%s,%s,%s,%s)")
	
        transcript_cds = len(transcript['cds'].keys())
        transcript_exons = len(transcript['exons'].keys())

        for iso_transcript in cds_matches:
                cursor.execute(get_cds_number,(iso_transcript,))
                for (i,) in cursor:
                        iso_cds = i
                wb_coverage_cds = round(float(cds_matches[iso_transcript])/float(transcript_cds),2)
                iso_coverage_cds = round(float(cds_matches[iso_transcript])/float(iso_cds),2)
                cursor.execute(get_exon_number,(iso_transcript,))
                for (i,) in cursor:
                        iso_exons = i
                wb_coverage_exons = round(float(exon_matches[iso_transcript])/float(transcript_exons),2)
                iso_coverage_exons = round(float(exon_matches[iso_transcript])/float(iso_exons),2)              
                data=(transcript,iso_transcript,gene,wb_coverage_exons,iso_coverage_exons,wb_coverage_cds,iso_coverage_cds)
                cursor.execute(insert_gene_iso_relation,data)
	
        cnx.commit()
	cursor.close()
        cnx.close()
	
###################################################

def identify_splits(relations):

        cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()

	splits = ("SELECT wb_gene FROM (SELECT DISTINCT wb_genes.wb_gene, transcripts.gene FROM wb_genes LEFT JOIN transcripts ON wb_genes.isoseq_transcript = transcripts.transcript) AS temp GROUP BY wb_gene HAVING COUNT(wb_gene) > 1")

	if 'split' not in relations:
		relations['split']={}

	cursor.execute(splits)
	
	for (wb_gene,) in cursor:
		 relations['split'][wb_gene] = ()
	
        cursor.close()
	cnx.close()
	
	return(relations)

#####################################################


def identify_merges(relations):

        cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()

	merges = ("SELECT wb_gene,gene FROM "
	"(SELECT DISTINCT wb_genes.wb_gene, transcripts.gene FROM wb_genes LEFT JOIN transcripts ON wb_genes.isoseq_transcript = transcripts.transcript) t "
	"WHERE gene IN (SELECT gene FROM (SELECT DISTINCT wb_genes.wb_gene, transcripts.gene FROM wb_genes LEFT JOIN transcripts "
	"ON wb_genes.isoseq_transcript = transcripts.transcript) t1 "
	"GROUP BY gene HAVING COUNT(gene) > 1)")

	if 'merge' not in relations:
		relations['merge']={}

	cursor.execute(merges)

	for (wb_gene,gene) in cursor:
		relations['merge'][wb_gene] = gene

        cursor.close()
        cnx.close()

        return(relations)

######################################################

def identify_matches(relations):

        cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()

	matches = ("SELECT wb_gene,wb_transcript,isoseq_transcript,wb_coverage_cds,iso_coverage_cds FROM wb_genes")

	relations['full_match']={}
	relations['part_match']={}
	relations['suggest_alts']={}
	
	cursor.execute(matches)	

	for (wb_gene,wb_transcript,isoseq_transcript,wb_coverage_cds,iso_coverage_cds) in cursor:
        	if (wb_gene in relations['split'] or wb_gene in relations['merge'] or wb_gene in relations['complex']):
                	continue
		if (wb_coverage_cds == 1.0 and iso_coverage_cds == 1.0):
			relations['full_match'][wb_gene]={}
		else:
			relations['part_match'][wb_gene]={}	
	for wb_gene in relations['full_match'].keys():
		if wb_gene in relations['part_match']:
			del relations['full_match'][wb_gene]
			del relations['part_match'][wb_gene]
			relations['suggest_alts'][wb_gene]=()

        cursor.close()
        cnx.close()

        return(relations)

#########################################################

def update_relationships(relations,relation):
	
        cnx=mysql.connector.connect(**config.config)
        cursor=cnx.cursor()

	update_wb_genes = ("UPDATE wb_genes SET relation = %s WHERE wb_gene = %s")

	for wb_gene in relations[relation]:
		data=(relation,wb_gene)
		cursor.execute(update_wb_genes,data)

        cnx.commit()
        cursor.close()
        cnx.close()


#############################################################
	







