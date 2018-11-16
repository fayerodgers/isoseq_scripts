import sys
import re
import pprint
import mysql.connector
import config
import json
import isoseq

print 'Retieving existing clusters.'
clusters=isoseq.retrieve_clusters('all')
#rint(json.dumps(clusters, indent=4))
print 'Retrieving non-clustered reads'
reads=isoseq.retrieve_reads('non_clustered_only')
#print(reads)
print 'Doing initial clustering'
clusters=isoseq.cluster_reads(reads,clusters) #top level clustering
#print(json.dumps(clusters, indent=4))
print 'Extending cluster ends'
clusters=isoseq.extend_ends(clusters)
#print(json.dumps(clusters, indent=4))
print "Collapsing 5' ends"
collapsed_clusters=isoseq.retrieve_clusters('collapsed')
print(json.dumps(collapsed_clusters, indent=4))
collapsed_clusters=isoseq.collapse_ends(clusters,collapsed_clusters) #collapse 5' ends 
#print(json.dumps(collapsed_clusters, indent=4))
