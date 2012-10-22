from __future__ import print_function, unicode_literals

generation = 12

from nti.contentsearch.generations._utils import reindex_all
						
def evolve(context):
	"""
	Evolve generation 11 to generation 12 by reindexing in the user space
	"""
	reindex_all(context)
		
