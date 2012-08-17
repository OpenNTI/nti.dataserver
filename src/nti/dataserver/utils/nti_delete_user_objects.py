#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import json
import datetime
from collections import defaultdict

from zope.component import getAdapter
from zope.generations.utility import findObjectsProviding, findObjectsMatching

from nti.dataserver import users
from nti.dataserver.users import Community
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import toExternalObject
from nti.contentsearch.utils.nti_remove_user_content import remove_user_content
from nti.dataserver.chat_transcripts import _DocidMeetingTranscriptStorage as DMTS

def get_object_type(obj):
	result = obj.__class__.__name__
	return result.lower() if result else u''

def get_user_objects(user, object_types=()):
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		type_name = get_object_type(obj)
		if (not object_types or type_name in object_types) and not isinstance(obj, Community):
			yield type_name, obj, obj

	if not object_types or 'transcript' in object_types or 'messageinfo' in object_types:
		for mts in findObjectsMatching( user, lambda x: isinstance(x, DMTS) ):
			adapted = getAdapter(mts, nti_interfaces.ITranscript)
			yield 'messageinfo', adapted, mts

def remove_user_objects( username, object_types=(), export_dir=None ):
	user = users.User.get_user( username )
	if not user:
		print( "User '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	# normalize object types
	object_types = set(map(lambda x: x.lower(), object_types))

	captured_types = defaultdict(list)
	if export_dir:
		export_dir = os.path.expanduser(export_dir)
		if not os.path.exists(export_dir):
			os.makedirs(export_dir)

	counter = 0
	for type_name, adapted, obj in get_user_objects( user, object_types):
		external = toExternalObject(adapted)
		with user.updates():
			_id = getattr(obj, 'id', None )
			containerId = getattr(obj, 'containerId', None )
			if containerId and _id and user.deleteContainedObject( containerId, _id ):
				captured_types[type_name].append(external)
				counter = counter +  1

	if captured_types:
		remove_user_content(username, captured_types.keys())
		if export_dir:
			utc_datetime = datetime.datetime.utcnow()
			s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
			for name, objs in captured_types.items():
				name = "%s-%s-%s.json" % (username, name, s)
				outname = os.path.join(export_dir, name)
				with open(outname, "w") as fp:
					json.dump(objs, fp, indent=4)
	else:
		print( "No objects were removed for user '%s'" % username, file=sys.stderr)

def main():
	if len(sys.argv) < 2:
		print( "Usage %s env_dir username [*types]" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = sys.argv[1]
	username = sys.argv[2]
	object_types = set(sys.argv[3:])
	run_with_dataserver( environment_dir=env_dir, function=lambda: remove_user_objects(username, object_types, env_dir) )

if __name__ == '__main__':
	main()
