from __future__ import print_function, unicode_literals

generation = 14

from evolve12 import do_evolve
from evolve13 import do_remove_user_catalogs

def evolve(context):
	"""
	Evolve generation 13 to 14 by reindexing user content after catalog def were changed
	"""
	users = context.connection.root()['nti.dataserver']['users']
	for user in users.values():
		do_remove_user_catalogs(user)
		
	do_evolve(context)
		
