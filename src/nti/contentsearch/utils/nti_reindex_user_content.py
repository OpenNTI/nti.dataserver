#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys

from zope import component
from ZODB.POSException import POSKeyError
from zope.generations.utility import findObjectsMatching
from zope.generations.utility import findObjectsProviding

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.oids import toExternalOID

import nti.contentsearch
from nti.contentsearch.common import get_type_name
from nti.contentsearch.interfaces import IRepozeDataStore
from nti.contentsearch.common import indexable_type_names
from nti.contentsearch._repoze_index import create_catalog
from nti.dataserver.chat_transcripts import _MeetingTranscriptStorage as MTS

def main():
	if len(sys.argv) < 3:
		print( "Usage %s env_dir username" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = os.path.expanduser(sys.argv[1])
	username = sys.argv[2]
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: _reindex_user_content(username) )

def indexable_objects(user, indexable_types=indexable_type_names):
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		type_name = get_type_name(obj)
		if type_name and type_name in indexable_types:
			yield type_name, obj
	
	for mts in findObjectsMatching( user, lambda x: isinstance(x,MTS) ):
		for obj in mts.itervalues():
			type_name = get_type_name(obj)
			if type_name and type_name in indexable_types:
				yield type_name, obj
			
def _reindex_user_content( username ):
	user = users.User.get_user( username )
	if not user:
		print( "user '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	# get and register rds
	lsm = component.getSiteManager()
	conn = getattr( lsm, '_p_jar', None )
	search_conn = conn.get_connection( 'Search' )
	rds = search_conn.root()['repoze_datastore']
	lsm.registerUtility( rds, provided=IRepozeDataStore )

	# remove user catalogs
	rds.remove_user(username)

	# recreate catalogs
	for type_name in indexable_type_names:
		catalog = create_catalog(type_name)
		rds.add_catalog(username, catalog, type_name)

	counter = 0
	for type_name, obj in indexable_objects(user):
		catalog = rds.get_catalog(username, type_name)
		try:
			address = toExternalOID(obj)
			docid = rds.get_or_create_docid_for_address(username, address)
			catalog.index_doc(docid, obj)
			counter = counter + 1
		except POSKeyError:
			# broken reference for object
			pass

if __name__ == '__main__':
	main()
