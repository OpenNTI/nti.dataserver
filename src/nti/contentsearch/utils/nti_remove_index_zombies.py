#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys

import zope.intid
from zope import component

from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

import nti.contentsearch
from nti.contentsearch import get_indexable_types
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch import interfaces as search_interfaces

def main():
	if len(sys.argv) < 2:
		print( "Usage %s env_dir *usernames" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = os.path.expanduser(sys.argv[1])
	usernames = sys.argv[2:]
	idx_types = sys.argv[3:]
	if not idx_types:
		content_types = get_indexable_types()
	else:
		content_types = set()
		for tname in idx_types:
			tname = tname.lower()
			if tname in get_indexable_types():
				content_types.append(tname)
		
		if not content_types:
			print("No valid content type(s) were specified")
			sys.exit(2)
			
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: remove_zombies(usernames) )
		

def _get_object(uid):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	result = _ds_intid.queryObject(uid, None)
	return result

def _get_docids_from_catalog_field(catfield):
	if 	isinstance(catfield, CatalogTextIndexNG3) or \
		isinstance(catfield, CatalogFieldIndex) or \
		isinstance(catfield, CatalogKeywordIndex):
		
		return catfield._indexed()
	else:
		return ()
		
def _get_docids_from_rim(rim):
	for catalog in rim.values():
		for catfield in catalog.values():
			yield catalog, _get_docids_from_catalog_field(catfield)
			
def remove_zombies( usernames ):
	
	if not usernames:
		dataserver = component.getUtility( nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout( dataserver ).users_folder
		usernames = _users.iterkeys()
	
	counter = 0
	for username in usernames:
		entity = users.Entity.get_entity( username )
		if entity is None or nti_interfaces.IFriendsList.providedBy(entity):
			continue
		
		rim = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if rim is not None:
			for catalog, docids in _get_docids_from_rim(rim):
				for docid in docids:
					if _get_object(docid) is None:
						catalog.unindex_doc(docid)
						counter = counter + 1
	return counter

if __name__ == '__main__':
	main()
