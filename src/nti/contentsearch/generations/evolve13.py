from __future__ import print_function, unicode_literals

generation = 13

from nti.contentsearch import interfaces as search_interfaces 

from evolve12 import do_evolve
	
def do_remove_user_catalogs(user):
	rim = search_interfaces.IRepozeEntityIndexManager(user)
	for key in list(rim.keys()):
		rim.pop(key, None)

def evolve(context):
	"""
	Evolve generation 12 to  13 by reindexing user content after catalog def
	were changed
	"""
	users = context.connection.root()['nti.dataserver']['users']
	for user in users.values():
		do_remove_user_catalogs(user)
		
	do_evolve(context)
		
