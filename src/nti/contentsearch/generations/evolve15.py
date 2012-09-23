from __future__ import print_function, unicode_literals

generation = 15

from evolve14 import reindex_all

def evolve(context):
	"""
	Evolve generation 14 to 15 by reindexing user content to add ngrams
	"""
	reindex_all(context)
		
