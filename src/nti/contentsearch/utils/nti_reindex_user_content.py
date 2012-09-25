#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys

import zope.intid
from zope import component
from ZODB.POSException import POSKeyError
from zope.generations.utility import findObjectsProviding

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

import nti.contentsearch
from nti.contentsearch.common import get_type_name
from nti.contentsearch import get_indexable_types
from nti.contentsearch import interfaces as search_interfaces

def _get_uid(obj):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	result = _ds_intid.getId(obj)
	return result

def _get_sharedWith(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	if adapted and hasattr(adapted, "get_sharedWith"):
		result = adapted.get_sharedWith()
	else:
		result = ()
	return result

def _get_indeaxable_objects(user, rim=None):
	username = user.username

	indexable_types = get_indexable_types()
	rim = rim or search_interfaces.IRepozeEntityIndexManager(user, None)
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		
		if get_type_name(obj) not in indexable_types:
			continue
		
		yield (rim, obj)
		
		for uname in _get_sharedWith(obj):
			sharing_user = users.Entity.get_entity(uname)
			if sharing_user and uname != username: 
				srim = search_interfaces.IRepozeEntityIndexManager(sharing_user, None)
				if srim is not None:
					yield (srim, obj)
		
def _index(rim, obj):
	catalog = rim.get_create_catalog(obj)
	if catalog:
		docid = _get_uid(obj)
		catalog.index_doc(docid, obj)
		return True
	return False
			
def _reindex_entity_content( username ):
	entity = users.Entity.get_entity( username )
	if not entity:
		print( "user/entity '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	counter = 0
	rim = search_interfaces.IRepozeEntityIndexManager(entity, None)
	if rim is not None:
		# remove all catalogs
		for key in list(rim.keys()):
			rim.pop(key, None)
		
		for eim, obj in _get_indeaxable_objects(entity, rim):
			try:
				if _index(eim, obj):
					counter = counter + 1
			except POSKeyError:
				# broken reference for object
				pass
	
	return counter

def main():
	if len(sys.argv) < 3:
		print( "Usage %s env_dir username" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = os.path.expanduser(sys.argv[1])
	username = sys.argv[2]
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: _reindex_entity_content(username) )

if __name__ == '__main__':
	main()
