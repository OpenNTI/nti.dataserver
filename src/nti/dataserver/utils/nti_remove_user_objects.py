#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import json
import datetime
from collections import defaultdict

from zope.generations.utility import findObjectsProviding

from nti.dataserver import users
from nti.dataserver.mimetype import MIME_BASE
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.contentsearch.utils.nti_remove_user_content import remove_user_content

type_exceptions = (u'friendslist')

def normalize_type_name(x, encode=True):
	result = ''
	if x:
		result =x[0:-1].lower() if x.endswith('s') else x.lower()
	return unicode(result) if encode else result
	
def get_object_type(obj):
	if not isinstance(obj, dict):
		result = obj.__class__.__name__
	elif StandardExternalFields.CLASS in obj:
		result = obj[StandardExternalFields.CLASS]
	elif StandardExternalFields.MIMETYPE in obj:
		result = obj[StandardExternalFields.MIMETYPE]
		if result and result.startswith(MIME_BASE):
			idx = len(MIME_BASE) + 1
			result = result[idx:]
	else:
		result = None
	return normalize_type_name(result) if result else u''


def remove_user_objects( username, object_types=(), export_dir=None ):
	
	user = users.User.get_user( username )
	if not user:
		print( "User '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	captured_types = defaultdict(list)	
	if export_dir:
		export_dir = os.path.expanduser(export_dir)
		if not os.path.exists(export_dir):
			os.makedirs(export_dir)
		
	object_types = set(map(lambda x: normalize_type_name(x), object_types))
	
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		external = toExternalObject(obj)
		type_name = get_object_type(external)
		if 	type_name and type_name not in type_exceptions and \
			(not object_types or type_name in object_types):			

			with user.updates():
				_id = getattr(obj, 'id', None )		
				containerId = getattr(obj, 'containerId', None )
				if containerId and _id and user.deleteContainedObject( containerId, _id ):
						captured_types[type_name].append(external)

	if captured_types:
		remove_user_content(username, captured_types.keys())
		for name, objs in captured_types.items():
			print("%s %s object(s) was/were removed for user '%s'" % (len(objs), name, username), file=sys.stderr )
			if export_dir:
				utc_datetime = datetime.datetime.utcnow()
				s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
				name = "%s-%s-%s.json" % (username, name, s)
				outname = os.path.join(export_dir, name)
				with open(outname, "w") as fp:
					for obj in objs:
						json.dump(obj, fp, indent=4)
						fp.write("\n")
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
