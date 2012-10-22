from __future__ import print_function, unicode_literals

generation = 19

from nti.contentsearch.generations._utils import reindex_all
		
def evolve(context):
	"""
	Evolve generation 18 to 19 by reindexing all.
	"""
	reindex_all(context)