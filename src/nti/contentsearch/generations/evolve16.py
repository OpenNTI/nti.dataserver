from __future__ import print_function, unicode_literals

generation = 16

from evolve14 import reindex_all

def evolve(context):
	"""
	Evolve generation 15 to 16 by reindexing user content to get new words ids based on the new tokenizer
	"""
	reindex_all(context)
		
