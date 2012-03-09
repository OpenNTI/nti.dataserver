import logging
logger = logging.getLogger( __name__ )

#import time
#from hashlib import md5

#from contenttypes import empty_search_result
#from contenttypes import empty_suggest_result
#from contenttypes import merge_search_results
#from contenttypes import merge_suggest_results
#from contenttypes import empty_suggest_and_search_result
#from contenttypes import merge_suggest_and_search_results

from zope import interface
from . import interfaces

class RepozeUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username, datastore, use_md5=True):
		self.use_md5 = use_md5
		self.username = username
		self.datastore = datastore

	# -------------------
	
	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'RepozeUserIndexManager(user=%s)' % self.username

	# -------------------
	
	def get_username(self):
		return self.username

	# -------------------

	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			lm = lambda x: x[0:-1] if x.endswith('s') else x
			search_on = [lm(x) for x in search_on]
		return search_on

	def search(self, query, limit=None, search_on=None):
		pass
