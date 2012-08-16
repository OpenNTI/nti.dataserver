#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys

import zope.intid
from zope import component
from ZODB.POSException import POSKeyError
from zope.generations.utility import findObjectsMatching
from zope.generations.utility import findObjectsProviding

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.chat_transcripts import _MeetingTranscriptStorage as MTS

import nti.contentsearch
from nti.contentsearch.common import get_type_name
from nti.contentsearch import get_indexable_types
from nti.contentsearch import interfaces as search_interfaces

def _get_uid(obj):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	result = _ds_intid.getId(obj)
	return result

def _get_sharedWith(obj):
	# from IPython.core.debugger import Tracer;  Tracer()() ## DEBUG ##
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	if adapted and hasattr(adapted, "get_sharedWith"):
		result = adapted.get_sharedWith()
	else:
		result = ()
	return result

def _get_indeaxable_objects(user, users, process_shared=True):
	username = user.username
	
	from IPython.core.debugger import Tracer;  Tracer()() ## DEBUG ##
	rim = search_interfaces.IRepozeEntityIndexManager(user, None)
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		
		# ignore friends lists
		if nti_interfaces.IFriendsList.providedBy(obj):
			continue
		
		yield (rim, obj)
		
		for uname in _get_sharedWith(obj):
			sharing_user = users.get(uname, None)
			if sharing_user and uname != username: 
				srim = search_interfaces.IRepozeEntityIndexManager(sharing_user, None)
				if srim is not None:
					yield (srim, obj)
		
	for mts in findObjectsMatching( user, lambda x: isinstance(x,MTS) ):
		for obj in mts.itervalues():
			type_name = get_type_name(obj)
			if type_name in get_indexable_types():
				yield (rim, obj)			
	
def _index(rim, obj):
	catalog = rim.get_create_catalog(obj)
	if catalog:
		docid = _get_uid(obj)
		catalog.index_doc(docid, obj)
		return True
	return False
			
def _reindex_user_content( username ):
	user = users.User.get_user( username )
	if not user:
		print( "user '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	# remove all catalogs
	rim = search_interfaces.IRepozeEntityIndexManager(user)
	for key in list(rim.keys()):
		rim.pop(key, None)
		
	counter = 0
	for rim, obj in _get_indeaxable_objects(user):
		try:
			_index(rim, obj)
			counter = counter + 1
		except POSKeyError:
			# broken reference for object
			pass

def main():
	if len(sys.argv) < 3:
		print( "Usage %s env_dir username" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = os.path.expanduser(sys.argv[1])
	username = sys.argv[2]
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: _reindex_user_content(username) )

if __name__ == '__main__':
	main()
